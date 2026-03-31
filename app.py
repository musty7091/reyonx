from flask import Flask, request, redirect, render_template
from flask_sqlalchemy import SQLAlchemy
from decimal import Decimal
from flask import session


db = SQLAlchemy()

app = Flask(__name__)

app.config["SECRET_KEY"] = "secret"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///reyonx.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)


# =========================
# MODELS
# =========================

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    barcode = db.Column(db.String(100), unique=True, nullable=False)
    name = db.Column(db.String(150), nullable=False)

    supplier_id = db.Column(db.Integer, db.ForeignKey("supplier.id"))
    supplier = db.relationship("Supplier")

    unit = db.Column(db.String(20))  # adet / kg

    is_active = db.Column(db.Boolean, default=True)  # 🔥 pasif/aktif


class Supplier(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    contact_person = db.Column(db.String(150))
    phone = db.Column(db.String(50))

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)


# =========================
# ROUTES - PRODUCT
# =========================
@app.before_request
def check_login():
    allowed_routes = ["login", "static"]

    if request.endpoint not in allowed_routes and "user_id" not in session:
        return redirect("/login")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        user = User.query.filter_by(username=username).first()

        if user and user.password == password:
            session["user_id"] = user.id
            return redirect("/")

        return "Hatalı giriş"

    return render_template("login.html")

@app.route("/products", methods=["GET", "POST"])
def products():
    suppliers = Supplier.query.all()

    error = None

    if request.method == "POST":
        barcode = request.form.get("barcode")
        name = request.form.get("name")
        supplier_id = request.form.get("supplier_id")
        unit = request.form.get("unit")

        # 🔥 VALIDATION
        if not barcode or not name:
            error = "Barkod ve ürün adı zorunlu"

        # 🔥 DUPLICATE KONTROL
        elif Product.query.filter_by(barcode=barcode).first():
            error = "Bu barkod zaten kayıtlı"

        else:
            p = Product(
                barcode=barcode,
                name=name,
                supplier_id=supplier_id,
                unit=unit,
                is_active=True
            )
            db.session.add(p)
            db.session.commit()
            return redirect("/products")

    data = Product.query.all()

    return render_template(
        "products.html",
        products=data,
        suppliers=suppliers,
        error=error
    )

@app.route("/product/toggle/<int:id>")
def toggle_product(id):
    p = Product.query.get(id)

    if p:
        p.is_active = not p.is_active
        db.session.commit()

    return redirect("/products")

@app.route("/product/delete/<int:id>")
def delete_product(id):
    p = Product.query.get(id)

    if p:
        db.session.delete(p)
        db.session.commit()

    return redirect("/products")

@app.route("/product/edit/<int:id>", methods=["GET", "POST"])
def edit_product(id):
    p = Product.query.get(id)
    suppliers = Supplier.query.all()

    if not p:
        return "Ürün bulunamadı"

    if request.method == "POST":
        barcode = request.form.get("barcode")
        name = request.form.get("name")
        supplier_id = request.form.get("supplier_id")
        unit = request.form.get("unit")

        # duplicate kontrol (kendisi hariç)
        existing = Product.query.filter(Product.barcode == barcode, Product.id != id).first()

        if existing:
            return "Bu barkod başka üründe var"

        p.barcode = barcode
        p.name = name
        p.supplier_id = supplier_id
        p.unit = unit

        db.session.commit()
        return redirect("/products")

    return render_template("product_edit.html", product=p, suppliers=suppliers)

@app.route("/")
def index():
    products = Product.query.all()

    total_products = len(products)
    total_value = 0
    avg_price = 0

    return render_template(
        "index.html",
        total_products=total_products,
        total_value=total_value,
        avg_price=avg_price
    )


@app.route("/delete/<int:id>")
def delete(id):
    product = Product.query.get(id)

    if product:
        db.session.delete(product)
        db.session.commit()

    return redirect("/")


@app.route("/edit/<int:id>", methods=["GET", "POST"])
def edit(id):
    product = Product.query.get(id)

    if not product:
        return "Ürün bulunamadı"

    if request.method == "POST":
        product.name = request.form.get("name")
        product.price = Decimal(request.form.get("price"))

        db.session.commit()
        return redirect("/")

    return render_template("edit.html", product=product)


# =========================
# ROUTES - SUPPLIER
# =========================

@app.route("/suppliers", methods=["GET", "POST"])
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

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")


with app.app_context():
    db.create_all()

    if not User.query.filter_by(username="admin").first():
        admin = User(username="admin", password="1234")
        db.session.add(admin)
        db.session.commit()
# =========================
# INIT
# =========================

if __name__ == "__main__":
    with app.app_context():
        db.create_all()

    app.run(debug=True)