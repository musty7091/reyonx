from database import db

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    barcode = db.Column(db.String(100), unique=True, nullable=False)
    name = db.Column(db.String(150), nullable=False)
    supplier_id = db.Column(db.Integer, db.ForeignKey("supplier.id"))
    unit = db.Column(db.String(20)) # adet / kg
    price = db.Column(db.Float, default=0.0) # Satış fiyatı (Yeni ekledik)
    is_active = db.Column(db.Boolean, default=True)
    
    supplier = db.relationship("Supplier")