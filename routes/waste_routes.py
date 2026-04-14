from flask import Blueprint, request, redirect, render_template
from database import db
from models import Waste, Product, InvoiceItem, Invoice, Period
from decimal import Decimal

waste_bp = Blueprint("waste", __name__)

def get_active_period():
    period = Period.query.filter_by(is_active=True).first()
    if not period:
        period = Period(name="1. Dönem")
        db.session.add(period)
        db.session.commit()
    return period

@waste_bp.route("/wastes", methods=["GET", "POST"])
def wastes():
    active_period = get_active_period()
    error = None
    
    if request.method == "POST":
        try:
            product_id = request.form.get("product_id")
            quantity = request.form.get("quantity")
            reason = request.form.get("reason")
            
            if product_id and quantity:
                quantity = quantity.replace(',', '.')
                
                product = Product.query.get(product_id)
                qty_dec = Decimal(quantity)
                
                last_invoice_item = InvoiceItem.query.join(Invoice).filter(
                    InvoiceItem.product_id == product_id,
                    Invoice.invoice_type == "alis",
                    Invoice.is_cancelled == False
                ).order_by(Invoice.date.desc()).first()
                
                if last_invoice_item and Decimal(last_invoice_item.quantity) > Decimal('0'):
                    cost_at_waste = Decimal(last_invoice_item.line_total) / Decimal(last_invoice_item.quantity)
                else:
                    cost_at_waste = Decimal(product.avg_cost) if product and product.avg_cost else Decimal('0.00')
                
                new_waste = Waste(
                    product_id=product_id, 
                    period_id=active_period.id,
                    quantity=qty_dec, 
                    cost=cost_at_waste, 
                    reason=reason
                )
                db.session.add(new_waste)
                
                if product:
                    if getattr(product, 'stock_quantity', None) is None:
                        product.stock_quantity = Decimal('0.00')
                    product.stock_quantity = Decimal(product.stock_quantity) - qty_dec
                    
                db.session.commit()
            return redirect("/wastes")
        except Exception as e:
            db.session.rollback()
            error = "Fire kaydedilirken bir sorun oluştu."
            print(f"Sistem Hatası: {e}")

    page = request.args.get('page', 1, type=int)
    # İptal edilenleri gösterme
    paginated_wastes = Waste.query.filter_by(period_id=active_period.id, is_cancelled=False).order_by(Waste.id.desc()).paginate(page=page, per_page=10, error_out=False)
    
    products = Product.query.filter_by(is_active=True).all()
    
    return render_template(
        "wastes.html", 
        wastes=paginated_wastes.items, 
        pagination=paginated_wastes, 
        products=products, 
        active_period=active_period, 
        error=error
    )

@waste_bp.route("/waste/delete/<int:id>")
def delete_waste(id):
    try:
        waste = Waste.query.get(id)
        if waste and not waste.is_cancelled:
            product = Product.query.get(waste.product_id)
            if product:
                product.stock_quantity = Decimal(product.stock_quantity) + Decimal(waste.quantity)
            
            # SİLME YERİNE İPTAL
            waste.is_cancelled = True
            db.session.commit()
    except Exception as e:
        db.session.rollback()
    return redirect("/wastes")