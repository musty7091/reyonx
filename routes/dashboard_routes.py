from flask import Blueprint, render_template
from database import db
from models import Product, Invoice, Sale, Waste, Expense, Period, Payment, SaleItem
from decimal import Decimal
from flask import session, redirect, url_for
from flask import request

dashboard_bp = Blueprint("dashboard", __name__)

def login_required():
    if "user_id" not in session:
        return False
    return True

def get_active_period():
    period = Period.query.filter_by(is_active=True).first()
    if not period:
        period = Period(name="1. Dönem")
        db.session.add(period)
        db.session.commit()
    return period

@dashboard_bp.route("/")
def index():

    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    active_period = get_active_period()
    products = Product.query.all()
    
    # İptal edilen kayıtları analizden çıkarıyoruz (is_cancelled=False)
    invoices = Invoice.query.filter_by(period_id=active_period.id, is_cancelled=False).all()
    sales = Sale.query.filter_by(period_id=active_period.id, is_cancelled=False).all()
    wastes = Waste.query.filter_by(period_id=active_period.id, is_cancelled=False).all()
    expenses = Expense.query.filter_by(period_id=active_period.id, is_cancelled=False).all()
    
    total_products = len(products)
    
    total_stock_count = sum([p.stock_quantity for p in products if p.stock_quantity], Decimal('0.00'))
    
    total_investment = sum([
        p.stock_quantity * (p.avg_cost or Decimal('0.00'))
        for p in products
        if p.stock_quantity and p.stock_quantity > Decimal('0')
    ], Decimal('0.00'))
    
    total_revenue = sum([s.total_revenue for s in sales], Decimal('0.00'))
    total_cost = sum([s.total_cost for s in sales], Decimal('0.00'))
    
    gross_profit = sum([s.total_profit for s in sales], Decimal('0.00'))
    total_waste_cost = sum([w.quantity * w.cost for w in wastes], Decimal('0.00'))
    total_expense_amount = sum([e.amount for e in expenses], Decimal('0.00'))
    
    real_net_profit = gross_profit - total_waste_cost - total_expense_amount
    
    chart_data = {
        "maliyet": float(total_cost),
        "giderler": float(total_waste_cost + total_expense_amount),
        "net_kar": float(real_net_profit if real_net_profit > 0 else 0)
    }

    all_invoices = Invoice.query.filter_by(is_cancelled=False).all()
    all_payments = Payment.query.filter_by(is_cancelled=False).all()

    total_alis_all = sum([
        inv.total_amount for inv in all_invoices
        if inv.invoice_type == "alis"
    ], Decimal('0.00'))

    total_iade_all = sum([
        inv.total_amount for inv in all_invoices
        if inv.invoice_type == "iade"
    ], Decimal('0.00'))

    total_paid_all = sum([pay.amount for pay in all_payments], Decimal('0.00'))

    total_debt = total_alis_all - total_iade_all - total_paid_all

    critical_stocks = [
        p for p in products
        if p.stock_quantity is not None and p.stock_quantity <= Decimal('10.00')
    ]
    critical_stocks.sort(key=lambda x: x.stock_quantity)

    # İptal edilmeyen satışlardan en çok satılanları bulma
    top_products = db.session.query(
        Product.name,
        db.func.sum(SaleItem.quantity).label('total_sold')
    ).join(SaleItem).join(Sale).filter(Sale.is_cancelled == False).group_by(Product.id).order_by(
        db.func.sum(SaleItem.quantity).desc()
    ).limit(5).all()

    recent_activities = []
    
    # Sadece iptal edilmeyen işlemleri recent activity listesine al
    for s in Sale.query.filter_by(is_cancelled=False).order_by(Sale.id.desc()).limit(5).all():
        recent_activities.append({"date": s.date, "desc": "Satış Yüklendi", "amount": s.total_revenue, "color": "success", "icon": "🛒"})
        
    for inv in Invoice.query.filter_by(is_cancelled=False).order_by(Invoice.id.desc()).limit(5).all():
        if inv.invoice_type == 'alis':
            recent_activities.append({"date": inv.date, "desc": f"Mal Alındı ({inv.supplier.name})", "amount": inv.total_amount, "color": "danger", "icon": "📥"})
        else:
            recent_activities.append({"date": inv.date, "desc": f"Mal İade ({inv.supplier.name})", "amount": inv.total_amount, "color": "warning", "icon": "📤"})
            
    for e in Expense.query.filter_by(is_cancelled=False).order_by(Expense.id.desc()).limit(5).all():
        recent_activities.append({"date": e.date, "desc": f"Gider: {e.description}", "amount": e.amount, "color": "danger", "icon": "💸"})
        
    for p in Payment.query.filter_by(is_cancelled=False).order_by(Payment.id.desc()).limit(5).all():
        recent_activities.append({"date": p.date, "desc": f"Ödeme: {p.supplier.name}", "amount": p.amount, "color": "success", "icon": "💳"})

    recent_activities.sort(key=lambda x: x["date"], reverse=True)
    recent_activities = recent_activities[:6]

    return render_template(
        "index.html",
        active_period=active_period,
        total_products=total_products,
        total_stock=total_stock_count, 
        total_value=total_investment, 
        total_revenue=total_revenue,
        total_profit=real_net_profit,
        chart_data=chart_data,
        total_debt=total_debt,
        critical_stocks=critical_stocks[:6],
        top_products=top_products,
        recent_activities=recent_activities
    )

@dashboard_bp.route("/inventory")
def inventory():

    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    page = request.args.get("page", 1, type=int)

    data = Product.query.filter_by(is_active=True).order_by(Product.name.asc()).paginate(
        page=page,
        per_page=10,
        error_out=False
    )

    return render_template(
        "inventory.html",
        products=data.items,
        pagination=data
    )