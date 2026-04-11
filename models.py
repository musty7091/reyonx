from database import db
from datetime import datetime

class Period(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    start_date = db.Column(db.DateTime, default=datetime.utcnow)
    end_date = db.Column(db.DateTime)
    is_active = db.Column(db.Boolean, default=True)
    
    # Finansal Özetler (Kuruş hassasiyeti için Numeric yapıldı)
    total_revenue = db.Column(db.Numeric(15, 2), default=0.0)
    total_cost = db.Column(db.Numeric(15, 2), default=0.0)
    total_waste_cost = db.Column(db.Numeric(15, 2), default=0.0)
    total_expenses = db.Column(db.Numeric(15, 2), default=0.0)
    net_profit = db.Column(db.Numeric(15, 2), default=0.0)

class Supplier(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    contact_person = db.Column(db.String(150))
    phone = db.Column(db.String(50))

class Payment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    supplier_id = db.Column(db.Integer, db.ForeignKey("supplier.id"))
    amount = db.Column(db.Numeric(15, 2), nullable=False) 
    description = db.Column(db.String(200)) 
    date = db.Column(db.DateTime, default=datetime.utcnow)
    
    supplier = db.relationship("Supplier", backref="payments")

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    barcode = db.Column(db.String(100), unique=True, nullable=False)
    name = db.Column(db.String(150), nullable=False)
    supplier_id = db.Column(db.Integer, db.ForeignKey("supplier.id"))
    unit = db.Column(db.String(20))
    price = db.Column(db.Numeric(15, 2), default=0.0)  
    stock_quantity = db.Column(db.Numeric(15, 2), default=0.0) 
    avg_cost = db.Column(db.Numeric(15, 2), default=0.0) 
    vat_rate = db.Column(db.Numeric(5, 2), default=20.0) 
    is_active = db.Column(db.Boolean, default=True)
    
    supplier = db.relationship("Supplier")

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(200))

class Invoice(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    invoice_no = db.Column(db.String(100)) 
    invoice_type = db.Column(db.String(20), default="alis") 
    supplier_id = db.Column(db.Integer, db.ForeignKey("supplier.id"))
    period_id = db.Column(db.Integer, db.ForeignKey("period.id")) 
    date = db.Column(db.DateTime, default=datetime.utcnow) 
    total_net = db.Column(db.Numeric(15, 2), default=0.0) 
    total_vat = db.Column(db.Numeric(15, 2), default=0.0) 
    total_amount = db.Column(db.Numeric(15, 2), default=0.0) 
    
    supplier = db.relationship("Supplier")
    period = db.relationship("Period")
    items = db.relationship("InvoiceItem", backref="invoice", lazy=True, cascade="all, delete-orphan")

class InvoiceItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey("invoice.id"))
    product_id = db.Column(db.Integer, db.ForeignKey("product.id"))
    quantity = db.Column(db.Numeric(15, 2), nullable=False)
    unit_price = db.Column(db.Numeric(15, 2), nullable=False) 
    vat_rate = db.Column(db.Numeric(5, 2), default=0.0) 
    vat_amount = db.Column(db.Numeric(15, 2), default=0.0) 
    net_total = db.Column(db.Numeric(15, 2), default=0.0) 
    line_total = db.Column(db.Numeric(15, 2)) 

    product = db.relationship("Product")

class Waste(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey("product.id"))
    period_id = db.Column(db.Integer, db.ForeignKey("period.id")) 
    quantity = db.Column(db.Numeric(15, 2), nullable=False)
    cost = db.Column(db.Numeric(15, 2), default=0.0) 
    reason = db.Column(db.String(200))
    date = db.Column(db.DateTime, default=datetime.utcnow)
    
    product = db.relationship("Product")
    period = db.relationship("Period")

class Sale(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    period_id = db.Column(db.Integer, db.ForeignKey("period.id")) 
    date = db.Column(db.DateTime, default=datetime.utcnow)
    total_revenue = db.Column(db.Numeric(15, 2), default=0.0) 
    total_cost = db.Column(db.Numeric(15, 2), default=0.0)    
    total_profit = db.Column(db.Numeric(15, 2), default=0.0)  
    
    period = db.relationship("Period")
    items = db.relationship("SaleItem", backref="sale", lazy=True, cascade="all, delete-orphan")

class SaleItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sale_id = db.Column(db.Integer, db.ForeignKey("sale.id"))
    product_id = db.Column(db.Integer, db.ForeignKey("product.id"))
    quantity = db.Column(db.Numeric(15, 2), nullable=False)
    unit_sales_price = db.Column(db.Numeric(15, 2), nullable=False) 
    unit_cost = db.Column(db.Numeric(15, 2), nullable=False)        
    line_revenue = db.Column(db.Numeric(15, 2), default=0.0)
    line_profit = db.Column(db.Numeric(15, 2), default=0.0)
    
    product = db.relationship("Product")

class Expense(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    period_id = db.Column(db.Integer, db.ForeignKey("period.id")) 
    description = db.Column(db.String(250), nullable=False)
    amount = db.Column(db.Numeric(15, 2), nullable=False)
    date = db.Column(db.DateTime, default=datetime.utcnow)
    
    period = db.relationship("Period")