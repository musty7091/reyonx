from flask import Flask, request, redirect, render_template, session
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

app = Flask(__name__)

app.config["SECRET_KEY"] = "secret"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///reyonx.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)


# =========================
# MODELS
# =========================

class Supplier(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    contact_person = db.Column(db.String(150))
    phone = db.Column(db.String(50))


class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    barcode = db.Column(db.String(100), unique=True, nullable=False)
    name = db.Column(db.String(150), nullable=False)

    supplier_id = db.Column(db.Integer, db.ForeignKey("supplier.id"))
    supplier = db.relationship("Supplier")

    unit = db.Column(db.String(20))
    is_active = db.Column(db.Boolean, default=True)


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(200))


# =========================
# LOGIN CONTROL
# =========================

@app.before_request
def check_login():
    allowed = ["login", "static"]
    if request.endpoint not in allowed and "user_id" not in session:
        return redirect("/login")


# =========================
# AUTH
# =========================

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        u = request.form.get("username")
        p = request.form.get("password")

        user = User.query.filter_by(username=u).first()

        if user and user.password == p:
            session["user_id"] = user.id
            return redirect("/")

        return "Hatalı giriş"

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")


# =========================
# DASHBOARD
# =========================

@app.route("/")
def index():
    total_products = Product.query.count()

    return render_template(
        "index.html",
        total_products=total_products,
        total_value=0,
        avg_price=0
    )


# =========================
# SUPPLIERS
# =========================

@app.route("/suppliers", methods=["GET", "POST"])
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

    return render_template("suppliers.html", suppliers=Supplier.query.all())


# =========================
# PRODUCTS (FINAL)
# =========================

@app.route("/products", methods=["GET", "POST"])
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
                is_active=True
            )
            db.session.add(p)
            db.session.commit()
            return redirect("/products")

    # 🔥 pagination + sıralama
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


@app.route("/product/delete/<int:id>")
def delete_product(id):
    p = Product.query.get(id)
    if p:
        db.session.delete(p)
        db.session.commit()
    return redirect("/products")


@app.route("/product/toggle/<int:id>")
def toggle_product(id):
    p = Product.query.get(id)
    if p:
        p.is_active = not p.is_active
        db.session.commit()
    return redirect("/products")


@app.route("/product/edit/<int:id>", methods=["GET", "POST"])
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

        db.session.commit()
        return redirect("/products")

    return render_template("product_edit.html", product=p, suppliers=suppliers)


# =========================
# INIT
# =========================

if __name__ == "__main__":
    with app.app_context():
        db.create_all()

        if not User.query.filter_by(username="admin").first():
            db.session.add(User(username="admin", password="1234"))
            db.session.commit()

    app.run(debug=True)