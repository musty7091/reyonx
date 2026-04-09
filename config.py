import os

class Config:
    SECRET_KEY = "super-secret-key"
    SQLALCHEMY_DATABASE_URI = "sqlite:///reyonx.db"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Personel Prim Oranı (Örneğin %5 için 0.05)
    # İleride bunu panelden değiştirebilir hale de getirebiliriz.
    BONUS_RATE = 0.05