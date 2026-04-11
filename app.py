from flask import Flask
from database import db
from flask_migrate import Migrate
import os

# Rota (Sayfa) dosyalarımızı içeri aktarıyoruz
from routes.auth_routes import auth_bp
from routes.dashboard_routes import dashboard_bp
from routes.supplier_routes import supplier_bp
from routes.product_routes import product_bp
from routes.invoice_routes import invoice_bp
from routes.sale_routes import sale_bp
from routes.waste_routes import waste_bp
from routes.expense_routes import expense_bp
from routes.report_routes import report_bp

# Admin kullanıcı oluşturmak için User modelini çağırıyoruz
from models import User

app = Flask(__name__)

# Ayarlar
app.config["SECRET_KEY"] = "super-secret-key"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///reyonx.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["BONUS_RATE"] = 0.05  # Prim oranı %5

# Veritabanını uygulamaya bağlıyoruz
db.init_app(app)

# Esnek Veritabanı (Migration) sistemini başlatıyoruz
migrate = Migrate(app, db)

# Odalarımızı (Blueprints) ana binaya (uygulamaya) bağlıyoruz
app.register_blueprint(auth_bp)
app.register_blueprint(dashboard_bp)
app.register_blueprint(supplier_bp)
app.register_blueprint(product_bp)
app.register_blueprint(invoice_bp)
app.register_blueprint(sale_bp)
app.register_blueprint(waste_bp)
app.register_blueprint(expense_bp)
app.register_blueprint(report_bp)

# BAŞLATMA
if __name__ == "__main__":
    with app.app_context():
        # Tüm tabloları veritabanında oluşturur
        db.create_all()
        
        # Eğer sistemde admin yoksa otomatik oluşturur (Şifre: 1234)
        if not User.query.filter_by(username="admin").first():
            db.session.add(User(username="admin", password="1234"))
            db.session.commit()

    app.run(debug=True)