from flask import Blueprint, render_template, request, redirect, current_app
from database import db
from eskimodels import Sale, Waste, Expense, Period
from datetime import datetime
from decimal import Decimal

# Bu dosyanın raporlama ve dönem işlemlerinden sorumlu olduğunu belirtiyoruz
report_bp = Blueprint("report", __name__)

def get_active_period():
    period = Period.query.filter_by(is_active=True).first()
    if not period:
        period = Period(name="1. Dönem")
        db.session.add(period)
        db.session.commit()
    return period

@report_bp.route("/report")
def report():
    active_period = get_active_period()
    sales = Sale.query.filter_by(period_id=active_period.id).all()
    wastes = Waste.query.filter_by(period_id=active_period.id).all()
    expenses = Expense.query.filter_by(period_id=active_period.id).all()

    total_revenue = sum([s.total_revenue for s in sales], Decimal('0.00'))
    total_cost = sum([s.total_cost for s in sales], Decimal('0.00'))
    gross_profit = total_revenue - total_cost

    total_waste_cost = sum([w.quantity * w.cost for w in wastes], Decimal('0.00'))
    total_expenses = sum([e.amount for e in expenses], Decimal('0.00'))

    net_profit = gross_profit - total_waste_cost - total_expenses
    
    # Prim oranını config dosyasından çekip Decimal formata çeviriyoruz
    bonus_rate = Decimal(str(current_app.config.get("BONUS_RATE", 0.05)))
    bonus = (net_profit * bonus_rate) if net_profit > Decimal('0') else Decimal('0.00')

    return render_template(
        "profit_report.html",
        active_period=active_period,
        total_revenue=total_revenue,
        total_cost=total_cost,
        gross_profit=gross_profit,
        total_waste_cost=total_waste_cost,
        total_expenses=total_expenses,
        net_profit=net_profit,
        bonus=bonus,
        wastes=wastes
    )

@report_bp.route("/period/close", methods=["POST"])
def close_period():
    active_period = get_active_period()
    
    sales = Sale.query.filter_by(period_id=active_period.id).all()
    wastes = Waste.query.filter_by(period_id=active_period.id).all()
    expenses = Expense.query.filter_by(period_id=active_period.id).all()

    t_rev = sum([s.total_revenue for s in sales], Decimal('0.00'))
    t_cost = sum([s.total_cost for s in sales], Decimal('0.00'))
    t_waste = sum([w.quantity * w.cost for w in wastes], Decimal('0.00'))
    t_exp = sum([e.amount for e in expenses], Decimal('0.00'))
    n_prof = (t_rev - t_cost) - t_waste - t_exp

    active_period.total_revenue = t_rev
    active_period.total_cost = t_cost
    active_period.total_waste_cost = t_waste
    active_period.total_expenses = t_exp
    active_period.net_profit = n_prof
    active_period.end_date = datetime.utcnow()
    active_period.is_active = False 

    new_name = request.form.get("new_period_name", "Yeni Dönem")
    new_period = Period(name=new_name)
    db.session.add(new_period)
    db.session.commit()

    return redirect("/periods")

@report_bp.route("/periods")
def periods():
    all_periods = Period.query.order_by(Period.id.desc()).all()
    return render_template("periods.html", periods=all_periods)