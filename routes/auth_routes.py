from flask import Blueprint, request, redirect, render_template, session
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
        u = request.form.get("username")
        p = request.form.get("password")
        user = User.query.filter_by(username=u).first()
        if user and user.password == p:
            session["user_id"] = user.id
            return redirect("/")
        return "Hatalı giriş"
    return render_template("login.html")

@auth_bp.route("/logout")
def logout():
    session.clear()
    return redirect("/login")