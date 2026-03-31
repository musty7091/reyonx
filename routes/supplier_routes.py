from flask import Blueprint, render_template, request, redirect
from database import db
from models.supplier import Supplier

supplier_bp = Blueprint("supplier", __name__)

@supplier_bp.route("/suppliers", methods=["GET", "POST"])
def suppliers():
    if request.method == "POST":
        name = request.form.get("name")
        contact = request.form.get("contact")
        phone = request.form.get("phone")

        if name:
            s = Supplier(
                name=name,
                contact_person=contact,
                phone=phone
            )
            db.session.add(s)
            db.session.commit()

        return redirect("/suppliers")

    data = Supplier.query.all()
    return render_template("suppliers.html", suppliers=data)