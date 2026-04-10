from flask import Flask, request, redirect, render_template, session
from flask_sqlalchemy import SQLAlchemy
import os

# Veritabanı tanımlama
db = SQLAlchemy()

app = Flask(__name__)

# Ayarlar
app.config["SECRET_KEY"] = "secret"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///reyonx.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["BONUS_RATE"] = 0.05  # Prim oranı %5

db.init_app(app)

# =========================
# MODELLER
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
    unit = db.Column(db.String(20))
    price = db.Column(db.Float, default=0.0)  
    stock_quantity = db.Column(db.Float, default=0.0) 
    avg_cost = db.Column(db.Float, default=0.0) # Net Maliyet
    vat_rate = db.Column(db.Float, default=20.0) # Ürünün KDV Oranı (%)
    is_active = db.Column(db.Boolean, default=True)
    supplier = db.relationship("Supplier")

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(200))

class Invoice(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    supplier_id = db.Column(db.Integer, db.ForeignKey("supplier.id"))
    date = db.Column(db.DateTime, default=db.func.now())
    is_vat_included = db.Column(db.Boolean, default=True) # Fatura girilirken KDV dahil miydi?
    total_net = db.Column(db.Float, default=0.0) # KDV Hariç Toplam
    total_vat = db.Column(db.Float, default=0.0) # Toplam KDV
    total_amount = db.Column(db.Float, default=0.0) # KDV Dahil Genel Toplam
    is_paid = db.Column(db.Boolean, default=False)
    
    supplier = db.relationship("Supplier")
    items = db.relationship("InvoiceItem", backref="invoice", lazy=True, cascade="all, delete-orphan")

class InvoiceItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey("invoice.id"))
    product_id = db.Column(db.Integer, db.ForeignKey("product.id"))
    quantity = db.Column(db.Float, nullable=False)
    unit_price = db.Column(db.Float, nullable=False) # Formdan girilen ham fiyat
    vat_rate = db.Column(db.Float, default=0.0) # O anki KDV oranı
    vat_amount = db.Column(db.Float, default=0.0) # KDV Tutarı
    net_total = db.Column(db.Float, default=0.0) # KDV Hariç Satır Toplamı
    line_total = db.Column(db.Float) # KDV Dahil Satır Toplamı

    product = db.relationship("Product")

class Waste(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey("product.id"))
    quantity = db.Column(db.Float, nullable=False)
    reason = db.Column(db.String(200))
    date = db.Column(db.DateTime, default=db.func.now())
    product = db.relationship("Product")

class Sale(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.DateTime, default=db.func.now())
    total_revenue = db.Column(db.Float, default=0.0) # Satıştan kasaya giren (Net Ciro)
    total_cost = db.Column(db.Float, default=0.0)    # Satılan malın maliyeti
    total_profit = db.Column(db.Float, default=0.0)  # Ciro - Maliyet
    items = db.relationship("SaleItem", backref="sale", lazy=True, cascade="all, delete-orphan")

class SaleItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sale_id = db.Column(db.Integer, db.ForeignKey("sale.id"))
    product_id = db.Column(db.Integer, db.ForeignKey("product.id"))
    quantity = db.Column(db.Float, nullable=False)
    unit_sales_price = db.Column(db.Float, nullable=False) # KDV Hariç Satış Fiyatı
    unit_cost = db.Column(db.Float, nullable=False)        # Satıldığı andaki Net maliyeti
    line_revenue = db.Column(db.Float, default=0.0)
    line_profit = db.Column(db.Float, default=0.0)
    product = db.relationship("Product")

class Expense(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(250), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    date = db.Column(db.DateTime, default=db.func.now())

# =========================
# GİRİŞ KONTROLÜ
# =========================

@app.before_request
def check_login():
    allowed = ["login", "static"]
    if request.endpoint not in allowed and "user_id" not in session:
        return redirect("/login")

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
# ANA SAYFA (DASHBOARD)
# =========================

@app.route("/")
def index():
    products = Product.query.all()
    invoices = Invoice.query.all()
    sales = Sale.query.all()
    wastes = Waste.query.all()
    expenses = Expense.query.all()
    
    total_products = len(products)
    total_stock = sum([p.stock_quantity for p in products if p.stock_quantity])
    total_investment = sum([inv.total_amount for inv in invoices])
    total_revenue = sum([s.total_revenue for s in sales])
    
    # Gerçek net kâr hesaplaması (Ciro - Fire - Giderler)
    gross_profit = sum([s.total_profit for s in sales])
    total_waste_cost = sum([w.quantity * (w.product.avg_cost if w.product and w.product.avg_cost else 0) for w in wastes])
    total_expense_amount = sum([e.amount for e in expenses])
    real_net_profit = gross_profit - total_waste_cost - total_expense_amount
    
    return render_template(
        "index.html",
        total_products=total_products,
        total_value=round(total_investment, 2), 
        avg_price=round(total_stock, 2),
        total_revenue=round(total_revenue, 2),
        total_profit=round(real_net_profit, 2)
    )

# =========================
# TEDARİKÇİLER
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
# ÜRÜNLER
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
        p.vat_rate = float(request.form.get("vat_rate", 20.0))
        db.session.commit()
        return redirect("/products")
    return render_template("product_edit.html", product=p, suppliers=suppliers)

# =========================
# FATURA İŞLEMLERİ (KDV HARİÇ MALİYET)
# =========================

@app.route("/invoices", methods=["GET", "POST"])
def invoices():
    if request.method == "POST":
        s_id = request.form.get("supplier_id")
        is_vat_inc = request.form.get("is_vat_included") == "1" 
        
        product_ids = request.form.getlist("product_id[]")
        quantities = request.form.getlist("quantity[]")
        unit_prices = request.form.getlist("unit_price[]")
        
        if s_id and product_ids:
            new_inv = Invoice(supplier_id=s_id, is_vat_included=is_vat_inc)
            db.session.add(new_inv)
            db.session.flush() 
            
            calc_net = 0
            calc_vat = 0
            calc_gross = 0
            
            for i in range(len(product_ids)):
                p_id = product_ids[i]
                qty = float(quantities[i])
                u_price = float(unit_prices[i]) 
                
                product = Product.query.get(p_id)
                v_rate = product.vat_rate if product else 20.0
                calc_v_rate = 0.0 if v_rate == -1 else v_rate
                
                if is_vat_inc:
                    gross_unit = u_price
                    net_unit = gross_unit / (1 + (calc_v_rate / 100))
                else:
                    net_unit = u_price
                    gross_unit = net_unit * (1 + (calc_v_rate / 100))
                
                line_net = net_unit * qty
                line_gross = gross_unit * qty
                line_vat = line_gross - line_net
                
                item = InvoiceItem(
                    invoice_id=new_inv.id,
                    product_id=p_id,
                    quantity=qty,
                    unit_price=u_price,
                    vat_rate=v_rate,
                    vat_amount=line_vat,
                    net_total=line_net,
                    line_total=line_gross
                )
                db.session.add(item)
                
                calc_net += line_net
                calc_vat += line_vat
                calc_gross += line_gross
                
                if product:
                    if not hasattr(product, 'stock_quantity') or product.stock_quantity is None:
                        product.stock_quantity = 0
                        
                    old_stock = product.stock_quantity
                    old_cost = product.avg_cost if product.avg_cost else 0.0
                    new_stock = old_stock + qty
                    
                    if new_stock > 0:
                        # KDV HARİÇ (NET) maliyet hesaplanıyor (net_unit)
                        product.avg_cost = ((old_stock * old_cost) + (qty * net_unit)) / new_stock
                        
                    product.stock_quantity = new_stock
            
            new_inv.total_net = round(calc_net, 2)
            new_inv.total_vat = round(calc_vat, 2)
            new_inv.total_amount = round(calc_gross, 2)
            db.session.commit()
            return redirect("/invoices")
    
    all_invoices = Invoice.query.order_by(Invoice.id.desc()).all()
    suppliers = Supplier.query.all()
    products = Product.query.all()
    return render_template("invoices.html", invoices=all_invoices, suppliers=suppliers, products=products)

@app.route("/invoice/<int:id>", methods=["GET", "POST"])
def invoice_detail(id):
    inv = Invoice.query.get_or_404(id)
    products = Product.query.all()
    
    if request.method == "POST":
        p_id = request.form.get("product_id")
        qty = float(request.form.get("quantity"))
        u_price = float(request.form.get("unit_price"))
        
        product = Product.query.get(p_id)
        v_rate = product.vat_rate if product else 20.0
        calc_v_rate = 0.0 if v_rate == -1 else v_rate
        
        if inv.is_vat_included:
            gross_unit = u_price
            net_unit = gross_unit / (1 + (calc_v_rate / 100))
        else:
            net_unit = u_price
            gross_unit = net_unit * (1 + (calc_v_rate / 100))
            
        line_net = net_unit * qty
        line_gross = gross_unit * qty
        line_vat = line_gross - line_net
        
        item = InvoiceItem(
            invoice_id=id,
            product_id=p_id,
            quantity=qty,
            unit_price=u_price,
            vat_rate=v_rate,
            vat_amount=line_vat,
            net_total=line_net,
            line_total=line_gross
        )
        db.session.add(item)
        
        if product:
            if not hasattr(product, 'stock_quantity') or product.stock_quantity is None:
                product.stock_quantity = 0
            
            old_stock = product.stock_quantity
            old_cost = product.avg_cost if product.avg_cost else 0.0
            new_stock = old_stock + qty
            
            if new_stock > 0:
                # KDV HARİÇ (NET) maliyet hesaplanıyor (net_unit)
                product.avg_cost = ((old_stock * old_cost) + (qty * net_unit)) / new_stock
                
            product.stock_quantity = new_stock
        
        inv.total_net += line_net
        inv.total_vat += line_vat
        inv.total_amount += line_gross
        db.session.commit()
        return redirect(f"/invoice/{id}")
        
    return render_template("invoice_detail.html", invoice=inv, products=products)

@app.route("/invoice/item/delete/<int:item_id>")
def delete_invoice_item(item_id):
    item = InvoiceItem.query.get(item_id)
    if item:
        inv_id = item.invoice_id
        product = Product.query.get(item.product_id)
        
        if product:
            product.stock_quantity -= item.quantity
        
        item.invoice.total_net -= item.net_total
        item.invoice.total_vat -= item.vat_amount
        item.invoice.total_amount -= item.line_total
        
        db.session.delete(item)
        db.session.commit()
        return redirect(f"/invoice/{inv_id}")
    return redirect("/invoices")

@app.route("/invoice/delete/<int:id>")
def delete_invoice(id):
    inv = Invoice.query.get(id)
    if inv:
        for item in inv.items:
            product = Product.query.get(item.product_id)
            if product:
                product.stock_quantity -= item.quantity
        db.session.delete(inv)
        db.session.commit()
    return redirect("/invoices")

# =========================
# SATIŞ İŞLEMLERİ (NET CİRO HESABI)
# =========================

@app.route("/sales", methods=["GET", "POST"])
def sales():
    if request.method == "POST":
        product_ids = request.form.getlist("product_id[]")
        quantities = request.form.getlist("quantity[]")
        unit_prices = request.form.getlist("unit_price[]")
        
        if product_ids:
            new_sale = Sale()
            db.session.add(new_sale)
            db.session.flush()
            
            calc_revenue, calc_cost = 0, 0
            
            for i in range(len(product_ids)):
                p_id = product_ids[i]
                qty = float(quantities[i])
                u_price_gross = float(unit_prices[i]) # Kasadan geçen Brüt rakam
                
                product = Product.query.get(p_id)
                v_rate = product.vat_rate if product else 20.0
                calc_v_rate = 0.0 if v_rate == -1 else v_rate
                
                # CİROYU NETLEŞTİR (KDV HARİÇ)
                u_price_net = u_price_gross / (1 + (calc_v_rate / 100))
                cost = product.avg_cost if product and product.avg_cost else 0.0
                
                line_rev_net = qty * u_price_net
                line_cst = qty * cost
                line_prf = line_rev_net - line_cst
                
                item = SaleItem(
                    sale_id=new_sale.id, 
                    product_id=p_id, 
                    quantity=qty, 
                    unit_sales_price=u_price_net, 
                    unit_cost=cost, 
                    line_revenue=line_rev_net, 
                    line_profit=line_prf
                )
                db.session.add(item)
                
                calc_revenue += line_rev_net
                calc_cost += line_cst
                
                if product:
                    product.stock_quantity -= qty
                    
            new_sale.total_revenue = round(calc_revenue, 2)
            new_sale.total_cost = round(calc_cost, 2)
            new_sale.total_profit = round(calc_revenue - calc_cost, 2)
            db.session.commit()
            return redirect("/sales")
            
    all_sales = Sale.query.order_by(Sale.id.desc()).all()
    products = Product.query.filter_by(is_active=True).all()
    return render_template("sales.html", sales=all_sales, products=products)

@app.route("/sale/delete/<int:id>")
def delete_sale(id):
    sale = Sale.query.get(id)
    if sale:
        for item in sale.items:
            product = Product.query.get(item.product_id)
            if product:
                product.stock_quantity += item.quantity
        db.session.delete(sale)
        db.session.commit()
    return redirect("/sales")

# =========================
# FİRE İŞLEMLERİ
# =========================

@app.route("/wastes", methods=["GET", "POST"])
def wastes():
    products = Product.query.all()
    if request.method == "POST":
        product_id = request.form.get("product_id")
        quantity = request.form.get("quantity")
        reason = request.form.get("reason")
        
        if product_id and quantity:
            new_waste = Waste(product_id=product_id, quantity=float(quantity), reason=reason)
            db.session.add(new_waste)
            
            product = Product.query.get(product_id)
            if product:
                if not hasattr(product, 'stock_quantity') or product.stock_quantity is None:
                    product.stock_quantity = 0
                product.stock_quantity -= float(quantity)
                
            db.session.commit()
        return redirect("/wastes")

    all_wastes = Waste.query.order_by(Waste.id.desc()).all()
    return render_template("wastes.html", wastes=all_wastes, products=products)

# =========================
# ENVANTER (STOK) İŞLEMLERİ
# =========================

@app.route("/inventory")
def inventory():
    products = Product.query.filter_by(is_active=True).all()
    return render_template("inventory.html", products=products)

# =========================
# GİDER İŞLEMLERİ
# =========================

@app.route("/expenses", methods=["GET", "POST"])
def expenses():
    if request.method == "POST":
        desc = request.form.get("description")
        amt = request.form.get("amount")
        if desc and amt:
            new_exp = Expense(description=desc, amount=float(amt))
            db.session.add(new_exp)
            db.session.commit()
        return redirect("/expenses")
    
    all_expenses = Expense.query.order_by(Expense.id.desc()).all()
    return render_template("expenses.html", expenses=all_expenses)

@app.route("/expense/delete/<int:id>")
def delete_expense(id):
    exp = Expense.query.get(id)
    if exp:
        db.session.delete(exp)
        db.session.commit()
    return redirect("/expenses")


# =========================
# KÂR & PRİM RAPORU (TAM NET)
# =========================

@app.route("/report")
def report():
    sales = Sale.query.all()
    wastes = Waste.query.all()
    expenses = Expense.query.all()

    total_revenue = sum([s.total_revenue for s in sales])
    total_cost = sum([s.total_cost for s in sales])
    gross_profit = total_revenue - total_cost

    total_waste_cost = sum([w.quantity * (w.product.avg_cost if w.product and w.product.avg_cost else 0) for w in wastes])
    total_expenses = sum([e.amount for e in expenses])

    net_profit = gross_profit - total_waste_cost - total_expenses
    bonus = net_profit * app.config["BONUS_RATE"] if net_profit > 0 else 0

    return render_template(
        "profit_report.html",
        total_revenue=total_revenue,
        total_cost=total_cost,
        gross_profit=gross_profit,
        total_waste_cost=total_waste_cost,
        total_expenses=total_expenses,
        net_profit=net_profit,
        bonus=bonus,
        wastes=wastes
    )

# =========================
# BAŞLATMA
# =========================

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        if not User.query.filter_by(username="admin").first():
            db.session.add(User(username="admin", password="1234"))
            db.session.commit()

    app.run(debug=True)