from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from models import User
from database import db
from datetime import datetime, timedelta
from utils.audit import log_action

auth_bp = Blueprint("auth", __name__)

MAX_ATTEMPTS = 5
LOCK_MINUTES = 5
SESSION_TIMEOUT_MINUTES = 30


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":

        username = request.form.get("username")
        password = request.form.get("password")

        user = User.query.filter_by(username=username).first()

        # Kullanıcı yoksa (aynı davranış)
        if not user:
            flash("Kullanıcı adı veya şifre hatalı", "danger")
            return redirect(url_for("auth.login"))

        # Hesap kilitli mi?
        if user.lock_until and user.lock_until > datetime.utcnow():
            kalan = (user.lock_until - datetime.utcnow()).seconds // 60 + 1
            flash(f"Hesap kilitli. {kalan} dakika sonra tekrar deneyin.", "danger")
            return redirect(url_for("auth.login"))

        # Şifre kontrol
        if user.check_password(password):
            

            # RESET
            user.failed_login_attempts = 0
            user.lock_until = None
            db.session.commit()

            # 🔐 SESSION HARDENING
            session.clear()  # eski session temizle
            session["user_id"] = user.id
            session["login_time"] = datetime.utcnow().isoformat()

            log_action("LOGIN", "User", user.id, "Kullanıcı giriş yaptı")

            flash("Giriş başarılı", "success")

            return redirect(url_for("dashboard.index"))

        else:
            user.failed_login_attempts += 1

            if user.failed_login_attempts >= MAX_ATTEMPTS:
                user.lock_until = datetime.utcnow() + timedelta(minutes=LOCK_MINUTES)
                user.failed_login_attempts = 0
                flash("Çok fazla hatalı giriş. Hesap 5 dakika kilitlendi.", "danger")
            else:
                kalan = MAX_ATTEMPTS - user.failed_login_attempts
                flash(f"Hatalı giriş. {kalan} hakkınız kaldı.", "warning")

            db.session.commit()
            return redirect(url_for("auth.login"))

    return render_template("login.html")


@auth_bp.route("/logout")
def logout():
    session.clear()
    flash("Çıkış yapıldı", "info")
    return redirect(url_for("auth.login"))