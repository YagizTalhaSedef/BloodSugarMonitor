from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                           QTableWidget, QTableWidgetItem, QPushButton, QFormLayout,
                           QMessageBox, QGroupBox, QHeaderView, QSplitter, QTabWidget, QDialog,
                           QFileDialog, QLineEdit, QDateEdit, QTimeEdit, QRadioButton, QCheckBox,
                           QScrollArea)
from PyQt5.QtCore import Qt, QBuffer, QDate, QTime
from PyQt5.QtGui import QFont, QPixmap, QDoubleValidator
import mysql.connector
import matplotlib
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import numpy as np
from graph_utils import create_blood_sugar_graph, create_weekly_graph, embed_matplotlib_figure, pixmap_from_figure

# Import config
try:
    from config import DB_HOST, DB_USER, DB_PASSWORD, DB_NAME, DB_CHARSET
except ImportError:
    DB_HOST = "localhost"
    DB_USER = "root"
    DB_PASSWORD = "YOUR_PASSWORD"
    DB_NAME = "diyabet"
    DB_CHARSET = "utf8mb4"

# Import dialog
from diyaloglar import HastaEkleDiyalog
from uyari_dialog import HastaUyariDialog  # Add this import
from diyet_egzersiz import DiyetEgzersizPlanDialog, HastaDiyetEgzersizRaporDialog
# Import the missing functions from diyet_egzersiz module
from diyet_egzersiz import get_active_plan, get_patient_adherence_history

# Import Main module
import Main as MainModule

class DoktorEkrani(QMainWindow):
    def __init__(self, doktor_bilgisi):
        super().__init__()
        self.doktor = doktor_bilgisi
        self.setWindowTitle(f"Dr. {self.doktor['isim_soyisim']} - Diyabet Takip Sistemi")
        self.setMinimumSize(1000, 600)
        
        # Açık mavi tema için styleSheet
        self.setStyleSheet("""
            QMainWindow, QWidget {
                background-color: #E3F2FD;
            }
            QPushButton {
                background-color: #64B5F6;
                color: white;
                border-radius: 5px;
                padding: 8px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #42A5F5;
            }
            QGroupBox {
                border: 1px solid #64B5F6;
                border-radius: 5px;
                margin-top: 10px;
            }
            QGroupBox::title {
                color: #1976D2;
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
            QLabel {
                color: #1976D2;
            }
            QLineEdit, QComboBox {
                border: 1px solid #64B5F6;
                border-radius: 3px;
                padding: 5px;
                selection-background-color: #42A5F5;
            }
        """)
        
        # Ana tabbed layout oluştur
        self.tab_widget = QTabWidget()
        
        # Hasta yönetimi ve profil tablarını oluştur
        self.hasta_tab = QWidget()
        self.profil_tab = QWidget()
        
        # Tab'ları oluştur ve doldur
        self.hasta_yonetimi_arayuzu_olustur()
        self.profil_arayuzu_olustur()
        
        # Tab widgeta sayfaları ekle
        self.tab_widget.addTab(self.hasta_tab, "Hasta Yönetimi")
        self.tab_widget.addTab(self.profil_tab, "Profil")
        
        # Ana widget'a tab widget ekle
        self.setCentralWidget(self.tab_widget)
        
        # Hastaları liste - otomatik olarak başlangıçta listele
        self.hastalari_listele()
        
        # Varsa profil fotoğrafını getir
        self.profil_foto_goster()
    
    def profil_arayuzu_olustur(self):
        # Profil tab'ı için layout
        self.profil_layout = QVBoxLayout(self.profil_tab)
        
        # Profil bilgileri grubu
        profil_grup = QGroupBox("Kişisel Bilgilerim")
        profil_form = QFormLayout()
        
        # Profil fotoğrafı
        foto_layout = QHBoxLayout()
        self.profil_foto_label = QLabel()
        self.profil_foto_label.setFixedSize(200, 200)
        self.profil_foto_label.setAlignment(Qt.AlignCenter)
        self.profil_foto_label.setStyleSheet("border: 2px solid #64B5F6; border-radius: 100px;")
        
        # Varsayılan profil fotoğrafı göster
        self.default_foto = QPixmap(200, 200)
        self.default_foto.fill(Qt.lightGray)
        self.profil_foto_label.setPixmap(self.default_foto)
        
        foto_layout.addWidget(self.profil_foto_label)
        
        # Profil fotoğrafı değiştirme butonu
        foto_buton_layout = QVBoxLayout()
        self.foto_degistir_btn = QPushButton("Fotoğraf Değiştir")
        self.foto_degistir_btn.clicked.connect(self.profil_foto_degistir)
        foto_buton_layout.addWidget(self.foto_degistir_btn)
        foto_buton_layout.addStretch()
        
        foto_layout.addLayout(foto_buton_layout)
        
        # Profil bilgileri etiketleri
        tc_label = QLabel(self.doktor['tc_kimlik_no'])
        isim_label = QLabel(self.doktor['isim_soyisim'])
        cinsiyet_label = QLabel('Erkek' if self.doktor['cinsiyet'] == 'E' else 'Kadın')
        email_label = QLabel(self.doktor['mail'])
        uzmanlik_label = QLabel(self.doktor['uzmanlik'])
        
        profil_form.addRow("TC Kimlik No:", tc_label)
        profil_form.addRow("İsim Soyisim:", isim_label)
        profil_form.addRow("Cinsiyet:", cinsiyet_label)
        profil_form.addRow("Email:", email_label)
        profil_form.addRow("Uzmanlık:", uzmanlik_label)
        
        profil_grup.setLayout(profil_form)
        
        self.profil_layout.addLayout(foto_layout)
        self.profil_layout.addWidget(profil_grup)
        self.profil_layout.addStretch()
    
    def hasta_yonetimi_arayuzu_olustur(self):
        # Hasta yönetimi tab'ı için layout
        ana_layout = QHBoxLayout(self.hasta_tab)
        
        # Sol taraf - Hasta listesi ve butonlar
        sol_panel = QWidget()
        sol_layout = QVBoxLayout(sol_panel)
        
        # Hasta arama
        arama_layout = QHBoxLayout()
        self.arama_input = QLineEdit()
        self.arama_input.setPlaceholderText("TC No veya isim ile hasta ara...")
        arama_btn = QPushButton("Ara")
        arama_btn.clicked.connect(self.hasta_ara)
        
        # Gelişmiş filtreleme butonu ekle
        filtre_btn = QPushButton("Gelişmiş Filtrele")
        filtre_btn.setStyleSheet("background-color: #9C27B0; color: white;")
        filtre_btn.clicked.connect(self.gelismis_filtre_diyalogu)
        
        arama_layout.addWidget(self.arama_input)
        arama_layout.addWidget(arama_btn)
        arama_layout.addWidget(filtre_btn)
        sol_layout.addLayout(arama_layout)
        
        # Hasta listesi
        self.hasta_tablosu = QTableWidget()
        self.hasta_tablosu.setColumnCount(5)  # 5 sütun olacak (ortalama kan şekeri ekledik)
        self.hasta_tablosu.setHorizontalHeaderLabels([
            "TC Kimlik No", "İsim Soyisim", "Cinsiyet", "Email", "Ort. Kan Şekeri"
        ])
        self.hasta_tablosu.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.hasta_tablosu.setSelectionBehavior(QTableWidget.SelectRows)
        self.hasta_tablosu.setSelectionMode(QTableWidget.SingleSelection)
        self.hasta_tablosu.itemSelectionChanged.connect(self.hasta_secildi)
        
        # Enable sorting
        self.hasta_tablosu.setSortingEnabled(True)
        self.hasta_tablosu.horizontalHeader().setSortIndicatorShown(True)
        
        # Connect sort indicator changed signal to custom handler
        self.hasta_tablosu.horizontalHeader().sortIndicatorChanged.connect(self.tabla_sirala)
        
        sol_layout.addWidget(self.hasta_tablosu)
        
        # İşlem butonları
        buton_layout = QHBoxLayout()
        
        ekle_btn = QPushButton("Yeni Hasta Ekle")
        ekle_btn.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold; padding: 10px;")
        ekle_btn.clicked.connect(self.hasta_ekle_diyalog)
        
        sil_btn = QPushButton("Hastayı Sil")
        sil_btn.setStyleSheet("background-color: #F44336; color: white; font-weight: bold; padding: 10px;")
        sil_btn.clicked.connect(self.hasta_sil)
        
        profil_btn = QPushButton("Profilim")
        profil_btn.setStyleSheet("background-color: #2196F3; color: white; font-weight: bold; padding: 10px;")
        profil_btn.clicked.connect(self.profil_goster)
        
        buton_layout.addWidget(ekle_btn)
        buton_layout.addWidget(sil_btn)
        buton_layout.addWidget(profil_btn)
        
        sol_layout.addLayout(buton_layout)
        
        # Sağ taraf - Hasta detayları
        sag_panel = QWidget()
        sag_layout = QVBoxLayout(sag_panel)
        
        # Hasta detay başlığı
        self.hasta_detay_baslik = QLabel("Hasta Detayları")
        self.hasta_detay_baslik.setFont(QFont("Arial", 14, QFont.Bold))
        self.hasta_detay_baslik.setAlignment(Qt.AlignCenter)
        sag_layout.addWidget(self.hasta_detay_baslik)
        
        # Hasta bilgileri formu
        detay_grup = QGroupBox("Kişisel Bilgiler")
        detay_form = QFormLayout()
        
        self.detay_tc = QLabel("-")
        self.detay_isim = QLabel("-")
        self.detay_cinsiyet = QLabel("-")
        self.detay_email = QLabel("-")
        
        detay_form.addRow("TC Kimlik No:", self.detay_tc)
        detay_form.addRow("İsim Soyisim:", self.detay_isim)
        detay_form.addRow("Cinsiyet:", self.detay_cinsiyet)
        detay_form.addRow("Email:", self.detay_email)
        
        detay_grup.setLayout(detay_form)
        sag_layout.addWidget(detay_grup)
        
        # Fiziksel bilgiler grubu - YENİ EKLENEN
        self.fiziksel_grup = QGroupBox("Fiziksel Bilgiler")
        fiziksel_form = QFormLayout()
        
        self.detay_yas = QLabel("-")
        self.detay_boy = QLabel("-")
        self.detay_kilo = QLabel("-")
        self.detay_vki = QLabel("-")
        
        fiziksel_form.addRow("Yaş:", self.detay_yas)
        fiziksel_form.addRow("Boy:", self.detay_boy)
        fiziksel_form.addRow("Kilo:", self.detay_kilo)
        fiziksel_form.addRow("Vücut Kitle İndeksi:", self.detay_vki)
        
        self.fiziksel_grup.setLayout(fiziksel_form)
        sag_layout.addWidget(self.fiziksel_grup)
        
        # Hasta belirtileri grubu - YENİ EKLENEN
        self.belirti_grup = QGroupBox("Belirtiler")
        belirti_layout = QVBoxLayout()
        
        self.belirti_label = QLabel("Belirtiler yükleniyor...")
        self.belirti_label.setWordWrap(True)
        self.belirti_label.setStyleSheet("color: #D32F2F;")
        belirti_layout.addWidget(self.belirti_label)
        
        self.belirti_grup.setLayout(belirti_layout)
        self.belirti_grup.setVisible(False)  # Başlangıçta gizli
        sag_layout.addWidget(self.belirti_grup)
        
        # Hasta kan şekeri takibi
        self.seker_takip_grup = QGroupBox("Kan Şekeri Takibi")
        self.seker_takip_grup.setVisible(False)  # Başlangıçta gizli
        seker_takip_layout = QVBoxLayout()
        
        # Kan şekeri raporları için buton
        seker_rapor_btn = QPushButton("Kan Şekeri Raporlarını Görüntüle")
        seker_rapor_btn.clicked.connect(self.seker_raporlarini_goster)
        seker_takip_layout.addWidget(seker_rapor_btn)
        
        # İnsülin yönetimi butonu
        insulin_btn = QPushButton("İnsülin Takibi ve Kan Şekeri Geçmişi")
        insulin_btn.setStyleSheet("background-color: #2196F3; color: white; font-weight: bold;")
        insulin_btn.clicked.connect(self.insulin_yonetimi_goster)
        seker_takip_layout.addWidget(insulin_btn)
        
        # Hasta uyarıları butonu
        hasta_uyari_btn = QPushButton("Hasta Uyarılarını Görüntüle")
        hasta_uyari_btn.setStyleSheet("background-color: #F44336; color: white; font-weight: bold;")
        hasta_uyari_btn.clicked.connect(self.hasta_uyarilarini_goster)
        seker_takip_layout.addWidget(hasta_uyari_btn)
        
        # Okunmamış uyarı sayısı etiketi
        self.okunmamis_uyari_label = QLabel("Okunmamış uyarı yok")
        self.okunmamis_uyari_label.setAlignment(Qt.AlignCenter)
        seker_takip_layout.addWidget(self.okunmamis_uyari_label)
        
        # Hasta uyarıları
        self.uyari_label = QLabel("Hasta için uyarılar burada görüntülenecek")
        self.uyari_label.setWordWrap(True)
        self.uyari_label.setStyleSheet("color: red;")
        seker_takip_layout.addWidget(self.uyari_label)
        
        # Add Diet and Exercise Plan section to the existing seker_takip_grup
        diyet_egzersiz_layout = QHBoxLayout()
        
        # Plan creation button
        diyet_egzersiz_btn = QPushButton("Diyet & Egzersiz Planı Oluştur")
        diyet_egzersiz_btn.setStyleSheet("background-color: #8BC34A; color: white; font-weight: bold;")
        diyet_egzersiz_btn.clicked.connect(self.diyet_egzersiz_plan_olustur)
        diyet_egzersiz_layout.addWidget(diyet_egzersiz_btn)
        
        # Report viewing button
        diyet_egzersiz_rapor_btn = QPushButton("Plan Takibini Görüntüle")
        diyet_egzersiz_rapor_btn.setStyleSheet("background-color: #FF9800; color: white; font-weight: bold;")
        diyet_egzersiz_rapor_btn.clicked.connect(self.hasta_diyet_egzersiz_raporlari_goster)
        diyet_egzersiz_layout.addWidget(diyet_egzersiz_rapor_btn)
        
        # Add the layout to the existing group
        seker_takip_layout.addLayout(diyet_egzersiz_layout)
        
        self.seker_takip_grup.setLayout(seker_takip_layout)
        sag_layout.addWidget(self.seker_takip_grup)
        
        # Boş alan ekleyerek düzeni iyileştir
        sag_layout.addStretch()
        
        # Sol ve sağ panelleri birleştir
        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(sol_panel)
        splitter.addWidget(sag_panel)
        splitter.setSizes([500, 500])  # İlk açılışta iki panelin genişliği
        
        ana_layout.addWidget(splitter)
    
    def profil_goster(self):
        # Profil tabına geç
        self.tab_widget.setCurrentIndex(1)
    
    def hastalari_listele(self):
        # Doktorun hastalarını ve kan şekeri ortalamalarını getir
        conn = mysql.connector.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME,
            charset=DB_CHARSET
        )
        cursor = conn.cursor(dictionary=True)
        
        try:
            # Son 30 günün kan şekeri ortalamalarını içeren sorgu
            cursor.execute("""
                SELECT h.*, 
                    (SELECT ROUND(AVG(k.seker_seviyesi), 1) 
                     FROM KanSekeriKayitlari k 
                     WHERE k.tc_kimlik_no = h.tc_kimlik_no 
                     AND k.tarih >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
                     AND k.ortalamaya_dahil = TRUE) as ortalama_seker
                FROM Hastalar h
                WHERE h.doktor_tc = %s
                ORDER BY h.isim_soyisim
            """, (self.doktor['tc_kimlik_no'],))
            
            hastalar = cursor.fetchall()
            
            self.hasta_tablosu.setRowCount(0)  # Mevcut tabloyu temizle
            
            for i, hasta in enumerate(hastalar):
                self.hasta_tablosu.insertRow(i)
                self.hasta_tablosu.setItem(i, 0, QTableWidgetItem(hasta['tc_kimlik_no']))
                self.hasta_tablosu.setItem(i, 1, QTableWidgetItem(hasta['isim_soyisim']))
                self.hasta_tablosu.setItem(i, 2, QTableWidgetItem('Erkek' if hasta['cinsiyet'] == 'E' else 'Kadın'))
                self.hasta_tablosu.setItem(i, 3, QTableWidgetItem(hasta['mail']))
                
                # Ortalama kan şekeri (varsa)
                ortalama_item = QTableWidgetItem()
                if hasta['ortalama_seker'] is not None:
                    ortalama_item.setText(f"{hasta['ortalama_seker']} mg/dL")
                    
                    # Renklendirme: Normal/Yüksek/Düşük
                    if float(hasta['ortalama_seker']) < 70:
                        ortalama_item.setForeground(Qt.blue)  # Düşük
                    elif float(hasta['ortalama_seker']) <= 180:
                        ortalama_item.setForeground(Qt.darkGreen)  # Normal
                    else:
                        ortalama_item.setForeground(Qt.red)  # Yüksek
                else:
                    ortalama_item.setText("Veri yok")
                
                self.hasta_tablosu.setItem(i, 4, ortalama_item)
                
        except Exception as e:
            QMessageBox.warning(self, "Hata", f"Hastalar listelenirken bir hata oluştu: {str(e)}")
        finally:
            cursor.close()
            conn.close()
    
    def hasta_ara(self):
        arama_metni = self.arama_input.text()
        
        if not arama_metni:
            self.hastalari_listele()  # Arama metni yoksa tüm hastaları listele
            return
            
        # Arama yap - ortalama kan şekeri değerlerini de getir
        conn = mysql.connector.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME,
            charset=DB_CHARSET
        )
        cursor = conn.cursor(dictionary=True)
        
        try:
            cursor.execute("""
                SELECT h.*, 
                    (SELECT ROUND(AVG(k.seker_seviyesi), 1) 
                     FROM KanSekeriKayitlari k 
                     WHERE k.tc_kimlik_no = h.tc_kimlik_no 
                     AND k.tarih >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
                     AND k.ortalamaya_dahil = TRUE) as ortalama_seker
                FROM Hastalar h
                WHERE h.doktor_tc = %s AND 
                    (h.tc_kimlik_no LIKE %s OR 
                     h.isim_soyisim LIKE %s)
                ORDER BY h.isim_soyisim
            """, (self.doktor['tc_kimlik_no'], f"%{arama_metni}%", f"%{arama_metni}%"))
            
            hastalar = cursor.fetchall()
            
            self.hasta_tablosu.setRowCount(0)  # Mevcut tabloyu temizle
            
            for i, hasta in enumerate(hastalar):
                self.hasta_tablosu.insertRow(i)
                self.hasta_tablosu.setItem(i, 0, QTableWidgetItem(hasta['tc_kimlik_no']))
                self.hasta_tablosu.setItem(i, 1, QTableWidgetItem(hasta['isim_soyisim']))
                self.hasta_tablosu.setItem(i, 2, QTableWidgetItem('Erkek' if hasta['cinsiyet'] == 'E' else 'Kadın'))
                self.hasta_tablosu.setItem(i, 3, QTableWidgetItem(hasta['mail']))
                
                # Ortalama kan şekeri (varsa)
                ortalama_item = QTableWidgetItem()
                if hasta['ortalama_seker'] is not None:
                    ortalama_item.setText(f"{hasta['ortalama_seker']} mg/dL")
                    
                    # Renklendirme: Normal/Yüksek/Düşük
                    if float(hasta['ortalama_seker']) < 70:
                        ortalama_item.setForeground(Qt.blue)  # Düşük
                    elif float(hasta['ortalama_seker']) <= 180:
                        ortalama_item.setForeground(Qt.darkGreen)  # Normal
                    else:
                        ortalama_item.setForeground(Qt.red)  # Yüksek
                else:
                    ortalama_item.setText("Veri yok")
                
                self.hasta_tablosu.setItem(i, 4, ortalama_item)
                
            if not hastalar:
                QMessageBox.information(self, "Bilgi", f"'{arama_metni}' aramasıyla eşleşen hasta bulunamadı.")
                
        except Exception as e:
            QMessageBox.warning(self, "Arama Hatası", f"Arama sırasında bir hata oluştu: {str(e)}")
        finally:
            cursor.close()
            conn.close()
    
    def hasta_secildi(self):
        secili_satir = self.hasta_tablosu.selectedItems()
        if secili_satir:
            tc_no = self.hasta_tablosu.item(secili_satir[0].row(), 0).text()
            isim = self.hasta_tablosu.item(secili_satir[0].row(), 1).text()
            cinsiyet = self.hasta_tablosu.item(secili_satir[0].row(), 2).text()
            email = self.hasta_tablosu.item(secili_satir[0].row(), 3).text()
            
            # Hasta detaylarını güncelle
            self.hasta_detay_baslik.setText(f"Hasta Detayları: {isim}")
            self.detay_tc.setText(tc_no)
            self.detay_isim.setText(isim)
            self.detay_cinsiyet.setText(cinsiyet)
            self.detay_email.setText(email)
            
            # Fiziksel bilgileri veritabanından getir ve göster
            self.fiziksel_bilgileri_goster(tc_no)
            
            # Belirtileri göster
            self.belirtileri_goster(tc_no)
            
            # Şeker takip grubunu göster
            self.seker_takip_grup.setVisible(True)
            
            # İlk ölçüm kontrolü yap
            ilk_olcum_durumu = MainModule.hasta_ilk_olcum_kontrolu(tc_no)
            
            # Eğer ilk ölçüm yapılmamışsa, buton göster
            if not ilk_olcum_durumu:
                # İlk ölçüm butonu yoksa oluştur
                if not hasattr(self, 'ilk_olcum_btn') or not self.ilk_olcum_btn:
                    self.ilk_olcum_btn = QPushButton("İlk Kan Şekeri Ölçümlerini Gir")
                    self.ilk_olcum_btn.setStyleSheet("background-color: #FF9800; color: white; font-weight: bold;")
                    self.ilk_olcum_btn.clicked.connect(self.ilk_olcumleri_gir)
                    self.seker_takip_grup.layout().addWidget(self.ilk_olcum_btn)
            else:
                # İlk ölçüm yapılmışsa, buton varsa kaldır
                if hasattr(self, 'ilk_olcum_btn') and self.ilk_olcum_btn:
                    self.seker_takip_grup.layout().removeWidget(self.ilk_olcum_btn)
                    self.ilk_olcum_btn.setParent(None)
                    self.ilk_olcum_btn = None
            
            # Hasta uyarılarını yükle
            self.hasta_uyarilarini_yukle(tc_no)

    def hasta_uyarilarini_yukle(self, hasta_tc):
        try:
            # Veritabanı bağlantısı
            conn = mysql.connector.connect(
                host=DB_HOST,
                user=DB_USER,
                password=DB_PASSWORD,
                database=DB_NAME,
                charset=DB_CHARSET
            )
            cursor = conn.cursor(dictionary=True)
            
            # Veritabanı tablosunda okundu sütunu var mı kontrol et ve yoksa ekle
            try:
                cursor.execute("SHOW COLUMNS FROM Uyarilar LIKE 'okundu'")
                column_exists = cursor.fetchone()
                
                if not column_exists:
                    cursor.execute("ALTER TABLE Uyarilar ADD COLUMN okundu BOOLEAN DEFAULT FALSE")
                    conn.commit()
            except Exception as e:
                pass
            
            # Son 5 uyarıyı getir
            cursor.execute("""
                SELECT * FROM Uyarilar 
                WHERE tc_kimlik_no = %s 
                ORDER BY tarih_zaman DESC 
                LIMIT 5
            """, (hasta_tc,))
            
            uyarilar = cursor.fetchall()
            
            # Okunmamış uyarı sayısını getir
            # Use COALESCE to handle missing okundu column or NULL values
            cursor.execute("""
                SELECT COUNT(*) as okunmamis_sayi FROM Uyarilar 
                WHERE tc_kimlik_no = %s AND (okundu = 0 OR okundu IS NULL)
            """, (hasta_tc,))
            
            okunmamis = cursor.fetchone()
            okunmamis_sayi = okunmamis['okunmamis_sayi'] if okunmamis else 0
            
            # Okunmayan uyarıları güncelle
            if okunmamis_sayi > 0:
                self.okunmamis_uyari_label.setText(f"<b style='color:red;'>{okunmamis_sayi} okunmamış uyarı</b>")
            else:
                self.okunmamis_uyari_label.setText("Okunmamış uyarı yok")
            
            if uyarilar:
                uyari_metni = "<b>Son Uyarılar:</b><br>"
                for uyari in uyarilar:
                    tarih = uyari['tarih_zaman'].strftime("%d.%m.%Y %H:%M")
                    
                    # Uyarı tipine göre renk ve metin belirle
                    if uyari['uyari_tipi'] == 'OlcumEksik':
                        uyari_tipi = "Ölçüm Eksik"
                        renk = "orange"
                    elif uyari['uyari_tipi'] == 'OlcumYetersiz':
                        uyari_tipi = "Yetersiz Ölçüm"
                        renk = "orange"
                    elif uyari['uyari_tipi'] == 'KritikDusuk':
                        uyari_tipi = "KRİTİK DÜŞÜK"
                        renk = "blue"
                    elif uyari['uyari_tipi'] == 'KritikYuksek':
                        uyari_tipi = "KRİTİK YÜKSEK"
                        renk = "red"
                    elif uyari['uyari_tipi'] == 'OrtaYuksek':
                        uyari_tipi = "Orta Yüksek"
                        renk = "#FF9800"  # Orange
                    elif uyari['uyari_tipi'] == 'Yuksek':
                        uyari_tipi = "Yüksek"
                        renk = "#F44336"  # Red
                    else:
                        uyari_tipi = uyari['uyari_tipi']
                        renk = "black"
                    
                    # Okunmamış uyarılar için özel stil
                    okundu_stili = "" if 'okundu' in uyari and uyari['okundu'] else "font-weight: bold; text-decoration: underline;"
                    
                    # Şeker seviyesi varsa göster
                    seker_bilgisi = f" ({uyari['seker_seviyesi']} mg/dL)" if 'seker_seviyesi' in uyari and uyari['seker_seviyesi'] else ""
                    
                    uyari_metni += f"<p style='{okundu_stili}'><span style='color:{renk};'><b>{uyari_tipi}</b></span>{seker_bilgisi} - {tarih}<br>{uyari['aciklama']}</p>"
                
                self.uyari_label.setText(uyari_metni)
                self.uyari_label.setTextFormat(Qt.RichText)
            else:
                self.uyari_label.setText("Bu hasta için herhangi bir uyarı bulunmamaktadır.")
            
            cursor.close()
            conn.close()
            
        except Exception as e:
            self.uyari_label.setText(f"Uyarılar yüklenirken hata oluştu: {str(e)}")

    def hasta_uyarilarini_goster(self):
        """Display patient alerts dialog"""
        if not self.detay_tc.text() or self.detay_tc.text() == "-":
            QMessageBox.warning(self, "Hata", "Lütfen önce bir hasta seçin.")
            return
            
        hasta_tc = self.detay_tc.text()
        hasta_isim = self.detay_isim.text()
        
        try:
            # Import the dialog class here to avoid circular imports
            from uyari_dialog import HastaUyariDialog
            
            dialog = HastaUyariDialog(hasta_tc, hasta_isim, self)
            dialog.exec_()
            
            # After dialog is closed, refresh the alerts
            self.hasta_uyarilarini_yukle(hasta_tc)
        except Exception as e:
            QMessageBox.warning(self, "Hata", f"Hasta uyarıları görüntülenirken bir hata oluştu: {str(e)}")

    def seker_raporlarini_goster(self):
        if not self.detay_tc.text() or self.detay_tc.text() == "-":
            QMessageBox.warning(self, "Hata", "Lütfen önce bir hasta seçin.")
            return
            
        hasta_tc = self.detay_tc.text()
        hasta_isim = self.detay_isim.text()
        
        try:
            # Directly create and show SekerRaporDialog
            dialog = SekerRaporDialog(hasta_tc, hasta_isim, self.doktor['tc_kimlik_no'], self)
            # Set initial tab to graph view (index 1)
            dialog.tab_widget.setCurrentIndex(1)
            # Trigger graph update
            dialog.update_blood_sugar_graph()
            dialog.exec_()
        except Exception as e:
            QMessageBox.warning(self, "Hata", f"Kan şekeri raporları yüklenirken hata oluştu: {str(e)}")

    def hasta_ekle_diyalog(self):
        dialog = HastaEkleDiyalog(self.doktor['tc_kimlik_no'])
        if dialog.exec_() == QDialog.Accepted:
            self.hastalari_listele()  # Hasta ekledikten sonra listeyi yenile
    
    def hasta_sil(self):
        secili_satir = self.hasta_tablosu.selectedItems()
        
        if not secili_satir:
            QMessageBox.warning(self, "Hata", "Lütfen silinecek hastayı seçin.")
            return
            
        tc_no = self.hasta_tablosu.item(secili_satir[0].row(), 0).text()
        isim = self.hasta_tablosu.item(secili_satir[0].row(), 1).text()
        
        # Silme işlemi için onay iste
        cevap = QMessageBox.question(self, "Onay", 
                                     f"{isim} isimli hastayı silmek istediğinize emin misiniz?",
                                     QMessageBox.Yes | QMessageBox.No)
        
        if cevap == QMessageBox.Yes:
            # Hasta silme işlemini gerçekleştir
            basarili, mesaj = MainModule.hasta_sil(self.doktor['tc_kimlik_no'], tc_no)
            
            if basarili:
                QMessageBox.information(self, "Başarılı", mesaj)
                self.hastalari_listele()  # Listeyi güncelle
                
                # Hasta detaylarını temizle
                self.hasta_detay_baslik.setText("Hasta Detayları")
                self.detay_tc.setText("-")
                self.detay_isim.setText("-")
                self.detay_cinsiyet.setText("-")
                self.detay_email.setText("-")
            else:
                QMessageBox.warning(self, "Hata", mesaj)
    
    def profil_foto_degistir(self):
        # Dosya seçim diyalogu aç
        dosya_yolu, _ = QFileDialog.getOpenFileName(self, "Profil Fotoğrafı Seç", "", "Resim Dosyaları (*.png *.jpg *.jpeg *.bmp)")
        
        if not dosya_yolu:
            return
        
        try:
            # Resmi yükle ve boyutlandır
            pixmap = QPixmap(dosya_yolu)
            pixmap = pixmap.scaled(200, 200, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            
            # Resmi göster
            self.profil_foto_label.setPixmap(pixmap)
            
            # Resmi veritabanına kaydetmek için byte array'e dönüştür
            img = pixmap.toImage()
            buffer = QBuffer()
            buffer.open(QBuffer.ReadWrite)
            img.save(buffer, "PNG")
            foto_data = buffer.data().data()
            
            # Veritabanına kaydet
            basarili, mesaj = MainModule.profil_foto_guncelle(self.doktor['tc_kimlik_no'], foto_data, "doktor")
            
            if not basarili:
                QMessageBox.warning(self, "Hata", mesaj)
        except Exception as e:
            QMessageBox.warning(self, "Hata", f"Profil fotoğrafı yüklenirken bir hata oluştu: {e}")
    
    def profil_foto_goster(self):
        try:
            # Veritabanından profil fotoğrafını getir
            basarili, sonuc = MainModule.profil_foto_getir(self.doktor['tc_kimlik_no'], "doktor")
            
            if basarili:
                # Byte array'i QPixmap'e dönüştür
                pixmap = QPixmap()
                pixmap.loadFromData(sonuc)
                pixmap = pixmap.scaled(200, 200, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self.profil_foto_label.setPixmap(pixmap)
        except Exception:
            # Sessizce başarısız ol, hiç bir şey yazdırma
            pass

    def ilk_olcumleri_gir(self):
        """
        İlk kan şekeri ölçümlerini girmek için diyalog gösterir.
        """
        hasta_tc = self.detay_tc.text()
        hasta_isim = self.detay_isim.text()
        
        # İlk ölçüm diyalogunu göster
        dialog = IlkOlcumGirisDialog(hasta_tc, hasta_isim, self.doktor['tc_kimlik_no'], self)
        if dialog.exec_() == QDialog.Accepted:
            QMessageBox.information(self, "Başarılı", "İlk ölçümler başarıyla kaydedildi.")
            # İlk ölçüm kontrolünü güncelle - buton gösterilmemeli artık
            if hasattr(self, 'ilk_olcum_btn') and self.ilk_olcum_btn:
                self.seker_takip_grup.layout().removeWidget(self.ilk_olcum_btn)
                self.ilk_olcum_btn.setParent(None)
                self.ilk_olcum_btn = None
                
            # Hasta uyarılarını yenile
            self.hasta_uyarilarini_yukle(hasta_tc)

    def insulin_yonetimi_goster(self):
        """Display insulin management dialog for the selected patient"""
        if not self.detay_tc.text() or self.detay_tc.text() == "-":
            QMessageBox.warning(self, "Hata", "Lütfen önce bir hasta seçin.")
            return
            
        hasta_tc = self.detay_tc.text()
        hasta_isim = self.detay_isim.text()
        
        try:
            from insulin_yonetimi_dialog import InsulinYonetimiDialog
            dialog = InsulinYonetimiDialog(hasta_tc, hasta_isim, self.doktor['tc_kimlik_no'], self)
            # Set the dialog to a larger size for better visibility of historical data
            dialog.resize(1000, 700)
            dialog.exec_()
        except Exception as e:
            QMessageBox.warning(self, "Hata", f"İnsülin yönetimi görüntülenirken bir hata oluştu: {str(e)}")
            
            # If the dialog class is missing, show a simple dialog using the SekerRaporDialog
            # as it already has insulin management capabilities
            try:
                from SekerRaporDialog import SekerRaporDialog
                dialog = SekerRaporDialog(hasta_tc, hasta_isim, self.doktor['tc_kimlik_no'], self)
                dialog.setWindowTitle(f"İnsülin Yönetimi - {hasta_isim}")
                dialog.exec_()
            except Exception as e2:
                QMessageBox.warning(self, "Hata", f"Alternatif diyalog yüklenirken bir hata oluştu: {str(e2)}")

    def fiziksel_bilgileri_goster(self, hasta_tc):
        """Hastanın fiziksel bilgilerini veritabanından çeker ve gösterir"""
        try:
            # Veritabanı bağlantısı
            conn = mysql.connector.connect(
                host=DB_HOST,
                user=DB_USER,
                password=DB_PASSWORD,
                database=DB_NAME,
                charset=DB_CHARSET
            )
            cursor = conn.cursor(dictionary=True)
            
            # Önce sütunların varlığını kontrol et
            cursor.execute("SHOW COLUMNS FROM Hastalar LIKE 'yas'")
            yas_exists = cursor.fetchone() is not None
            
            cursor.execute("SHOW COLUMNS FROM Hastalar LIKE 'boy'")
            boy_exists = cursor.fetchone() is not None
            
            cursor.execute("SHOW COLUMNS FROM Hastalar LIKE 'kilo'")
            kilo_exists = cursor.fetchone() is not None
            
            cursor.execute("SHOW COLUMNS FROM Hastalar LIKE 'vki'")
            vki_exists = cursor.fetchone() is not None
            
            # Eğer herhangi bir sütun eksikse, ekle
            if not all([yas_exists, boy_exists, kilo_exists, vki_exists]):
                print("Fiziksel bilgi sütunları eksik, ekleniyor...")
                
                if not yas_exists:
                    cursor.execute("ALTER TABLE Hastalar ADD COLUMN yas INT NULL")
                
                if not boy_exists:
                    cursor.execute("ALTER TABLE Hastalar ADD COLUMN boy INT NULL COMMENT 'Boy (cm cinsinden)'")
                
                if not kilo_exists:
                    cursor.execute("ALTER TABLE Hastalar ADD COLUMN kilo DECIMAL(5,2) NULL COMMENT 'Kilo (kg cinsinden)'")
                
                if not vki_exists:
                    cursor.execute("ALTER TABLE Hastalar ADD COLUMN vki DECIMAL(4,2) NULL COMMENT 'Vücut Kitle İndeksi'")
                
                conn.commit()
                print("Fiziksel bilgi sütunları eklendi.")
            
            # Hastanın fiziksel bilgilerini getir
            cursor.execute("""
                SELECT yas, boy, kilo, vki FROM Hastalar
                WHERE tc_kimlik_no = %s
            """, (hasta_tc,))
            
            fiziksel_bilgiler = cursor.fetchone()
            
            # Varsayılan metin
            varsayilan_metin = "Bilgi girilmemiş"
            
            if fiziksel_bilgiler:
                # Yaş bilgisi
                yas = fiziksel_bilgiler['yas']
                self.detay_yas.setText(str(yas) if yas else varsayilan_metin)
                
                # Boy bilgisi
                boy = fiziksel_bilgiler['boy']
                self.detay_boy.setText(f"{boy} cm" if boy else varsayilan_metin)
                
                # Kilo bilgisi
                kilo = fiziksel_bilgiler['kilo']
                self.detay_kilo.setText(f"{kilo} kg" if kilo else varsayilan_metin)
                
                # VKİ bilgisi
                vki = fiziksel_bilgiler['vki']
                if vki:
                    # VKİ'ye göre durum belirleme
                    if vki < 18.5:
                        durum = "Zayıf"
                        renk = "blue"
                    elif vki < 25:
                        durum = "Normal"
                        renk = "green"
                    elif vki < 30:
                        durum = "Fazla Kilolu"
                        renk = "orange"
                    else:
                        durum = "Obez"
                        renk = "red"
                    
                    self.detay_vki.setText(f"{vki:.1f} ({durum})")
                    self.detay_vki.setStyleSheet(f"color: {renk}; font-weight: bold;")
                else:
                    self.detay_vki.setText(varsayilan_metin)
                    self.detay_vki.setStyleSheet("")
            else:
                # Bilgiler yoksa varsayılan değerleri göster
                self.detay_yas.setText(varsayilan_metin)
                self.detay_boy.setText(varsayilan_metin)
                self.detay_kilo.setText(varsayilan_metin)
                self.detay_vki.setText(varsayilan_metin)
                self.detay_vki.setStyleSheet("")
            
            cursor.close()
            conn.close()
            
        except Exception as e:
            print(f"Fiziksel bilgileri gösterirken hata: {e}")  # Hatayı konsola yazdır
            self.detay_yas.setText("Yüklenemedi")
            self.detay_boy.setText("Yüklenemedi")
            self.detay_kilo.setText("Yüklenemedi")
            self.detay_vki.setText("Yüklenemedi")

    def diyet_egzersiz_plan_olustur(self):
        """Create a diet and exercise plan for the selected patient"""
        if not self.detay_tc.text() or self.detay_tc.text() == "-":
            QMessageBox.warning(self, "Hata", "Lütfen önce bir hasta seçin.")
            return
            
        hasta_tc = self.detay_tc.text()
        hasta_isim = self.detay_isim.text()
        
        try:
            dialog = DiyetEgzersizPlanDialog(hasta_tc, hasta_isim, self.doktor['tc_kimlik_no'], self)
            if dialog.exec_() == QDialog.Accepted:
                QMessageBox.information(self, "Başarılı", "Diyet ve egzersiz planı başarıyla oluşturuldu.")
        except Exception as e:
            QMessageBox.warning(self, "Hata", f"Diyet ve egzersiz planı oluşturulurken bir hata oluştu: {str(e)}")

    def hasta_diyet_egzersiz_raporlari_goster(self):
        """View diet and exercise reports for the selected patient"""
        if not self.detay_tc.text() or self.detay_tc.text() == "-":
            QMessageBox.warning(self, "Hata", "Lütfen önce bir hasta seçin.")
            return
            
        hasta_tc = self.detay_tc.text()
        hasta_isim = self.detay_isim.text()
        
        try:
            dialog = HastaDiyetEgzersizRaporDialog(hasta_tc, hasta_isim, self)
            dialog.exec_()
        except Exception as e:
            QMessageBox.warning(self, "Hata", f"Diyet ve egzersiz raporları görüntülenirken bir hata oluştu: {str(e)}")

    def gelismis_filtre_diyalogu(self):
        """Hastaları kan şekeri seviyeleri ve belirtilere göre filtreleme diyaloğu"""
        try:
            dialog = HastaFiltrelemeDialog(self.doktor['tc_kimlik_no'], self)
            if dialog.exec_() == QDialog.Accepted and dialog.filtered_patients:
                # Filtrelenmiş hastaları tablo içerisinde göster
                self.hasta_tablosu.setRowCount(0)
                for i, hasta in enumerate(dialog.filtered_patients):
                    self.hasta_tablosu.insertRow(i)
                    self.hasta_tablosu.setItem(i, 0, QTableWidgetItem(hasta['tc_kimlik_no']))
                    self.hasta_tablosu.setItem(i, 1, QTableWidgetItem(hasta['isim_soyisim']))
                    self.hasta_tablosu.setItem(i, 2, QTableWidgetItem('Erkek' if hasta['cinsiyet'] == 'E' else 'Kadın'))
                    self.hasta_tablosu.setItem(i, 3, QTableWidgetItem(hasta['mail']))
                    
                    # Ortalama kan şekeri (varsa)
                    ortalama_item = QTableWidgetItem()
                    if 'ortalama_seker' in hasta and hasta['ortalama_seker'] is not None:
                        ortalama_item.setText(f"{hasta['ortalama_seker']} mg/dL")
                        
                        # Renklendirme: Normal/Yüksek/Düşük
                        if float(hasta['ortalama_seker']) < 70:
                            ortalama_item.setForeground(Qt.blue)  # Düşük
                        elif float(hasta['ortalama_seker']) <= 180:
                            ortalama_item.setForeground(Qt.darkGreen)  # Normal
                        else:
                            ortalama_item.setForeground(Qt.red)  # Yüksek
                    else:
                        ortalama_item.setText("Veri yok")
                    
                    self.hasta_tablosu.setItem(i, 4, ortalama_item)
        except Exception as e:
            QMessageBox.warning(self, "Hata", f"Filtreleme sırasında bir hata oluştu: {str(e)}")

    def tabla_sirala(self, column, order):
        """Handle custom sorting for the table, particularly for the average blood sugar column"""
        # If sorting by average blood sugar (column 4)
        if column == 4:
            # Temporarily disable sorting to avoid issues while we manually sort
            self.hasta_tablosu.setSortingEnabled(False)
            
            # Get all patients from the table
            patients = []
            for row in range(self.hasta_tablosu.rowCount()):
                patient = {}
                for col in range(self.hasta_tablosu.columnCount()):
                    item = self.hasta_tablosu.item(row, col)
                    patient[col] = item.text() if item else ""
                patients.append(patient)
            
            # Custom sort based on blood sugar value
            def sort_key(patient):
                sugar_text = patient[4]
                try:
                    # Extract numeric value from text (e.g., "120.5 mg/dL" -> 120.5)
                    if "mg/dL" in sugar_text:
                        value = float(sugar_text.split("mg/dL")[0].strip())
                        return value
                    elif "Veri yok" in sugar_text:
                        return float('-inf') if order == Qt.AscendingOrder else float('inf')
                    else:
                        return 0
                except:
                    return 0
            
            # Sort the patient list based on our custom sort key
            patients.sort(key=sort_key, reverse=(order == Qt.DescendingOrder))
            
            # Rebuild the table with sorted data
            self.hasta_tablosu.setRowCount(0)
            for i, patient in enumerate(patients):
                self.hasta_tablosu.insertRow(i)
                for col, value in patient.items():
                    item = QTableWidgetItem(value)
                    
                    # Set the text color for average blood sugar column
                    if col == 4 and "mg/dL" in value:
                        try:
                            sugar_value = float(value.split("mg/dL")[0].strip())
                            if sugar_value < 70:
                                item.setForeground(Qt.blue)  # Düşük
                            elif sugar_value <= 180:
                                item.setForeground(Qt.darkGreen)  # Normal
                            else:
                                item.setForeground(Qt.red)  # Yüksek
                        except:
                            pass
                    
                    self.hasta_tablosu.setItem(i, col, item)
            
            # Re-enable sorting
            self.hasta_tablosu.setSortingEnabled(True)

    def belirtileri_goster(self, hasta_tc):
        """Hastanın aktif planındaki belirtilerini gösterir"""
        try:
            # Aktif planı al
            active_plan = get_active_plan(hasta_tc)
            
            if active_plan and active_plan['ozel_notlar']:
                # Belirtileri çıkar
                belirtiler = self.belirtileri_cikar(active_plan['ozel_notlar'])
                
                if belirtiler:
                    try:
                        # BELIRTILER sözlüğünü al
                        from diyet_egzersiz import BELIRTILER
                        
                        # Belirtileri liste halinde HTML olarak göster
                        belirtiler_html = "<ul style='margin-top: 5px; margin-bottom: 5px;'>"
                        for belirti in belirtiler:
                            aciklama = BELIRTILER.get(belirti, "")
                            if aciklama:
                                belirtiler_html += f"<li><b>{belirti}</b>: {aciklama}</li>"
                            else:
                                belirtiler_html += f"<li><b>{belirti}</b></li>"
                        belirtiler_html += "</ul>"
                        
                        self.belirti_label.setText(belirtiler_html)
                        self.belirti_label.setTextFormat(Qt.RichText)
                        self.belirti_grup.setVisible(True)
                        return
                    except Exception as e:
                        print(f"Belirti açıklamaları yüklenirken hata: {e}")
            
            # Eğer belirti bulunamazsa veya plan yoksa
            self.belirti_label.setText("Henüz semptom girilmemiş")
            self.belirti_grup.setVisible(True)  # Yine de gösteriyoruz ama "Henüz semptom girilmemiş" yazıyor
            
        except Exception as e:
            print(f"Belirtiler gösterilirken hata: {e}")
            self.belirti_grup.setVisible(False)
    
    def belirtileri_cikar(self, notlar):
        """Plan notlarından belirtileri çıkarır"""
        if not notlar:
            return []
        
        # "Belirtiler: " ile başlayan satırı bul
        lines = notlar.split('\n')
        for line in lines:
            if "Belirtiler:" in line:
                belirti_text = line.split("Belirtiler:")[1].strip()
                return [b.strip() for b in belirti_text.split(',')]
        
        return []

class SekerRaporDialog(QDialog):
    def __init__(self, hasta_tc, hasta_isim, doktor_tc, parent=None):
        super().__init__(parent)
        self.hasta_tc = hasta_tc
        self.hasta_isim = hasta_isim
        self.doktor_tc = doktor_tc
        self.setWindowTitle(f"Kan Şekeri Raporları - {hasta_isim}")
        self.resize(900, 700)  # Increased height for graph
        self.arayuz_olustur()
        self.raporlari_yukle()
        
    def arayuz_olustur(self):
        layout = QVBoxLayout(self)
        
        # Başlık
        baslik = QLabel(f"{self.hasta_isim} - Kan Şekeri Raporları")
        baslik.setFont(QFont("Arial", 14, QFont.Bold))
        baslik.setAlignment(Qt.AlignCenter)
        layout.addWidget(baslik)
        
        # Tab widget for different views
        self.tab_widget = QTabWidget()
        
        # Table tab
        table_tab = QWidget()
        table_layout = QVBoxLayout(table_tab)
        
        # Tarih seçimi
        tarih_layout = QHBoxLayout()
        tarih_label = QLabel("Tarih:")
        self.tarih_secici = QDateEdit()
        self.tarih_secici.setDate(QDate.currentDate())
        self.tarih_secici.setCalendarPopup(True)
        self.tarih_secici.dateChanged.connect(self.raporlari_yukle)
        
        tarih_btn = QPushButton("Göster")
        tarih_btn.clicked.connect(self.raporlari_yukle)
        
        tarih_layout.addWidget(tarih_label)
        tarih_layout.addWidget(self.tarih_secici)
        tarih_layout.addWidget(tarih_btn)
        table_layout.addLayout(tarih_layout)
        
        # Tablo
        self.rapor_tablosu = QTableWidget()
        self.rapor_tablosu.setColumnCount(6)
        self.rapor_tablosu.setHorizontalHeaderLabels([
            "Ölçüm Zamanı", "Saat", "Değer (mg/dL)", "Seviye", "Uygun Zaman", "Ortalamaya Dahil"
        ])
        self.rapor_tablosu.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        table_layout.addWidget(self.rapor_tablosu)
        
        # Özet bilgisi
        self.ozet_label = QLabel()
        self.ozet_label.setWordWrap(True)
        table_layout.addWidget(self.ozet_label)
        
        # İnsülin önerisi
        self.insulin_label = QLabel()
        self.insulin_label.setFont(QFont("Arial", 12, QFont.Bold))
        self.insulin_label.setAlignment(Qt.AlignCenter)
        table_layout.addWidget(self.insulin_label)
        
        # Daily graph tab
        graph_tab = QWidget()
        graph_layout = QVBoxLayout(graph_tab)
        
        # Placeholder for the graph
        self.graph_container = QVBoxLayout()
        graph_layout.addLayout(self.graph_container)
        
        # Weekly graph tab
        weekly_tab = QWidget()
        weekly_layout = QVBoxLayout(weekly_tab)
        
        # Date range for weekly graph - MODIFIED FOR START AND END DATES
        weekly_date_layout = QHBoxLayout()
        
        # Add start date picker
        weekly_start_label = QLabel("Başlangıç Tarihi:")
        self.weekly_start_date = QDateEdit()
        self.weekly_start_date.setDate(QDate.currentDate().addDays(-7))  # Default to 7 days before end date
        self.weekly_start_date.setDisplayFormat("dd.MM.yyyy")
        self.weekly_start_date.setCalendarPopup(True)
        
        weekly_end_label = QLabel("Bitiş Tarihi:")
        self.weekly_date = QDateEdit()
        self.weekly_date.setDate(QDate.currentDate())
        self.weekly_date.setDisplayFormat("dd.MM.yyyy")
        self.weekly_date.setCalendarPopup(True)
        
        # Connect date signals to validate
        self.weekly_start_date.dateChanged.connect(self.validate_date_range)
        self.weekly_date.dateChanged.connect(self.validate_date_range)
        
        weekly_refresh_btn = QPushButton("Grafiği Güncelle")
        weekly_refresh_btn.clicked.connect(self.update_weekly_graph)
        
        weekly_date_layout.addWidget(weekly_start_label)
        weekly_date_layout.addWidget(self.weekly_start_date)
        weekly_date_layout.addWidget(weekly_end_label)
        weekly_date_layout.addWidget(self.weekly_date)
        weekly_date_layout.addWidget(weekly_refresh_btn)
        
        weekly_layout.addLayout(weekly_date_layout)
        
        # Placeholder for the weekly graph
        self.weekly_graph_container = QVBoxLayout()
        weekly_layout.addLayout(self.weekly_graph_container)
        
        # Add tabs
        self.tab_widget.addTab(table_tab, "Tablo Görünümü")
        self.tab_widget.addTab(graph_tab, "Günlük Grafik")
        self.tab_widget.addTab(weekly_tab, "Haftalık Grafik")
        
        # Connect tab changed signal
        self.tab_widget.currentChanged.connect(self.on_tab_changed)
        
        layout.addWidget(self.tab_widget)
        
        # Kapat butonu
        kapat_btn = QPushButton("Kapat")
        kapat_btn.clicked.connect(self.reject)
        layout.addWidget(kapat_btn)
    
    def on_tab_changed(self, index):
        """Handle tab changes - load appropriate data"""
        if index == 1:  # Daily graph tab
            self.update_blood_sugar_graph()
        elif index == 2:  # Weekly graph tab
            self.update_weekly_graph()
    
    def update_blood_sugar_graph(self):
        """Update the blood sugar graph for the selected date"""
        try:
            selected_date = self.tarih_secici.date().toPyDate()
            
            # Create the graph
            fig = create_blood_sugar_graph(self.hasta_tc, selected_date)
            
            # Display the graph
            embed_matplotlib_figure(self.graph_container, fig)
        except Exception as e:
            QMessageBox.warning(self, "Hata", f"Günlük grafik güncellenirken bir hata oluştu: {str(e)}")
    
    def validate_date_range(self):
        """Ensure start date is before or equal to end date"""
        start_date = self.weekly_start_date.date()
        end_date = self.weekly_date.date()
        
        if start_date > end_date:
            # If start date is after end date, set start date to end date
            self.weekly_start_date.setDate(end_date)
            QMessageBox.warning(self, "Uyarı", "Başlangıç tarihi bitiş tarihinden sonra olamaz.")
    
    def update_weekly_graph(self):
        """Update the weekly blood sugar graph with selected date range"""
        # Get both start and end dates
        start_date = self.weekly_start_date.date().toPyDate()
        end_date = self.weekly_date.date().toPyDate()
        
        # Create the graph with date range
        fig = create_weekly_graph(self.hasta_tc, end_date, start_date=start_date)
        
        # Display the graph
        embed_matplotlib_figure(self.weekly_graph_container, fig)
    
    def raporlari_yukle(self):
        # Doktorun hastasını seçtiği günün raporlarını getir
        basarili, raporlar = MainModule.raporlari_getir(self.hasta_tc, self.tarih_secici.date().toPyDate())
        
        if basarili:
            self.rapor_tablosu.setRowCount(0)  # Mevcut tabloyu temizle
            
            for i, rapor in enumerate(raporlar):
                self.rapor_tablosu.insertRow(i)
                self.rapor_tablosu.setItem(i, 0, QTableWidgetItem(rapor['olcum_zamani']))
                self.rapor_tablosu.setItem(i, 1, QTableWidgetItem(rapor['saat']))
                self.rapor_tablosu.setItem(i, 2, QTableWidgetItem(str(rapor['seker_seviyesi'])))
                self.rapor_tablosu.setItem(i, 3, QTableWidgetItem(rapor['seviye_durumu']))
                self.rapor_tablosu.setItem(i, 4, QTableWidgetItem("Evet" if rapor['zaman_uygun'] else "Hayır"))
                self.rapor_tablosu.setItem(i, 5, QTableWidgetItem("Evet" if rapor['ortalamaya_dahil'] else "Hayır"))
            
            # İstatistiksel verileri hesapla
            try:
                # Convert decimal values to float to avoid type mismatch
                toplam_seker = sum(float(rapor['seker_seviyesi']) for rapor in raporlar)
                ortalama_seker = toplam_seker / len(raporlar) if raporlar else 0
                
                # Özet bilgilerini güncelle
                self.ozet_label.setText(f"Toplam Ölçüm: {len(raporlar)}, Ortalama Şeker: {ortalama_seker:.1f} mg/dL")
                
                # İnsülin önerisi hesapla
                # Basit bir örnek: Eğer ortalama şeker 180'in üzerindeyse, insülin dozu öner
                if ortalama_seker > 180:
                    insülin_dozu = float(ortalama_seker) * 0.1  # Explicitly convert to float
                    self.insulin_label.setText(f"Önerilen İnsülin Dozu: {insülin_dozu:.1f} ünite")
                else:
                    self.insulin_label.setText("İnsülin gereksinimi yok")
            except Exception as e:
                # Handle any conversion errors
                self.ozet_label.setText(f"Ölçüm verilerinde hata: {str(e)}")
                self.insulin_label.setText("İnsülin önerisi hesaplanamadı")
            
            # Ayrıca, seçili tarih için grafiği güncelle
            try:
                if self.tab_widget.currentIndex() == 1:
                    self.update_blood_sugar_graph()
                elif self.tab_widget.currentIndex() == 2:
                    self.update_weekly_graph()
            except Exception as e:
                QMessageBox.warning(self, "Hata", f"Grafikler güncellenirken bir hata oluştu: {str(e)}")
        else:
            QMessageBox.warning(self, "Hata", str(raporlar))


class IlkOlcumGirisDialog(QDialog):
    def __init__(self, hasta_tc, hasta_isim, doktor_tc, parent=None):
        super().__init__(parent)
        self.hasta_tc = hasta_tc
        self.hasta_isim = hasta_isim
        self.doktor_tc = doktor_tc  # Doktor TC'sini ekledik
        self.setWindowTitle(f"{hasta_isim} - İlk Kan Şekeri Ölçümleri")
        self.setMinimumWidth(500)
        
        self.arayuz_olustur()
    
    def arayuz_olustur(self):
        from datetime import date
        
        layout = QVBoxLayout(self)
        
        # Başlık
        baslik = QLabel(f"{self.hasta_isim} - İlk Kan Şekeri Ölçümleri")
        baslik.setFont(QFont("Arial", 12, QFont.Bold))
        baslik.setAlignment(Qt.AlignCenter)
        layout.addWidget(baslik)
        
        # Bilgilendirme
        bilgi = QLabel("Hastanın ilk kan şekeri ölçümlerini aşağıya giriniz. "
                      "Tüm ölçümler aynı güne ait olmalıdır.")
        bilgi.setWordWrap(True)
        layout.addWidget(bilgi)
        
        # Tarih seçimi - 24.12.2023 formatında göster
        tarih_layout = QHBoxLayout()
        tarih_label = QLabel("Tarih:")
        self.tarih_secici = QDateEdit()
        self.tarih_secici.setDate(QDate.currentDate())
        self.tarih_secici.setDisplayFormat("dd.MM.yyyy")  # Gün.Ay.Yıl formatı
        self.tarih_secici.setCalendarPopup(True)
        
        tarih_layout.addWidget(tarih_label)
        tarih_layout.addWidget(self.tarih_secici)
        layout.addLayout(tarih_layout)
        
        # Ölçüm girişleri için form
        olcum_grup = QGroupBox("Kan Şekeri Ölçümleri")
        olcum_layout = QFormLayout()
        
        # Saat aralıkları
        from seker_utils import OLCUM_ZAMANLARI
        self.olcum_saati = {}
        self.olcum_degeri = {}
        
        for zaman, aralik in OLCUM_ZAMANLARI.items():
            # Her zaman dilimi için bir satır oluştur
            satir_layout = QHBoxLayout()
            
            # Saat girişi - 24 saatlik formatı kullan
            saat_secici = QTimeEdit()
            saat_secici.setTime(QTime(aralik[0].hour, aralik[0].minute))
            saat_secici.setDisplayFormat("HH:mm")  # 24 saatlik format
            satir_layout.addWidget(saat_secici)
            self.olcum_saati[zaman] = saat_secici
            
            # Değer girişi - improve validator
            deger_input = QLineEdit()
            deger_input.setPlaceholderText("mg/dL")
            
            # Set explicit validator parameters
            validator = QDoubleValidator(0, 999, 1)
            validator.setNotation(QDoubleValidator.StandardNotation)
            deger_input.setValidator(validator)
            
            # Add max length to prevent entering more than 3 digits + decimal + 1 decimal place
            deger_input.setMaxLength(5)
            
            # Connect to filter function to enforce constraints
            deger_input.textChanged.connect(self.filter_seker_input)
            
            satir_layout.addWidget(deger_input)
            self.olcum_degeri[zaman] = deger_input
            
            # Formu ekle
            olcum_layout.addRow(f"{zaman} ({aralik[0].hour}:00-{aralik[1].hour}:00):", satir_layout)
        
        olcum_grup.setLayout(olcum_layout)
        layout.addWidget(olcum_grup)
        
        # Butonlar
        buton_layout = QHBoxLayout()
        
        iptal_btn = QPushButton("İptal")
        iptal_btn.clicked.connect(self.reject)
        
        kaydet_btn = QPushButton("Ölçümleri Kaydet")
        kaydet_btn.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")
        kaydet_btn.clicked.connect(self.olcumleri_kaydet)
        
        buton_layout.addWidget(iptal_btn)
        buton_layout.addWidget(kaydet_btn)
        
        layout.addLayout(buton_layout)
    
    def olcumleri_kaydet(self):
        from seker_utils import zaman_kontrolu, seviye_belirle
        import mysql.connector
        from datetime import datetime
        
        olcum_tarihi = self.tarih_secici.date().toPyDate()
        
        # Veritabanı bağlantısı
        conn = mysql.connector.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME,
            charset=DB_CHARSET
        )
        cursor = conn.cursor()
        
        # En az bir ölçüm girilmiş mi kontrol et
        en_az_bir_olcum = False
        
        try:
            for zaman, deger_input in self.olcum_degeri.items():
                # Boş değerleri atla
                if not deger_input.text():
                    continue
                
                seker_degeri = float(deger_input.text().replace(',', '.'))
                olcum_saati = self.olcum_saati[zaman].time().toPyTime()
                
                # Zaman kontrolü yap
                zaman_uygun = zaman_kontrolu(zaman, olcum_saati)
                seviye_durumu = seviye_belirle(seker_degeri)
                
                # Veritabanına kaydet - Doktor tarafından yapıldığını belirtmek için olcum_turu eklendi
                cursor.execute("""
                    INSERT INTO KanSekeriKayitlari 
                    (tc_kimlik_no, tarih, saat, olcum_zamani, seker_seviyesi, olcum_turu, zaman_uygun, 
                    seviye_durumu, ortalamaya_dahil) 
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (self.hasta_tc, olcum_tarihi, olcum_saati, zaman, 
                    seker_degeri, "Doktor", zaman_uygun, seviye_durumu, zaman_uygun))
                
                en_az_bir_olcum = True
            
            if not en_az_bir_olcum:
                QMessageBox.warning(self, "Uyarı", "Lütfen en az bir ölçüm değeri giriniz.")
                return
            
            # İlk ölçüm yapıldığına dair bilgi kaydet - yeni tablo kullanarak
            cursor.execute("""
                INSERT INTO IlkOlcumKaydi (hasta_tc, doktor_tc, olcum_tarihi)
                VALUES (%s, %s, %s)
                ON DUPLICATE KEY UPDATE doktor_tc = %s, olcum_tarihi = %s
            """, (self.hasta_tc, self.doktor_tc, olcum_tarihi, self.doktor_tc, olcum_tarihi))
                
            conn.commit()
            self.accept()
            
        except ValueError:
            QMessageBox.warning(self, "Hata", "Lütfen geçerli bir kan şekeri değeri giriniz.")
        except Exception as e:
            QMessageBox.warning(self, "Hata", f"Ölçümler kaydedilirken bir hata oluştu: {str(e)}")
        finally:
            cursor.close()
            conn.close()
    
    # Add new method to filter input and prevent negative values
    def filter_seker_input(self, text):
        """Filters blood sugar input to ensure it's a positive number with at most 3 digits"""
        if not text:
            return
            
        # Get the sender (which QLineEdit triggered this)
        sender = self.sender()
        
        # Replace comma with decimal point for consistency
        if ',' in text:
            text = text.replace(',', '.')
            sender.setText(text)
            
        # Remove any non-numeric characters except decimal point
        filtered_text = ''.join([c for c in text if c.isdigit() or c == '.'])
        
        # Ensure only one decimal point
        if filtered_text.count('.') > 1:
            decimal_pos = filtered_text.find('.')
            filtered_text = filtered_text[:decimal_pos+1] + filtered_text[decimal_pos+1:].replace('.', '')
            
        # Ensure the value is not negative and not exceeding 3 digits before decimal
        try:
            value = float(filtered_text)
            if value < 0:
                filtered_text = '0'
            elif value > 999:
                filtered_text = '999'
                
            # Handle case when there are more than 3 digits before decimal
            if '.' in filtered_text:
                parts = filtered_text.split('.')
                if len(parts[0]) > 3:
                    filtered_text = parts[0][:3] + '.' + parts[1]
            elif len(filtered_text) > 3:
                filtered_text = filtered_text[:3]
                
        except ValueError:
            # If conversion fails, keep valid parts
            pass
            
        # Update text if it changed
        if filtered_text != text:
            sender.setText(filtered_text)

class HastaFiltrelemeDialog(QDialog):
    """Hastaları kan şekeri değerleri ve belirtilere göre filtreleme diyaloğu"""
    def __init__(self, doktor_tc, parent=None):
        super().__init__(parent)
        self.doktor_tc = doktor_tc
        self.filtered_patients = []
        
        self.setWindowTitle("Gelişmiş Hasta Filtreleme")
        self.setMinimumWidth(600)
        
        self.arayuz_olustur()
    
    def arayuz_olustur(self):
        layout = QVBoxLayout(self)
        
        # Başlık
        baslik = QLabel("Hastaları Kan Şekeri Değeri ve Belirtilere Göre Filtrele")
        baslik.setFont(QFont("Arial", 12, QFont.Bold))
        baslik.setAlignment(Qt.AlignCenter)
        layout.addWidget(baslik)
        
        # Kan şekeri aralığı
        kan_grup = QGroupBox("Kan Şekeri Aralığı")
        kan_layout = QHBoxLayout()
        
        self.min_seker = QLineEdit()
        self.min_seker.setPlaceholderText("Min (mg/dL)")
        self.min_seker.setValidator(QDoubleValidator(0, 999, 1))
        
        self.max_seker = QLineEdit()
        self.max_seker.setPlaceholderText("Max (mg/dL)")
        self.max_seker.setValidator(QDoubleValidator(0, 999, 1))
        
        kan_layout.addWidget(QLabel("Minimum:"))
        kan_layout.addWidget(self.min_seker)
        kan_layout.addWidget(QLabel("Maximum:"))
        kan_layout.addWidget(self.max_seker)
        
        kan_grup.setLayout(kan_layout)
        layout.addWidget(kan_grup)
        
        # Filtreleme tipi seçimi
        tip_grup = QGroupBox("Filtreleme Tipi")
        tip_layout = QVBoxLayout()
        
        self.son_olcum_radio = QRadioButton("Son ölçüme göre")
        self.son_olcum_radio.setChecked(True)
        
        self.ortalama_radio = QRadioButton("Ortalama ölçüme göre")
        
        tip_layout.addWidget(self.son_olcum_radio)
        tip_layout.addWidget(self.ortalama_radio)
        
        tip_grup.setLayout(tip_layout)
        layout.addWidget(tip_grup)
        
        # Tarih aralığı
        tarih_grup = QGroupBox("Tarih Aralığı (İsteğe Bağlı)")
        tarih_layout = QHBoxLayout()
        
        self.baslangic_tarih = QDateEdit()
        self.baslangic_tarih.setDate(QDate.currentDate().addMonths(-1))
        self.baslangic_tarih.setCalendarPopup(True)
        
        self.bitis_tarih = QDateEdit()
        self.bitis_tarih.setDate(QDate.currentDate())
        self.bitis_tarih.setCalendarPopup(True)
        
        tarih_layout.addWidget(QLabel("Başlangıç:"))
        tarih_layout.addWidget(self.baslangic_tarih)
        tarih_layout.addWidget(QLabel("Bitiş:"))
        tarih_layout.addWidget(self.bitis_tarih)
        
        tarih_grup.setLayout(tarih_layout)
        layout.addWidget(tarih_grup)
        
        # Belirtiler - diyet_egzersiz.py modülünden BELIRTILER sözlüğünü kullan
        try:
            from diyet_egzersiz import BELIRTILER
            
            belirtiler_grup = QGroupBox("Belirtiler (İsteğe Bağlı)")
            belirtiler_layout = QVBoxLayout(belirtiler_grup)
            
            self.belirtiler_check = {}
            for belirti, aciklama in BELIRTILER.items():
                checkbox = QCheckBox(f"{belirti} ({aciklama})")
                self.belirtiler_check[belirti] = checkbox
                belirtiler_layout.addWidget(checkbox)
            
            belirtiler_grup.setLayout(belirtiler_layout)
            
            # Çok sayıda belirti varsa kaydırma alanı ekle
            scroll = QScrollArea()
            scroll.setWidget(belirtiler_grup)
            scroll.setWidgetResizable(True)
            scroll.setMinimumHeight(200)
            layout.addWidget(scroll)
        except ImportError:
            # BELIRTILER sözlüğü bulunamazsa basit bir metin alanı ekle
            self.belirti_input = QLineEdit()
            self.belirti_input.setPlaceholderText("Belirtileri virgülle ayırarak yazın")
            layout.addWidget(QLabel("Belirtiler (İsteğe Bağlı):"))
            layout.addWidget(self.belirti_input)
        
        # Butonlar
        buton_layout = QHBoxLayout()
        
        iptal_btn = QPushButton("İptal")
        iptal_btn.clicked.connect(self.reject)
        
        filtrele_btn = QPushButton("Filtrele")
        filtrele_btn.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")
        filtrele_btn.clicked.connect(self.hastalari_filtrele)
        
        temizle_btn = QPushButton("Filtreleri Temizle")
        temizle_btn.clicked.connect(self.filtreleri_temizle)
        
        buton_layout.addWidget(iptal_btn)
        buton_layout.addWidget(temizle_btn)
        buton_layout.addWidget(filtrele_btn)
        
        layout.addLayout(buton_layout)
    
    def filtreleri_temizle(self):
        """Filtreleri temizle"""
        self.min_seker.clear()
        self.max_seker.clear()
        self.son_olcum_radio.setChecked(True)
        self.baslangic_tarih.setDate(QDate.currentDate().addMonths(-1))
        self.bitis_tarih.setDate(QDate.currentDate())
        
        # Belirtileri temizle
        if hasattr(self, 'belirtiler_check'):
            for checkbox in self.belirtiler_check.values():
                checkbox.setChecked(False)
        elif hasattr(self, 'belirti_input'):
            self.belirti_input.clear()
    
    def hastalari_filtrele(self):
        """Hastaları seçilen kriterlere göre filtrele"""
        # Filtre değerlerini al
        min_seker = self.min_seker.text().strip()
        max_seker = self.max_seker.text().strip()
        kullan_son_olcum = self.son_olcum_radio.isChecked()
        baslangic_tarih = self.baslangic_tarih.date().toPyDate()
        bitis_tarih = self.bitis_tarih.date().toPyDate()
        
        # Seçilen belirtileri al
        secili_belirtiler = []
        if hasattr(self, 'belirtiler_check'):
            for belirti, checkbox in self.belirtiler_check.items():
                if checkbox.isChecked():
                    secili_belirtiler.append(belirti)
        elif hasattr(self, 'belirti_input'):
            belirti_text = self.belirti_input.text().strip()
            if belirti_text:
                secili_belirtiler = [b.strip() for b in belirti_text.split(',')]
        
        # Girişleri doğrula
        if (min_seker and not max_seker) or (not min_seker and max_seker):
            QMessageBox.warning(self, "Uyarı", "Lütfen hem minimum hem de maksimum kan şekeri değerini girin.")
            return
        
        if baslangic_tarih > bitis_tarih:
            QMessageBox.warning(self, "Uyarı", "Başlangıç tarihi bitiş tarihinden sonra olamaz.")
            return
        
        try:
            # Değerleri sayısal tipe dönüştür
            min_seker_val = float(min_seker) if min_seker else None
            max_seker_val = float(max_seker) if max_seker else None
            
            # Veritabanına bağlan
            conn = mysql.connector.connect(
                host=DB_HOST,
                user=DB_USER,
                password=DB_PASSWORD,
                database=DB_NAME,
                charset=DB_CHARSET
            )
            cursor = conn.cursor(dictionary=True)
            
            # Her sorgu, ortalama kan şekeri değerini de getirsin
            if min_seker_val is not None and max_seker_val is not None:
                # Kan şekeri aralığına göre filtreleme
                if kullan_son_olcum:
                    # Son ölçüme göre filtreleme
                    query = """
                    SELECT h.*, ROUND(AVG(k.seker_seviyesi), 1) as ortalama_seker
                    FROM Hastalar h
                    JOIN (
                        SELECT tc_kimlik_no, MAX(tarih) as son_tarih 
                        FROM KanSekeriKayitlari
                        WHERE tarih BETWEEN %s AND %s
                        GROUP BY tc_kimlik_no
                    ) son ON h.tc_kimlik_no = son.tc_kimlik_no
                    JOIN KanSekeriKayitlari k ON h.tc_kimlik_no = k.tc_kimlik_no 
                        AND k.tarih = son.son_tarih
                    WHERE h.doktor_tc = %s 
                        AND k.seker_seviyesi BETWEEN %s AND %s
                    GROUP BY h.tc_kimlik_no
                    """
                    params = [baslangic_tarih, bitis_tarih, self.doktor_tc, min_seker_val, max_seker_val]
                else:
                    # Ortalama ölçüme göre filtreleme
                    query = """
                    SELECT h.*, ROUND(AVG(k.seker_seviyesi), 1) as ortalama_seker
                    FROM Hastalar h
                    JOIN KanSekeriKayitlari k ON h.tc_kimlik_no = k.tc_kimlik_no
                    WHERE h.doktor_tc = %s 
                        AND k.tarih BETWEEN %s AND %s
                    GROUP BY h.tc_kimlik_no
                    HAVING AVG(k.seker_seviyesi) BETWEEN %s AND %s
                    """
                    params = [self.doktor_tc, baslangic_tarih, bitis_tarih, min_seker_val, max_seker_val]
            else:
                # Sadece belirtilere göre filtreleme veya tüm hastaları getirme
                query = """
                SELECT h.*, ROUND(AVG(k.seker_seviyesi), 1) as ortalama_seker
                FROM Hastalar h
                LEFT JOIN KanSekeriKayitlari k ON h.tc_kimlik_no = k.tc_kimlik_no 
                    AND k.tarih BETWEEN %s AND %s
                WHERE h.doktor_tc = %s
                GROUP BY h.tc_kimlik_no
                """
                params = [baslangic_tarih, bitis_tarih, self.doktor_tc]
            
            cursor.execute(query, params)
            filtered_patients = cursor.fetchall()
            
            # Belirtilere göre filtreleme (varsa)
            if secili_belirtiler and filtered_patients:
                try:
                    # TC kimlik listesi oluştur
                    tc_list = ', '.join([f"'{patient['tc_kimlik_no']}'" for patient in filtered_patients])
                    
                    # Belirtileri içeren notları bul - DiyetEgzersizTakip yerine DiyetEgzersizPlanlari tablosundan
                    # ve notlar yerine ozel_notlar alanından arama yap
                    symptom_query = f"""
                    SELECT DISTINCT hasta_tc
                    FROM DiyetEgzersizPlanlari
                    WHERE hasta_tc IN ({tc_list})
                    AND (
                    """
                    
                    # Her belirti için koşul oluştur
                    symptom_conditions = []
                    for symptom in secili_belirtiler:
                        symptom_conditions.append(f"ozel_notlar LIKE '%{symptom}%'")
                    
                    symptom_query += " OR ".join(symptom_conditions)
                    symptom_query += ")"
                    
                    cursor.execute(symptom_query)
                    symptom_patients = cursor.fetchall()
                    
                    if symptom_patients:
                        # Belirtilere uyan hastaların TC numaralarını al
                        symptom_tc_list = [patient['hasta_tc'] for patient in symptom_patients]
                        
                        # İlk filtreleme sonucunu belirtilere uyanlara göre filtrele
                        filtered_patients = [patient for patient in filtered_patients 
                                         if patient['tc_kimlik_no'] in symptom_tc_list]
                except Exception as e:
                    print(f"Belirtiler filtreleme hatası: {e}")
            
            # Filtrelenmiş hastaları tabloya yükle
            self.filtered_patients = filtered_patients
            
            if not filtered_patients:
                QMessageBox.information(self, "Bilgi", "Belirtilen kriterlere uygun hasta bulunamadı.")
                return
            
            QMessageBox.information(self, "Sonuç", f"{len(filtered_patients)} hasta kriterlere uygun bulundu.")
            self.accept()
            
            # Temizle butonuna basıldığında filtreleri sıfırla
            self.filtreleri_temizle()
            
        except Exception as e:
            QMessageBox.warning(self, "Hata", f"Filtreleme sırasında bir hata oluştu: {str(e)}")
        finally:
            if 'conn' in locals() and conn:
                if 'cursor' in locals() and cursor:
                    cursor.close()
                conn.close()

class HastaDiyetEgzersizRaporDialog(QDialog):
    """Dialog for viewing a patient's diet and exercise adherence reports"""
    def __init__(self, hasta_tc, hasta_isim, parent=None):
        super().__init__(parent)
        self.hasta_tc = hasta_tc
        self.hasta_isim = hasta_isim
        
        self.setWindowTitle(f"Diyet ve Egzersiz Raporları - {hasta_isim}")
        self.setMinimumWidth(800)  # Increased width for charts
        self.setMinimumHeight(700)  # Ensure enough height for charts
        
        self.arayuz_olustur()
        self.raporlari_yukle()
    
    def arayuz_olustur(self):
        layout = QVBoxLayout(self)
        
        # Title
        baslik = QLabel(f"{self.hasta_isim} - Diyet ve Egzersiz Raporları")
        baslik.setFont(QFont("Arial", 14, QFont.Bold))
        baslik.setAlignment(Qt.AlignCenter)
        layout.addWidget(baslik)
        
        # Plan information
        self.plan_bilgi = QLabel("Plan bilgisi yükleniyor...")
        self.plan_bilgi.setWordWrap(True)
        self.plan_bilgi.setStyleSheet("font-weight: bold; color: #1976D2;")
        layout.addWidget(self.plan_bilgi)
        
        # Add compliance summary section
        self.compliance_summary = QLabel("Uyum bilgisi yükleniyor...")
        self.compliance_summary.setAlignment(Qt.AlignCenter)
        self.compliance_summary.setStyleSheet("font-size: 14px; font-weight: bold; margin: 10px;")
        layout.addWidget(self.compliance_summary)
        
        # Create horizontal layout for pie charts
        charts_layout = QHBoxLayout()
        
        # Diet compliance chart container
        diet_chart_container = QGroupBox("Diyet Uyumu")
        diet_chart_layout = QVBoxLayout(diet_chart_container)
        self.diet_chart_widget = QLabel("Grafik yükleniyor...")
        self.diet_chart_widget.setAlignment(Qt.AlignCenter)
        self.diet_chart_widget.setMinimumSize(300, 300)
        diet_chart_layout.addWidget(self.diet_chart_widget)
        
        # Exercise compliance chart container
        exercise_chart_container = QGroupBox("Egzersiz Uyumu")
        exercise_chart_layout = QVBoxLayout(exercise_chart_container)
        self.exercise_chart_widget = QLabel("Grafik yükleniyor...")
        self.exercise_chart_widget.setAlignment(Qt.AlignCenter)
        self.exercise_chart_widget.setMinimumSize(300, 300)
        exercise_chart_layout.addWidget(self.exercise_chart_widget)
        
        # Add chart containers to layout
        charts_layout.addWidget(diet_chart_container)
        charts_layout.addWidget(exercise_chart_container)
        
        # Add charts layout to main layout
        layout.addLayout(charts_layout)
        
        # Reports table
        self.rapor_tablosu = QTableWidget()
        self.rapor_tablosu.setColumnCount(5)
        self.rapor_tablosu.setHorizontalHeaderLabels([
            "Tarih", "Diyet Yapıldı", "Egzersiz Yapıldı", "Notlar", "Bildirim Zamanı"
        ])
        self.rapor_tablosu.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.rapor_tablosu)
        
        # Mark as read button
        self.okundu_btn = QPushButton("Seçili Raporları Okundu Olarak İşaretle")
        self.okundu_btn.clicked.connect(self.okundu_isaretle)
        layout.addWidget(self.okundu_btn)
        
        # Close button
        kapat_btn = QPushButton("Kapat")
        kapat_btn.clicked.connect(self.accept)
        layout.addWidget(kapat_btn)
    
    def hesapla_uyum_yuzdesi(self, active_plan, history):
        """Calculate diet and exercise compliance percentages"""
        if not active_plan or not history:
            return 0, 0, 0
        
        # Get plan dates
        from datetime import datetime, date
        baslangic = active_plan['baslangic_tarihi']
        bitis = active_plan['bitis_tarihi']
        bugun = date.today()
        
        # If plan hasn't started yet
        if baslangic > bugun:
            return 0, 0, 0
        
        # If plan has ended, use end date, otherwise use today
        son_gun = min(bitis, bugun)
        
        # Calculate total days in plan so far
        from datetime import timedelta
        toplam_gun = (son_gun - baslangic).days + 1
        
        if toplam_gun <= 0:
            return 0, 0, 0
        
        # Count days with diet and exercise
        diyet_gun = sum(1 for report in history if report['diyet_yapildi'] and report['tarih'] >= baslangic and report['tarih'] <= son_gun)
        egzersiz_gun = sum(1 for report in history if report['egzersiz_yapildi'] and report['tarih'] >= baslangic and report['tarih'] <= son_gun)
        
        # Calculate percentages
        diyet_yuzde = (diyet_gun / toplam_gun) * 100
        egzersiz_yuzde = (egzersiz_gun / toplam_gun) * 100
        
        return diyet_yuzde, egzersiz_yuzde, toplam_gun
    
    def olustur_uyum_grafigi(self, yuzde, baslik, renk='#4CAF50'):
        """Create a pie chart showing compliance percentage"""
        import matplotlib.pyplot as plt
        import numpy as np
        import io
        
        # Create figure
        fig, ax = plt.subplots(figsize=(5, 5), subplot_kw=dict(aspect="equal"))
        
        # Data
        data = [yuzde, 100-yuzde]
        labels = [f"Uyum ({yuzde:.1f}%)", f"Eksik ({100-yuzde:.1f}%)"]
        colors = [renk, '#F5F5F5']  # Green for compliance, light gray for non-compliance
        
        # Create pie chart
        wedges, texts, autotexts = ax.pie(
            data, 
            labels=labels, 
            colors=colors,
            autopct='%1.1f%%', 
            startangle=90,
            wedgeprops={'edgecolor': 'w', 'linewidth': 2},
            textprops={'fontsize': 12, 'fontweight': 'bold'}
        )
        
        # Equal aspect ratio ensures that pie is drawn as a circle
        ax.set_title(baslik, fontsize=14, fontweight='bold')
        
        # Save to buffer
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=100, bbox_inches='tight')
        plt.close(fig)
        buf.seek(0)
        
        # Convert to QPixmap
        from PyQt5.QtGui import QPixmap, QImage
        image = QImage.fromData(buf.getvalue())
        pixmap = QPixmap.fromImage(image)
        
        return pixmap
    
    def raporlari_yukle(self):
        """Load the patient's adherence reports"""
        # Get active plan
        active_plan = get_active_plan(self.hasta_tc)
        
        if active_plan:
            self.plan_bilgi.setText(
                f"Aktif Plan: {active_plan['baslangic_tarihi']} - {active_plan['bitis_tarihi']}\n"
                f"Diyet: {active_plan['diyet_turu']} - {active_plan['diyet_aciklama']}\n"
                f"Egzersiz: {active_plan['egzersiz_turu']} - {active_plan['egzersiz_aciklama']}\n"
                f"Notlar: {active_plan['ozel_notlar'] if active_plan['ozel_notlar'] else 'Yok'}"
            )
        else:
            self.plan_bilgi.setText("Hastanın aktif bir diyet ve egzersiz planı bulunmamaktadır.")
        
        # Get adherence history - get all history, not just limited to 30 days
        history = get_patient_adherence_history(self.hasta_tc, limit=1000)
        
        # Calculate compliance percentages
        diyet_yuzde, egzersiz_yuzde, toplam_gun = self.hesapla_uyum_yuzdesi(active_plan, history)
        
        # Update compliance summary
        if active_plan:
            self.compliance_summary.setText(
                f"Plan Başlangıç: {active_plan['baslangic_tarihi'].strftime('%d.%m.%Y')} - "
                f"Bitiş: {active_plan['bitis_tarihi'].strftime('%d.%m.%Y')} | "
                f"Toplam {toplam_gun} gün | "
                f"Diyet Uyumu: %{diyet_yuzde:.1f} | "
                f"Egzersiz Uyumu: %{egzersiz_yuzde:.1f}"
            )
        else:
            self.compliance_summary.setText("Uyum hesaplaması için aktif plan bulunmamaktadır.")
        
        # Create and display compliance charts
        if active_plan:
            # Diet compliance chart
            diet_pixmap = self.olustur_uyum_grafigi(diyet_yuzde, "Diyet Uyumu", '#4CAF50')  # Green
            self.diet_chart_widget.setPixmap(diet_pixmap)
            
            # Exercise compliance chart
            exercise_pixmap = self.olustur_uyum_grafigi(egzersiz_yuzde, "Egzersiz Uyumu", '#2196F3')  # Blue
            self.exercise_chart_widget.setPixmap(exercise_pixmap)
        else:
            self.diet_chart_widget.setText("Aktif plan bulunmamaktadır.")
            self.exercise_chart_widget.setText("Aktif plan bulunmamaktadır.")
        
        # Clear table
        self.rapor_tablosu.setRowCount(0)
        
        # Fill table with reports
        for i, report in enumerate(history):
            self.rapor_tablosu.insertRow(i)
            
            # Date
            tarih_item = QTableWidgetItem(report['tarih'].strftime("%d.%m.%Y"))
            self.rapor_tablosu.setItem(i, 0, tarih_item)
            
            # Diet status
            diyet_item = QTableWidgetItem("✓" if report['diyet_yapildi'] else "✗")
            diyet_item.setTextAlignment(Qt.AlignCenter)
            diyet_item.setForeground(Qt.darkGreen if report['diyet_yapildi'] else Qt.red)
            self.rapor_tablosu.setItem(i, 1, diyet_item)
            
            # Exercise status
            egzersiz_item = QTableWidgetItem("✓" if report['egzersiz_yapildi'] else "✗")
            egzersiz_item.setTextAlignment(Qt.AlignCenter)
            egzersiz_item.setForeground(Qt.darkGreen if report['egzersiz_yapildi'] else Qt.red)
            self.rapor_tablosu.setItem(i, 2, egzersiz_item)
            
            # Notes
            notlar_item = QTableWidgetItem(report['notlar'] if report['notlar'] else "-")
            self.rapor_tablosu.setItem(i, 3, notlar_item)
            
            # Notification time
            bildirim_item = QTableWidgetItem(report['bildirim_zamani'].strftime("%d.%m.%Y %H:%M"))
            self.rapor_tablosu.setItem(i, 4, bildirim_item)
            
            # Highlight unread reports
            if not report['okundu']:
                for col in range(5):
                    self.rapor_tablosu.item(i, col).setBackground(Qt.yellow)
            
            # Store report ID for marking as read
            tarih_item.setData(Qt.UserRole, report['id'])

    def okundu_isaretle(self):
        """Mark selected reports as read"""
        # Get selected rows
        selected_rows = set(item.row() for item in self.rapor_tablosu.selectedItems())
        
        if not selected_rows:
            QMessageBox.information(self, "Bilgi", "Lütfen okundu olarak işaretlenecek raporları seçin.")
            return
        
        # Get report IDs from table
        report_ids = []
        for row in selected_rows:
            # Report ID is stored in first column's UserRole data
            item = self.rapor_tablosu.item(row, 0)
            if item and item.data(Qt.UserRole):
                report_ids.append(item.data(Qt.UserRole))
        
        if not report_ids:
            QMessageBox.warning(self, "Uyarı", "Seçilen raporların ID bilgisi bulunamadı.")
            return
        
        # Call the function to mark reports as read
        from diyet_egzersiz import mark_reports_as_read
        
        if mark_reports_as_read(report_ids):
            # Refresh the reports display
            self.raporlari_yukle()
            QMessageBox.information(self, "Başarılı", "Seçili raporlar okundu olarak işaretlendi.")
        else:
            QMessageBox.warning(self, "Hata", "Raporlar işaretlenirken bir hata oluştu.")

