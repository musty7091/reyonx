from flask import Blueprint, request, redirect, render_template
from database import db
from models import Invoice, InvoiceItem, Product, Supplier, Period
from decimal import Decimal
from datetime import datetime

invoice_bp = Blueprint("invoice", __name__)

def get_active_period():
    period = Period.query.filter_by(is_active=True).first()
    if not period:
        period = Period(name="1. Dönem")
        db.session.add(period)
        db.session.commit()
    return period

@invoice_bp.route("/invoices", methods=["GET", "POST"])
def invoices():
    active_period = get_active_period()
    error = None

    if request.method == "POST":
        try:
            s_id = request.form.get("supplier_id")
            invoice_no = request.form.get("invoice_no") 
            invoice_type = request.form.get("invoice_type", "alis") 
            invoice_date_str = request.form.get("invoice_date") 
            
            product_ids = request.form.getlist("product_id[]")
            quantities = request.form.getlist("quantity[]")
            unit_prices = request.form.getlist("unit_price[]") # KULLANICI BURAYA KDV HARİÇ GİRER
            
            if s_id and product_ids:
                new_inv = Invoice(supplier_id=s_id, period_id=active_period.id, invoice_no=invoice_no, invoice_type=invoice_type)
                
                if invoice_date_str:
                    try:
                        new_inv.date = datetime.strptime(invoice_date_str, "%Y-%m-%d")
                    except ValueError:
                        pass
                
                db.session.add(new_inv)
                db.session.flush() 
                
                calc_net = Decimal('0.00')
                calc_vat = Decimal('0.00')
                calc_gross = Decimal('0.00')
                
                for i in range(len(product_ids)):
                    p_id = product_ids[i]
                    qty = Decimal(quantities[i])
                    net_unit = Decimal(unit_prices[i]) 
                    
                    product = Product.query.get(p_id)
                    v_rate = Decimal(product.vat_rate) if product else Decimal('20.00')
                    calc_v_rate = Decimal('0.00') if v_rate == Decimal('-1') else v_rate
                    
                    gross_unit = net_unit * (Decimal('1') + (calc_v_rate / Decimal('100')))
                    
                    line_net = net_unit * qty
                    line_gross = gross_unit * qty
                    line_vat = line_gross - line_net
                    
                    item = InvoiceItem(
                        invoice_id=new_inv.id,
                        product_id=p_id,
                        quantity=qty,
                        unit_price=net_unit,
                        vat_rate=v_rate,
                        vat_amount=line_vat,
                        net_total=line_net,
                        line_total=line_gross
                    )
                    db.session.add(item)
                    
                    calc_net += line_net
                    calc_vat += line_vat
                    calc_gross += line_gross
                    
                    if product:
                        if getattr(product, 'stock_quantity', None) is None:
                            product.stock_quantity = Decimal('0.00')
                            
                        old_stock = Decimal(product.stock_quantity)
                        old_cost = Decimal(product.avg_cost) if product.avg_cost else Decimal('0.00')
                        
                        if new_inv.invoice_type == "alis":
                            new_stock = old_stock + qty
                            if new_stock > Decimal('0'):
                                product.avg_cost = ((old_stock * old_cost) + (qty * gross_unit)) / new_stock
                        else:
                            new_stock = old_stock - qty 
                            
                        product.stock_quantity = new_stock
                
                new_inv.total_net = calc_net
                new_inv.total_vat = calc_vat
                new_inv.total_amount = calc_gross 
                db.session.commit()
                return redirect("/invoices")
        except Exception as e:
            # Hata yakalandı, sistemi geriye sar!
            db.session.rollback()
            error = "Fatura işlenirken bir hata oluştu. Lütfen boş alan bırakmadığınızdan emin olun."
            print(f"Sistem Hatası: {e}")
    
    # SAYFALAMA (PAGINATION) İŞLEMİ
    page = request.args.get('page', 1, type=int)
    paginated_invoices = Invoice.query.filter_by(period_id=active_period.id).order_by(Invoice.date.desc()).paginate(page=page, per_page=10, error_out=False)
    
    suppliers = Supplier.query.all()
    products = Product.query.all()
    
    return render_template(
        "invoices.html", 
        invoices=paginated_invoices.items, 
        pagination=paginated_invoices, 
        suppliers=suppliers, 
        products=products, 
        active_period=active_period, 
        error=error
    )

@invoice_bp.route("/invoice/<int:id>", methods=["GET", "POST"])
def invoice_detail(id):
    inv = Invoice.query.get_or_404(id)
    products = Product.query.all()
    error = None
    
    if request.method == "POST":
        try:
            p_id = request.form.get("product_id")
            qty = Decimal(request.form.get("quantity"))
            net_unit = Decimal(request.form.get("unit_price")) 
            
            product = Product.query.get(p_id)
            v_rate = Decimal(product.vat_rate) if product else Decimal('20.00')
            calc_v_rate = Decimal('0.00') if v_rate == Decimal('-1') else v_rate
            
            gross_unit = net_unit * (Decimal('1') + (calc_v_rate / Decimal('100')))
                
            line_net = net_unit * qty
            line_gross = gross_unit * qty
            line_vat = line_gross - line_net
            
            item = InvoiceItem(
                invoice_id=id,
                product_id=p_id,
                quantity=qty,
                unit_price=net_unit,
                vat_rate=v_rate,
                vat_amount=line_vat,
                net_total=line_net,
                line_total=line_gross
            )
            db.session.add(item)
            
            if product:
                if getattr(product, 'stock_quantity', None) is None:
                    product.stock_quantity = Decimal('0.00')
                
                old_stock = Decimal(product.stock_quantity)
                old_cost = Decimal(product.avg_cost) if product.avg_cost else Decimal('0.00')
                
                if inv.invoice_type == "alis":
                    new_stock = old_stock + qty
                    if new_stock > Decimal('0'):
                        product.avg_cost = ((old_stock * old_cost) + (qty * gross_unit)) / new_stock
                else:
                    new_stock = old_stock - qty
                    
                product.stock_quantity = new_stock
            
            inv.total_net = Decimal(inv.total_net) + line_net
            inv.total_vat = Decimal(inv.total_vat) + line_vat
            inv.total_amount = Decimal(inv.total_amount) + line_gross
            db.session.commit()
            return redirect(f"/invoice/{id}")
        except Exception as e:
            db.session.rollback()
            error = "Ürün eklenirken bir hata oluştu. Miktar veya fiyat kısmını kontrol edin."
            print(f"Sistem Hatası: {e}")
            
    return render_template("invoice_detail.html", invoice=inv, products=products, error=error)

@invoice_bp.route("/invoice/item/delete/<int:item_id>")
def delete_invoice_item(item_id):
    try:
        item = InvoiceItem.query.get(item_id)
        if item:
            inv_id = item.invoice_id
            inv = item.invoice
            product = Product.query.get(item.product_id)
            
            if product:
                if inv.invoice_type == "alis":
                    product.stock_quantity = Decimal(product.stock_quantity) - Decimal(item.quantity)
                else:
                    product.stock_quantity = Decimal(product.stock_quantity) + Decimal(item.quantity)
            
            inv.total_net = Decimal(inv.total_net) - Decimal(item.net_total)
            inv.total_vat = Decimal(inv.total_vat) - Decimal(item.vat_amount)
            inv.total_amount = Decimal(inv.total_amount) - Decimal(item.line_total)
            
            db.session.delete(item)
            db.session.commit()
            return redirect(f"/invoice/{inv_id}")
    except Exception as e:
        db.session.rollback()
    return redirect("/invoices")

@invoice_bp.route("/invoice/delete/<int:id>")
def delete_invoice(id):
    try:
        inv = Invoice.query.get(id)
        if inv:
            for item in inv.items:
                product = Product.query.get(item.product_id)
                if product:
                    if inv.invoice_type == "alis":
                        product.stock_quantity = Decimal(product.stock_quantity) - Decimal(item.quantity)
                    else:
                        product.stock_quantity = Decimal(product.stock_quantity) + Decimal(item.quantity)
            db.session.delete(inv)
            db.session.commit()
    except Exception as e:
        db.session.rollback()
    return redirect("/invoices")