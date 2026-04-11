from database import db
from datetime import datetime

class Waste(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey("product.id"))
    quantity = db.Column(db.Float, nullable=False) # Miktar
    reason = db.Column(db.String(200)) # Neden bozuldu?
    date = db.Column(db.DateTime, default=datetime.utcnow) # Ne zaman?
    
    product = db.relationship("Product")