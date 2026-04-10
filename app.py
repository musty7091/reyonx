from flask import Flask, request, redirect, render_template, session
from flask_sqlalchemy import SQLAlchemy
import os
from datetime import datetime

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

class Period(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False) # Örn: Nisan 2026
    start_date = db.Column(db.DateTime, default=db.func.now())
    end_date = db.Column(db.DateTime)
    is_active = db.Column(db.Boolean, default=True)
    
    # Kapanış Anındaki Finansal Özetler (Arşiv için)
    total_revenue = db.Column(db.Float, default=0.0)
    total_cost = db.Column(db.Float, default=0.0)
    total_waste_cost = db.Column(db.Float, default=0.0)
    total_expenses = db.Column(db.Float, default=0.0)
    net_profit = db.Column(db.Float, default=0.0)

class Supplier(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    contact_person = db.Column(db.String(150))
    phone = db.Column(db.String(50))

class Payment(db.Model):
    # Tedarikçiye yapılan ödemeler (Dönemden bağımsız)
    id = db.Column(db.Integer, primary_key=True)
    supplier_id = db.Column(db.Integer, db.ForeignKey("supplier.id"))
    amount = db.Column(db.Float, nullable=False) # Ödenen tutar
    description = db.Column(db.String(200)) # Açıklama (Nakit, Havale vb.)
    date = db.Column(db.DateTime, default=db.func.now())
    
    supplier = db.relationship("Supplier", backref="payments")

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    barcode = db.Column(db.String(100), unique=True, nullable=False)
    name = db.Column(db.String(150), nullable=False)
    supplier_id = db.Column(db.Integer, db.ForeignKey("supplier.id"))
    unit = db.Column(db.String(20))
    price = db.Column(db.Float, default=0.0)  
    stock_quantity = db.Column(db.Float, default=0.0) 
    avg_cost = db.Column(db.Float, default=0.0) # Net Maliyet (KDV Hariç)
    vat_rate = db.Column(db.Float, default=20.0) # Ürünün KDV Oranı (%)
    is_active = db.Column(db.Boolean, default=True)
    supplier = db.relationship("Supplier")

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(200))

class Invoice(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    invoice_no = db.Column(db.String(100)) 
    invoice_type = db.Column(db.String(20), default="alis") # "alis" veya "iade"
    supplier_id = db.Column(db.Integer, db.ForeignKey("supplier.id"))
    period_id = db.Column(db.Integer, db.ForeignKey("period.id")) 
    date = db.Column(db.DateTime, default=db.func.now()) 
    total_net = db.Column(db.Float, default=0.0) 
    total_vat = db.Column(db.Float, default=0.0) 
    total_amount = db.Column(db.Float, default=0.0) 
    
    supplier = db.relationship("Supplier")
    period = db.relationship("Period")
    items = db.relationship("InvoiceItem", backref="invoice", lazy=True, cascade="all, delete-orphan")

class InvoiceItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey("invoice.id"))
    product_id = db.Column(db.Integer, db.ForeignKey("product.id"))
    quantity = db.Column(db.Float, nullable=False)
    unit_price = db.Column(db.Float, nullable=False) 
    vat_rate = db.Column(db.Float, default=0.0) 
    vat_amount = db.Column(db.Float, default=0.0) 
    net_total = db.Column(db.Float, default=0.0) 
    line_total = db.Column(db.Float) 

    product = db.relationship("Product")

class Waste(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey("product.id"))
    period_id = db.Column(db.Integer, db.ForeignKey("period.id")) 
    quantity = db.Column(db.Float, nullable=False)
    cost = db.Column(db.Float, default=0.0) 
    reason = db.Column(db.String(200))
    date = db.Column(db.DateTime, default=db.func.now())
    
    product = db.relationship("Product")
    period = db.relationship("Period")

class Sale(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    period_id = db.Column(db.Integer, db.ForeignKey("period.id")) 
    date = db.Column(db.DateTime, default=db.func.now())
    total_revenue = db.Column(db.Float, default=0.0) 
    total_cost = db.Column(db.Float, default=0.0)    
    total_profit = db.Column(db.Float, default=0.0)  
    
    period = db.relationship("Period")
    items = db.relationship("SaleItem", backref="sale", lazy=True, cascade="all, delete-orphan")

class SaleItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sale_id = db.Column(db.Integer, db.ForeignKey("sale.id"))
    product_id = db.Column(db.Integer, db.ForeignKey("product.id"))
    quantity = db.Column(db.Float, nullable=False)
    unit_sales_price = db.Column(db.Float, nullable=False) 
    unit_cost = db.Column(db.Float, nullable=False)        
    line_revenue = db.Column(db.Float, default=0.0)
    line_profit = db.Column(db.Float, default=0.0)
    product = db.relationship("Product")

class Expense(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    period_id = db.Column(db.Integer, db.ForeignKey("period.id")) 
    description = db.Column(db.String(250), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    date = db.Column(db.DateTime, default=db.func.now())
    
    period = db.relationship("Period")

# =========================
# YARDIMCI FONKSİYONLAR
# =========================

def get_active_period():
    period = Period.query.filter_by(is_active=True).first()
    if not period:
        period = Period(name="1. Dönem")
        db.session.add(period)
        db.session.commit()
    return period

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
    active_period = get_active_period()
    products = Product.query.all()
    
    invoices = Invoice.query.filter_by(period_id=active_period.id).all()
    sales = Sale.query.filter_by(period_id=active_period.id).all()
    wastes = Waste.query.filter_by(period_id=active_period.id).all()
    expenses = Expense.query.filter_by(period_id=active_period.id).all()
    
    total_products = len(products)
    total_stock = sum([p.stock_quantity for p in products if p.stock_quantity])
    
    # Yatırım tutarını hesaplarken İadeleri düşüyoruz
    total_investment = sum([inv.total_amount for inv in invoices if inv.invoice_type == "alis"]) - sum([inv.total_amount for inv in invoices if inv.invoice_type == "iade"])
    
    total_revenue = sum([s.total_revenue for s in sales])
    
    gross_profit = sum([s.total_profit for s in sales])
    total_waste_cost = sum([w.quantity * w.cost for w in wastes]) 
    total_expense_amount = sum([e.amount for e in expenses])
    real_net_profit = gross_profit - total_waste_cost - total_expense_amount
    
    return render_template(
        "index.html",
        active_period=active_period,
        total_products=total_products,
        total_stock=round(total_stock, 2), 
        total_value=round(total_investment, 2), 
        total_revenue=round(total_revenue, 2),
        total_profit=round(real_net_profit, 2)
    )

# =========================
# TEDARİKÇİLER VE CARİ (EKSTRE)
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
    
    suppliers_data = []
    for s in Supplier.query.all():
        alis_invoices = sum(inv.total_amount for inv in Invoice.query.filter_by(supplier_id=s.id, invoice_type="alis").all())
        iade_invoices = sum(inv.total_amount for inv in Invoice.query.filter_by(supplier_id=s.id, invoice_type="iade").all())
        total_payments = sum(pay.amount for pay in Payment.query.filter_by(supplier_id=s.id).all())
        
        # Bakiye = Aldıklarımız - İade Ettiklerimiz - Ödediklerimiz
        balance = alis_invoices - iade_invoices - total_payments 
        suppliers_data.append({"supplier": s, "balance": balance})
        
    return render_template("suppliers.html", suppliers_data=suppliers_data)

@app.route("/supplier/<int:id>", methods=["GET", "POST"])
def supplier_detail(id):
    supplier = Supplier.query.get_or_404(id)
    
    if request.method == "POST":
        amount = request.form.get("amount")
        desc = request.form.get("description")
        if amount:
            payment = Payment(supplier_id=id, amount=float(amount), description=desc)
            db.session.add(payment)
            db.session.commit()
            return redirect(f"/supplier/{id}")

    transactions = []
    invoices = Invoice.query.filter_by(supplier_id=id).all()
    payments = Payment.query.filter_by(supplier_id=id).all()
    
    for inv in invoices:
        if inv.invoice_type == "alis":
            transactions.append({
                "date": inv.date,
                "type": "Alış Faturası",
                "desc": f"Fatura No: {inv.invoice_no if inv.invoice_no else inv.id}", 
                "debt": inv.total_amount, 
                "credit": 0.0
            })
        else: # İade faturası ise borcumuzu siler (Alacak yazılır)
            transactions.append({
                "date": inv.date,
                "type": "İade Faturası",
                "desc": f"İade Fatura No: {inv.invoice_no if inv.invoice_no else inv.id}", 
                "debt": 0.0, 
                "credit": inv.total_amount 
            })
        
    for pay in payments:
        transactions.append({
            "date": pay.date,
            "type": "Ödeme Yapıldı",
            "desc": pay.description,
            "debt": 0.0,
            "credit": pay.amount 
        })
        
    # Önce eskiden yeniye (kronolojik) sıralıyoruz ki bakiye hesabı doğru çıksın
    transactions.sort(key=lambda x: x["date"])
    
    running_balance = 0.0
    for t in transactions:
        running_balance += (t["debt"] - t["credit"])
        t["balance"] = running_balance
        
    # Hesaplama bittikten sonra en yeni işlemi en üste almak için listeyi ters çeviriyoruz
    transactions.reverse()
        
    return render_template("supplier_detail.html", supplier=supplier, transactions=transactions, current_balance=running_balance)

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
# FATURA İŞLEMLERİ (ALIŞ VE İADE)
# =========================

@app.route("/invoices", methods=["GET", "POST"])
def invoices():
    active_period = get_active_period()
    if request.method == "POST":
        s_id = request.form.get("supplier_id")
        invoice_no = request.form.get("invoice_no") 
        invoice_type = request.form.get("invoice_type", "alis") 
        invoice_date_str = request.form.get("invoice_date") 
        
        product_ids = request.form.getlist("product_id[]")
        quantities = request.form.getlist("quantity[]")
        unit_prices = request.form.getlist("unit_price[]") 
        
        if s_id and product_ids:
            new_inv = Invoice(supplier_id=s_id, period_id=active_period.id, invoice_no=invoice_no, invoice_type=invoice_type)
            
            if invoice_date_str:
                try:
                    new_inv.date = datetime.strptime(invoice_date_str, "%Y-%m-%d")
                except ValueError:
                    pass
            
            db.session.add(new_inv)
            db.session.flush() 
            
            calc_net = 0
            calc_vat = 0
            calc_gross = 0
            
            for i in range(len(product_ids)):
                p_id = product_ids[i]
                qty = float(quantities[i])
                net_unit = float(unit_prices[i]) 
                
                product = Product.query.get(p_id)
                v_rate = product.vat_rate if product else 20.0
                calc_v_rate = 0.0 if v_rate == -1 else v_rate
                
                gross_unit = net_unit * (1 + (calc_v_rate / 100))
                
                line_net = net_unit * qty
                line_gross = gross_unit * qty
                line_vat = line_gross - line_net
                
                item = InvoiceItem(
                    invoice_id=new_inv.id,
                    product_id=p_id,
                    quantity=qty,
                    unit_price=net_unit,
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
                    
                    if new_inv.invoice_type == "alis":
                        new_stock = old_stock + qty
                        if new_stock > 0:
                            product.avg_cost = ((old_stock * old_cost) + (qty * net_unit)) / new_stock
                    else:
                        new_stock = old_stock - qty 
                        
                    product.stock_quantity = new_stock
            
            new_inv.total_net = round(calc_net, 2)
            new_inv.total_vat = round(calc_vat, 2)
            new_inv.total_amount = round(calc_gross, 2) 
            db.session.commit()
            return redirect("/invoices")
    
    all_invoices = Invoice.query.filter_by(period_id=active_period.id).order_by(Invoice.date.asc()).all()
    suppliers = Supplier.query.all()
    products = Product.query.all()
    return render_template("invoices.html", invoices=all_invoices, suppliers=suppliers, products=products, active_period=active_period)

@app.route("/invoice/<int:id>", methods=["GET", "POST"])
def invoice_detail(id):
    inv = Invoice.query.get_or_404(id)
    products = Product.query.all()
    
    if request.method == "POST":
        p_id = request.form.get("product_id")
        qty = float(request.form.get("quantity"))
        net_unit = float(request.form.get("unit_price")) 
        
        product = Product.query.get(p_id)
        v_rate = product.vat_rate if product else 20.0
        calc_v_rate = 0.0 if v_rate == -1 else v_rate
        
        gross_unit = net_unit * (1 + (calc_v_rate / 100))
            
        line_net = net_unit * qty
        line_gross = gross_unit * qty
        line_vat = line_gross - line_net
        
        item = InvoiceItem(
            invoice_id=id,
            product_id=p_id,
            quantity=qty,
            unit_price=net_unit,
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
            
            if inv.invoice_type == "alis":
                new_stock = old_stock + qty
                if new_stock > 0:
                    product.avg_cost = ((old_stock * old_cost) + (qty * net_unit)) / new_stock
            else:
                new_stock = old_stock - qty
                
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
        inv = item.invoice
        product = Product.query.get(item.product_id)
        
        if product:
            if inv.invoice_type == "alis":
                product.stock_quantity -= item.quantity 
            else:
                product.stock_quantity += item.quantity 
        
        inv.total_net -= item.net_total
        inv.total_vat -= item.vat_amount
        inv.total_amount -= item.line_total
        
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
                if inv.invoice_type == "alis":
                    product.stock_quantity -= item.quantity
                else:
                    product.stock_quantity += item.quantity
        db.session.delete(inv)
        db.session.commit()
    return redirect("/invoices")

# =========================
# SATIŞ İŞLEMLERİ
# =========================

@app.route("/sales", methods=["GET", "POST"])
def sales():
    active_period = get_active_period()
    if request.method == "POST":
        product_ids = request.form.getlist("product_id[]")
        quantities = request.form.getlist("quantity[]")
        unit_prices = request.form.getlist("unit_price[]") 
        
        if product_ids:
            new_sale = Sale(period_id=active_period.id)
            db.session.add(new_sale)
            db.session.flush()
            
            calc_revenue, calc_cost = 0, 0
            
            for i in range(len(product_ids)):
                p_id = product_ids[i]
                qty = float(quantities[i])
                u_price_net = float(unit_prices[i]) 
                
                product = Product.query.get(p_id)
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
            
    all_sales = Sale.query.filter_by(period_id=active_period.id).order_by(Sale.id.desc()).all()
    products = Product.query.filter_by(is_active=True).all()
    return render_template("sales.html", sales=all_sales, products=products, active_period=active_period)

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
    active_period = get_active_period()
    products = Product.query.all()
    if request.method == "POST":
        product_id = request.form.get("product_id")
        quantity = request.form.get("quantity")
        reason = request.form.get("reason")
        
        if product_id and quantity:
            product = Product.query.get(product_id)
            
            last_invoice_item = InvoiceItem.query.join(Invoice).filter(
                InvoiceItem.product_id == product_id,
                Invoice.invoice_type == "alis"
            ).order_by(Invoice.date.desc()).first()
            
            if last_invoice_item and last_invoice_item.quantity > 0:
                cost_at_waste = last_invoice_item.net_total / last_invoice_item.quantity
            else:
                cost_at_waste = product.avg_cost if product and product.avg_cost else 0.0
            
            new_waste = Waste(
                product_id=product_id, 
                period_id=active_period.id,
                quantity=float(quantity), 
                cost=cost_at_waste, 
                reason=reason
            )
            db.session.add(new_waste)
            
            if product:
                if not hasattr(product, 'stock_quantity') or product.stock_quantity is None:
                    product.stock_quantity = 0
                product.stock_quantity -= float(quantity)
                
            db.session.commit()
        return redirect("/wastes")

    all_wastes = Waste.query.filter_by(period_id=active_period.id).order_by(Waste.id.desc()).all()
    return render_template("wastes.html", wastes=all_wastes, products=products, active_period=active_period)

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
    active_period = get_active_period()
    if request.method == "POST":
        desc = request.form.get("description")
        amt = request.form.get("amount")
        if desc and amt:
            new_exp = Expense(description=desc, amount=float(amt), period_id=active_period.id)
            db.session.add(new_exp)
            db.session.commit()
        return redirect("/expenses")
    
    all_expenses = Expense.query.filter_by(period_id=active_period.id).order_by(Expense.id.desc()).all()
    return render_template("expenses.html", expenses=all_expenses, active_period=active_period)

@app.route("/expense/delete/<int:id>")
def delete_expense(id):
    exp = Expense.query.get(id)
    if exp:
        db.session.delete(exp)
        db.session.commit()
    return redirect("/expenses")

# =========================
# KÂR & PRİM RAPORU
# =========================

@app.route("/report")
def report():
    active_period = get_active_period()
    sales = Sale.query.filter_by(period_id=active_period.id).all()
    wastes = Waste.query.filter_by(period_id=active_period.id).all()
    expenses = Expense.query.filter_by(period_id=active_period.id).all()

    total_revenue = sum([s.total_revenue for s in sales])
    total_cost = sum([s.total_cost for s in sales])
    gross_profit = total_revenue - total_cost

    total_waste_cost = sum([w.quantity * w.cost for w in wastes])
    total_expenses = sum([e.amount for e in expenses])

    net_profit = gross_profit - total_waste_cost - total_expenses
    bonus = net_profit * app.config["BONUS_RATE"] if net_profit > 0 else 0

    return render_template(
        "profit_report.html",
        active_period=active_period,
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
# DÖNEM YÖNETİMİ VE ARŞİV
# =========================

@app.route("/period/close", methods=["POST"])
def close_period():
    active_period = get_active_period()
    
    sales = Sale.query.filter_by(period_id=active_period.id).all()
    wastes = Waste.query.filter_by(period_id=active_period.id).all()
    expenses = Expense.query.filter_by(period_id=active_period.id).all()

    t_rev = sum([s.total_revenue for s in sales])
    t_cost = sum([s.total_cost for s in sales])
    t_waste = sum([w.quantity * w.cost for w in wastes])
    t_exp = sum([e.amount for e in expenses])
    n_prof = (t_rev - t_cost) - t_waste - t_exp

    active_period.total_revenue = t_rev
    active_period.total_cost = t_cost
    active_period.total_waste_cost = t_waste
    active_period.total_expenses = t_exp
    active_period.net_profit = n_prof
    active_period.end_date = datetime.utcnow()
    active_period.is_active = False 

    new_name = request.form.get("new_period_name", "Yeni Dönem")
    new_period = Period(name=new_name)
    db.session.add(new_period)
    db.session.commit()

    return redirect("/periods")

@app.route("/periods")
def periods():
    all_periods = Period.query.order_by(Period.id.desc()).all()
    return render_template("periods.html", periods=all_periods)

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