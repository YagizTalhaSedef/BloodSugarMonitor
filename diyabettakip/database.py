import mysql.connector

# Import config
try:
    from config import DB_HOST, DB_USER, DB_PASSWORD, DB_NAME, DB_CHARSET
except ImportError:
    print("UYARI: config.py bulunamadı. config.example.py dosyasını config.py olarak kopyalayın ve düzenleyin.")
    DB_HOST = "localhost"
    DB_USER = "root"
    DB_PASSWORD = "YOUR_PASSWORD"
    DB_NAME = "diyabet"
    DB_CHARSET = "utf8mb4"

def tablo_olustur():
    conn = mysql.connector.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        charset=DB_CHARSET,
        collation="utf8mb4_turkish_ci"
    )

    cursor = conn.cursor()

    # Create tables in the correct order for foreign keys
    # First, create tables with no dependencies
    
    # Doktorlar tablosu (no foreign keys)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS Doktorlar (
        tc_kimlik_no CHAR(11) PRIMARY KEY,
        sifre VARCHAR(8) NOT NULL,
        isim_soyisim VARCHAR(100) NOT NULL,
        cinsiyet CHAR(1),
        mail VARCHAR(100),
        uzmanlik VARCHAR(100),
        profil_foto LONGBLOB NULL
    ) CHARACTER SET utf8mb4 COLLATE utf8mb4_turkish_ci;
    """)

    # Kullanıcılar tablosu (no foreign keys)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS Kullanicilar (
        tc_kimlik_no CHAR(11) PRIMARY KEY,
        ad VARCHAR(50),
        soyad VARCHAR(50),
        dogum_tarihi DATE,
        cinsiyet CHAR(1),
        sifre VARCHAR(8)
    ) CHARACTER SET utf8mb4 COLLATE utf8mb4_turkish_ci;
    """)

    # Hastalar tablosu - depends on Doktorlar
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS Hastalar (
        tc_kimlik_no CHAR(11) PRIMARY KEY,
        sifre VARCHAR(8) NOT NULL,
        isim_soyisim VARCHAR(100) NOT NULL,
        cinsiyet CHAR(1),
        mail VARCHAR(100),
        doktor_tc CHAR(11),
        kayit_tarihi DATETIME DEFAULT CURRENT_TIMESTAMP,
        son_giris_tarihi DATETIME,
        gecerlimi BOOLEAN DEFAULT TRUE,  
        profil_foto LONGBLOB NULL,
        yas INT NULL,
        boy INT NULL COMMENT 'Boy (cm cinsinden)',
        kilo DECIMAL(5,2) NULL COMMENT 'Kilo (kg cinsinden)',
        vki DECIMAL(4,2) NULL COMMENT 'Vücut Kitle İndeksi',
        FOREIGN KEY (doktor_tc) REFERENCES Doktorlar(tc_kimlik_no) ON DELETE SET NULL
    ) CHARACTER SET utf8mb4 COLLATE utf8mb4_turkish_ci;
    """)

    # Now create tables that depend on Hastalar
    
    # Kan Şekeri Kayıtları - depends on Hastalar
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS KanSekeriKayitlari (
        id INT AUTO_INCREMENT PRIMARY KEY,
        tc_kimlik_no CHAR(11),
        tarih DATE NOT NULL COMMENT 'YYYY-MM-DD format',
        saat TIME NOT NULL COMMENT 'HH:MM:SS 24-hour format',
        olcum_zamani ENUM('Sabah', 'Ogle', 'Ikindi', 'Aksam', 'Gece') NOT NULL,
        seker_seviyesi DECIMAL(5,2) NOT NULL,
        olcum_turu VARCHAR(20) DEFAULT 'Hasta',
        zaman_uygun BOOLEAN DEFAULT FALSE,
        seviye_durumu ENUM('Dusuk', 'Normal', 'Orta', 'Yuksek', 'CokYuksek'),
        insülin_onerisi DECIMAL(3,1) DEFAULT 0,
        ortalamaya_dahil BOOLEAN DEFAULT TRUE,
        doktor_tc CHAR(11),
        FOREIGN KEY (tc_kimlik_no) REFERENCES Hastalar(tc_kimlik_no) ON DELETE CASCADE,
        FOREIGN KEY (doktor_tc) REFERENCES Doktorlar(tc_kimlik_no) ON DELETE SET NULL
    ) CHARACTER SET utf8mb4 COLLATE utf8mb4_turkish_ci;
    """)

    # İlk Ölçüm Kaydı tablosu - depends on Hastalar and Doktorlar
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS IlkOlcumKaydi (
        hasta_tc CHAR(11) PRIMARY KEY,
        doktor_tc CHAR(11) NOT NULL,
        olcum_tarihi DATE NOT NULL COMMENT 'YYYY-MM-DD format',
        FOREIGN KEY (hasta_tc) REFERENCES Hastalar(tc_kimlik_no) ON DELETE CASCADE,
        FOREIGN KEY (doktor_tc) REFERENCES Doktorlar(tc_kimlik_no) ON DELETE CASCADE
    ) CHARACTER SET utf8mb4 COLLATE utf8mb4_turkish_ci;
    """)

    # İnsülin Kayıtları tablosu - bildirildi alanını kaldırdık
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS InsulinKayitlari (
        id INT AUTO_INCREMENT PRIMARY KEY,
        hasta_tc CHAR(11),
        doktor_tc CHAR(11),
        tarih DATE NOT NULL,
        saat TIME DEFAULT NULL COMMENT 'İnsülin kullanım saati',
        doz DECIMAL(3,1) NOT NULL COMMENT 'ml cinsinden insülin dozu',
        kullanildi BOOLEAN DEFAULT NULL COMMENT 'NULL:Belirtilmemiş, 0:Kullanılmadı, 1:Kullanıldı',
        okundu BOOLEAN DEFAULT FALSE COMMENT 'Doktor tarafından okundu mu',
        FOREIGN KEY (hasta_tc) REFERENCES Hastalar(tc_kimlik_no) ON DELETE CASCADE,
        FOREIGN KEY (doktor_tc) REFERENCES Doktorlar(tc_kimlik_no) ON DELETE SET NULL
    ) CHARACTER SET utf8mb4 COLLATE utf8mb4_turkish_ci;
    """)

    # Uyarılar tablosu - depends on Hastalar and Doktorlar
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS Uyarilar (
        id INT AUTO_INCREMENT PRIMARY KEY,
        tc_kimlik_no CHAR(11),
        doktor_tc CHAR(11),
        tarih_zaman DATETIME DEFAULT CURRENT_TIMESTAMP,
        uyari_tipi ENUM('OlcumEksik', 'OlcumYetersiz', 'KritikDusuk', 'KritikYuksek', 'OrtaYuksek', 'Yuksek'),
        aciklama TEXT,
        seker_seviyesi DECIMAL(5,2) NULL,
        okundu BOOLEAN DEFAULT FALSE,
        FOREIGN KEY (tc_kimlik_no) REFERENCES Hastalar(tc_kimlik_no) ON DELETE CASCADE,
        FOREIGN KEY (doktor_tc) REFERENCES Doktorlar(tc_kimlik_no) ON DELETE SET NULL
    ) CHARACTER SET utf8mb4 COLLATE utf8mb4_turkish_ci;
    """)

   
   
    conn.commit()
    cursor.close()
    conn.close()
    print("Tablolar kontrol edildi.")
