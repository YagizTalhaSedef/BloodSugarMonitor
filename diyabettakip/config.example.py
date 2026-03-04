# Veritabanı Ayarları
# Bu dosyayı config.py olarak kopyalayın ve kendi değerlerinizi girin

DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "YOUR_PASSWORD_HERE",  # MySQL şifrenizi buraya girin
    "database": "diyabet",
    "charset": "utf8mb4"
}

# Email Ayarları (Gmail için)
EMAIL_CONFIG = {
    "sender_email": "your_email@gmail.com",  # Gönderen email adresi
    "password": "your_app_password",  # Gmail App Password
    "smtp_server": "smtp.gmail.com",
    "smtp_port": 587
}
