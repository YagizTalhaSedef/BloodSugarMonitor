from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                           QLineEdit, QMessageBox, QGroupBox, QPushButton, QStackedWidget,
                           QFileDialog, QFormLayout, QComboBox, QDateEdit, QTimeEdit,
                           QTableWidget, QTableWidgetItem, QHeaderView,QTabWidget,QDialog,QSizePolicy)
from PyQt5.QtCore import Qt, QBuffer, QDateTime, QDate, QTime
from PyQt5.QtGui import QFont, QPixmap, QDoubleValidator
import mysql.connector
from datetime import datetime, date, time
import matplotlib
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import numpy as np
from graph_utils import create_blood_sugar_graph, create_weekly_graph, embed_matplotlib_figure

# Import config
try:
    from config import DB_HOST, DB_USER, DB_PASSWORD, DB_NAME, DB_CHARSET
except ImportError:
    DB_HOST = "localhost"
    DB_USER = "root"
    DB_PASSWORD = "YOUR_PASSWORD"
    DB_NAME = "diyabet"
    DB_CHARSET = "utf8mb4"

# Import utility modules
from seker_utils import (zaman_kontrolu, seviye_belirle, insulin_onerisi_hesapla,
                        gunluk_olcumleri_getir, ortalama_hesapla, uyari_olustur,
                        kontrol_ve_uyari_olustur, kontrol_gunluk_olcumler,
                        OLCUM_ZAMANLARI, SEKER_SEVIYELERI)

# Import the diet and exercise widget
from diyet_egzersiz import HastaDiyetEgzersizWidget

# Import Main module
import Main as MainModule

# Import the new utility function
from ui_utils import format_time_safely  

class HastaEkrani(QMainWindow):
    def __init__(self, hasta_bilgisi):
        super().__init__()
        self.hasta = hasta_bilgisi
        
        # Handle potential missing fields with defaults
        if 'isim_soyisim' not in self.hasta or not self.hasta['isim_soyisim']:
            self.hasta['isim_soyisim'] = "Hasta"
        if 'tc_kimlik_no' not in self.hasta:
            self.hasta['tc_kimlik_no'] = ""
        if 'cinsiyet' not in self.hasta:
            self.hasta['cinsiyet'] = "E"
        if 'mail' not in self.hasta:
            self.hasta['mail'] = ""
        
        self.setWindowTitle(f"{self.hasta['isim_soyisim']} - Diyabet Takip Sistemi")
        self.setMinimumSize(1000, 600)
        
        # Fıstık yeşili tema için styleSheet
        self.setStyleSheet("""
            QMainWindow, QWidget {
                background-color: #E8F5E9;
            }
            QPushButton {
                background-color: #81C784;
                color: white;
                border-radius: 5px;
                padding: 8px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #66BB6A;
            }
            QGroupBox {
                border: 1px solid #81C784;
                border-radius: 5px;
                margin-top: 10px;
            }
            QGroupBox::title {
                color: #2E7D32;
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
            QLabel {
                color: #2E7D32;
            }
            QLineEdit, QComboBox {
                border: 1px solid #81C784;
                border-radius: 3px;
                padding: 5px;
                selection-background-color: #66BB6A;
            }
        """)
        
        try:
            self.arayuz_olustur()
            # Safely try to load profile photo if available
            try:
                self.profil_foto_goster()
            except Exception:
                # Silently handle errors without printing
                pass
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Hasta ekranı oluşturulurken bir hata oluştu: {e}")

    def arayuz_olustur(self):
        # Ana widget ve layout
        merkez_widget = QWidget()
        ana_layout = QVBoxLayout(merkez_widget)
        
        # Hasta bilgileri başlığı
        baslik = QLabel(f"Hoş Geldiniz, {self.hasta['isim_soyisim']}")
        baslik.setFont(QFont("Arial", 16, QFont.Bold))
        baslik.setAlignment(Qt.AlignCenter)
        ana_layout.addWidget(baslik)
        
        # Menü butonları
        menu_layout = QHBoxLayout()
        
        profil_btn = QPushButton("Profil")
        profil_btn.clicked.connect(self.profil_goster)
        
        insulin_btn = QPushButton("İnsülin Takibi")
        insulin_btn.clicked.connect(self.insulin_takibi)
        
        seker_btn = QPushButton("Kan Şekeri Ölçümü")
        seker_btn.clicked.connect(self.kan_sekeri_olcumu)
        
        diyet_btn = QPushButton("Diyet")
        diyet_btn.clicked.connect(self.diyet_takibi)
        
        rapor_btn = QPushButton("Raporlar")
        rapor_btn.clicked.connect(self.raporlari_goster)
        
        menu_layout.addWidget(profil_btn)
        menu_layout.addWidget(insulin_btn)
        menu_layout.addWidget(seker_btn)
        menu_layout.addWidget(diyet_btn)
        menu_layout.addWidget(rapor_btn)
        
        ana_layout.addLayout(menu_layout)
        
        # İçerik alanı - stackedWidget kullanarak farklı sayfalar arasında geçiş yapabiliriz
        self.sayfa_alani = QStackedWidget()
        
        # Profil sayfası - Düzenlendi
        self.profil_sayfasi = QWidget()
        profil_layout = QVBoxLayout(self.profil_sayfasi)
        
        # Profil fotoğrafı
        foto_layout = QHBoxLayout()
        self.profil_foto_label = QLabel()
        self.profil_foto_label.setFixedSize(200, 200)
        self.profil_foto_label.setAlignment(Qt.AlignCenter)
        self.profil_foto_label.setStyleSheet("border: 2px solid #81C784; border-radius: 100px;")
        
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
        
        profil_layout.addLayout(foto_layout)
        
        # Kişisel bilgiler
        profil_grup = QGroupBox("Kişisel Bilgilerim")
        profil_form = QFormLayout()
        
        tc_label = QLabel(self.hasta['tc_kimlik_no'])
        isim_label = QLabel(self.hasta['isim_soyisim'])
        cinsiyet_label = QLabel('Erkek' if self.hasta['cinsiyet'] == 'E' else 'Kadın')
        email_label = QLabel(self.hasta['mail'])
        
        profil_form.addRow("TC Kimlik No:", tc_label)
        profil_form.addRow("İsim Soyisim:", isim_label)
        profil_form.addRow("Cinsiyet:", cinsiyet_label)
        profil_form.addRow("Email:", email_label)
        
        profil_grup.setLayout(profil_form)
        profil_layout.addWidget(profil_grup)
        
        # Fiziksel bilgiler grubu - YENİ EKLENEN
        fiziksel_grup = QGroupBox("Fiziksel Bilgilerim")
        fiziksel_form = QFormLayout()
        
        # Fiziksel bilgiler için varsayılan metin
        varsayilan_metin = "Bilgi girilmemiş"
        
        # Yaş bilgisi
        yas_text = str(self.hasta.get('yas', '')) if self.hasta.get('yas') else varsayilan_metin
        yas_label = QLabel(yas_text)
        
        # Boy bilgisi
        boy_text = f"{self.hasta.get('boy', '')} cm" if self.hasta.get('boy') else varsayilan_metin
        boy_label = QLabel(boy_text)
        
        # Kilo bilgisi
        kilo_text = f"{self.hasta.get('kilo', '')} kg" if self.hasta.get('kilo') else varsayilan_metin
        kilo_label = QLabel(kilo_text)
        
        # VKİ bilgisi
        vki = self.hasta.get('vki')
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
            
            vki_text = f"{vki:.1f} ({durum})"
            vki_label = QLabel(vki_text)
            vki_label.setStyleSheet(f"color: {renk}; font-weight: bold;")
        else:
            vki_label = QLabel(varsayilan_metin)
        
        fiziksel_form.addRow("Yaş:", yas_label)
        fiziksel_form.addRow("Boy:", boy_label)
        fiziksel_form.addRow("Kilo:", kilo_label)
        fiziksel_form.addRow("Vücut Kitle İndeksi:", vki_label)
        
        fiziksel_grup.setLayout(fiziksel_form)
        profil_layout.addWidget(fiziksel_grup)
        
        profil_layout.addStretch()
        
        # İnsülin takibi sayfası
        self.insulin_sayfasi = QWidget()
        insulin_layout = QVBoxLayout(self.insulin_sayfasi)
        
        insulin_baslik = QLabel("İnsülin Takibi")
        insulin_baslik.setFont(QFont("Arial", 14, QFont.Bold))
        insulin_baslik.setAlignment(Qt.AlignCenter)
        insulin_layout.addWidget(insulin_baslik)

        # İnsülin kayıtları tablosu
        insulin_grup = QGroupBox("İnsülin Kayıtları")
        insulin_tablo_layout = QVBoxLayout()

        self.insulin_tablosu = QTableWidget()
        self.insulin_tablosu.setColumnCount(4)
        self.insulin_tablosu.setHorizontalHeaderLabels(["Tarih", "Doz (mL)", "Durum", "İşlemler"])
        self.insulin_tablosu.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        insulin_tablo_layout.addWidget(self.insulin_tablosu)

        insulin_grup.setLayout(insulin_tablo_layout)
        insulin_layout.addWidget(insulin_grup)

        # Günlük insülin durum raporu
        insulin_durum_grup = QGroupBox("Günlük İnsülin Durum")
        insulin_durum_layout = QVBoxLayout()

        # Günün insülin bilgisi
        self.gunluk_insulin_bilgi = QLabel("Günlük insülin bilgisi burada gösterilecektir.")
        self.gunluk_insulin_bilgi.setAlignment(Qt.AlignCenter)
        self.gunluk_insulin_bilgi.setWordWrap(True)
        self.gunluk_insulin_bilgi.setStyleSheet("font-size: 14px; color: #2196F3; font-weight: bold;")
        insulin_durum_layout.addWidget(self.gunluk_insulin_bilgi)

        # İnsülin kullanım durumu seçimi
        kullanim_layout = QHBoxLayout()
        kullanim_label = QLabel("İnsülin Kullanımı:")
        self.insulin_kullanildi_btn = QPushButton("Kullandım")
        self.insulin_kullanilmadi_btn = QPushButton("Kullanmadım")
        self.insulin_kullanildi_btn.setStyleSheet("background-color: #4CAF50; color: white;")
        self.insulin_kullanilmadi_btn.setStyleSheet("background-color: #F44336; color: white;")
        self.insulin_kullanildi_btn.clicked.connect(self.insulin_kullanildi)
        self.insulin_kullanilmadi_btn.clicked.connect(self.insulin_kullanilmadi)

        kullanim_layout.addWidget(kullanim_label)
        kullanim_layout.addWidget(self.insulin_kullanildi_btn)
        kullanim_layout.addWidget(self.insulin_kullanilmadi_btn)
        insulin_durum_layout.addLayout(kullanim_layout)

        insulin_durum_grup.setLayout(insulin_durum_layout)
        insulin_layout.addWidget(insulin_durum_grup)

        # Yenile butonu
        insulin_yenile_btn = QPushButton("Bilgileri Yenile")
        insulin_yenile_btn.clicked.connect(self.insulin_bilgilerini_yukle)
        insulin_layout.addWidget(insulin_yenile_btn)
        
        # Kan şekeri ölçüm sayfası - Completely updated
        self.seker_sayfasi = QWidget()
        seker_layout = QVBoxLayout(self.seker_sayfasi)
        
        # Başlık
        seker_baslik = QLabel("Kan Şekeri Takibi")
        seker_baslik.setFont(QFont("Arial", 14, QFont.Bold))
        seker_baslik.setAlignment(Qt.AlignCenter)
        seker_layout.addWidget(seker_baslik)
        
        # İki bölümlü düzen: Yeni ölçüm girişi ve Günlük özet
        seker_alt_layout = QHBoxLayout()
        
        # Sol panel - Yeni ölçüm ekleme ve grafik görünümü
        sol_panel = QWidget()
        sol_layout = QVBoxLayout(sol_panel)
        
        # Tab widget to switch between form and graph
        sol_tab = QTabWidget()
        
        # Form tab
        form_tab = QWidget()
        yeni_olcum_layout = QFormLayout(form_tab)
        
        # İlk ölçüm uyarısı - varsayılan olarak gizli
        self.ilk_olcum_uyari = QLabel(
            "İlk ölçümler sadece doktorunuz tarafından yapılabilir. "
            "Lütfen doktorunuzla iletişime geçin."
        )
        self.ilk_olcum_uyari.setStyleSheet("color: red; font-weight: bold;")
        self.ilk_olcum_uyari.setWordWrap(True)
        self.ilk_olcum_uyari.setVisible(False)
        yeni_olcum_layout.addRow(self.ilk_olcum_uyari)

        # Ölçüm zamanı seçimi
        self.olcum_zamani_combo = QComboBox()
        for zaman in OLCUM_ZAMANLARI.keys():
            self.olcum_zamani_combo.addItem(zaman)
        
        # Tarih ve saat seçimi - 24 saat ve gün.ay.yıl formatı
        self.olcum_tarihi = QDateEdit()
        self.olcum_tarihi.setDate(QDate.currentDate())
        self.olcum_tarihi.setDisplayFormat("dd.MM.yyyy")  # Gün.Ay.Yıl formatı
        self.olcum_tarihi.setCalendarPopup(True)
        
        self.olcum_saati = QTimeEdit()
        self.olcum_saati.setTime(QTime.currentTime())
        self.olcum_saati.setDisplayFormat("HH:mm")  # 24-saat formatı
        
        # Ölçüm değeri girişi
        self.seker_deger = QLineEdit()
        self.seker_deger.setPlaceholderText("mg/dL")
        
        # Update validator to only allow positive values with maximum 3 digits
        # Parameters: (bottom, top, decimals)
        validator = QDoubleValidator(0, 999, 1)
        validator.setNotation(QDoubleValidator.StandardNotation)
        self.seker_deger.setValidator(validator)
        
        # Add input mask to restrict length (optional, can be used with validator)
        self.seker_deger.setMaxLength(5)  # Allow for 3 digits + decimal point + 1 decimal place
        
        # Connect textChanged signal to filter invalid input
        self.seker_deger.textChanged.connect(self.filter_seker_input)
        
        # Form alanlarını ekle
        yeni_olcum_layout.addRow("Ölçüm Zamanı:", self.olcum_zamani_combo)
        yeni_olcum_layout.addRow("Tarih:", self.olcum_tarihi)
        yeni_olcum_layout.addRow("Saat:", self.olcum_saati)
        yeni_olcum_layout.addRow("Kan Şekeri Değeri:", self.seker_deger)
        
        # Ölçüm bilgi alanı
        self.olcum_bilgi = QLabel("")
        self.olcum_bilgi.setWordWrap(True)
        self.olcum_bilgi.setStyleSheet("color: #FF5722;")
        yeni_olcum_layout.addRow(self.olcum_bilgi)
        
        # Kaydet butonu
        seker_kaydet = QPushButton("Ölçümü Kaydet")
        seker_kaydet.clicked.connect(self.seker_kaydet)
        yeni_olcum_layout.addRow(seker_kaydet)
        
        # Graph tab - New Addition
        graph_tab = QWidget()
        graph_layout = QVBoxLayout(graph_tab)
        
        # Date selector for graph
        graph_date_layout = QHBoxLayout()
        graph_date_label = QLabel("Tarih:")
        self.graph_date = QDateEdit()
        self.graph_date.setDate(QDate.currentDate())
        self.graph_date.setDisplayFormat("dd.MM.yyyy")
        self.graph_date.setCalendarPopup(True)
        self.graph_date.dateChanged.connect(self.update_blood_sugar_graph)
        
        graph_date_layout.addWidget(graph_date_label)
        graph_date_layout.addWidget(self.graph_date)
        
        graph_refresh_btn = QPushButton("Grafiği Güncelle")
        graph_refresh_btn.clicked.connect(self.update_blood_sugar_graph)
        graph_date_layout.addWidget(graph_refresh_btn)
        
        graph_layout.addLayout(graph_date_layout)
        
        # Graph container - make it fill available space
        self.graph_container = QVBoxLayout()
        
        # Create a widget to contain the graph
        graph_widget = QWidget()
        graph_widget.setLayout(self.graph_container)
        
        # Set size policy to make the container expand
        from PyQt5.QtWidgets import QSizePolicy
        graph_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        graph_layout.addWidget(graph_widget, 1)  # Use stretch factor of 1
        
        # Weekly graph tab with similar enhancements
        weekly_tab = QWidget()
        weekly_layout = QVBoxLayout(weekly_tab)
        
        # Date range for weekly graph - ADD START DATE
        weekly_date_layout = QHBoxLayout()
        
        # Start date picker
        weekly_start_label = QLabel("Başlangıç Tarihi:")
        self.weekly_start_picker = QDateEdit()
        self.weekly_start_picker.setDate(QDate.currentDate().addDays(-6))  # Default to 6 days before end date
        self.weekly_start_picker.setDisplayFormat("dd.MM.yyyy")
        self.weekly_start_picker.setCalendarPopup(True)
        
        # End date picker
        weekly_end_label = QLabel("Bitiş Tarihi:")
        self.weekly_date = QDateEdit()
        self.weekly_date.setDate(QDate.currentDate())
        self.weekly_date.setDisplayFormat("dd.MM.yyyy")
        self.weekly_date.setCalendarPopup(True)
        self.weekly_date.dateChanged.connect(self.update_weekly_graph)
        
        weekly_refresh_btn = QPushButton("Grafiği Güncelle")
        weekly_refresh_btn.clicked.connect(self.update_weekly_graph)
        
        weekly_date_layout.addWidget(weekly_start_label)
        weekly_date_layout.addWidget(self.weekly_start_picker)
        weekly_date_layout.addWidget(weekly_end_label)
        weekly_date_layout.addWidget(self.weekly_date)
        weekly_date_layout.addWidget(weekly_refresh_btn)
        
        weekly_layout.addLayout(weekly_date_layout)
        
        # Weekly graph container - make it fill available space
        self.weekly_graph_container = QVBoxLayout()
        
        # Create a widget to contain the weekly graph
        weekly_graph_widget = QWidget()
        weekly_graph_widget.setLayout(self.weekly_graph_container)
        
        # Set size policy to make the container expand
        weekly_graph_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        weekly_layout.addWidget(weekly_graph_widget, 1)  # Use stretch factor of 1
        
        # Add tabs to tab widget
        sol_tab.addTab(form_tab, "Yeni Ölçüm")
        sol_tab.addTab(graph_tab, "Günlük Grafik")
        sol_tab.addTab(weekly_tab, "Haftalık Grafik")
        
        sol_layout.addWidget(sol_tab)
        
        # Sağ panel - Günlük özet
        sag_panel = QWidget()
        sag_layout = QVBoxLayout(sag_panel)
        
        # Tablo (Günün ölçümleri)
        self.olcum_tablosu = QTableWidget()
        self.olcum_tablosu.setColumnCount(5)
        self.olcum_tablosu.setHorizontalHeaderLabels(["Zaman", "Saat", "Değer (mg/dL)", "Seviye", "Dahil"])
        self.olcum_tablosu.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        
        # Özet bilgi alanı
        self.ozet_bilgi = QLabel("Bugünkü ölçüm bilgileri burada gösterilecek.")
        self.ozet_bilgi.setWordWrap(True)
        
        # İnsülin önerisi alanı
        self.insulin_onerisi = QLabel("")
        self.insulin_onerisi.setStyleSheet("font-size: 14px; font-weight: bold; color: #2196F3;")
        self.insulin_onerisi.setAlignment(Qt.AlignCenter)
        
        sag_layout.addWidget(self.olcum_tablosu)
        sag_layout.addWidget(self.ozet_bilgi)
        sag_layout.addWidget(self.insulin_onerisi)
        
        # Günlük ölçümleri yenile buton
        gunluk_yenile = QPushButton("Günlük Ölçümleri Güncelle")
        gunluk_yenile.clicked.connect(self.gunluk_olcumleri_yenile)
        sag_layout.addWidget(gunluk_yenile)
        
        # Sol ve sağ panelleri ekle
        seker_alt_layout.addWidget(sol_panel, 3)  # Larger proportion
        seker_alt_layout.addWidget(sag_panel, 2)  # Smaller proportion
        
        seker_layout.addLayout(seker_alt_layout)
        
        # Diyet sayfası - Replace this section
        self.diyet_sayfasi = QWidget()
        diyet_layout = QVBoxLayout(self.diyet_sayfasi)
        
        # We'll replace this content with the HastaDiyetEgzersizWidget in the diyet_takibi method
        # This ensures the widget is only created when the user actually navigates to the page
        
        # ...existing code...
        
        # Raporlar sayfası
        self.raporlar_sayfasi = QWidget()
        self.raporlar_layout = QVBoxLayout(self.raporlar_sayfasi)
        self.olustur_raporlar_sayfasi()
        
        # Sayfaları ekle
        self.sayfa_alani.addWidget(self.profil_sayfasi)
        self.sayfa_alani.addWidget(self.insulin_sayfasi)
        self.sayfa_alani.addWidget(self.seker_sayfasi)
        self.sayfa_alani.addWidget(self.diyet_sayfasi)
        self.sayfa_alani.addWidget(self.raporlar_sayfasi)
        
        ana_layout.addWidget(self.sayfa_alani)
        
        self.setCentralWidget(merkez_widget)
        
        # Başlangıçta profil sayfasını göster
        self.sayfa_alani.setCurrentIndex(0)
    
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
            basarili, mesaj = MainModule.profil_foto_guncelle(self.hasta['tc_kimlik_no'], foto_data, "hasta")
            
            if not basarili:
                QMessageBox.warning(self, "Hata", mesaj)
        except Exception as e:
            QMessageBox.warning(self, "Hata", f"Profil fotoğrafı yüklenirken bir hata oluştu: {e}")
    
    def profil_foto_goster(self):
        try:
            # Veritabanından profil fotoğrafını getir
            basarili, sonuc = MainModule.profil_foto_getir(self.hasta['tc_kimlik_no'], "hasta")
            
            if basarili:
                # Byte array'i QPixmap'e dönüştür
                pixmap = QPixmap()
                pixmap.loadFromData(sonuc)
                pixmap = pixmap.scaled(200, 200, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self.profil_foto_label.setPixmap(pixmap)
        except Exception:
            # Sessizce başarısız ol, hiç bir şey yazdırma
            pass
    
    def profil_goster(self):
        # Set the stacked widget to show the profile page (index 0)
        self.sayfa_alani.setCurrentIndex(0)
    
    def insulin_takibi(self):
        self.sayfa_alani.setCurrentIndex(1)
        # İnsülin bilgilerini güncelle
        self.insulin_bilgilerini_yukle()
    
    def kan_sekeri_olcumu(self):
        # Önce ilk ölçüm kontrolü yap
        ilk_olcum_durumu = MainModule.hasta_ilk_olcum_kontrolu(self.hasta['tc_kimlik_no'])
        
        # Eğer ilk ölçüm değilse, normal şekilde sayfaya geçiş yap
        if ilk_olcum_durumu:
            # İlk ölçüm değil, formu etkinleştir
            self.ilk_olcum_uyari.setVisible(False)
            self.olcum_zamani_combo.setEnabled(True)
            self.olcum_tarihi.setEnabled(True)
            self.olcum_saati.setEnabled(True)
            self.seker_deger.setEnabled(True)
        else:
            # İlk ölçüm, form alanlarını devre dışı bırak ve uyarıyı göster
            self.ilk_olcum_uyari.setVisible(True)
            self.olcum_zamani_combo.setEnabled(False)
            self.olcum_tarihi.setEnabled(False)
            self.olcum_saati.setEnabled(False)
            self.seker_deger.setEnabled(False)

        # Kan şekeri sayfasını göster
        self.sayfa_alani.setCurrentIndex(2)
        
        # Mevcut ölçümleri yenile
        self.gunluk_olcumleri_yenile()
        
        # Also update the graph
        self.update_blood_sugar_graph()
        self.update_weekly_graph()

    def diyet_takibi(self):
        # Switch to the diet tab
        self.sayfa_alani.setCurrentIndex(3)  # Make sure this index matches your layout
    
        # If the diet widget hasn't been initialized yet, create it
        if not hasattr(self, 'diyet_widget') or not self.diyet_widget:
            # Clear any existing content in the diet page
            for i in reversed(range(self.diyet_sayfasi.layout().count())):
                item = self.diyet_sayfasi.layout().itemAt(i)
                if item.widget():
                    item.widget().deleteLater()
            
            # Create the diet and exercise widget
            self.diyet_widget = HastaDiyetEgzersizWidget(self.hasta['tc_kimlik_no'], self.hasta['isim_soyisim'])
            self.diyet_sayfasi.layout().addWidget(self.diyet_widget)
        
        # Refresh the diet widget data
        if hasattr(self, 'diyet_widget') and self.diyet_widget:
            self.diyet_widget.plan_yukle()
            self.diyet_widget.gecmis_yukle()
    
    def insulin_kaydet(self):
        # Şu anlık sadece bir mesaj gösterelim
        QMessageBox.information(self, "Bilgi", "İnsülin kaydı ekleme fonksiyonu.")
        # İlerde veritabanı kaydı eklenecek
    
    def seker_kaydet(self):
        try:
            # Form verilerini al
            olcum_zamani = self.olcum_zamani_combo.currentText()
            olcum_tarihi = self.olcum_tarihi.date().toPyDate()
            olcum_saati = self.olcum_saati.time().toPyTime()
            seker_degeri_text = self.seker_deger.text().replace(',', '.')  # Virgül girişini nokta ile değiştir
            
            # Boş değer kontrolü
            if not seker_degeri_text:
                QMessageBox.warning(self, "Hata", "Lütfen kan şekeri değerini giriniz.")
                return
            
            # Kan şekeri değerini float olarak dönüştür
            seker_degeri = float(seker_degeri_text)
            
            # Zaman aralığı kontrolü
            zaman_uygun = zaman_kontrolu(olcum_zamani, olcum_saati)
            seviye_durumu = seviye_belirle(seker_degeri)
            
            # Veritabanı bağlantısı
            conn = mysql.connector.connect(
                host=DB_HOST,
                user=DB_USER,
                password=DB_PASSWORD,
                database=DB_NAME,
                charset=DB_CHARSET
            )
            cursor = conn.cursor()
            
            # Hastanın doktor bilgisini getir
            doktor_tc = ""
            try:
                cursor.execute("SELECT doktor_tc FROM Hastalar WHERE tc_kimlik_no = %s", (self.hasta['tc_kimlik_no'],))
                doktor_sonuc = cursor.fetchone()
                if doktor_sonuc and doktor_sonuc[0]:
                    doktor_tc = doktor_sonuc[0]
            except Exception as e:
                print(f"Doktor bilgisi alınamadı: {e}")
            
            # Aynı gün ve aynı zaman dilimi için önceki ölçüm kontrolü
            cursor.execute("""
                SELECT COUNT(*) FROM KanSekeriKayitlari 
                WHERE tc_kimlik_no = %s AND tarih = %s AND olcum_zamani = %s
            """, (self.hasta['tc_kimlik_no'], olcum_tarihi, olcum_zamani))
            
            existing_count = cursor.fetchone()[0]
            
            if existing_count > 0:
                # Önceki ölçümü güncelle
                cursor.execute("""
                    UPDATE KanSekeriKayitlari SET
                    saat = %s,
                    seker_seviyesi = %s,
                    zaman_uygun = %s,
                    seviye_durumu = %s,
                    ortalamaya_dahil = %s,
                    doktor_tc = %s
                    WHERE tc_kimlik_no = %s AND tarih = %s AND olcum_zamani = %s
                """, (olcum_saati, seker_degeri, zaman_uygun, seviye_durumu, zaman_uygun, 
                      doktor_tc, self.hasta['tc_kimlik_no'], olcum_tarihi, olcum_zamani))
            else:
                # Yeni ölçüm ekle
                cursor.execute("""
                    INSERT INTO KanSekeriKayitlari 
                    (tc_kimlik_no, tarih, saat, olcum_zamani, seker_seviyesi, zaman_uygun, 
                    seviye_durumu, ortalamaya_dahil, doktor_tc) 
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (self.hasta['tc_kimlik_no'], olcum_tarihi, olcum_saati, olcum_zamani, 
                      seker_degeri, zaman_uygun, seviye_durumu, zaman_uygun, doktor_tc))
        
            # Günlük ölçümleri getir
            olcumler = gunluk_olcumleri_getir(self.hasta['tc_kimlik_no'], olcum_tarihi, conn)
            
            # Ortalama hesapla
            ortalama, olcum_sayisi, eksik_olcumler, uyarilar = ortalama_hesapla(olcumler)
            
            # İnsülin önerisi hesapla
            insulin_onerisi = insulin_onerisi_hesapla(ortalama)
            
            # Kritik değerler için uyarı oluştur
            kontrol_ve_uyari_olustur(
                self.hasta['tc_kimlik_no'], 
                seker_degeri,
                doktor_tc, 
                conn
            )
            
            # Her zaman günlük ölçümleri kontrol et (yetersiz ölçüm uyarısı için)
            kontrol_gunluk_olcumler(self.hasta['tc_kimlik_no'], olcum_tarihi, conn)
            
            conn.commit()
            
            # Kullanıcıya bilgi mesajı göster
            bilgi_mesaji = f"Kan şekeri ölçümü kaydedildi: {seker_degeri} mg/dL ({seviye_durumu})"
            
            if not zaman_uygun:
                bilgi_mesaji += "\nDikkat: Ölçüm zamanı uygun değil! Bu ölçüm ortalamaya dahil edilmeyecek."
            
            QMessageBox.information(self, "Başarılı", bilgi_mesaji)
            
            # Tabloyu güncelle
            self.gunluk_olcumleri_yenile()
            
            # Form alanlarını temizle
            self.seker_deger.clear()
            
        except ValueError:
            QMessageBox.warning(self, "Hata", "Lütfen geçerli bir kan şekeri değeri giriniz.")
        except Exception as e:
            QMessageBox.warning(self, "Hata", f"Ölçüm kaydedilirken bir hata oluştu: {str(e)}")
        finally:
            if 'conn' in locals() and conn:
                if 'cursor' in locals() and cursor:
                    cursor.close()
                conn.close()

    def update_blood_sugar_graph(self):
        """Update the blood sugar graph for the selected date"""
        try:
            selected_date = self.graph_date.date().toPyDate()
            
            # Create the graph
            fig = create_blood_sugar_graph(self.hasta['tc_kimlik_no'], selected_date)
            
            # Display the graph
            embed_matplotlib_figure(self.graph_container, fig)
        except Exception as e:
            QMessageBox.warning(self, "Hata", f"Günlük grafik güncellenirken bir hata oluştu: {str(e)}")

    def update_weekly_graph(self):
        """Update the weekly blood sugar graph"""
        try:
            end_date = self.weekly_date.date().toPyDate()
            start_date = self.weekly_start_picker.date().toPyDate()  # Get start date
            
            # Create the graph
            fig = create_weekly_graph(self.hasta['tc_kimlik_no'], end_date, start_date=start_date)
            
            # Display the graph
            embed_matplotlib_figure(self.weekly_graph_container, fig)
        except Exception as e:
            QMessageBox.warning(self, "Hata", f"Haftalık grafik güncellenirken bir hata oluştu: {str(e)}")
    
    def gunluk_olcumleri_yenile(self):
        try:
            secili_tarih = self.olcum_tarihi.date().toPyDate()
            
            # Veritabanı bağlantısı
            conn = mysql.connector.connect(
                host=DB_HOST,
                user=DB_USER,
                password=DB_PASSWORD,
                database=DB_NAME,
                charset=DB_CHARSET
            )
            
            # Günlük ölçümleri getir - parametrede fazladan boşluk olmadan
            olcumler = gunluk_olcumleri_getir(self.hasta['tc_kimlik_no'], secili_tarih, conn)
            
            # Tabloyu temizle
            self.olcum_tablosu.setRowCount(0)
            
            # Tabloyu doldur
            for i, (zaman, olcum) in enumerate(olcumler.items()):
                self.olcum_tablosu.insertRow(i)
                
                # Zaman adı
                self.olcum_tablosu.setItem(i, 0, QTableWidgetItem(zaman))
                
                if olcum:
                    # Saat - 24 saat formatında göster
                    from ui_utils import saat_goruntu_formatla
                    saat_str = saat_goruntu_formatla(olcum['saat'])
                    self.olcum_tablosu.setItem(i, 1, QTableWidgetItem(saat_str))
                    
                    # Değer
                    self.olcum_tablosu.setItem(i, 2, QTableWidgetItem(str(olcum['seker_seviyesi'])))
                    
                    # Seviye
                    seviye_item = QTableWidgetItem(olcum['seviye_durumu'])
                    if olcum['seviye_durumu'] == 'Dusuk':
                        seviye_item.setForeground(Qt.blue)
                    elif olcum['seviye_durumu'] == 'Normal':
                        seviye_item.setForeground(Qt.darkGreen)
                    elif olcum['seviye_durumu'] == 'Orta':
                        seviye_item.setForeground(Qt.darkYellow)
                    elif olcum['seviye_durumu'] == 'Yuksek':
                        seviye_item.setForeground(Qt.red)
                    elif olcum['seviye_durumu'] == 'CokYuksek':
                        seviye_item.setForeground(Qt.darkRed)
                    self.olcum_tablosu.setItem(i, 3, seviye_item)
                    
                    # Ortalamaya dahil mi?
                    dahil_text = "✓" if olcum['ortalamaya_dahil'] else "✗"
                    dahil_item = QTableWidgetItem(dahil_text)
                    dahil_item.setTextAlignment(Qt.AlignCenter)
                    self.olcum_tablosu.setItem(i, 4, QTableWidgetItem(dahil_item))
                else:
                    # Boş ölçüm
                    self.olcum_tablosu.setItem(i, 1, QTableWidgetItem("-"))
                    self.olcum_tablosu.setItem(i, 2, QTableWidgetItem("-"))
                    self.olcum_tablosu.setItem(i, 3, QTableWidgetItem("-"))
                    self.olcum_tablosu.setItem(i, 4, QTableWidgetItem("-"))
        
            # Ortalama hesapla
            ortalama, olcum_sayisi, eksik_olcumler, uyarilar = ortalama_hesapla(olcumler)
            
            # İnsülin önerisi hesapla
            insulin_onerisi = insulin_onerisi_hesapla(ortalama)
            
            # Özet bilgiyi güncelle
            if ortalama > 0:
                ozet_text = f"Ortalama Kan Şekeri: {ortalama:.1f} mg/dL ({olcum_sayisi}/5 ölçüm)"
                if uyarilar:
                    ozet_text += "\n" + "\n".join(uyarilar)
                self.ozet_bilgi.setText(ozet_text)
                
                # İnsülin önerisi göster
                if insulin_onerisi == 0:
                    if ortalama < 70:
                        oneri_text = "İnsülin Önerisi: İnsülin Kullanımı Önerilmez (Hipoglisemi Riski)"
                        self.insulin_onerisi.setStyleSheet("font-size: 14px; font-weight: bold; color: blue;")
                    else:
                        oneri_text = "İnsülin Önerisi: İnsülin Kullanımı Gerekmiyor"
                        self.insulin_onerisi.setStyleSheet("font-size: 14px; font-weight: bold; color: green;")
                else:
                    oneri_text = f"İnsülin Önerisi: {insulin_onerisi} ml İnsülin"
                    self.insulin_onerisi.setStyleSheet("font-size: 14px; font-weight: bold; color: #FF5722;")
                
                self.insulin_onerisi.setText(oneri_text)
            else:
                self.ozet_bilgi.setText("Bugün için kayıtlı ölçüm bulunmamaktadır.")
                self.insulin_onerisi.setText("")
            
            # Günün tamamında eksik ölçüm kontrolü (Gün sonu yaklaşırken)
            if secili_tarih == date.today():
                now = datetime.now().time()
                if now >= time(23, 0):  # 23:00 sonrası kontrol
                    kontrol_gunluk_olcumler(self.hasta['tc_kimlik_no'], secili_tarih, conn)
            # Geçmiş tarihler için her zaman kontrol et
            elif secili_tarih < date.today():
                kontrol_gunluk_olcumler(self.hasta['tc_kimlik_no'], secili_tarih, conn)
            
            conn.close()
            
        except Exception as e:
            QMessageBox.warning(self, "Hata", f"Ölçümler listelenirken bir hata oluştu: {str(e)}")
    
    def seker_raporlarini_goster(self):
        """Kan şekeri raporlarını kapsamlı şekilde görüntüler"""
        try:
            # Use simplified graph dialog instead of full report dialog
            from PyQt5.QtWidgets import QDialog, QVBoxLayout, QPushButton, QHBoxLayout, QLabel, QDateEdit, QTabWidget
            from PyQt5.QtCore import QDate
            from graph_utils import create_weekly_graph, create_blood_sugar_graph, embed_matplotlib_figure
            
            # Create simple dialog for graph
            dialog = QDialog(self)
            dialog.setWindowTitle(f"Kan Şekeri Grafiği - {self.hasta['isim_soyisim']}")
            dialog.resize(900, 700)
            
            layout = QVBoxLayout(dialog)
            
            # Create tab widget for different graph views
            tab_widget = QTabWidget()
            
            # --- Daily Graph Tab ---
            daily_tab = QWidget()
            daily_layout = QVBoxLayout(daily_tab)
            
            # Date selector for daily graph
            daily_date_layout = QHBoxLayout()
            daily_date_label = QLabel("Tarih:")
            daily_date_picker = QDateEdit()
            daily_date_picker.setDate(QDate.currentDate())
            daily_date_picker.setDisplayFormat("dd.MM.yyyy")
            daily_date_picker.setCalendarPopup(True)
            
            daily_refresh_btn = QPushButton("Grafiği Güncelle")
            
            daily_date_layout.addWidget(daily_date_label)
            daily_date_layout.addWidget(daily_date_picker)
            daily_date_layout.addWidget(daily_refresh_btn)
            
            daily_layout.addLayout(daily_date_layout)
            
            # Daily graph container
            daily_graph_container = QVBoxLayout()
            daily_layout.addLayout(daily_graph_container)
            
            # --- Weekly Graph Tab ---
            weekly_tab = QWidget()
            weekly_layout = QVBoxLayout(weekly_tab)
            
            # Date range for weekly graph - ADD START DATE
            weekly_date_layout = QHBoxLayout()
            
            # Start date picker
            weekly_start_label = QLabel("Başlangıç Tarihi:")
            weekly_start_picker = QDateEdit()
            weekly_start_picker.setDate(QDate.currentDate().addDays(-6))  # Default to 6 days before end date
            weekly_start_picker.setDisplayFormat("dd.MM.yyyy")
            weekly_start_picker.setCalendarPopup(True)
            
            # End date picker
            weekly_end_label = QLabel("Bitiş Tarihi:")
            weekly_end_picker = QDateEdit()
            weekly_end_picker.setDate(QDate.currentDate())
            weekly_end_picker.setDisplayFormat("dd.MM.yyyy")
            weekly_end_picker.setCalendarPopup(True)
            
            weekly_refresh_btn = QPushButton("Grafiği Güncelle")
            
            weekly_date_layout.addWidget(weekly_start_label)
            weekly_date_layout.addWidget(weekly_start_picker)
            weekly_date_layout.addWidget(weekly_end_label)
            weekly_date_layout.addWidget(weekly_end_picker)
            weekly_date_layout.addWidget(weekly_refresh_btn)
            
            weekly_layout.addLayout(weekly_date_layout)
            
            # Weekly graph container - FIX: Use local variable without self prefix
            weekly_graph_container = QVBoxLayout()
            weekly_layout.addLayout(weekly_graph_container)
            
            # Add tabs to tab widget
            tab_widget.addTab(daily_tab, "Günlük Grafik")
            tab_widget.addTab(weekly_tab, "Tarih Aralığı Grafiği")
            
            # Add tab widget to main layout
            layout.addWidget(tab_widget)
            
            # Close button
            close_btn = QPushButton("Kapat")
            close_btn.clicked.connect(dialog.accept)
            layout.addWidget(close_btn)
            
            # Function to update daily graph
            def update_daily_graph():
                selected_date = daily_date_picker.date().toPyDate()
                fig = create_blood_sugar_graph(self.hasta['tc_kimlik_no'], selected_date)
                embed_matplotlib_figure(daily_graph_container, fig)
            
            # Function to update weekly graph with custom date range
            def update_weekly_graph():
                start_date = weekly_start_picker.date().toPyDate()
                end_date = weekly_end_picker.date().toPyDate()
                
                # Validate dates
                if start_date > end_date:
                    from PyQt5.QtWidgets import QMessageBox
                    QMessageBox.warning(dialog, "Uyarı", "Başlangıç tarihi bitiş tarihinden sonra olamaz!")
                    # Swap the dates
                    weekly_start_picker.setDate(weekly_end_picker.date().addDays(-6))
                    return
                
                # Pass both start and end dates to the graph function
                fig = create_weekly_graph(self.hasta['tc_kimlik_no'], end_date, start_date=start_date)
                # FIX: Use local variable without self prefix
                embed_matplotlib_figure(weekly_graph_container, fig)
            
            # Connect signals for daily graph
            daily_refresh_btn.clicked.connect(update_daily_graph)
            daily_date_picker.dateChanged.connect(update_daily_graph)
            
            # Connect signals for weekly graph
            weekly_refresh_btn.clicked.connect(update_weekly_graph)
            weekly_start_picker.dateChanged.connect(update_weekly_graph)
            weekly_end_picker.dateChanged.connect(update_weekly_graph)
            
            # Connect tab change signal
            def on_tab_changed(index):
                if index == 0:  # Daily graph tab
                    update_daily_graph()
                elif index == 1:  # Weekly graph tab
                    update_weekly_graph()
            
            tab_widget.currentChanged.connect(on_tab_changed)
            
            # Initial graph update based on active tab
            if tab_widget.currentIndex() == 0:
                update_daily_graph()
            else:
                update_weekly_graph()
            
            # Show dialog
            dialog.exec_()
            
        except Exception as e:
            QMessageBox.warning(self, "Hata", f"Kan şekeri grafiği yüklenirken hata oluştu: {str(e)}")
    
    def olustur_raporlar_sayfasi(self):
        """Create the reports page UI"""
        # Clear the layout first
        for i in reversed(range(self.raporlar_layout.count())): 
            self.raporlar_layout.itemAt(i).widget().setParent(None)
        
        # Başlık
        baslik = QLabel("Kan Şekeri Raporları")
        baslik.setFont(QFont("Arial", 14, QFont.Bold))
        baslik.setAlignment(Qt.AlignCenter)
        self.raporlar_layout.addWidget(baslik)
        
        # Add buttons for different report types
        rapor_butonlar_layout = QHBoxLayout()
        
        tablo_rapor_btn = QPushButton("Tablo Raporları")
        tablo_rapor_btn.clicked.connect(self.rapor_yukle)
        
        grafik_rapor_btn = QPushButton("Detaylı Grafik Raporları")
        grafik_rapor_btn.clicked.connect(self.seker_raporlarini_goster)
        grafik_rapor_btn.setStyleSheet("background-color: #2196F3; color: white; font-weight: bold;")
        
        rapor_butonlar_layout.addWidget(tablo_rapor_btn)
        rapor_butonlar_layout.addWidget(grafik_rapor_btn)
        
        self.raporlar_layout.addLayout(rapor_butonlar_layout)
        
        # Tarih aralığı seçici
        tarih_layout = QHBoxLayout()
        
        baslangic_label = QLabel("Başlangıç:")
        self.rapor_baslangic = QDateEdit()
        self.rapor_baslangic.setDate(QDate.currentDate().addDays(-30))
        self.rapor_baslangic.setDisplayFormat("dd.MM.yyyy")
        self.rapor_baslangic.setCalendarPopup(True)
        
        bitis_label = QLabel("Bitiş:")
        self.rapor_bitis = QDateEdit()
        self.rapor_bitis.setDate(QDate.currentDate())
        self.rapor_bitis.setDisplayFormat("dd.MM.yyyy")
        self.rapor_bitis.setCalendarPopup(True)
        
        rapor_goster_btn = QPushButton("Raporu Göster")
        rapor_goster_btn.clicked.connect(self.rapor_yukle)
        
        tarih_layout.addWidget(baslangic_label)
        tarih_layout.addWidget(self.rapor_baslangic)
        tarih_layout.addWidget(bitis_label)
        tarih_layout.addWidget(self.rapor_bitis)
        tarih_layout.addWidget(rapor_goster_btn)
        
        self.raporlar_layout.addLayout(tarih_layout)
        
        # Kan şekeri tablosu
        kan_sekeri_grup = QGroupBox("Kan Şekeri Ölçüm Geçmişi")
        kan_sekeri_layout = QVBoxLayout()
        
        self.kan_sekeri_tablosu = QTableWidget()
        self.kan_sekeri_tablosu.setColumnCount(5)
        self.kan_sekeri_tablosu.setHorizontalHeaderLabels(["Tarih", "Zaman", "Saat", "Değer", "Durum"])
        self.kan_sekeri_tablosu.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        
        kan_sekeri_layout.addWidget(self.kan_sekeri_tablosu)
        kan_sekeri_grup.setLayout(kan_sekeri_layout)
        self.raporlar_layout.addWidget(kan_sekeri_grup)

        # Initial load
        self.rapor_yukle()

    def rapor_yukle(self):
        """Load reports for the selected date range"""
        try:
            baslangic_tarih = self.rapor_baslangic.date().toPyDate()
            bitis_tarih = self.rapor_bitis.date().toPyDate()
            
            # Veritabanı bağlantısı
            conn = mysql.connector.connect(
                host=DB_HOST,
                user=DB_USER,
                password=DB_PASSWORD,
                database=DB_NAME,
                charset=DB_CHARSET
            )
            cursor = conn.cursor(dictionary=True)
            
            # Get blood sugar measurements
            cursor.execute("""
            SELECT * FROM KanSekeriKayitlari
            WHERE tc_kimlik_no = %s AND tarih BETWEEN %s AND %s
            ORDER BY tarih DESC, saat DESC
            """, (self.hasta['tc_kimlik_no'], baslangic_tarih, bitis_tarih))
            
            measurements = cursor.fetchall()
            
            # Fill blood sugar table
            self.kan_sekeri_tablosu.setRowCount(0)
            for i, measurement in enumerate(measurements):
                self.kan_sekeri_tablosu.insertRow(i)
                
                # Format date as day.month.year
                tarih_str = measurement['tarih'].strftime("%d.%m.%Y")
                
                self.kan_sekeri_tablosu.setItem(i, 0, QTableWidgetItem(tarih_str))
                self.kan_sekeri_tablosu.setItem(i, 1, QTableWidgetItem(measurement['olcum_zamani']))
                
                # Format time as 24-hour
                from ui_utils import saat_goruntu_formatla
                saat_str = saat_goruntu_formatla(measurement['saat'])
                self.kan_sekeri_tablosu.setItem(i, 2, QTableWidgetItem(saat_str))
                
                self.kan_sekeri_tablosu.setItem(i, 3, QTableWidgetItem(str(measurement['seker_seviyesi'])))
                
                durum_item = QTableWidgetItem(measurement['seviye_durumu'])
                if measurement['seviye_durumu'] == 'Dusuk':
                    durum_item.setForeground(Qt.blue)
                elif measurement['seviye_durumu'] == 'Normal':
                    durum_item.setForeground(Qt.darkGreen)
                elif measurement['seviye_durumu'] == 'Orta':
                    durum_item.setForeground(Qt.darkYellow)
                elif measurement['seviye_durumu'] == 'Yuksek':
                    durum_item.setForeground(Qt.red)
                elif measurement['seviye_durumu'] == 'CokYuksek':
                    durum_item.setForeground(Qt.darkRed)
                
                self.kan_sekeri_tablosu.setItem(i, 4, durum_item)
            
            conn.close()
            
        except Exception as e:
            QMessageBox.warning(self, "Hata", f"Rapor yüklenirken bir hata oluştu: {str(e)}")

    def raporlari_goster(self):
        # Show reports page
        self.sayfa_alani.setCurrentIndex(4) # Update index according to your page order
        self.rapor_yukle()
    
    def insulin_bilgilerini_yukle(self):
        """İnsülin kayıtlarını yükler ve tabloyu günceller"""
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
            
            # Son 30 günlük insülin kayıtlarını getir (en yeni en üstte)
            cursor.execute("""
                SELECT * FROM InsulinKayitlari 
                WHERE hasta_tc = %s 
                ORDER BY tarih DESC 
                LIMIT 30
                """, (self.hasta['tc_kimlik_no'],))
            
            kayitlar = cursor.fetchall()
            
            # Tabloyu temizle
            self.insulin_tablosu.setRowCount(0)
            
            # Bugünün tarihi
            bugun = datetime.now().date()
            bugun_kaydi = None
            
            # Tabloyu doldur
            for i, kayit in enumerate(kayitlar):
                self.insulin_tablosu.insertRow(i)
                
                # Tarih ve saat bilgisini göster
                tarih_str = kayit['tarih'].strftime("%d.%m.%Y")
                time_str = ""
                
                # Use the safe formatter for time display
                if kayit['kullanildi'] and kayit['saat'] is not None:
                    time_str = f" ({format_time_safely(kayit['saat'])})"
                
                self.insulin_tablosu.setItem(i, 0, QTableWidgetItem(f"{tarih_str}{time_str}"))
                
                # Doz
                self.insulin_tablosu.setItem(i, 1, QTableWidgetItem(f"{kayit['doz']} mL"))
                
                # Durum
                if kayit['kullanildi'] is None:
                    durum = "Belirtilmemiş"
                    durum_renk = Qt.black
                elif kayit['kullanildi']:
                    durum = "Kullanıldı"
                    durum_renk = Qt.darkGreen
                    # Use the safe formatter for time display
                    if kayit['saat'] is not None:
                        durum = f"Kullanıldı ({format_time_safely(kayit['saat'])})"
                else:
                    durum = "Kullanılmadı"
                    durum_renk = Qt.red
                
                durum_item = QTableWidgetItem(durum)
                durum_item.setForeground(durum_renk)
                self.insulin_tablosu.setItem(i, 2, durum_item)
                
                # İşlemler - Sadece bugünün kaydı için butonlar göster
                if kayit['tarih'] == bugun:
                    bugun_kaydi = kayit
                    buton_widget = QWidget()
                    buton_layout = QHBoxLayout(buton_widget)
                    buton_layout.setContentsMargins(2, 2, 2, 2)
                    
                    kullandim_btn = QPushButton("Kullandım")
                    kullanmadim_btn = QPushButton("Kullanmadım")
                    
                    kullandim_btn.setStyleSheet("background-color: #4CAF50; color: white; font-size: 10px;")
                    kullanmadim_btn.setStyleSheet("background-color: #F44336; color: white; font-size: 10px;")
                    
                    # Lambda ile kayıt ID'sini bağla
                    kullandim_btn.clicked.connect(lambda _, id=kayit['id']: self.insulin_durumu_guncelle(id, True))
                    kullanmadim_btn.clicked.connect(lambda _, id=kayit['id']: self.insulin_durumu_guncelle(id, False))
                    
                    buton_layout.addWidget(kullandim_btn)
                    buton_layout.addWidget(kullanmadim_btn)
                    
                    self.insulin_tablosu.setCellWidget(i, 3, buton_widget)
                else:
                    # Eski kayıtlar için boş hücre
                    self.insulin_tablosu.setItem(i, 3, QTableWidgetItem("-"))
        
            # Günlük insülin bilgisini güncelle
            if bugun_kaydi:
                if bugun_kaydi['kullanildi'] is None:
                    self.gunluk_insulin_bilgi.setText(f"Bugün için önerilen insülin dozu: {bugun_kaydi['doz']} mL\nHenüz kullanım durumunu belirtmediniz.")
                    self.gunluk_insulin_bilgi.setStyleSheet("color: #FF9800; font-weight: bold;")
                    
                    # Butonları etkinleştir
                    self.insulin_kullanildi_btn.setEnabled(True)
                    self.insulin_kullanilmadi_btn.setEnabled(True)
                elif bugun_kaydi['kullanildi']:
                    # Kullanıldıysa saat bilgisini de göster
                    saat_str = ""
                    if bugun_kaydi['saat']:
                        saat_str = f" (Saat: {bugun_kaydi['saat'].strftime('%H:%M')})"
                    self.gunluk_insulin_bilgi.setText(f"Bugün için önerilen insülin dozu: {bugun_kaydi['doz']} mL\nKullanım durumu: Kullanıldı ✓{saat_str}")
                    self.gunluk_insulin_bilgi.setStyleSheet("color: #4CAF50; font-weight: bold;")
                    
                    # Butonları devre dışı bırak
                    self.insulin_kullanildi_btn.setEnabled(False)
                    self.insulin_kullanilmadi_btn.setEnabled(False)
                else:
                    self.gunluk_insulin_bilgi.setText(f"Bugün için önerilen insülin dozu: {bugun_kaydi['doz']} mL\nKullanım durumu: Kullanılmadı ✗")
                    self.gunluk_insulin_bilgi.setStyleSheet("color: #F44336; font-weight: bold;")
                    
                    # Butonları devre dışı bırak
                    self.insulin_kullanildi_btn.setEnabled(False)
                    self.insulin_kullanilmadi_btn.setEnabled(False)
            else:
                # Bugün için kayıt yoksa ortalama kan şekeri değerine göre öneri göster
                try:
                    # Günlük ölçümleri getir
                    olcumler = gunluk_olcumleri_getir(self.hasta['tc_kimlik_no'], bugun, conn)
                    
                    # Ortalama hesapla
                    ortalama, _, _, _ = ortalama_hesapla(olcumler)
                    
                    if ortalama > 0:
                        # İnsülin önerisi hesapla
                        insulin_onerisi = insulin_onerisi_hesapla(ortalama)
                        
                        if insulin_onerisi == 0:
                            if ortalama < 70:
                                self.gunluk_insulin_bilgi.setText(f"Bugün için ortalama kan şekeri: {ortalama:.1f} mg/dL\nİnsülin önerisi: Kullanım Önerilmiyor (Düşük Kan Şekeri)")
                                self.gunluk_insulin_bilgi.setStyleSheet("color: blue; font-weight: bold;")
                            else:
                                self.gunluk_insulin_bilgi.setText(f"Bugün için ortalama kan şekeri: {ortalama:.1f} mg/dL\nİnsülin önerisi: Kullanım Gerekmiyor (Normal)")
                                self.gunluk_insulin_bilgi.setStyleSheet("color: green; font-weight: bold;")
                        else:
                            self.gunluk_insulin_bilgi.setText(f"Bugün için ortalama kan şekeri: {ortalama:.1f} mg/dL\nÖnerilen insülin dozu: {insulin_onerisi} mL\nDoktorunuz tarafından henüz reçete edilmemiş.")
                            self.gunluk_insulin_bilgi.setStyleSheet("color: #FF9800; font-weight: bold;")
                    else:
                        self.gunluk_insulin_bilgi.setText("Bugün için kan şekeri ölçümü bulunmadığından insülin önerisi yapılamıyor.")
                        self.gunluk_insulin_bilgi.setStyleSheet("color: #9E9E9E; font-weight: bold;")
                except Exception as e:
                    self.gunluk_insulin_bilgi.setText(f"Bugün için insülin kaydı bulunmuyor. İnsülin kayıtları doktorunuz tarafından oluşturulur.")
                    self.gunluk_insulin_bilgi.setStyleSheet("color: #9E9E9E; font-weight: bold;")
            
            # Butonları devre dışı bırak
            self.insulin_kullanildi_btn.setEnabled(False)
            self.insulin_kullanilmadi_btn.setEnabled(False)
        
            # Add clarification text that only doctors can add insulin records
            insulin_note = QLabel("Not: İnsülin dozları sadece doktorunuz tarafından belirlenir. Hasta olarak yalnızca kullanım durumunu belirtebilirsiniz.")
            insulin_note.setStyleSheet("color: #1976D2; font-style: italic;")
            insulin_note.setWordWrap(True)
            
            # Add the note to the layout if it doesn't already exist
            layout = self.insulin_sayfasi.layout()
            found = False
            for i in range(layout.count()):
                widget = layout.itemAt(i).widget()
                if isinstance(widget, QLabel) and widget.text().startswith("Not: İnsülin dozları"):
                    found = True
                    break
            
            if not found:
                layout.addWidget(insulin_note)
        
        except Exception as e:
            
            if 'conn' in locals() and conn:
                conn.close()

    def insulin_kullanildi(self):
        """Bugünkü insülinin kullanıldığını işaretler"""
        self.insulin_durumu_guncelle(None, True)

    def insulin_kullanilmadi(self):
        """Bugünkü insülinin kullanılmadığını işaretler"""
        self.insulin_durumu_guncelle(None, False)

    def insulin_durumu_guncelle(self, kayit_id=None, kullanildi=None):
        """
        İnsülin kullanım durumunu günceller
        
        Args:
            kayit_id: Güncellenecek kaydın ID'si (None ise bugünün kaydı)
            kullanildi: True (Kullanıldı) veya False (Kullanılmadı)
        """
        try:
            # Veritabanı bağlantısı
            conn = mysql.connector.connect(
                host=DB_HOST,
                user=DB_USER,
                password=DB_PASSWORD,
                database=DB_NAME,
                charset=DB_CHARSET
            )
            cursor = conn.cursor()
            
            bugun = datetime.now().date()
            current_time = datetime.now().time()  # Get current time
            
            # Kayıt ID belli değilse bugünün kaydını bul
            if kayit_id is None:
                cursor.execute("""
                SELECT id FROM InsulinKayitlari 
                WHERE hasta_tc = %s AND tarih = %s
                """, (self.hasta['tc_kimlik_no'], bugun))
                
                sonuc = cursor.fetchone()
                if sonuc:
                    kayit_id = sonuc[0]
                else:
                    QMessageBox.warning(self, "Bilgi", "Bugün için insülin kaydı bulunamadı.")
                    return
            
            # Kaydı güncelle - kullanıldıysa saat bilgisini de kaydet
            if kullanildi:
                # Store current time as TIME type for better compatibility
                current_time_str = current_time.strftime('%H:%M:%S')
                cursor.execute("""
                UPDATE InsulinKayitlari SET kullanildi = %s, saat = %s
                WHERE id = %s
                """, (kullanildi, current_time_str, kayit_id))
            else:
                cursor.execute("""
                UPDATE InsulinKayitlari SET kullanildi = %s, saat = NULL
                WHERE id = %s
                """, (kullanildi, kayit_id))
            
            conn.commit()
            
            # Bilgileri yenile
            self.insulin_bilgilerini_yukle()
            
            # Kullanıcıya bilgi ver
            durum = "kullanıldı" if kullanildi else "kullanılmadı"
            QMessageBox.information(self, "Başarılı", f"İnsülin {durum} olarak kaydedildi.")
            
        except Exception as e:
            QMessageBox.warning(self, "Hata", f"İnsülin durumu güncellenirken bir hata oluştu: {str(e)}")
        finally:
            if 'conn' in locals() and conn:
                cursor.close()
                conn.close()

    def filter_seker_input(self, text):
        """Filters blood sugar input to ensure it's a positive number with at most 3 digits"""
        if not text:
            return
            
        # Replace comma with decimal point for consistency
        if ',' in text:
            text = text.replace(',', '.')
            self.seker_deger.setText(text)
            
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
            self.seker_deger.setText(filtered_text)
