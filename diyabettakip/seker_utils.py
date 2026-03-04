from datetime import datetime, time
import mysql.connector

# Import config
try:
    from config import DB_HOST, DB_USER, DB_PASSWORD, DB_NAME, DB_CHARSET
except ImportError:
    DB_HOST = "localhost"
    DB_USER = "root"
    DB_PASSWORD = "YOUR_PASSWORD"
    DB_NAME = "diyabet"
    DB_CHARSET = "utf8mb4"

# Ölçüm zamanları ve saat aralıkları
OLCUM_ZAMANLARI = {
    'Sabah': (time(7, 0), time(8, 0)),   # 07:00-08:00
    'Ogle': (time(12, 0), time(13, 0)),  # 12:00-13:00
    'Ikindi': (time(15, 0), time(16, 0)),  # 15:00-16:00
    'Aksam': (time(18, 0), time(19, 0)),  # 18:00-19:00
    'Gece': (time(22, 0), time(23, 0))   # 22:00-23:00
}

# Kan şekeri seviye aralıkları
SEKER_SEVIYELERI = {
    'Dusuk': (0, 70),     # < 70 mg/dL (Hipoglisemi)
    'Normal': (70, 100),   # 70-99 mg/dL (Normal)
    'Orta': (100, 126),   # 100-125 mg/dL (Prediyabet)
    'Yuksek': (126, 200), # ≥ 126 mg/dL (Diyabet)
    'CokYuksek': (200, 1000)  # > 200 mg/dL (Çok Yüksek)
}

# İnsülin önerileri için ortalama kan şekeri aralıkları
INSULIN_ONERILERI = {
    'Yok_Dusuk': (0, 70),     # < 70 mg/dL - Yok (Hipoglisemi)
    'Yok_Normal': (70, 111),  # 70-110 mg/dL - Yok (Normal)
    'Az': (111, 151),         # 111-150 mg/dL - 1 ml (Orta Yüksek)
    'Orta': (151, 201),       # 151-200 mg/dL - 2 ml (Yüksek)
    'Yuksek': (201, 1000)     # > 200 mg/dL - 3 ml (Çok Yüksek)
}

# Kan şekeri uyarı seviyeleri ve mesajları
SEKER_UYARILARI = {
    'KritikDusuk': {
        'sinir': (0, 70),
        'tip': 'Acil Uyarı',
        'mesaj': "Hastanın kan şekeri seviyesi 70 mg/dL'nin altına düştü. Hipoglisemi riski! Hızlı müdahale gerekebilir."
    },
    'Normal': {
        'sinir': (70, 111),
        'tip': 'Uyarı Yok',
        'mesaj': "Kan şekeri seviyesi normal aralıkta. Hiçbir işlem gerekmez."
    },
    'OrtaYuksek': {
        'sinir': (111, 151),
        'tip': 'Takip Uyarısı',
        'mesaj': "Hastanın kan şekeri 111–150 mg/dL arasında. Durum izlenmeli."
    },
    'Yuksek': {
        'sinir': (151, 201),
        'tip': 'İzleme Uyarısı',
        'mesaj': "Hastanın kan şekeri 151–200 mg/dL arasında. Diyabet kontrolü gerekebilir."
    },
    'KritikYuksek': {
        'sinir': (201, 1000),
        'tip': 'Acil Müdahale Uyarısı',
        'mesaj': "Hastanın kan şekeri 200 mg/dL'nin üzerinde. Hiperglisemi durumu. Acil müdahale gerekebilir."
    },
    'OlcumEksik': {
        'tip': 'Ölçüm Eksik Uyarısı',
        'mesaj': "Hasta gün boyunca kan şekeri ölçümü yapmamıştır. Acil takip önerilir."
    },
    'OlcumYetersiz': {
        'tip': 'Ölçüm Yetersiz Uyarısı',
        'mesaj': "Hastanın günlük kan şekeri ölçüm sayısı yetersiz (<3). Durum izlenmelidir."
    }
}

def zaman_kontrolu(olcum_zamani, saat):
    """
    Verilen saat, belirtilen ölçüm zamanı aralığında mı kontrol eder.
    
    Args:
        olcum_zamani (str): Ölçüm zamanı ('Sabah', 'Ogle', 'Ikindi', 'Aksam', 'Gece')
        saat (time): Kontrol edilecek saat
        
    Returns:
        bool: Saat uygun aralıkta ise True, değilse False
    """
    if olcum_zamani not in OLCUM_ZAMANLARI:
        return False
        
    baslangic, bitis = OLCUM_ZAMANLARI[olcum_zamani]
    return baslangic <= saat <= bitis

def seviye_belirle(seker_degeri):
    """
    Kan şekeri değerine göre seviyeyi belirler.
    
    Args:
        seker_degeri (float): Kan şekeri değeri (mg/dL)
        
    Returns:
        str: Seviye adı ('Dusuk', 'Normal', 'Orta', 'Yuksek', 'CokYuksek')
    """
    for seviye, (alt_sinir, ust_sinir) in SEKER_SEVIYELERI.items():
        if alt_sinir <= seker_degeri < ust_sinir:
            return seviye
    return 'CokYuksek'  # Çok yüksek değerler için

def insulin_onerisi_hesapla(ortalama_seker):
    """
    Ortalama kan şekeri değerine göre insülin önerisini belirler.
    
    Args:
        ortalama_seker (float): Ortalama kan şekeri değeri (mg/dL)
        
    Returns:
        float: Önerilen insülin miktarı (ml)
    """
    if ortalama_seker < 70:  # Hipoglisemi
        return 0
    elif ortalama_seker <= 110:  # Normal
        return 0
    elif ortalama_seker <= 150:  # Orta Yüksek
        return 1
    elif ortalama_seker <= 200:  # Yüksek
        return 2
    else:  # Çok Yüksek
        return 3

def gunluk_olcumleri_getir(hasta_tc, tarih, conn):
    """
    Belirli bir hasta ve tarih için tüm kan şekeri ölçümlerini getirir.
    
    Args:
        hasta_tc (str): Hastanın TC kimlik numarası
        tarih (date): Sorgulanacak tarih (GG.AA.YYYY formatında)
        conn: Veritabanı bağlantısı
        
    Returns:
        dict: Ölçüm zamanlarına göre sıralanmış ölçümler
    """
    cursor = conn.cursor(dictionary=True)
    
    # SQL sorgusunda fazladan boşluk olmadığına emin ol
    cursor.execute("""
    SELECT * FROM KanSekeriKayitlari
    WHERE tc_kimlik_no = %s AND tarih = %s
    ORDER BY saat
    """, (hasta_tc, tarih))
    
    olcumler = {
        'Sabah': None,
        'Ogle': None,
        'Ikindi': None,
        'Aksam': None,
        'Gece': None
    }
    
    for olcum in cursor.fetchall():
        olcum_zamani = olcum['olcum_zamani']
        
        # 24 saat formatında saat_str ekle
        from ui_utils import saat_goruntu_formatla
        olcum['saat_str'] = saat_goruntu_formatla(olcum['saat'])
                
        if olcum_zamani in olcumler:
            olcumler[olcum_zamani] = olcum
    
    cursor.close()
    return olcumler

def ortalama_hesapla(olcumler):
    """
    Günlük ölçümlerin ortalamasını hesaplar.
    
    Args:
        olcumler (dict): Ölçüm zamanlarına göre ölçümler
        
    Returns:
        tuple: (ortalama, dahil_edilen_olcum_sayisi, eksik_olcumler, uyarilar)
    """
    degerler = []
    eksik_olcumler = []
    uyarilar = []
    
    for zaman, olcum in olcumler.items():
        if olcum and olcum['ortalamaya_dahil']:
            degerler.append(olcum['seker_seviyesi'])
        else:
            eksik_olcumler.append(zaman)
    
    if not degerler:
        uyarilar.append("Ölçüm bulunamadı! Ortalama hesaplanamıyor.")
        return 0, 0, eksik_olcumler, uyarilar
    
    if len(eksik_olcumler) > 0:
        uyarilar.append(f"Ölçüm eksik! Ortalama alınırken {', '.join(eksik_olcumler)} ölçümleri hesaba katılmadı.")
    
    if len(degerler) <= 3:
        uyarilar.append("Yetersiz veri! Ortalama hesaplaması güvenilir değildir.")
    
    ortalama = sum(degerler) / len(degerler)
    return ortalama, len(degerler), eksik_olcumler, uyarilar

def uyari_olustur(hasta_tc, doktor_tc, uyari_tipi, aciklama, conn, seker_seviyesi=None):
    """
    Sistemde uyarı oluşturur ve doktora bildirim gönderir.
    
    Args:
        hasta_tc (str): Hastanın TC kimlik numarası
        doktor_tc (str): Doktorun TC kimlik numarası
        uyari_tipi (str): Uyarı tipi ('OlcumEksik', 'OlcumYetersiz', 'KritikDusuk', 'KritikYuksek', 'OrtaYuksek', 'Yuksek')
        aciklama (str): Uyarı açıklaması
        conn: Veritabanı bağlantısı
        seker_seviyesi (float, optional): Kan şekeri seviyesi. Defaults to None.
    """
    cursor = conn.cursor()
    
    try:
        # Doktor TC boş olabilir mi kontrol et (Null değer hatası önlemi)
        if not doktor_tc:
            # Hastanın doktorunu bulmaya çalış
            cursor.execute("SELECT doktor_tc FROM Hastalar WHERE tc_kimlik_no = %s", (hasta_tc,))
            hasta_bilgisi = cursor.fetchone()
            if hasta_bilgisi and hasta_bilgisi[0]:
                doktor_tc = hasta_bilgisi[0]
            else:
                print(f"Uyarı: {hasta_tc} TC'li hasta için doktor bulunamadı!")
        
        # Önemli: Uyarı tipinin enum değerler içinde olduğundan emin ol
        valid_types = ['OlcumEksik', 'OlcumYetersiz', 'KritikDusuk', 'KritikYuksek', 'OrtaYuksek', 'Yuksek']
        if uyari_tipi not in valid_types:
            print(f"Hata: Geçersiz uyarı tipi '{uyari_tipi}'. Geçerli tipler: {', '.join(valid_types)}")
            return
        
        try:
            # Uyarıyı oluştur - DESCRIBE tablosu ikinci kez sorgulama
            cursor.execute("""
            INSERT INTO Uyarilar (tc_kimlik_no, doktor_tc, uyari_tipi, aciklama, seker_seviyesi)
            VALUES (%s, %s, %s, %s, %s)
            """, (hasta_tc, doktor_tc, uyari_tipi, aciklama, seker_seviyesi))
            conn.commit()
            print(f"Uyarı başarıyla oluşturuldu: {uyari_tipi} - {hasta_tc}")
        except mysql.connector.Error as err:
            print(f"Uyarı ekleme hatası: {err}")
            
            # Bir sütun sorunu mu?
            if "Unknown column" in str(err):
                # Uyarilar tablosu yapısını onar
                try:
                    # Tabloyu silip yeniden oluştur
                    cursor.execute("DROP TABLE IF EXISTS Uyarilar")
                    cursor.execute("""
                    CREATE TABLE Uyarilar (
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
                    print("Uyarilar tablosu başarıyla yeniden oluşturuldu.")
                    
                    # Tekrar dene
                    cursor.execute("""
                    INSERT INTO Uyarilar (tc_kimlik_no, doktor_tc, uyari_tipi, aciklama, seker_seviyesi)
                    VALUES (%s, %s, %s, %s, %s)
                    """, (hasta_tc, doktor_tc, uyari_tipi, aciklama, seker_seviyesi))
                    conn.commit()
                    print("Uyarı başarıyla eklendi.")
                except Exception as e:
                    print(f"Tablo onarım hatası: {e}")
    except Exception as e:
        print(f"Uyarı oluşturma hatası: {e}")
    finally:
        cursor.close()

def fix_uyarilar_table(cursor, conn=None):
    """Uyarilar tablosunu onar ve doktor_tc sütununu ekler"""
    close_connection = False
    try:
        if conn is None:
            # Eğer bağlantı sağlanmamışsa, yeni bir bağlantı oluştur
            import mysql.connector
            conn = mysql.connector.connect(
                host=DB_HOST,
                user=DB_USER,
                password=DB_PASSWORD,
                database=DB_NAME,
                charset=DB_CHARSET
            )
            cursor = conn.cursor()
            close_connection = True
        
        # Uyarilar tablosunu yeniden oluştur veya doktor_tc sütununu ekle
        try:
            # İlk olarak, Uyarilar tablosunun varlığını kontrol et
            cursor.execute("SHOW TABLES LIKE 'Uyarilar'")
            table_exists = cursor.fetchone()
            
            if not table_exists:
                # Eğer tablo yoksa, baştan oluştur
                cursor.execute("""
                CREATE TABLE Uyarilar (
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
                print("Uyarilar tablosu başarıyla oluşturuldu.")
            else:
                # Tablo varsa, doktor_tc sütunu olup olmadığını kontrol et
                cursor.execute("SHOW COLUMNS FROM Uyarilar LIKE 'doktor_tc'")
                column_exists = cursor.fetchone()
                
                if not column_exists:
                    print("Uyarilar tablosunda doktor_tc sütunu ekleniyor...")
                    cursor.execute("""
                    ALTER TABLE Uyarilar
                    ADD COLUMN doktor_tc CHAR(11),
                    ADD FOREIGN KEY (doktor_tc) REFERENCES Doktorlar(tc_kimlik_no) ON DELETE SET NULL
                    """)
                    print("doktor_tc sütunu başarıyla eklendi!")
                    
                    # Mevcut uyarıları güncelle - her uyarı için hasta kaydındaki doktor bilgisini kullan
                    cursor.execute("""
                    UPDATE Uyarilar u
                    JOIN Hastalar h ON u.tc_kimlik_no = h.tc_kimlik_no
                    SET u.doktor_tc = h.doktor_tc
                    WHERE u.doktor_tc IS NULL AND h.doktor_tc IS NOT NULL
                    """)
                    print(f"{cursor.rowcount} uyarı kaydı güncellendi.")
            
            # İşlemler tamamlandı
            conn.commit()
            return True
            
        except Exception as e:
            print(f"Uyarilar tablosu onarım hatası: {e}")
            return False
    
    finally:
        if close_connection and conn:
            cursor.close()
            conn.close()

def kontrol_ve_uyari_olustur(hasta_tc, seker_degeri, doktor_tc, conn):
    """
    Kan şekeri değerine göre uyarı oluşturur.
    
    Args:
        hasta_tc (str): Hastanın TC kimlik numarası
        seker_degeri (float): Kan şekeri seviyesi (mg/dL)
        doktor_tc (str): Doktorun TC kimlik numarası
        conn: Veritabanı bağlantısı
    """
    # Hasta bilgilerini getir
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
        SELECT isim_soyisim, doktor_tc FROM Hastalar WHERE tc_kimlik_no = %s
        """, (hasta_tc,))
        
        hasta = cursor.fetchone()
        hasta_adi = hasta['isim_soyisim'] if hasta else "Hasta"
        
        # Eğer doktor_tc parametresi boşsa, hastanın doktor_tc'sini kullan
        if not doktor_tc and hasta and 'doktor_tc' in hasta:
            doktor_tc = hasta['doktor_tc']
        
        # Şeker seviyesine göre uyarı tipini belirle
        if seker_degeri < 70:  # Hipoglisemi
            uyari_tipi = 'KritikDusuk'
            mesaj = f"Hasta {hasta_adi} için düşük kan şekeri uyarısı: {seker_degeri} mg/dL. {SEKER_UYARILARI[uyari_tipi]['mesaj']}"
            uyari_olustur(hasta_tc, doktor_tc, uyari_tipi, mesaj, conn, seker_degeri)
        elif 70 <= seker_degeri < 111:
            # Normal seviye, uyarı yok
            pass
        elif 111 <= seker_degeri < 151:
            uyari_tipi = 'OrtaYuksek'
            mesaj = f"Hasta {hasta_adi} için orta yüksek kan şekeri bildirimi: {seker_degeri} mg/dL. {SEKER_UYARILARI[uyari_tipi]['mesaj']}"
            uyari_olustur(hasta_tc, doktor_tc, uyari_tipi, mesaj, conn, seker_degeri)
        elif 151 <= seker_degeri < 201:
            uyari_tipi = 'Yuksek'
            mesaj = f"Hasta {hasta_adi} için yüksek kan şekeri uyarısı: {seker_degeri} mg/dL. {SEKER_UYARILARI[uyari_tipi]['mesaj']}"
            uyari_olustur(hasta_tc, doktor_tc, uyari_tipi, mesaj, conn, seker_degeri)
        elif seker_degeri >= 201:  # Hiperglisemi
            uyari_tipi = 'KritikYuksek'
            mesaj = f"Hasta {hasta_adi} için çok yüksek kan şekeri uyarısı: {seker_degeri} mg/dL. {SEKER_UYARILARI[uyari_tipi]['mesaj']}"
            uyari_olustur(hasta_tc, doktor_tc, uyari_tipi, mesaj, conn, seker_degeri)
    except Exception as e:
        print(f"Uyarı oluşturma hatası: {e}")
    finally:
        cursor.close()

def kontrol_gunluk_olcumler(hasta_tc, tarih, conn):
    """
    Günlük ölçüm sayısını kontrol eder ve yetersizse uyarı oluşturur.
    
    Args:
        hasta_tc (str): Hastanın TC kimlik numarası
        tarih (date): Kontrol edilecek tarih
        conn: Veritabanı bağlantısı
    """
    cursor = conn.cursor(dictionary=True)
    
    try:
        # Hastanın bilgilerini getir
        cursor.execute("""
        SELECT h.isim_soyisim, h.doktor_tc
        FROM Hastalar h 
        WHERE h.tc_kimlik_no = %s
        """, (hasta_tc,))
        
        hasta = cursor.fetchone()
        
        if not hasta:
            print(f"Hasta bulunamadı: {hasta_tc}")
            return
            
        hasta_adi = hasta['isim_soyisim']
        doktor_tc = hasta['doktor_tc']
        
        # Günün ölçümlerini say (ortalamaya dahil edilebilen ölçümler)
        cursor.execute("""
        SELECT COUNT(*) as olcum_sayisi
        FROM KanSekeriKayitlari
        WHERE tc_kimlik_no = %s AND tarih = %s AND ortalamaya_dahil = TRUE
        """, (hasta_tc, tarih))
        
        sonuc = cursor.fetchone()
        olcum_sayisi = sonuc['olcum_sayisi']
        
        # Bugün için daha önce uyarı oluşturulmuş mu kontrol et
        cursor.execute("""
        SELECT COUNT(*) as uyari_sayisi
        FROM Uyarilar
        WHERE tc_kimlik_no = %s AND DATE(tarih_zaman) = %s AND uyari_tipi = 'OlcumYetersiz'
        """, (hasta_tc, tarih))
        
        uyari_sonuc = cursor.fetchone()
        uyari_var = uyari_sonuc['uyari_sayisi'] > 0
        
        # Eğer ölçüm sayısı yetersizse ve daha önce uyarı oluşturulmadıysa uyarı oluştur
        if olcum_sayisi < 3 and not uyari_var:
            uyari_tipi = 'OlcumYetersiz'
            aciklama = f"Hasta {hasta_adi} {tarih.strftime('%d.%m.%Y')} tarihinde sadece {olcum_sayisi} kan şekeri ölçümü yaptı. Hastanın günlük kan şekeri ölçüm sayısı yetersiz (<3). Durum izlenmelidir."
            
            # NOT: seker_seviyesi parametresi NULL olarak geçiliyor
            uyari_olustur(hasta_tc, doktor_tc, uyari_tipi, aciklama, conn, None)
            print(f"Yetersiz ölçüm uyarısı oluşturuldu: {hasta_adi}, {tarih}, {olcum_sayisi} ölçüm")
        
    except Exception as e:
        print(f"Günlük ölçüm kontrolü hatası: {e}")
    finally:
        cursor.close()

# Bu modülde tanımlı olan ve dışa aktarılacak tüm fonksiyonlar
__all__ = [
    'zaman_kontrolu', 
    'seviye_belirle', 
    'insulin_onerisi_hesapla',
    'gunluk_olcumleri_getir', 
    'ortalama_hesapla', 
    'uyari_olustur',
    'fix_uyarilar_table',
    'kontrol_ve_uyari_olustur',
    'kontrol_gunluk_olcumler',
    'OLCUM_ZAMANLARI', 
    'SEKER_SEVIYELERI',
    'INSULIN_ONERILERI',
    'SEKER_UYARILARI'
]
