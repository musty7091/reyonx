from flask import Blueprint, render_template, request, redirect, flash
from database import db
from models import SystemSetting

settings_bp = Blueprint("settings", __name__)

@settings_bp.route("/settings", methods=["GET", "POST"])
def settings():
    # Prim oranı ayarını veritabanından bul, yoksa %5 olarak oluştur
    bonus_rate_setting = SystemSetting.query.filter_by(setting_key="bonus_rate").first()
    if not bonus_rate_setting:
        bonus_rate_setting = SystemSetting(setting_key="bonus_rate", setting_value="5")
        db.session.add(bonus_rate_setting)
        db.session.commit()

    if request.method == "POST":
        new_rate = request.form.get("bonus_rate")
        if new_rate:
            # Kullanıcı virgül girerse otomatik noktaya çevir
            new_rate = new_rate.replace(',', '.')
            try:
                # Sayısal kontrol
                float(new_rate)
                bonus_rate_setting.setting_value = str(new_rate)
                db.session.commit()
                flash("Ayarlar başarıyla güncellendi!", "success")
            except ValueError:
                flash("Lütfen geçerli bir sayı giriniz!", "danger")
        return redirect("/settings")

    return render_template("settings.html", bonus_rate=bonus_rate_setting.setting_value)