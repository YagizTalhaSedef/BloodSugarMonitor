from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
                           QPushButton, QFormLayout, QGroupBox, QMessageBox,QCheckBox, QComboBox)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIntValidator, QDoubleValidator

# Import Main module
import Main as MainModule

class HastaEkleDiyalog(QDialog):
    def __init__(self, doktor_tc):
        super().__init__()
        self.doktor_tc = doktor_tc
        self.setWindowTitle("Yeni Hasta Ekle")
        self.setFixedWidth(450)  # Genişliği biraz artırdık
        self.arayuz_olustur()
        
    def arayuz_olustur(self):
        layout = QVBoxLayout()
        
        # Hasta bilgileri formu
        form_layout = QFormLayout()
        
        self.tc_input = QLineEdit()
        self.tc_input.setPlaceholderText("11 haneli TC Kimlik No")
        self.tc_input.setMaxLength(11)
        
        self.isim_input = QLineEdit()
        self.isim_input.setPlaceholderText("Hasta isim soyisim")
        
        self.cinsiyet_input = QComboBox()
        self.cinsiyet_input.addItem("Erkek", "E")
        self.cinsiyet_input.addItem("Kadın", "K")
        
        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("örnek@email.com")
        
        # Yeni alanlar: Yaş, Boy, Kilo, VKİ
        self.yas_input = QLineEdit()
        self.yas_input.setPlaceholderText("Yaş")
        self.yas_input.setValidator(QIntValidator(1, 120))  # 1-120 yaş arası
        
        self.boy_input = QLineEdit()
        self.boy_input.setPlaceholderText("Boy (cm)")
        self.boy_input.setValidator(QIntValidator(50, 250))  # 50-250 cm arası
        
        self.kilo_input = QLineEdit()
        self.kilo_input.setPlaceholderText("Kilo (kg)")
        self.kilo_input.setValidator(QDoubleValidator(1, 300, 2))  # 1-300 kg arası, 2 ondalık
        
        # Boy ve kilo değiştiğinde VKİ hesapla
        self.boy_input.textChanged.connect(self.vki_hesapla)
        self.kilo_input.textChanged.connect(self.vki_hesapla)
        
        # VKİ sonucu için salt-okunur alan
        self.vki_sonuc = QLineEdit()
        self.vki_sonuc.setReadOnly(True)
        self.vki_sonuc.setPlaceholderText("VKİ değeri")
        
        # Temel bilgiler
        form_layout.addRow("TC Kimlik No*:", self.tc_input)
        form_layout.addRow("İsim Soyisim*:", self.isim_input)
        form_layout.addRow("Cinsiyet:", self.cinsiyet_input)
        form_layout.addRow("Email*:", self.email_input)
        
        # Fiziksel bilgiler 
        form_layout.addRow("Yaş:", self.yas_input)
        form_layout.addRow("Boy (cm):", self.boy_input)
        form_layout.addRow("Kilo (kg):", self.kilo_input)
        form_layout.addRow("Vücut Kitle İndeksi:", self.vki_sonuc)
        
        layout.addLayout(form_layout)
        
        # Bilgilendirme
        not_label = QLabel("* işaretli alanlar zorunludur. Hastanın şifresi otomatik oluşturulup email ile gönderilecektir.")
        not_label.setWordWrap(True)
        layout.addWidget(not_label)
        
        # Butonlar
        buton_layout = QHBoxLayout()
        
        iptal_btn = QPushButton("İptal")
        iptal_btn.clicked.connect(self.reject)
        
        kaydet_btn = QPushButton("Kaydet")
        kaydet_btn.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")
        kaydet_btn.clicked.connect(self.hasta_kaydet)
        
        buton_layout.addWidget(iptal_btn)
        buton_layout.addWidget(kaydet_btn)
        
        layout.addLayout(buton_layout)
        self.setLayout(layout)
    
    def vki_hesapla(self):
        """Boy ve kilo değerlerine göre VKİ'yi hesaplar"""
        try:
            boy_text = self.boy_input.text().strip()
            kilo_text = self.kilo_input.text().strip().replace(',', '.')
            
            if boy_text and kilo_text:
                boy_cm = float(boy_text)
                kilo_kg = float(kilo_text)
                
                if boy_cm > 0 and kilo_kg > 0:
                    # VKİ = kilo(kg) / (boy(m) * boy(m))
                    boy_metre = boy_cm / 100
                    vki = kilo_kg / (boy_metre * boy_metre)
                    
                    # VKİ sonucunu göster ve kategorisini belirle
                    if vki < 18.5:
                        kategori = "Zayıf"
                        renk = "blue"
                    elif vki < 25:
                        kategori = "Normal"
                        renk = "green"
                    elif vki < 30:
                        kategori = "Fazla Kilolu"
                        renk = "orange"
                    else:
                        kategori = "Obez"
                        renk = "red"
                    
                    self.vki_sonuc.setText(f"{vki:.2f} ({kategori})")
                    self.vki_sonuc.setStyleSheet(f"color: {renk}; font-weight: bold;")
                    return
        except:
            pass
        
        # Hesaplama yapılamazsa
        self.vki_sonuc.setText("")
        self.vki_sonuc.setStyleSheet("")
    
    def hasta_kaydet(self):
        tc_kimlik = self.tc_input.text()
        isim_soyisim = self.isim_input.text()
        cinsiyet = self.cinsiyet_input.currentData()
        email = self.email_input.text()
        
        # Fiziksel bilgiler (isteğe bağlı)
        yas = self.yas_input.text().strip()
        boy = self.boy_input.text().strip()
        kilo = self.kilo_input.text().strip().replace(',', '.')
        
        # VKİ değerini al (hesaplanmış değer)
        vki_text = self.vki_sonuc.text().strip()
        vki = None
        if vki_text:
            try:
                # Parantez içindeki kategori kısmını at
                vki = float(vki_text.split('(')[0].strip())
            except:
                pass
        
        # Zorunlu alanları kontrol et
        if not tc_kimlik or not isim_soyisim or not email:
            QMessageBox.warning(self, "Hata", "Lütfen zorunlu alanları doldurun.")
            return
            
        # TC Kimlik No kontrolü
        if len(tc_kimlik) != 11 or not tc_kimlik.isdigit():
            QMessageBox.warning(self, "Hata", "TC Kimlik No 11 haneli sayılardan oluşmalıdır.")
            return
            
        # Hasta kayıt işlemini gerçekleştir - sadece temel bilgilerle
        basarili, mesaj = MainModule.hasta_kaydet(
            self.doktor_tc, tc_kimlik, isim_soyisim, cinsiyet, email
        )
        
        if basarili:
            # Fiziksel bilgileri ayrı olarak güncelle
            if yas or boy or kilo or vki:
                try:
                    MainModule.hasta_fiziksel_bilgi_guncelle(
                        tc_kimlik,
                        yas=int(yas) if yas else None,
                        boy=int(boy) if boy else None, 
                        kilo=float(kilo) if kilo else None,
                        vki=vki
                    )
                except:
                    pass  # Fiziksel bilgi güncellemesi başarısız olsa da hasta kaydı yapılmış olur
                    
            QMessageBox.information(self, "Başarılı", mesaj)
            self.accept()  # Diyaloğu kapat
        else:
            QMessageBox.warning(self, "Hata", mesaj)


class SifreSifirlaDiyalog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Şifre Sıfırlama")
        self.setFixedWidth(400)
        self.arayuz_olustur()
        
    def arayuz_olustur(self):
        layout = QVBoxLayout()
        
        # Kullanıcı tipi seçimi
        kullanici_tipi_grup = QGroupBox("Kullanıcı Tipi")
        kullanici_tipi_layout = QHBoxLayout()
        
        self.doktor_radio = QPushButton("Doktor")
        self.hasta_radio = QPushButton("Hasta")
        
        self.doktor_radio.setCheckable(True)
        self.hasta_radio.setCheckable(True)
        self.doktor_radio.setChecked(True)  # Varsayılan olarak doktor girişi seçili
        
        kullanici_tipi_layout.addWidget(self.doktor_radio)
        kullanici_tipi_layout.addWidget(self.hasta_radio)
        
        kullanici_tipi_grup.setLayout(kullanici_tipi_layout)
        layout.addWidget(kullanici_tipi_grup)
        
        # TC Kimlik No girişi
        self.tc_input = QLineEdit()
        self.tc_input.setPlaceholderText("TC Kimlik No")
        self.tc_input.setMaxLength(11)
        
        layout.addWidget(self.tc_input)
        
        # Email girişi (yeni ekledik)
        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("Email Adresi")
        layout.addWidget(self.email_input)
        
        # Yeni şifre girişi - şifre gösterme seçeneği ekledik
        sifre_layout = QHBoxLayout()
        self.sifre_input = QLineEdit()
        self.sifre_input.setPlaceholderText("Yeni Şifre")
        self.sifre_input.setEchoMode(QLineEdit.Password)
        
        self.sifre_goster_cb = QCheckBox("Göster")
        self.sifre_goster_cb.toggled.connect(self.sifre_goster_gizle)
        
        sifre_layout.addWidget(self.sifre_input)
        sifre_layout.addWidget(self.sifre_goster_cb)
        layout.addLayout(sifre_layout)
        
        # Şifreyi onayla girişi - şifre gösterme seçeneği ekledik
        sifre_onay_layout = QHBoxLayout()
        self.sifre_onay_input = QLineEdit()
        self.sifre_onay_input.setPlaceholderText("Şifreyi Onayla")
        self.sifre_onay_input.setEchoMode(QLineEdit.Password)
        
        # Aynı checkbox'un etkisi her iki şifre alanını da etkilesin
        self.sifre_goster_cb.toggled.connect(lambda checked: self.sifre_onay_input.setEchoMode(
            QLineEdit.Normal if checked else QLineEdit.Password))
        
        sifre_onay_layout.addWidget(self.sifre_onay_input)
        # Checkbox'u tekrar eklemiyoruz, bir tane yeterli
        layout.addLayout(sifre_onay_layout)
        
        # Butonlar
        buton_layout = QHBoxLayout()
        
        iptal_btn = QPushButton("İptal")
        iptal_btn.clicked.connect(self.reject)
        
        sifirla_btn = QPushButton("Şifreyi Sıfırla")
        sifirla_btn.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")
        sifirla_btn.clicked.connect(self.sifre_sifirla)
        
        buton_layout.addWidget(iptal_btn)
        buton_layout.addWidget(sifirla_btn)
        
        layout.addLayout(buton_layout)
        
        self.setLayout(layout)
    
    def sifre_goster_gizle(self, checked):
        """Şifrenin gösterilme modunu değiştirir"""
        self.sifre_input.setEchoMode(QLineEdit.Normal if checked else QLineEdit.Password)
    
    def sifre_sifirla(self):
        tc_kimlik = self.tc_input.text()
        yeni_sifre = self.sifre_input.text()
        sifre_onay = self.sifre_onay_input.text()
        
        # TC Kimlik No kontrolü
        if len(tc_kimlik) != 11 or not tc_kimlik.isdigit():
            QMessageBox.warning(self, "Hata", "TC Kimlik No 11 haneli sayılardan oluşmalıdır.")
            return
        
        # Şifre boş mu kontrol et
        if not yeni_sifre or not sifre_onay:
            QMessageBox.warning(self, "Hata", "Şifre ve onayı boş bırakılamaz.")
            return
        
        # Şifreler eşleşiyor mu kontrol et
        if yeni_sifre != sifre_onay:
            QMessageBox.warning(self, "Hata", "Şifreler eşleşmiyor.")
            return
        
        # Şifre sıfırlama işlemini gerçekleştir
        if self.doktor_radio.isChecked():
            basarili, mesaj = MainModule.sifre_sifirla(tc_kimlik, yeni_sifre, "doktor")
        else:
            basarili, mesaj = MainModule.sifre_sifirla(tc_kimlik, yeni_sifre, "hasta")
        
        if basarili:
            QMessageBox.information(self, "Başarılı", "Şifreniz başarıyla sıfırlandı.")
            self.accept()
        else:
            QMessageBox.warning(self, "Hata", mesaj)
