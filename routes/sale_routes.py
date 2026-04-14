from flask import Blueprint, request, redirect, render_template
from database import db
from models import Sale, SaleItem, Product, Period
from decimal import Decimal

sale_bp = Blueprint("sale", __name__)

def get_active_period():
    period = Period.query.filter_by(is_active=True).first()
    if not period:
        period = Period(name="1. Dönem")
        db.session.add(period)
        db.session.commit()
    return period

@sale_bp.route("/sales", methods=["GET", "POST"])
def sales():
    active_period = get_active_period()
    error = None
    
    if request.method == "POST":
        try:
            product_ids = request.form.getlist("product_id[]")
            quantities = request.form.getlist("quantity[]")
            unit_prices = request.form.getlist("unit_price[]") # KDV DAHİL SATIŞ FİYATI
            
            if product_ids:
                new_sale = Sale(period_id=active_period.id)
                db.session.add(new_sale)
                db.session.flush()
                
                calc_revenue = Decimal('0.00')
                calc_cost = Decimal('0.00')
                
                for i in range(len(product_ids)):
                    p_id = product_ids[i]
                    qty = Decimal(quantities[i])
                    
                    # Kasadan çekilen KDV DAHİL satış fiyatı
                    u_price_gross = Decimal(unit_prices[i]) 
                    
                    product = Product.query.get(p_id)
                    # Depodaki maliyetimiz arka planda KDV DAHİL hesaplanmıştı
                    cost_gross = Decimal(product.avg_cost) if product and product.avg_cost else Decimal('0.00')
                    
                    line_rev = qty * u_price_gross
                    line_cst = qty * cost_gross
                    line_prf = line_rev - line_cst
                    
                    item = SaleItem(
                        sale_id=new_sale.id, 
                        product_id=p_id, 
                        quantity=qty, 
                        unit_sales_price=u_price_gross, 
                        unit_cost=cost_gross, 
                        line_revenue=line_rev, 
                        line_profit=line_prf
                    )
                    db.session.add(item)
                    
                    calc_revenue += line_rev
                    calc_cost += line_cst
                    
                    if product:
                        if getattr(product, 'stock_quantity', None) is None:
                            product.stock_quantity = Decimal('0.00')
                        product.stock_quantity = Decimal(product.stock_quantity) - qty
                        
                new_sale.total_revenue = calc_revenue
                new_sale.total_cost = calc_cost
                new_sale.total_profit = calc_revenue - calc_cost
                
                # AKTİF DÖNEMİN (PERIOD) KASA TOPLAMLARINA EKLEME YAPIYORUZ
                if active_period.total_revenue is None: active_period.total_revenue = Decimal('0.00')
                if active_period.total_cost is None: active_period.total_cost = Decimal('0.00')
                if active_period.net_profit is None: active_period.net_profit = Decimal('0.00')

                active_period.total_revenue += new_sale.total_revenue
                active_period.total_cost += new_sale.total_cost
                active_period.net_profit += new_sale.total_profit

                db.session.commit()
                return redirect("/sales")
        except Exception as e:
            # Hata yakalandı, sistemi geriye sar!
            db.session.rollback()
            error = "Satış işlenirken bir hata oluştu. Lütfen miktar ve fiyat alanlarını kontrol edin."
            print(f"Sistem Hatası: {e}")
            
    # SAYFALAMA (PAGINATION)
    page = request.args.get('page', 1, type=int)
    
    # error_out=False ile hata vermesini engelliyoruz
    paginated_sales = Sale.query.filter_by(period_id=active_period.id) \
                                .order_by(Sale.id.desc()) \
                                .paginate(page=page, per_page=10, error_out=False)
    
    products = Product.query.filter_by(is_active=True).all()
    
    # Tabloda dönmek için sales'i, alt butonlar için pagination'ı gönderiyoruz
    return render_template(
        "sales.html", 
        sales=paginated_sales.items,  # Sadece o sayfanın 10 adetlik verisi
        pagination=paginated_sales,   # Sayfa numaraları, ileri/geri bilgileri
        products=products, 
        active_period=active_period, 
        error=error
    )

@sale_bp.route("/sale/delete/<int:id>")
def delete_sale(id):
    try:
        sale = Sale.query.get(id)
        if sale:
            # SİLİNEN SATIŞIN TUTARLARINI KASADAN (PERIOD) GERİ DÜŞÜYORUZ
            period = Period.query.get(sale.period_id)
            if period:
                if period.total_revenue is not None:
                    period.total_revenue -= sale.total_revenue
                if period.total_cost is not None:
                    period.total_cost -= sale.total_cost
                if period.net_profit is not None:
                    period.net_profit -= sale.total_profit

            # STOKLARI GERİ EKLİYORUZ
            for item in sale.items:
                product = Product.query.get(item.product_id)
                if product:
                    product.stock_quantity = Decimal(product.stock_quantity) + Decimal(item.quantity)
            
            db.session.delete(sale)
            db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"Silme Hatası: {e}")
    return redirect("/sales")