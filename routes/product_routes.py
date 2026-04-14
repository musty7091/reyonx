from flask import Blueprint, request, redirect, render_template, flash
from database import db
from models import Product, Supplier
from utils.audit import log_action
from decimal import Decimal, InvalidOperation

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
            try:
                purchase_price = Decimal(request.form.get("purchase_price", "0"))
                price = Decimal(request.form.get("sale_price", "0"))
                stock_quantity = Decimal(request.form.get("stock_quantity", "0"))
                vat_rate = Decimal(request.form.get("vat_rate", "20"))

            except InvalidOperation:
                error = "Sayısal alanlarda geçersiz değer var"

                page = request.args.get("page", 1, type=int)
                sort = request.args.get("sort", "name")

                query = Product.query
                if sort == "name":
                    query = query.order_by(Product.name.asc())
                elif sort == "new":
                    query = query.order_by(Product.id.desc())

                data = query.paginate(page=page, per_page=10, error_out=False)

                return render_template(
                    "products.html",
                    products=data.items,
                    pagination=data,
                    suppliers=suppliers,
                    error=error,
                    sort=sort
                )

            p = Product(
                barcode=barcode,
                name=name,
                supplier_id=request.form.get("supplier_id") or None,
                category=request.form.get("category", "Genel"),
                unit=request.form.get("unit", "Adet"),
                vat_rate=vat_rate,
                purchase_price=purchase_price,
                price=price,
                stock_quantity=stock_quantity,
                is_active=True
            )

            db.session.add(p)
            db.session.commit()

            log_action("CREATE", "Product", p.id, "Yeni ürün eklendi")

            return redirect("/products")

    page = request.args.get("page", 1, type=int)
    sort = request.args.get("sort", "name")
    
    query = Product.query
    if sort == "name":
        query = query.order_by(Product.name.asc())
    elif sort == "new":
        query = query.order_by(Product.id.desc())
        
    data = query.paginate(page=page, per_page=10, error_out=False)

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
        try:
            db.session.delete(p)
            db.session.commit()
        except Exception as e:
            # Sistem çökmesin diye işlemi geri alıyoruz
            db.session.rollback()
            # Kullanıcıya hata mesajı gösteriyoruz
            flash("Bu ürün geçmiş satışlarda veya faturalarda kullanıldığı için tamamen silinemez! Bunun yerine pasife almayı deneyin.", "danger")
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
        
        try:
            p.purchase_price = Decimal(request.form.get("purchase_price", "0"))
            p.price = Decimal(request.form.get("sale_price", "0"))
            p.stock_quantity = Decimal(request.form.get("stock_quantity", "0"))
            p.vat_rate = Decimal(request.form.get("vat_rate", "20"))
        except InvalidOperation:
            return "Sayısal alanlarda hata var"

        p.barcode = barcode
        p.name = request.form.get("name")
        p.supplier_id = request.form.get("supplier_id") or None
        p.category = request.form.get("category", "Genel")
        p.unit = request.form.get("unit")
        
        db.session.commit()
        return redirect("/products")
        
    return render_template("product_edit.html", product=p, suppliers=suppliers)