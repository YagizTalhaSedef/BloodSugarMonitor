from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
                            QMessageBox, QFormLayout, QGroupBox, QPushButton, QCheckBox)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QIcon

# Import dialogs
from diyaloglar import SifreSifirlaDiyalog

# Import Main module
import Main as MainModule

class GirisEkrani(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Diyabet Takip Sistemi - Giriş")
        self.setFixedSize(400, 300)
        self.arayuz_olustur()
        
    def arayuz_olustur(self):
        ana_layout = QVBoxLayout()
        
        # Başlık
        baslik = QLabel("Diyabet Takip Sistemi")
        baslik.setAlignment(Qt.AlignCenter)
        baslik.setFont(QFont("Arial", 16, QFont.Bold))
        ana_layout.addWidget(baslik)
        
        # Kullanıcı tipi seçimi
        kullanici_tipi_grup = QGroupBox("Kullanıcı Tipi")
        kullanici_tipi_layout = QHBoxLayout()
        
        # Stil tanımlamaları - transition özelliğini kaldırıyoruz
        doktor_secili_stil = """
            background-color: #2196F3; 
            color: white; 
            font-weight: bold;
            border-radius: 10px;
            padding: 10px;
            border: none;
        """
        
        hasta_secili_stil = """
            background-color: #4CAF50; 
            color: white; 
            font-weight: bold;
            border-radius: 10px;
            padding: 10px;
            border: none;
        """
        
        secili_olmayan_stil = """
            background-color: #E0E0E0; 
            color: #424242;
            border-radius: 10px;
            padding: 10px;
            border: none;
        """
        
        self.doktor_radio = QPushButton("Doktor Girişi")
        self.hasta_radio = QPushButton("Hasta Girişi")
        
        self.doktor_radio.setCheckable(True)
        self.hasta_radio.setCheckable(True)
        
        # Varsayılan olarak doktor girişi seçili
        self.doktor_radio.setChecked(True)
        self.doktor_radio.setStyleSheet(doktor_secili_stil)
        self.hasta_radio.setStyleSheet(secili_olmayan_stil)
        
        # Buton tıklama işleyicileri - renkleri de güncelle
        self.doktor_radio.clicked.connect(lambda: self.kullanici_tipi_degistir("doktor"))
        self.hasta_radio.clicked.connect(lambda: self.kullanici_tipi_degistir("hasta"))
        
        kullanici_tipi_layout.addWidget(self.doktor_radio)
        kullanici_tipi_layout.addWidget(self.hasta_radio)
        
        kullanici_tipi_grup.setLayout(kullanici_tipi_layout)
        ana_layout.addWidget(kullanici_tipi_grup)
        
        # Giriş bilgileri
        form_layout = QFormLayout()
        
        self.tc_input = QLineEdit()
        self.tc_input.setPlaceholderText("11 haneli TC Kimlik No")
        self.tc_input.setMaxLength(11)
        
        # Şifre alanı ve göster/gizle düzeni
        sifre_layout = QHBoxLayout()
        self.sifre_input = QLineEdit()
        self.sifre_input.setPlaceholderText("Şifre")
        self.sifre_input.setEchoMode(QLineEdit.Password)
        
        self.sifre_goster_cb = QCheckBox("Göster")
        self.sifre_goster_cb.toggled.connect(self.sifre_goster_gizle)
        
        sifre_layout.addWidget(self.sifre_input)
        sifre_layout.addWidget(self.sifre_goster_cb)
        
        form_layout.addRow("TC Kimlik No:", self.tc_input)
        form_layout.addRow("Şifre:", sifre_layout)
        
        ana_layout.addLayout(form_layout)
        
        # Giriş butonu - box-shadow kaldırıldı
        giris_btn = QPushButton("Giriş Yap")
        giris_btn.clicked.connect(self.giris_yap)
        giris_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50; 
                color: white; 
                font-weight: bold; 
                padding: 10px;
                border-radius: 15px;
                border: none;
                font-size: 14px;
                margin: 8px 4px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3d8b40;
                padding-top: 11px;
                padding-bottom: 9px;
            }
        """)
        ana_layout.addWidget(giris_btn)
        
        # Şifremi unuttum bağlantısı - Daha yumuşak ve modern
        sifremi_unuttum = QPushButton("Şifremi Unuttum")
        sifremi_unuttum.setStyleSheet("""
            QPushButton {
                background-color: #F44336;
                color: white; 
                padding: 8px; 
                margin-top: 8px;
                border-radius: 12px;
                border: none;
                font-size: 12px;
                max-width: 150px;
            }
            QPushButton:hover {
                background-color: #e53935;
                color: white;
            }
            QPushButton:pressed {
                background-color: #d32f2f;
                padding-top: 9px;
                padding-bottom: 7px;
            }
        """)
        sifremi_unuttum.clicked.connect(self.sifremi_unuttum_fonk)
        ana_layout.addWidget(sifremi_unuttum, alignment=Qt.AlignCenter)
        
        self.setLayout(ana_layout)
    
    def kullanici_tipi_degistir(self, tip):
        """Kullanıcı tipini değiştirir ve butonları uygun şekilde günceller"""
        # Yumuşak geçişli stil tanımları - transition özelliğini kaldırıyoruz
        doktor_secili_stil = """
            background-color: #2196F3; 
            color: white; 
            font-weight: bold;
            border-radius: 10px;
            padding: 10px;
            border: none;
        """
        
        hasta_secili_stil = """
            background-color: #4CAF50; 
            color: white; 
            font-weight: bold;
            border-radius: 10px;
            padding: 10px;
            border: none;
        """
        
        secili_olmayan_stil = """
            background-color: #E0E0E0; 
            color: #424242;
            border-radius: 10px;
            padding: 10px;
            border: none;
        """
        
        if tip == "doktor":
            self.doktor_radio.setChecked(True)
            self.hasta_radio.setChecked(False)
            self.doktor_radio.setStyleSheet(doktor_secili_stil)
            self.hasta_radio.setStyleSheet(secili_olmayan_stil)
        else:  # "hasta"
            self.doktor_radio.setChecked(False)
            self.hasta_radio.setChecked(True)
            self.doktor_radio.setStyleSheet(secili_olmayan_stil)
            self.hasta_radio.setStyleSheet(hasta_secili_stil)
    
    def sifre_goster_gizle(self, checked):
        """Şifrenin gösterilme modunu değiştirir"""
        self.sifre_input.setEchoMode(QLineEdit.Normal if checked else QLineEdit.Password)
    
    def giris_yap(self):
        tc_kimlik = self.tc_input.text()
        sifre = self.sifre_input.text()
        
        # TC Kimlik doğrulama
        if len(tc_kimlik) != 11 or not tc_kimlik.isdigit():
            QMessageBox.warning(self, "Hata", "TC Kimlik No 11 haneli sayılardan oluşmalıdır.")
            return
            
        # Doktor girişi
        if self.doktor_radio.isChecked():
            basarili, sonuc = MainModule.doktor_giris(tc_kimlik, sifre)
            if basarili:
                self.close()
                # Import here to avoid circular imports
                from doktor_ekrani import DoktorEkrani
                self.doktor_ekrani = DoktorEkrani(sonuc)
                self.doktor_ekrani.show()
            else:
                QMessageBox.warning(self, "Giriş Hatası", str(sonuc))
        
        # Hasta girişi
        else:
            basarili, sonuc = MainModule.hasta_giris(tc_kimlik, sifre)
            if basarili:
                self.close()
                # Import here to avoid circular imports
                from hasta_ekrani import HastaEkrani
                self.hasta_ekrani = HastaEkrani(sonuc)
                self.hasta_ekrani.show()
            else:
                QMessageBox.warning(self, "Giriş Hatası", str(sonuc))
    
    def sifremi_unuttum_fonk(self):
        # Şifre sıfırlama ekranını göster
        dialog = SifreSifirlaDiyalog()
        dialog.exec_()
