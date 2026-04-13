from flask import Blueprint, request, redirect, render_template, session, flash
from models import User

# Bu dosyayı bir modül (Blueprint) olarak tanımlıyoruz
auth_bp = Blueprint("auth", __name__)

# Her tıklamada kişinin giriş yapıp yapmadığını kontrol eden güvenlik kapımız
@auth_bp.before_app_request
def check_login():
    allowed = ["auth.login", "static"]
    if request.endpoint not in allowed and "user_id" not in session:
        return redirect("/login")

@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        
        user = User.query.filter_by(username=username).first()
        
        # ARTIK DÜZ ŞİFRE KONTROLÜ YAPMIYORUZ! check_password fonksiyonunu kullanıyoruz.
        if user and user.check_password(password):
            session["user_id"] = user.id
            flash("Başarıyla giriş yapıldı!", "success")
            return redirect("/")
        else:
            flash("Kullanıcı adı veya şifre hatalı!", "danger")
            
    return render_template("login.html")

@auth_bp.route("/logout")
def logout():
    session.clear()
    return redirect("/login")