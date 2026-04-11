from flask import Blueprint, request, redirect, render_template
from database import db
from eskimodels import Product, Supplier

# Bu dosyanın "ürünler" (product) sayfalarından sorumlu olduğunu sisteme söylüyoruz
product_bp = Blueprint("product", __name__)

@product_bp.route("/products", methods=["GET", "POST"])
def products():
    suppliers = Supplier.query.all()
    error = None
    if request.method == "POST":
        barcode = request.form.get("barcode")
        name = request.form.get("name")
        if not barcode or not name:
            error = "Barkod ve ürün adı zorunlu"
        elif Product.query.filter_by(barcode=barcode).first():
            error = "Bu barkod zaten var"
        else:
            p = Product(
                barcode=barcode,
                name=name,
                supplier_id=request.form.get("supplier_id"),
                unit=request.form.get("unit"),
                vat_rate=float(request.form.get("vat_rate", 20.0)),
                is_active=True
            )
            db.session.add(p)
            db.session.commit()
            return redirect("/products")

    page = request.args.get("page", 1, type=int)
    sort = request.args.get("sort", "name")
    query = Product.query
    if sort == "name":
        query = query.order_by(Product.name.asc())
    elif sort == "new":
        query = query.order_by(Product.id.desc())
    data = query.paginate(page=page, per_page=10)

    return render_template(
        "products.html",
        products=data.items,
        pagination=data,
        suppliers=suppliers,
        error=error,
        sort=sort
    )

@product_bp.route("/product/delete/<int:id>")
def delete_product(id):
    p = Product.query.get(id)
    if p:
        db.session.delete(p)
        db.session.commit()
    return redirect("/products")

@product_bp.route("/product/toggle/<int:id>")
def toggle_product(id):
    p = Product.query.get(id)
    if p:
        p.is_active = not p.is_active
        db.session.commit()
    return redirect("/products")

@product_bp.route("/product/edit/<int:id>", methods=["GET", "POST"])
def edit_product(id):
    p = Product.query.get(id)
    suppliers = Supplier.query.all()
    if request.method == "POST":
        barcode = request.form.get("barcode")
        existing = Product.query.filter(Product.barcode == barcode, Product.id != id).first()
        if existing:
            return "Bu barkod başka üründe var"
        p.barcode = barcode
        p.name = request.form.get("name")
        p.supplier_id = request.form.get("supplier_id")
        p.unit = request.form.get("unit")
        p.vat_rate = float(request.form.get("vat_rate", 20.0))
        db.session.commit()
        return redirect("/products")
    return render_template("product_edit.html", product=p, suppliers=suppliers)