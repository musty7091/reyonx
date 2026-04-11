from flask import Blueprint, render_template
from database import db
from eskimodels import Product, Invoice, Sale, Waste, Expense, Period
from decimal import Decimal

# Bu dosyanın ana sayfa ve genel envanter sayfalarından sorumlu olduğunu belirtiyoruz
dashboard_bp = Blueprint("dashboard", __name__)

def get_active_period():
    period = Period.query.filter_by(is_active=True).first()
    if not period:
        period = Period(name="1. Dönem")
        db.session.add(period)
        db.session.commit()
    return period

@dashboard_bp.route("/")
def index():
    active_period = get_active_period()
    products = Product.query.all()
    
    invoices = Invoice.query.filter_by(period_id=active_period.id).all()
    sales = Sale.query.filter_by(period_id=active_period.id).all()
    wastes = Waste.query.filter_by(period_id=active_period.id).all()
    expenses = Expense.query.filter_by(period_id=active_period.id).all()
    
    total_products = len(products)
    
    # Tüm hesaplamalarda kuruş güvenliği (Decimal) kullanıyoruz
    total_stock = sum([p.stock_quantity for p in products if p.stock_quantity], Decimal('0.00'))
    
    # Yatırım tutarını hesaplarken İadeleri düşüyoruz
    alis_toplami = sum([inv.total_amount for inv in invoices if inv.invoice_type == "alis"], Decimal('0.00'))
    iade_toplami = sum([inv.total_amount for inv in invoices if inv.invoice_type == "iade"], Decimal('0.00'))
    total_investment = alis_toplami - iade_toplami
    
    total_revenue = sum([s.total_revenue for s in sales], Decimal('0.00'))
    
    gross_profit = sum([s.total_profit for s in sales], Decimal('0.00'))
    total_waste_cost = sum([w.quantity * w.cost for w in wastes], Decimal('0.00'))
    total_expense_amount = sum([e.amount for e in expenses], Decimal('0.00'))
    
    real_net_profit = gross_profit - total_waste_cost - total_expense_amount
    
    return render_template(
        "index.html",
        active_period=active_period,
        total_products=total_products,
        total_stock=total_stock, 
        total_value=total_investment, 
        total_revenue=total_revenue,
        total_profit=real_net_profit
    )

@dashboard_bp.route("/inventory")
def inventory():
    products = Product.query.filter_by(is_active=True).all()
    return render_template("inventory.html", products=products)