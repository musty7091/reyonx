from flask import Blueprint, render_template, request, redirect
from database import db
from models.invoice import Invoice
from models.supplier import Supplier

invoice_bp = Blueprint("invoice", __name__)

@invoice_bp.route("/invoices", methods=["GET", "POST"])
def invoices():
    if request.method == "POST":
        supplier_id = request.form.get("supplier_id")
        amount = request.form.get("amount")
        
        if supplier_id and amount:
            new_invoice = Invoice(
                supplier_id=supplier_id,
                amount=float(amount)
            )
            db.session.add(new_invoice)
            db.session.commit()
        return redirect("/invoices")

    all_invoices = Invoice.query.all()
    suppliers = Supplier.query.all()
    return render_template("invoices.html", invoices=all_invoices, suppliers=suppliers)