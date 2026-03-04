import mysql.connector
import hashlib
import random
import string
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import sys
# Import database module for table creation
import os.path
import importlib.util

# Import config
try:
    from config import DB_HOST, DB_USER, DB_PASSWORD, DB_NAME, DB_CHARSET
    from config import EMAIL_SENDER, EMAIL_PASSWORD, EMAIL_SMTP_SERVER, EMAIL_SMTP_PORT
except ImportError:
    print("UYARI: config.py bulunamadı. config.example.py dosyasını config.py olarak kopyalayın ve düzenleyin.")
    DB_HOST = "localhost"
    DB_USER = "root"
    DB_PASSWORD = "YOUR_PASSWORD"
    DB_NAME = "diyabet"
    DB_CHARSET = "utf8mb4"
    EMAIL_SENDER = "your_email@gmail.com"
    EMAIL_PASSWORD = "your_password"
    EMAIL_SMTP_SERVER = "smtp.gmail.com"
    EMAIL_SMTP_PORT = 587

# Import tablo_olustur function from database.py
def import_database_module():
    database_path = os.path.join(os.path.dirname(__file__), "database.py")
    if os.path.exists(database_path):
        spec = importlib.util.spec_from_file_location("database", database_path)
        database = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(database)
        return database
    else:
        print("Database module not found!")
        return None

def veritabani_olustur():
    conn = mysql.connector.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD
    )
    cursor = conn.cursor()
    cursor.execute(f"CREATE DATABASE IF NOT EXISTS {DB_NAME} CHARACTER SET utf8mb4 COLLATE utf8mb4_turkish_ci;")
    conn.close()

# Veritabanı bağlantı fonksiyonu
def baglanti_kur():
    conn = mysql.connector.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        charset=DB_CHARSET
    )
    return conn

# Şifre hash fonksiyonu
def sifre_hashleme(sifre):
    # Şifreyi UTF-8 formatına dönüştür ve SHA-256 ile hashle
    hash_object = hashlib.sha256(sifre.encode('utf-8'))
    return hash_object.hexdigest()

# Rastgele şifre oluşturma (güvenliği artırılmış)
def rastgele_sifre_olustur():
    # 8 karakterli karmaşık şifre oluştur (büyük/küçük harfler, rakamlar ve özel karakterler)
    uppercase_letters = string.ascii_uppercase
    lowercase_letters = string.ascii_lowercase
    digits = string.digits
    special_chars = "%!._"
    
    # Her kategoriden en az bir karakter içeren şifre oluştur
    password = [
        random.choice(uppercase_letters),  # Büyük harf
        random.choice(lowercase_letters),  # Küçük harf
        random.choice(digits),             # Rakam
        random.choice(special_chars)       # Özel karakter
    ]
    
    # Kalan 4 karakteri tüm gruplardan rastgele seç
    all_chars = uppercase_letters + lowercase_letters + digits + special_chars
    password.extend(random.choices(all_chars, k=4))
    
    # Şifredeki karakterlerin sırasını karıştır
    random.shuffle(password)
    
    return ''.join(password)

# Email gönderme fonksiyonu
def email_gonder(alici_email, konu, icerik):
    # Email sunucu ayarları
    sender_email = EMAIL_SENDER
    password = EMAIL_PASSWORD
    
    # Email oluşturma
    mesaj = MIMEMultipart()
    mesaj["From"] = sender_email
    mesaj["To"] = alici_email
    mesaj["Subject"] = konu
    
    # Email içeriği
    mesaj.attach(MIMEText(icerik, "plain"))
    
    try:
        # SMTP sunucusuna bağlanma
        server = smtplib.SMTP(EMAIL_SMTP_SERVER, EMAIL_SMTP_PORT)
        server.starttls()  # Güvenli bağlantı
        server.login(sender_email, password)
        
        # Email gönderme
        text = mesaj.as_string()
        server.sendmail(sender_email, alici_email, text)
        server.quit()
        return True
    except Exception as e:
        print(f"Email gönderme hatası: {e}")
        return False

# Doktor kayıt fonksiyonu
def doktor_kaydet(tc_kimlik_no, isim_soyisim, cinsiyet, mail, uzmanlik):
    # TC kimlik numarası kontrolü
    if len(tc_kimlik_no) != 11 or not tc_kimlik_no.isdigit():
        return False, "TC Kimlik No 11 haneli sayılardan oluşmalıdır."
    
    # Rastgele şifre oluştur
    sifre = rastgele_sifre_olustur()
    
    # Şifreyi hashle
    hashed_sifre = sifre_hashleme(sifre)
    
    conn = baglanti_kur()
    cursor = conn.cursor()
    
    try:
        # Doktoru veritabanına kaydet
        cursor.execute("""
        INSERT INTO Doktorlar (tc_kimlik_no, sifre, isim_soyisim, cinsiyet, mail, uzmanlik)
        VALUES (%s, %s, %s, %s, %s, %s)
        """, (tc_kimlik_no, hashed_sifre, isim_soyisim, cinsiyet, mail, uzmanlik))
        
        conn.commit()
        
        # Şifreyi email ile gönder
        email_konu = "Diyabet Takip Sistemi - Doktor Hesap Bilgileri"
        email_icerik = f"""
        Sayın {isim_soyisim},
        
        Diyabet Takip Sistemi doktor hesabınız oluşturulmuştur.
        
        TC Kimlik No: {tc_kimlik_no}
        Şifre: {sifre}
        
        Lütfen bu şifreyi kimseyle paylaşmayınız.
        """
        
        email_sonuc = email_gonder(mail, email_konu, email_icerik)
        
        if email_sonuc:
            return True, "Doktor kaydı başarılı. Şifre email ile gönderildi."
        else:
            return True, "Doktor kaydı başarılı fakat şifre email ile gönderilemedi."
            
    except mysql.connector.Error as err:
        if err.errno == 1062:  # Duplicate entry error
            return False, "Bu TC Kimlik No ile kayıtlı bir doktor zaten var."
        else:
            return False, f"Veritabanı hatası: {err}"
    finally:
        cursor.close()
        conn.close()

# Hasta kayıt fonksiyonu (doktor tarafından) - güncellendi
def hasta_kaydet(doktor_tc, hasta_tc, isim_soyisim, cinsiyet, mail):
    # TC kimlik numarası kontrolü
    if len(hasta_tc) != 11 or not hasta_tc.isdigit():
        return False, "TC Kimlik No 11 haneli sayılardan oluşmalıdır."
    
    # Doktorun yetkisini kontrol et
    conn = baglanti_kur()
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT * FROM Doktorlar WHERE tc_kimlik_no = %s", (doktor_tc,))
        doktor = cursor.fetchone()
        
        if not doktor:
            return False, "Yetkisiz işlem. Doktor bulunamadı."
        
        # Rastgele şifre oluştur
        sifre = rastgele_sifre_olustur()
        
        # Şifreyi hashle
        hashed_sifre = sifre_hashleme(sifre)
        
        # Hastayı veritabanına kaydet (doktor_tc eklendi)
        cursor.execute("""
        INSERT INTO Hastalar (tc_kimlik_no, sifre, isim_soyisim, cinsiyet, mail, doktor_tc)
        VALUES (%s, %s, %s, %s, %s, %s)
        """, (hasta_tc, hashed_sifre, isim_soyisim, cinsiyet, mail, doktor_tc))
        
        conn.commit()
        
        # Şifreyi email ile gönder
        email_konu = "Diyabet Takip Sistemi - Hasta Hesap Bilgileri"
        email_icerik = f"""
        Sayın {isim_soyisim},
        
        Diyabet Takip Sistemi hasta hesabınız oluşturulmuştur.
        
        TC Kimlik No: {hasta_tc}
        Şifre: {sifre}
        
        Lütfen bu şifreyi kimseyle paylaşmayınız.
        """
        
        email_sonuc = email_gonder(mail, email_konu, email_icerik)
        
        if email_sonuc:
            return True, "Hasta kaydı başarılı. Şifre email ile gönderildi."
        else:
            return True, "Hasta kaydı başarılı fakat şifre email ile gönderilemedi."
            
    except mysql.connector.Error as err:
        if err.errno == 1062:  # Duplicate entry error
            return False, "Bu TC Kimlik No ile kayıtlı bir hasta zaten var."
        else:
            return False, f"Veritabanı hatası: {err}"
    finally:
        cursor.close()
        conn.close()

# Doktor giriş fonksiyonu - son giriş tarihi güncellemesi kaldırıldı
def doktor_giris(tc_kimlik_no, sifre):
    conn = baglanti_kur()
    cursor = conn.cursor(dictionary=True)
    
    try:
        cursor.execute("SELECT * FROM Doktorlar WHERE tc_kimlik_no = %s", (tc_kimlik_no,))
        doktor = cursor.fetchone()
        
        if not doktor:
            return False, "TC Kimlik No veya şifre hatalı."
        
        # Girilen şifreyi hashle ve veritabanındaki ile karşılaştır
        hashed_sifre = sifre_hashleme(sifre)
        
        if hashed_sifre != doktor['sifre']:
            return False, "TC Kimlik No veya şifre hatalı."
            
        return True, doktor
        
    except Exception as e:
        return False, f"Giriş hatası: {e}"
    finally:
        cursor.close()
        conn.close()

# Hasta giriş fonksiyonu - güncellendi ve hata ele alma eklendi
def hasta_giris(tc_kimlik_no, sifre):
    conn = baglanti_kur()
    cursor = conn.cursor(dictionary=True)
    
    try:
        cursor.execute("SELECT * FROM Hastalar WHERE tc_kimlik_no = %s", (tc_kimlik_no,))
        hasta = cursor.fetchone()
        
        if not hasta:
            return False, "TC Kimlik No veya şifre hatalı."
        
        # Girilen şifreyi hashle ve veritabanındaki ile karşılaştır
        hashed_sifre = sifre_hashleme(sifre)
        
        if hashed_sifre != hasta['sifre']:
            return False, "TC Kimlik No veya şifre hatalı."
        
        # Ensure all needed fields are present
        required_fields = ['tc_kimlik_no', 'isim_soyisim', 'cinsiyet', 'mail']
        for field in required_fields:
            if field not in hasta or hasta[field] is None:
                if field == 'cinsiyet':
                    hasta[field] = 'E'  # Default to male
                else:
                    hasta[field] = ""  # Default to empty string
        
        # Son giriş tarihini güncelle
        try:
            cursor.execute("""
            UPDATE Hastalar SET son_giris_tarihi = CURRENT_TIMESTAMP
            WHERE tc_kimlik_no = %s
            """, (tc_kimlik_no,))
            conn.commit()
        except Exception as e:
            # Continue even if this fails, but don't print the error
            pass
            
        return True, hasta
        
    except Exception as e:
        return False, f"Giriş hatası: {e}"
    finally:
        cursor.close()
        conn.close()

# Şifre sıfırlama fonksiyonu (hem doktor hem hasta için)
def sifre_sifirla(tc_kimlik_no, mail, kullanici_tipi):
    conn = baglanti_kur()
    cursor = conn.cursor(dictionary=True)
    
    try:
        # Kullanıcı tipine göre tabloyu belirle
        if kullanici_tipi == "doktor":
            tablo = "Doktorlar"
        elif kullanici_tipi == "hasta":
            tablo = "Hastalar"
        else:
            return False, "Geçersiz kullanıcı tipi."
        
        # TC ve mail ile kullanıcıyı bul
        cursor.execute(f"SELECT * FROM {tablo} WHERE tc_kimlik_no = %s AND mail = %s", 
                      (tc_kimlik_no, mail))
        kullanici = cursor.fetchone()
        
        if not kullanici:
            return False, "Kullanıcı bulunamadı."
        
        # Yeni rastgele şifre oluştur
        yeni_sifre = rastgele_sifre_olustur()
        
        # Şifreyi hashle
        hashed_sifre = sifre_hashleme(yeni_sifre)
        
        # Şifreyi güncelle
        cursor.execute(f"UPDATE {tablo} SET sifre = %s WHERE tc_kimlik_no = %s", 
                      (hashed_sifre, tc_kimlik_no))
        
        conn.commit()
        
        # Yeni şifreyi email ile gönder
        email_konu = "Diyabet Takip Sistemi - Şifre Sıfırlama"
        email_icerik = f"""
        Sayın {kullanici['isim_soyisim']},
        
        Diyabet Takip Sistemi şifreniz sıfırlanmıştır.
        
        Yeni şifreniz: {yeni_sifre}
        
        Lütfen bu şifreyi kimseyle paylaşmayınız.
        """
        
        email_sonuc = email_gonder(mail, email_konu, email_icerik)
        
        if email_sonuc:
            return True, "Şifre başarıyla sıfırlandı ve email ile gönderildi."
        else:
            return True, "Şifre başarıyla sıfırlandı fakat email ile gönderilemedi."
            
    except Exception as e:
        return False, f"Şifre sıfırlama hatası: {e}"
    finally:
        cursor.close()
        conn.close()

# Doktorun hastalarını listeleme fonksiyonu
def hastalari_listele(doktor_tc):
    conn = baglanti_kur()
    cursor = conn.cursor(dictionary=True)
    
    try:
        cursor.execute("""
        SELECT tc_kimlik_no, isim_soyisim, cinsiyet, mail 
        FROM Hastalar 
        WHERE doktor_tc = %s
        ORDER BY isim_soyisim
        """, (doktor_tc,))
        
        hastalar = cursor.fetchall()
        return True, hastalar
    except Exception as e:
        return False, f"Hasta listeleme hatası: {e}"
    finally:
        cursor.close()
        conn.close()

# Hasta silme fonksiyonu (doktor tarafından)
def hasta_sil(doktor_tc, hasta_tc):
    conn = baglanti_kur()
    cursor = conn.cursor()
    
    try:
        # Hastanın bu doktora ait olup olmadığını kontrol et
        cursor.execute("""
        SELECT * FROM Hastalar 
        WHERE tc_kimlik_no = %s AND doktor_tc = %s
        """, (hasta_tc, doktor_tc))
        
        hasta = cursor.fetchone()
        
        if not hasta:
            return False, "Bu hasta sizin listenizde değil veya bulunamadı."
        
        # Hastanın bilgilerini önce değişkene kaydet (silme işlemi için email gönderilecekse)
        cursor.execute("SELECT isim_soyisim, mail FROM Hastalar WHERE tc_kimlik_no = %s", (hasta_tc,))
        hasta_bilgi = cursor.fetchone()
        isim_soyisim = hasta_bilgi[0]
        email = hasta_bilgi[1]
        
        # Hastayı sil
        cursor.execute("DELETE FROM Hastalar WHERE tc_kimlik_no = %s", (hasta_tc,))
        conn.commit()
        
        # İsteğe bağlı: Silme işlemi hakkında hastaya email bilgilendirmesi
        email_konu = "Diyabet Takip Sistemi - Hesap Bilgilendirmesi"
        email_icerik = f"""
        Sayın {isim_soyisim},
        
        Diyabet Takip Sistemi'ndeki hesabınız doktorunuz tarafından silinmiştir.
        
        Sorularınız için lütfen doktorunuzla iletişime geçiniz.
        """
        
        email_sonuc = email_gonder(email, email_konu, email_icerik)
        
        return True, "Hasta başarıyla silindi."
        
    except Exception as e:
        return False, f"Hasta silme hatası: {e}"
    finally:
        cursor.close()
        conn.close()

# Hasta arama fonksiyonu (doktor için)
def hasta_ara(doktor_tc, arama_metni):
    conn = baglanti_kur()
    cursor = conn.cursor(dictionary=True)
    
    try:
        # TC kimlik no veya isim ile arama yapabilme
        cursor.execute("""
        SELECT tc_kimlik_no, isim_soyisim, cinsiyet, mail 
        FROM Hastalar 
        WHERE doktor_tc = %s AND (tc_kimlik_no LIKE %s OR isim_soyisim LIKE %s)
        ORDER BY isim_soyisim
        """, (doktor_tc, f"%{arama_metni}%", f"%{arama_metni}%"))
        
        hastalar = cursor.fetchall()
        return True, hastalar
    except Exception as e:
        return False, f"Hasta arama hatası: {e}"
    finally:
        cursor.close()
        conn.close()

# Fix database schema issue (one-time fix)
def fix_database_schema():
    conn = baglanti_kur()
    cursor = conn.cursor()
    
    try:
        # Mevcut tabloları sil ve yeniden oluştur
        print("Şifre alanı boyutu sorunu tespit edildi. Tabloları yeniden oluşturuyorum...")
        
        # Drop tables if they exist
        cursor.execute("DROP TABLE IF EXISTS Hastalar")
        cursor.execute("DROP TABLE IF EXISTS Doktorlar")
        
        conn.commit()
        print("Tablolar başarıyla silindi, yeniden oluşturulacak.")
        
        return True
    except Exception as e:
        print(f"Şema düzeltme hatası: {e}")
        return False
    finally:
        cursor.close()
        conn.close()

# Enhanced database initialization with automatic repair - with safeguards to preserve data
def initialize_database():
    # Create database if it doesn't exist
    veritabani_olustur()
    
    # Only repair tables if absolutely necessary
    if check_database_structure() == False:
        print("Database structure issues detected. Attempting repair...")
        try_repair_tables()
    
    # Create tables if they don't exist (uses IF NOT EXISTS so won't drop existing tables)
    database_module = import_database_module()
    if database_module:
        database_module.tablo_olustur()
    else:
        print("Failed to import database module. Tables may not be created!")
    
    # Check and add missing columns for tables
    add_missing_columns()
    
    # Eksik sütunları kontrol et ve ekle
    check_and_add_missing_database_columns()

# New function to check database structure
def check_database_structure():
    """Check if database structure is intact before making any destructive changes"""
    try:
        conn = baglanti_kur()
        cursor = conn.cursor()
        
        # Check if essential tables exist and have basic structure intact
        essential_tables = ["Doktorlar", "Hastalar", "KanSekeriKayitlari"]
        all_good = True
        
        for table in essential_tables:
            try:
                cursor.execute(f"DESCRIBE {table}")
                cursor.fetchall()  # Consume results
            except Exception as e:
                print(f"Table {table} has issues: {e}")
                all_good = False
        
        return all_good
    except Exception as e:
        print(f"Database structure check failed: {e}")
        return False
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

# Extract column checking into a separate function
def add_missing_columns():
    """Add missing columns to existing tables - this is non-destructive"""
    try:
        conn = baglanti_kur()
        cursor = conn.cursor()
        
        try:
            # Check if Hastalar table has required columns
            cursor.execute("DESCRIBE Hastalar")
            columns = [column[0].lower() for column in cursor.fetchall()]
            
            if 'kayit_tarihi' not in columns:
                cursor.execute("ALTER TABLE Hastalar ADD COLUMN kayit_tarihi DATETIME DEFAULT CURRENT_TIMESTAMP")
                print("Added kayit_tarihi column to Hastalar table")
                
            if 'son_giris_tarihi' not in columns:
                cursor.execute("ALTER TABLE Hastalar ADD COLUMN son_giris_tarihi DATETIME NULL")
                print("Added son_giris_tarihi column to Hastalar table")
                
            if 'profil_foto' not in columns:
                cursor.execute("ALTER TABLE Hastalar ADD COLUMN profil_foto LONGBLOB NULL")
                print("Added profil_foto column to Hastalar table")
            
            # Check if Doktorlar table has profil_foto column
            cursor.execute("DESCRIBE Doktorlar")
            columns = [column[0].lower() for column in cursor.fetchall()]
            
            if 'profil_foto' not in columns:
                cursor.execute("ALTER TABLE Doktorlar ADD COLUMN profil_foto LONGBLOB NULL")
                print("Added profil_foto column to Doktorlar table")
            
            # Remove date columns from Doktorlar table if they exist
            if 'kayit_tarihi' in columns:
                cursor.execute("ALTER TABLE Doktorlar DROP COLUMN kayit_tarihi")
                print("Removed kayit_tarihi column from Doktorlar table")
                
            if 'son_giris_tarihi' in columns:
                cursor.execute("ALTER TABLE Doktorlar DROP COLUMN son_giris_tarihi")
                print("Removed son_giris_tarihi column from Doktorlar table")
                
            # Check if KanSekeriKayitlari table has the required columns
            try:
                cursor.execute("DESCRIBE KanSekeriKayitlari")
                columns = [column[0].lower() for column in cursor.fetchall()]
                
                if 'tarih' not in columns:
                    print("'tarih' column not found in KanSekeriKayitlari table, adding it...")
                    cursor.execute("ALTER TABLE KanSekeriKayitlari ADD COLUMN tarih DATE NOT NULL")
                    print("Added tarih column to KanSekeriKayitlari table")
                
                if 'saat' not in columns:
                    print("'saat' column not found in KanSekeriKayitlari table, adding it...")
                    cursor.execute("ALTER TABLE KanSekeriKayitlari ADD COLUMN saat TIME")
                    print("Added saat column to KanSekeriKayitlari table")
                
                # Check other columns as well
                required_columns = [
                    'olcum_zamani', 'seker_seviyesi', 'zaman_uygun', 
                    'seviye_durumu', 'ortalamaya_dahil'
                ]
                
                for col in required_columns:
                    if col not in columns:
                        print(f"'{col}' column not found in KanSekeriKayitlari table. Table may need repair.")
                        repair_kan_sekeri_table()
                        break
                        
            except Exception as e:
                print(f"Error checking KanSekeriKayitlari table structure: {e}")
                repair_kan_sekeri_table()
            
            conn.commit()
        except Exception as e:
            print(f"Error checking or modifying columns: {e}")
        finally:
            cursor.close()
            conn.close()
    except Exception as e:
        print(f"Database connection error: {e}")

# Fixed function to properly handle result sets
def try_repair_tables():
    conn = None
    cursor = None
    try:
        conn = baglanti_kur()
        cursor = conn.cursor()
        
        # Check if table structure needs repair
        try:
            cursor.execute("SELECT tc_kimlik_no, tarih, saat FROM KanSekeriKayitlari LIMIT 1")
            # Make sure to fetch all results
            cursor.fetchall()  # This consumes the result set
            print("KanSekeriKayitlari table structure looks OK")
            return False
        except Exception as e:
            print(f"KanSekeriKayitlari table check failed: {e}")
            # Drop the problematic table
            print("KanSekeriKayitlari table appears to have issues, dropping...")
            cursor.execute("DROP TABLE IF EXISTS KanSekeriKayitlari")
            conn.commit()
            return True
    except Exception as e:
        print(f"Error during table repair check: {e}")
        return False
    finally:
        # Properly close resources in finally block
        if cursor:
            try:
                # This will consume any remaining result sets
                while cursor.nextset():
                    pass
            except:
                pass
            cursor.close()
        if conn:
            conn.close()

# Updated repair function to work with existing cursor or create new one
def repair_kan_sekeri_table(cursor=None):
    close_conn = False
    conn = None
    
    if cursor is None:
        conn = baglanti_kur()
        cursor = conn.cursor()
        close_conn = True
    
    try:
        print("Repairing KanSekeriKayitlari table...")
        
        # Drop the existing table if it exists
        cursor.execute("DROP TABLE IF EXISTS KanSekeriKayitlari")
        
        # Create the table with all required columns
        cursor.execute("""
        CREATE TABLE KanSekeriKayitlari (
            id INT AUTO_INCREMENT PRIMARY KEY,
            tc_kimlik_no CHAR(11),
            tarih DATE NOT NULL,
            saat TIME NOT NULL,
            olcum_zamani ENUM('Sabah', 'Ogle', 'Ikindi', 'Aksam', 'Gece') NOT NULL,
            seker_seviyesi DECIMAL(5,2) NOT NULL,
            olcum_turu VARCHAR(20) DEFAULT 'Hasta',
            zaman_uygun BOOLEAN DEFAULT FALSE,
            seviye_durumu ENUM('Dusuk', 'Normal', 'Orta', 'Yuksek', 'CokYuksek'),
            insülin_onerisi DECIMAL(3,1) DEFAULT 0,
            ortalamaya_dahil BOOLEAN DEFAULT TRUE,
            FOREIGN KEY (tc_kimlik_no) REFERENCES Hastalar(tc_kimlik_no) ON DELETE CASCADE
        ) CHARACTER SET utf8mb4 COLLATE utf8mb4_turkish_ci;
        """)
        
        if conn:
            conn.commit()
        print("KanSekeriKayitlari table created with all required columns")
        
        # Try to restore data from backup if it exists
        cursor.execute("SHOW TABLES LIKE 'KanSekeriKayitlari_Backup'")
        backup_exists = cursor.fetchone()
        
        if backup_exists:
            try:
                # Get columns from both tables
                cursor.execute("DESCRIBE KanSekeriKayitlari")
                new_columns = [column[0] for column in cursor.fetchall()]
                
                cursor.execute("DESCRIBE KanSekeriKayitlari_Backup")
                backup_columns = [column[0] for column in cursor.fetchall()]
                
                # Find common columns
                common_columns = [col for col in backup_columns if col in new_columns]
                
                if common_columns:
                    columns_str = ", ".join(common_columns)
                    cursor.execute(f"INSERT IGNORE INTO KanSekeriKayitlari ({columns_str}) SELECT {columns_str} FROM KanSekeriKayitlari_Backup")
                    print("Data restored from backup")
            except Exception as e:
                print(f"Data restoration error: {e}")
        
        conn.commit()
        print("KanSekeriKayitlari table repair completed successfully")
        return True, "Table repaired successfully"
        
    except Exception as e:
        print(f"Error repairing table: {e}")
        return False, f"Error repairing table: {e}"
    finally:
        if close_conn and conn:
            cursor.close()
            conn.close()

# Profil fotoğrafı güncelleme fonksiyonu (doktor ve hasta için)
def profil_foto_guncelle(tc_kimlik_no, foto_data, kullanici_tipi):
    conn = baglanti_kur()
    cursor = conn.cursor()
    
    try:
        # Kullanıcı tipine göre tabloyu belirle
        if kullanici_tipi == "doktor":
            tablo = "Doktorlar"
        elif kullanici_tipi == "hasta":
            tablo = "Hastalar"
        else:
            return False, "Geçersiz kullanıcı tipi."
        
        # Fotoğrafı güncelle
        cursor.execute(f"UPDATE {tablo} SET profil_foto = %s WHERE tc_kimlik_no = %s", 
                      (foto_data, tc_kimlik_no))
        
        conn.commit()
        return True, "Profil fotoğrafı başarıyla güncellendi."
        
    except Exception as e:
        return False, f"Profil fotoğrafı güncelleme hatası: {e}"
    finally:
        cursor.close()
        conn.close()

# Profil fotoğrafı getirme fonksiyonu (doktor ve hasta için)
def profil_foto_getir(tc_kimlik_no, kullanici_tipi):
    conn = baglanti_kur()
    cursor = conn.cursor()
    
    try:
        # Kullanıcı tipine göre tabloyu belirle
        if kullanici_tipi == "doktor":
            tablo = "Doktorlar"
        elif kullanici_tipi == "hasta":
            tablo = "Hastalar"
        else:
            return False, "Geçersiz kullanıcı tipi."
        
        # Fotoğrafı getir - hiçbir şey print etmiyoruz
        cursor.execute(f"SELECT profil_foto FROM {tablo} WHERE tc_kimlik_no = %s", (tc_kimlik_no,))
        
        sonuc = cursor.fetchone()
        if sonuc and sonuc[0]:
            # Binary veriyi doğrudan döndür, print etmeden
            return True, sonuc[0]
        else:
            return False, "Profil fotoğrafı bulunamadı."
        
    except Exception as e:
        return False, f"Profil fotoğrafı getirme hatası: {e}"
    finally:
        cursor.close()
        conn.close()

# Hasta için ilk kan şekeri ölçümü kontrolü
def hasta_ilk_olcum_kontrolu(hasta_tc):
    """
    Hasta için ilk ölçümün yapılıp yapılmadığını kontrol eder.
    
    Returns:
        bool: True if initial measurements exist, False otherwise
    """
    conn = baglanti_kur()
    cursor = conn.cursor()
    
    try:
        # IlkOlcumKaydi tablosunda kayıt var mı kontrol et
        cursor.execute("""
        SELECT COUNT(*) FROM IlkOlcumKaydi WHERE hasta_tc = %s
        """, (hasta_tc,))
        
        count = cursor.fetchone()[0]
        return count > 0
    except Exception as e:
        print(f"İlk ölçüm kontrolü hatası: {e}")
        return False
    finally:
        cursor.close()
        conn.close()

# Updated generic function to safely close database connections
def safe_close_connection(cursor, conn):
    """Helper function to safely close database connections"""
    if cursor:
        try:
            # This will consume any remaining result sets
            while cursor.nextset():
                pass
        except:
            pass
        cursor.close()
    if conn:
        conn.close()

# Function to repair KanSekeriKayitlari table

def check_and_add_missing_database_columns():
    """Eksik veritabanı sütunlarını kontrol eder ve ekler"""
    try:
        conn = baglanti_kur()
        cursor = conn.cursor()
        
        # KanSekeriKayitlari tablosunda doktor_tc sütunu var mı kontrol et
        try:
            cursor.execute("SHOW COLUMNS FROM KanSekeriKayitlari LIKE 'doktor_tc'")
            column_exists = cursor.fetchone()
            
            if not column_exists:
                # Eğer sütun yoksa ekle
                cursor.execute("""
                ALTER TABLE KanSekeriKayitlari 
                ADD COLUMN doktor_tc CHAR(11),
                ADD FOREIGN KEY (doktor_tc) REFERENCES Doktorlar(tc_kimlik_no) ON DELETE SET NULL
                """)
                conn.commit()
                print("KanSekeriKayitlari tablosuna doktor_tc sütunu eklendi")
        except Exception as e:
            print(f"Sütun kontrolü sırasında hata: {e}")
        
        # Diğer sütun kontrolleri buraya eklenebilir
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"Veritabanı sütunları kontrol edilirken hata: {e}")

# Veritabanını oluştur
veritabani_olustur()

# Test için bir admin doktor oluştur (uygulama ilk çalıştığında)
def admin_doktor_olustur():
    conn = baglanti_kur()
    cursor = conn.cursor()
    
    try:
        # Admin doktorun var olup olmadığını kontrol et
        cursor.execute("SELECT * FROM Doktorlar WHERE tc_kimlik_no = %s", ("11111111111",))
        admin = cursor.fetchone()
        
        if not admin:
            # Rastgele şifre oluştur
            sifre = "12345678"  # Test için sabit şifre
            
            # Şifreyi hashle
            hashed_sifre = sifre_hashleme(sifre)
            
            # Admin doktoru ekle
            cursor.execute("""
            INSERT INTO Doktorlar (tc_kimlik_no, sifre, isim_soyisim, cinsiyet, mail, uzmanlik)
            VALUES (%s, %s, %s, %s, %s, %s)
            """, ("11111111111", hashed_sifre, "Yağız Talha Sedef", "E", "ytalhasedef@example.com", "Doktor"))
            
            conn.commit()
            print(f"Admin doktor oluşturuldu. TC: 11111111111, Şifre: {sifre}")
            
    except Exception as e:
        print(f"Admin doktor oluşturma hatası: {e}")
    finally:
        cursor.close()
        conn.close()

# Programı çalıştırdığımızda bu işlemler yapılsın
if __name__ == "__main__":
    # Initialize database and create all tables
    initialize_database()
    
    # Force repair of problematic tables if needed
    # You can uncomment the line below when you need to repair tables
    # try_repair_tables()
    
    # Create admin doctor
    admin_doktor_olustur()
    
    # PyQt5 arayüzünü başlat
    try:
        from PyQt5.QtWidgets import QApplication
        import os
        
        # Arayüz modülünü dinamik olarak import et
        arayuz_dosya = os.path.join(os.path.dirname(__file__), "arayuz.py")
        
        if os.path.exists(arayuz_dosya):
            import importlib.util
            spec = importlib.util.spec_from_file_location("arayuz", arayuz_dosya)
            arayuz = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(arayuz)
            
            app = QApplication(sys.argv)
            pencere = arayuz.GirisEkrani()
            pencere.show()
            sys.exit(app.exec_())
        else:
            print("Arayüz dosyası bulunamadı: arayuz.py")
            
    except ImportError:
        print("PyQt5 kütüphanesi bulunamadı. Lütfen 'pip install PyQt5' komutunu çalıştırınız.")
    except Exception as e:
        print(f"Arayüz başlatılırken hata oluştu: {e}")




# Hasta için ilk kan şekeri ölçümü kontrolü

def raporlari_getir(hasta_tc, tarih):
    """
    Belirli bir hastanın belirli bir tarihteki kan şekeri ölçümlerini getirir
    
    Args:
        hasta_tc: Hastanın TC kimlik numarası
        tarih: Raporun tarihi (datetime.date)
        
    Returns:
        (basarili, sonuc): Başarılı ise (True, ölçüm listesi), değilse (False, hata mesajı)
    """
    try:
        conn = mysql.connector.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME,
            charset=DB_CHARSET
        )
        cursor = conn.cursor(dictionary=True)
        
        # Ölçümleri getir - saat sırasına göre (sabahtan akşama)
        cursor.execute("""
            SELECT 
                olcum_zamani, 
                TIME_FORMAT(saat, '%H:%i') as saat, 
                seker_seviyesi, 
                seviye_durumu, 
                zaman_uygun, 
                ortalamaya_dahil
            FROM KanSekeriKayitlari 
            WHERE tc_kimlik_no = %s AND tarih = %s
            ORDER BY FIELD(olcum_zamani, 'Sabah', 'Ogle', 'Ikindi', 'Aksam', 'Gece')
        """, (hasta_tc, tarih))
        
        rapor = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return True, rapor
        
    except Exception as e:
        if 'conn' in locals() and conn:
            conn.close()
        return False, f"Raporlar yüklenirken bir hata oluştu: {str(e)}"

def hasta_fiziksel_bilgi_guncelle(tc_kimlik, yas=None, boy=None, kilo=None, vki=None):
    """Hastanın fiziksel bilgilerini günceller"""
    conn = None
    cursor = None
    
    try:
        conn = mysql.connector.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME,
            charset=DB_CHARSET
        )
        cursor = conn.cursor()
        
        # Güncellenecek alanları dinamik olarak oluştur
        update_parts = []
        params = []
        
        if yas is not None:
            update_parts.append("yas = %s")
            params.append(yas)
        
        if boy is not None:
            update_parts.append("boy = %s")
            params.append(boy)
        
        if kilo is not None:
            update_parts.append("kilo = %s")
            params.append(kilo)
        
        if vki is not None:
            update_parts.append("vki = %s")
            params.append(vki)
        
        if update_parts:
            # TC'yi parametrelere ekle
            params.append(tc_kimlik)
            
            # Güncelleme sorgusunu çalıştır
            query = f"UPDATE Hastalar SET {', '.join(update_parts)} WHERE tc_kimlik_no = %s"
            cursor.execute(query, params)
            conn.commit()
            
            print(f"Fiziksel bilgiler güncellendi: {tc_kimlik} - Yaş:{yas}, Boy:{boy}, Kilo:{kilo}, VKİ:{vki}")
            return True, "Fiziksel bilgiler güncellendi."
        else:
            return False, "Güncellenecek bilgi bulunamadı."
        
    except Exception as e:
        print(f"Fiziksel bilgi güncelleme hatası: {e}")
        return False, f"Güncelleme hatası: {str(e)}"
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()