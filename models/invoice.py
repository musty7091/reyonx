from database import db
from datetime import datetime

class Invoice(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    supplier_id = db.Column(db.Integer, db.ForeignKey("supplier.id"))
    amount = db.Column(db.Float, nullable=False) # Fatura tutarı
    invoice_date = db.Column(db.DateTime, default=datetime.utcnow)
    is_paid = db.Column(db.Boolean, default=False) # Ödendi mi?
    
    supplier = db.relationship("Supplier")