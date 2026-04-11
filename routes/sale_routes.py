from flask import Blueprint, request, redirect, render_template
from database import db
from eskimodels import Sale, SaleItem, Product, Period
from decimal import Decimal

# Bu dosyanın "satış" (sale) sayfalarından sorumlu olduğunu belirtiyoruz
sale_bp = Blueprint("sale", __name__)

# Yardımcı Fonksiyon: İşlemlerin hangi döneme kaydedileceğini bulur
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
    if request.method == "POST":
        product_ids = request.form.getlist("product_id[]")
        quantities = request.form.getlist("quantity[]")
        unit_prices = request.form.getlist("unit_price[]") 
        
        if product_ids:
            new_sale = Sale(period_id=active_period.id)
            db.session.add(new_sale)
            db.session.flush()
            
            # Kâr, Zarar ve Maliyet hesaplamaları için kuruş kumbaramızı sıfırlıyoruz
            calc_revenue = Decimal('0.00')
            calc_cost = Decimal('0.00')
            
            for i in range(len(product_ids)):
                p_id = product_ids[i]
                qty = Decimal(quantities[i])
                u_price_net = Decimal(unit_prices[i]) 
                
                product = Product.query.get(p_id)
                cost = Decimal(product.avg_cost) if product and product.avg_cost else Decimal('0.00')
                
                line_rev_net = qty * u_price_net
                line_cst = qty * cost
                line_prf = line_rev_net - line_cst
                
                item = SaleItem(
                    sale_id=new_sale.id, 
                    product_id=p_id, 
                    quantity=qty, 
                    unit_sales_price=u_price_net, 
                    unit_cost=cost, 
                    line_revenue=line_rev_net, 
                    line_profit=line_prf
                )
                db.session.add(item)
                
                calc_revenue += line_rev_net
                calc_cost += line_cst
                
                if product:
                    # Ürün stoktan düşülürken de ondalıklı sayı güvenliğini alıyoruz
                    if getattr(product, 'stock_quantity', None) is None:
                        product.stock_quantity = Decimal('0.00')
                    product.stock_quantity = Decimal(product.stock_quantity) - qty
                    
            new_sale.total_revenue = calc_revenue
            new_sale.total_cost = calc_cost
            new_sale.total_profit = calc_revenue - calc_cost
            db.session.commit()
            return redirect("/sales")
            
    all_sales = Sale.query.filter_by(period_id=active_period.id).order_by(Sale.id.desc()).all()
    products = Product.query.filter_by(is_active=True).all()
    return render_template("sales.html", sales=all_sales, products=products, active_period=active_period)

@sale_bp.route("/sale/delete/<int:id>")
def delete_sale(id):
    sale = Sale.query.get(id)
    if sale:
        # Bir satışı yanlışlıkla girdiysek ve silersek, içindeki ürünler depoya aynen geri döner
        for item in sale.items:
            product = Product.query.get(item.product_id)
            if product:
                product.stock_quantity = Decimal(product.stock_quantity) + Decimal(item.quantity)
        db.session.delete(sale)
        db.session.commit()
    return redirect("/sales")