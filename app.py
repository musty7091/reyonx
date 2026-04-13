from flask import Flask
import os
from dotenv import load_dotenv
from database import db
from flask_migrate import Migrate

# Gizli kasa dosyasını (.env) sisteme yüklüyoruz
load_dotenv()

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
from routes.settings_routes import settings_bp

# Admin kullanıcı oluşturmak için User modelini çağırıyoruz
from models import User

app = Flask(__name__)

# AYARLAR (Bilgileri .env dosyasından çekiyoruz)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY")
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///reyonx.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

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
app.register_blueprint(settings_bp)

# ==========================================
# UYGULAMA BAŞLATMA VE VERİTABANI KURULUMU
# ==========================================
if __name__ == "__main__":
    with app.app_context():
        # Veritabanı tablolarını oluşturur
        db.create_all()
        
        # Sistemde 'admin' isimli bir kullanıcı var mı diye bakıyoruz
        admin_user = User.query.filter_by(username="admin").first()
        
        # Eğer admin hesabı henüz hiç oluşturulmamışsa:
        if not admin_user:
            admin_user = User(username="admin")
            
            # Şifreyi kodun içinden değil, .env dosyasındaki kasadan alıyoruz
            # Eğer kasada şifre bulamazsa varsayılan olarak "1234" yapar
            default_password = os.getenv("ADMIN_DEFAULT_PASS", "1234")
            
            # models.py içindeki hashleme fonksiyonunu kullanarak şifreyi gizliyoruz
            admin_user.set_password(default_password) 
            
            db.session.add(admin_user)
            db.session.commit()
            print("Sistem İlk Kurulum: Güvenli yönetici hesabı oluşturuldu.")

    # Geliştirme modunda uygulamayı çalıştır
    app.run(debug=True)