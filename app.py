from flask import Flask, session, redirect, url_for, request
import os
from dotenv import load_dotenv
from database import db
from flask_migrate import Migrate
from datetime import datetime, timedelta, timezone
from flask_wtf import CSRFProtect

# .env yükle
load_dotenv()

# Blueprintler
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

from models import User

app = Flask(__name__)

# ==========================================
# GÜVENLİ CONFIG
# ==========================================

SECRET_KEY = os.getenv("SECRET_KEY")

if not SECRET_KEY:
    raise RuntimeError("SECRET_KEY tanımlı değil! .env dosyasını kontrol et.")

app.config["SECRET_KEY"] = SECRET_KEY

# DB
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv(
    "DATABASE_URL",
    "sqlite:///reyonx.db"
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Session güvenliği
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_SECURE"] = False
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(minutes=30)

# CSRF koruma
csrf = CSRFProtect(app)

# DB init
db.init_app(app)
migrate = Migrate(app, db)

# Blueprint register
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
# LOGIN + SESSION KONTROL
# ==========================================

@app.before_request
def security_control():

    # endpoint yoksa geç
    if not request.endpoint:
        return

    # login gerekmeyenler
    allowed_routes = ["auth.login", "static"]

    if request.endpoint in allowed_routes:
        return

    # login kontrolü
    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    # session timeout kontrolü
    login_time = session.get("login_time")

    if login_time:
        try:
            login_time = datetime.fromisoformat(login_time)
            
            if login_time.tzinfo is None:
                login_time = login_time.replace(tzinfo=timezone.utc)    
        except:
            session.clear()
            return redirect(url_for("auth.login"))

        now = datetime.now(timezone.utc)

        if now - login_time > timedelta(minutes=30):
            session.clear()
            return redirect(url_for("auth.login"))

        # aktif kullanıcı → süreyi yenile
        session["login_time"] = now.isoformat()

# ==========================================
# İLK KURULUM (ADMIN)
# ==========================================

if __name__ == "__main__":
    with app.app_context():

        admin_user = User.query.filter_by(username="admin").first()

        if not admin_user:
            default_password = os.getenv("ADMIN_DEFAULT_PASS")

            if not default_password:
                raise RuntimeError(
                    "ADMIN_DEFAULT_PASS .env içinde tanımlı olmalı!"
                )

            admin_user = User(username="admin")
            admin_user.set_password(default_password)

            db.session.add(admin_user)
            db.session.commit()

            print("Admin kullanıcı oluşturuldu.")

    DEBUG_MODE = os.getenv("DEBUG", "False") == "True"

    app.run(debug=DEBUG_MODE)