from flask import Blueprint, request, redirect, render_template
from database import db
from models import Expense, Period
from decimal import Decimal

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
    error = None
    
    if request.method == "POST":
        try:
            desc = request.form.get("description")
            amt = request.form.get("amount")
            
            if desc and amt:
                amt = amt.replace(',', '.')
                
                new_exp = Expense(
                    description=desc, 
                    amount=Decimal(amt), 
                    period_id=active_period.id
                )
                db.session.add(new_exp)
                db.session.commit()
            return redirect("/expenses")
        except Exception as e:
            db.session.rollback()
            error = "Gider kaydedilirken bir sorun oluştu."
            print(f"Sistem Hatası: {e}")
    
    page = request.args.get('page', 1, type=int)
    # İptal edilmeyen giderleri listele
    paginated_expenses = Expense.query.filter_by(period_id=active_period.id, is_cancelled=False).order_by(Expense.id.desc()).paginate(page=page, per_page=10, error_out=False)
    
    return render_template(
        "expenses.html", 
        expenses=paginated_expenses.items, 
        pagination=paginated_expenses, 
        active_period=active_period, 
        error=error
    )

@expense_bp.route("/expense/delete/<int:id>")
def delete_expense(id):
    try:
        exp = Expense.query.get(id)
        if exp and not exp.is_cancelled:
            # SİLME YERİNE İPTAL ET
            exp.is_cancelled = True
            db.session.commit()
    except Exception as e:
        db.session.rollback()
    return redirect("/expenses")