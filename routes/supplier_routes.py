from flask import Blueprint, request, redirect, render_template
from database import db
from models import Supplier, Invoice, Payment
from decimal import Decimal

supplier_bp = Blueprint("supplier", __name__)

@supplier_bp.route("/suppliers", methods=["GET", "POST"])
def suppliers():
    if request.method == "POST":
        s = Supplier(
            name=request.form.get("name"),
            contact_person=request.form.get("contact"),
            phone=request.form.get("phone")
        )
        db.session.add(s)
        db.session.commit()
        return redirect("/suppliers")
    
    suppliers_data = []
    for s in Supplier.query.all():
        # İptal edilen faturaları hesaba dahil etmiyoruz
        alis_invoices = sum([inv.total_amount for inv in Invoice.query.filter_by(supplier_id=s.id, invoice_type="alis", is_cancelled=False).all()]) or Decimal('0.00')
        iade_invoices = sum([inv.total_amount for inv in Invoice.query.filter_by(supplier_id=s.id, invoice_type="iade", is_cancelled=False).all()]) or Decimal('0.00')
        total_payments = sum([pay.amount for pay in Payment.query.filter_by(supplier_id=s.id, is_cancelled=False).all()]) or Decimal('0.00')
        
        balance = alis_invoices - iade_invoices - total_payments 
        suppliers_data.append({"supplier": s, "balance": balance})
        
    return render_template("suppliers.html", suppliers_data=suppliers_data)

@supplier_bp.route("/supplier/<int:id>", methods=["GET", "POST"])
def supplier_detail(id):
    supplier = Supplier.query.get_or_404(id)
    
    if request.method == "POST":
        amount = request.form.get("amount")
        desc = request.form.get("description")
        
        if amount:
            amount = amount.replace(',', '.')
            payment = Payment(supplier_id=id, amount=Decimal(amount), description=desc)
            db.session.add(payment)
            db.session.commit()
            return redirect(f"/supplier/{id}")

    transactions = []
    # İptal edilen işlemleri ekrana yansıtmıyoruz
    invoices = Invoice.query.filter_by(supplier_id=id, is_cancelled=False).all()
    payments = Payment.query.filter_by(supplier_id=id, is_cancelled=False).all()
    
    for inv in invoices:
        if inv.invoice_type == "alis":
            transactions.append({
                "date": inv.date,
                "type": "Alış Faturası",
                "desc": f"Fatura No: {inv.invoice_no if inv.invoice_no else inv.id}", 
                "debt": inv.total_amount, 
                "credit": Decimal('0.00')
            })
        else: 
            transactions.append({
                "date": inv.date,
                "type": "İade Faturası",
                "desc": f"İade Fatura No: {inv.invoice_no if inv.invoice_no else inv.id}", 
                "debt": Decimal('0.00'), 
                "credit": inv.total_amount 
            })
        
    for pay in payments:
        transactions.append({
            "date": pay.date,
            "type": "Ödeme Yapıldı",
            "desc": pay.description,
            "debt": Decimal('0.00'),
            "credit": pay.amount 
        })
        
    transactions.sort(key=lambda x: x["date"])
    
    running_balance = Decimal('0.00')
    for t in transactions:
        running_balance += (t["debt"] - t["credit"])
        t["balance"] = running_balance
        
    transactions.reverse()
        
    return render_template("supplier_detail.html", supplier=supplier, transactions=transactions, current_balance=running_balance)