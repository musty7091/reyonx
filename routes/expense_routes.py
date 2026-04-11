from flask import Blueprint, request, redirect, render_template
from database import db
from eskimodels import Expense, Period
from decimal import Decimal

# Bu dosyanın "giderler" (expense) sayfalarından sorumlu olduğunu belirtiyoruz
expense_bp = Blueprint("expense", __name__)

def get_active_period():
    period = Period.query.filter_by(is_active=True).first()
    if not period:
        period = Period(name="1. Dönem")
        db.session.add(period)
        db.session.commit()
    return period

@expense_bp.route("/expenses", methods=["GET", "POST"])
def expenses():
    active_period = get_active_period()
    if request.method == "POST":
        desc = request.form.get("description")
        amt = request.form.get("amount")
        if desc and amt:
            new_exp = Expense(
                description=desc, 
                amount=Decimal(amt), 
                period_id=active_period.id
            )
            db.session.add(new_exp)
            db.session.commit()
        return redirect("/expenses")
    
    all_expenses = Expense.query.filter_by(period_id=active_period.id).order_by(Expense.id.desc()).all()
    return render_template("expenses.html", expenses=all_expenses, active_period=active_period)

@expense_bp.route("/expense/delete/<int:id>")
def delete_expense(id):
    exp = Expense.query.get(id)
    if exp:
        db.session.delete(exp)
        db.session.commit()
    return redirect("/expenses")