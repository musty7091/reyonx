from database import db
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

# =========================
# BASE MODEL
# =========================
class BaseModel(db.Model):
    __abstract__ = True
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

# =========================
# AUDIT LOG
# =========================
class AuditLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    action = db.Column(db.String(100))
    table_name = db.Column(db.String(50))
    record_id = db.Column(db.Integer)
    description = db.Column(db.String(250))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

# =========================

class Period(BaseModel):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    start_date = db.Column(db.DateTime, default=datetime.utcnow)
    end_date = db.Column(db.DateTime)
    is_active = db.Column(db.Boolean, default=True)
    
    total_revenue = db.Column(db.Numeric(15, 2), default=0.0)
    total_cost = db.Column(db.Numeric(15, 2), default=0.0)
    total_waste_cost = db.Column(db.Numeric(15, 2), default=0.0)
    total_expenses = db.Column(db.Numeric(15, 2), default=0.0)
    net_profit = db.Column(db.Numeric(15, 2), default=0.0)
    bonus_rate = db.Column(db.Numeric(5, 2), nullable=True)

class Supplier(BaseModel):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    contact_person = db.Column(db.String(150))
    phone = db.Column(db.String(50))

class Payment(BaseModel):
    id = db.Column(db.Integer, primary_key=True)
    supplier_id = db.Column(db.Integer, db.ForeignKey("supplier.id"))
    amount = db.Column(db.Numeric(15, 2), nullable=False) 
    description = db.Column(db.String(200)) 
    date = db.Column(db.DateTime, default=datetime.utcnow)
    is_cancelled = db.Column(db.Boolean, default=False)
    
    supplier = db.relationship("Supplier", backref="payments")

class Product(BaseModel):
    id = db.Column(db.Integer, primary_key=True)
    barcode = db.Column(db.String(100), unique=True, nullable=False)
    name = db.Column(db.String(150), nullable=False)
    supplier_id = db.Column(db.Integer, db.ForeignKey("supplier.id"))
    unit = db.Column(db.String(20))

    price = db.Column(db.Numeric(15, 2), default=0.0)  # satış fiyatı
    purchase_price = db.Column(db.Numeric(15, 2), default=0.0)  # alış fiyatı
    avg_cost = db.Column(db.Numeric(15, 2), default=0.0)  # ortalama maliyet

    stock_quantity = db.Column(db.Numeric(15, 2), default=0.0)
    vat_rate = db.Column(db.Numeric(5, 2), default=20.0)
    is_active = db.Column(db.Boolean, default=True)
    category = db.Column(db.String(100))

    supplier = db.relationship("Supplier")

class User(BaseModel):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)

    failed_login_attempts = db.Column(db.Integer, default=0)
    lock_until = db.Column(db.DateTime, nullable=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password, method="pbkdf2:sha256", salt_length=16)
        
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Invoice(BaseModel):
    id = db.Column(db.Integer, primary_key=True)
    invoice_no = db.Column(db.String(100)) 
    invoice_type = db.Column(db.String(20), default="alis") 
    supplier_id = db.Column(db.Integer, db.ForeignKey("supplier.id"))
    period_id = db.Column(db.Integer, db.ForeignKey("period.id")) 
    date = db.Column(db.DateTime, default=datetime.utcnow) 
    total_net = db.Column(db.Numeric(15, 2), default=0.0) 
    total_vat = db.Column(db.Numeric(15, 2), default=0.0) 
    total_amount = db.Column(db.Numeric(15, 2), default=0.0) 
    is_cancelled = db.Column(db.Boolean, default=False)
    
    supplier = db.relationship("Supplier")
    period = db.relationship("Period")
    items = db.relationship("InvoiceItem", backref="invoice", lazy=True, cascade="all, delete-orphan")

class InvoiceItem(BaseModel):
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

class Waste(BaseModel):
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey("product.id"))
    period_id = db.Column(db.Integer, db.ForeignKey("period.id")) 
    quantity = db.Column(db.Numeric(15, 2), nullable=False)
    cost = db.Column(db.Numeric(15, 2), default=0.0) 
    reason = db.Column(db.String(200))
    date = db.Column(db.DateTime, default=datetime.utcnow)
    is_cancelled = db.Column(db.Boolean, default=False)
    
    product = db.relationship("Product")
    period = db.relationship("Period")

class Sale(BaseModel):
    id = db.Column(db.Integer, primary_key=True)
    period_id = db.Column(db.Integer, db.ForeignKey("period.id")) 
    date = db.Column(db.DateTime, default=datetime.utcnow)
    total_revenue = db.Column(db.Numeric(15, 2), default=0.0) 
    total_cost = db.Column(db.Numeric(15, 2), default=0.0)    
    total_profit = db.Column(db.Numeric(15, 2), default=0.0)  
    is_cancelled = db.Column(db.Boolean, default=False)
    
    period = db.relationship("Period")
    items = db.relationship("SaleItem", backref="sale", lazy=True, cascade="all, delete-orphan")

class SaleItem(BaseModel):
    id = db.Column(db.Integer, primary_key=True)
    sale_id = db.Column(db.Integer, db.ForeignKey("sale.id"))
    product_id = db.Column(db.Integer, db.ForeignKey("product.id"))
    quantity = db.Column(db.Numeric(15, 2), nullable=False)
    unit_sales_price = db.Column(db.Numeric(15, 2), nullable=False) 
    unit_cost = db.Column(db.Numeric(15, 2), nullable=False)        
    line_revenue = db.Column(db.Numeric(15, 2), default=0.0)
    line_profit = db.Column(db.Numeric(15, 2), default=0.0)
    
    product = db.relationship("Product")

class Expense(BaseModel):
    id = db.Column(db.Integer, primary_key=True)
    period_id = db.Column(db.Integer, db.ForeignKey("period.id")) 
    description = db.Column(db.String(250), nullable=False)
    amount = db.Column(db.Numeric(15, 2), nullable=False)
    date = db.Column(db.DateTime, default=datetime.utcnow)
    is_cancelled = db.Column(db.Boolean, default=False)
    
    period = db.relationship("Period")

class SystemSetting(BaseModel):
    id = db.Column(db.Integer, primary_key=True)
    setting_key = db.Column(db.String(50), unique=True, nullable=False)
    setting_value = db.Column(db.String(100), nullable=False)