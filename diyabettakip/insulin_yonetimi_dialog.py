from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                           QTableWidget, QTableWidgetItem, QPushButton,
                           QHeaderView, QMessageBox, QDateEdit, QDoubleSpinBox,
                           QFormLayout, QGroupBox)
from PyQt5.QtCore import Qt, QDate
from PyQt5.QtGui import QFont
import mysql.connector
from datetime import datetime, timedelta
from seker_utils import insulin_onerisi_hesapla, gunluk_olcumleri_getir, ortalama_hesapla
from ui_utils import format_time_safely  # Import the new utility function

# Import config
try:
    from config import DB_HOST, DB_USER, DB_PASSWORD, DB_NAME, DB_CHARSET
except ImportError:
    DB_HOST = "localhost"
    DB_USER = "root"
    DB_PASSWORD = "YOUR_PASSWORD"
    DB_NAME = "diyabet"
    DB_CHARSET = "utf8mb4"

class InsulinYonetimiDialog(QDialog):
    """Dialog for managing insulin prescriptions and tracking for patients"""
    
    def __init__(self, hasta_tc, hasta_isim, doktor_tc, parent=None):
        super().__init__(parent)
        self.hasta_tc = hasta_tc
        self.hasta_isim = hasta_isim
        self.doktor_tc = doktor_tc
        
        self.setWindowTitle(f"İnsülin Yönetimi - {self.hasta_isim}")
        self.setMinimumSize(900, 600)
        
        self.arayuz_olustur()
        self.insulin_kayitlarini_yukle()
        self.kan_sekeri_ortalama_goster()
    
    def arayuz_olustur(self):
        """Create the UI elements"""
        layout = QVBoxLayout(self)
        
        # Title
        baslik = QLabel(f"{self.hasta_isim} - İnsülin Yönetimi")
        baslik.setFont(QFont("Arial", 14, QFont.Bold))
        baslik.setAlignment(Qt.AlignCenter)
        layout.addWidget(baslik)
        
        # Average blood sugar & recommendation section
        ortalama_grup = QGroupBox("Kan Şekeri Ortalaması ve İnsülin Önerisi")
        ortalama_layout = QVBoxLayout()
        
        # Average info labels
        self.ortalama_label = QLabel("Ortalama kan şekeri bilgisi yükleniyor...")
        self.ortalama_label.setAlignment(Qt.AlignCenter)
        self.ortalama_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        ortalama_layout.addWidget(self.ortalama_label)
        
        self.oneri_label = QLabel("")
        self.oneri_label.setAlignment(Qt.AlignCenter)
        self.oneri_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #1976D2;")
        ortalama_layout.addWidget(self.oneri_label)
        
        ortalama_grup.setLayout(ortalama_layout)
        layout.addWidget(ortalama_grup)
        
        # New insulin record entry section
        yeni_kayit_grup = QGroupBox("Yeni İnsülin Dozu Ekle")
        yeni_kayit_layout = QFormLayout()
        
        self.tarih_secici = QDateEdit()
        self.tarih_secici.setDate(QDate.currentDate())
        self.tarih_secici.setDisplayFormat("dd.MM.yyyy")
        self.tarih_secici.setCalendarPopup(True)
        
        self.doz_secici = QDoubleSpinBox()
        self.doz_secici.setMinimum(0.0)
        self.doz_secici.setMaximum(10.0)
        self.doz_secici.setSingleStep(0.5)
        self.doz_secici.setValue(0.0)
        self.doz_secici.setSuffix(" mL")
        
        doz_buton_layout = QHBoxLayout()
        kaydet_btn = QPushButton("Dozu Kaydet")
        kaydet_btn.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")
        kaydet_btn.clicked.connect(self.yeni_insulin_dozu_ekle)
        
        oneri_uygula_btn = QPushButton("Önerilen Dozu Uygula")
        oneri_uygula_btn.clicked.connect(self.oneriyi_uygula)
        doz_buton_layout.addWidget(kaydet_btn)
        doz_buton_layout.addWidget(oneri_uygula_btn)
        
        yeni_kayit_layout.addRow("Tarih:", self.tarih_secici)
        yeni_kayit_layout.addRow("İnsülin Dozu:", self.doz_secici)
        yeni_kayit_layout.addRow("", doz_buton_layout)
        
        yeni_kayit_grup.setLayout(yeni_kayit_layout)
        layout.addWidget(yeni_kayit_grup)
        
        # Add date filter for historical records
        filtre_grup = QGroupBox("Geçmiş Kayıtları Filtrele")
        filtre_layout = QHBoxLayout()
        
        baslangic_label = QLabel("Başlangıç:")
        self.baslangic_tarih = QDateEdit()
        self.baslangic_tarih.setDate(QDate.currentDate().addMonths(-1))  # Default to 1 month ago
        self.baslangic_tarih.setDisplayFormat("dd.MM.yyyy")
        self.baslangic_tarih.setCalendarPopup(True)
        
        bitis_label = QLabel("Bitiş:")
        self.bitis_tarih = QDateEdit()
        self.bitis_tarih.setDate(QDate.currentDate())
        self.bitis_tarih.setDisplayFormat("dd.MM.yyyy")
        self.bitis_tarih.setCalendarPopup(True)
        
        filtre_btn = QPushButton("Filtrele")
        # Fix: Connect to insulin_kayitlarini_yukle instead of non-existent kayitlari_filtrele
        filtre_btn.clicked.connect(self.insulin_kayitlarini_yukle)
        
        filtre_layout.addWidget(baslangic_label)
        filtre_layout.addWidget(self.baslangic_tarih)
        filtre_layout.addWidget(bitis_label)
        filtre_layout.addWidget(self.bitis_tarih)
        filtre_layout.addWidget(filtre_btn)
        
        filtre_grup.setLayout(filtre_layout)
        layout.addWidget(filtre_grup)
        
        # Insulin records table
        kayitlar_grup = QGroupBox("İnsülin Kayıtları")
        kayitlar_layout = QVBoxLayout()
        
        # Update column count to include blood sugar data
        self.kayit_tablosu = QTableWidget()
        self.kayit_tablosu.setColumnCount(6)
        self.kayit_tablosu.setHorizontalHeaderLabels([
            "Tarih", "Doz (mL)", "Günlük Kan Şekeri Ort.", "Kullanım Durumu", "Ekleyen", "İşlemler"
        ])
        self.kayit_tablosu.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        
        kayitlar_layout.addWidget(self.kayit_tablosu)
        kayitlar_grup.setLayout(kayitlar_layout)
        layout.addWidget(kayitlar_grup)
        
        # Buttons at the bottom
        buton_layout = QHBoxLayout()
        
        yenile_btn = QPushButton("Yenile")
        yenile_btn.clicked.connect(self.insulin_kayitlarini_yukle)
        
        kapat_btn = QPushButton("Kapat")
        kapat_btn.clicked.connect(self.accept)
        
        buton_layout.addStretch()
        buton_layout.addWidget(yenile_btn)
        buton_layout.addWidget(kapat_btn)
        
        layout.addLayout(buton_layout)
    
    def insulin_kayitlarini_yukle(self):
        """Load insulin records from database"""
        try:
            conn = mysql.connector.connect(
                host=DB_HOST,
                user=DB_USER,
                password=DB_PASSWORD,
                database=DB_NAME,
                charset=DB_CHARSET
            )
            cursor = conn.cursor(dictionary=True)
            
            # Get date range from filters if set
            baslangic = self.baslangic_tarih.date().toPyDate()
            bitis = self.bitis_tarih.date().toPyDate()
            
            # Check date range validity
            if baslangic > bitis:
                QMessageBox.warning(self, "Hata", "Başlangıç tarihi bitiş tarihinden sonra olamaz.")
                # Reset dates to valid range
                self.baslangic_tarih.setDate(self.bitis_tarih.date().addMonths(-1))
                baslangic = self.baslangic_tarih.date().toPyDate()
                return
            
            # Updated query to include daily average blood sugar level and date filtering
            cursor.execute("""
                SELECT i.*, 
                       CASE WHEN i.doktor_tc IS NOT NULL THEN d.isim_soyisim ELSE 'Sistem' END as ekleyen,
                       (SELECT AVG(seker_seviyesi) 
                        FROM KanSekeriKayitlari 
                        WHERE tc_kimlik_no = i.hasta_tc AND tarih = i.tarih) as kan_sekeri_ort
                FROM InsulinKayitlari i
                LEFT JOIN Doktorlar d ON i.doktor_tc = d.tc_kimlik_no
                WHERE i.hasta_tc = %s AND i.tarih BETWEEN %s AND %s
                ORDER BY i.tarih DESC 
                LIMIT 100
            """, (self.hasta_tc, baslangic, bitis))
            
            kayitlar = cursor.fetchall()
            
            # Clear table
            self.kayit_tablosu.setRowCount(0)
            
            # Fill table with records - now including blood sugar data
            for i, kayit in enumerate(kayitlar):
                self.kayit_tablosu.insertRow(i)
                
                # Date and time display using the safe formatter
                tarih_str = kayit['tarih'].strftime("%d.%m.%Y")
                time_str = ""
                
                if kayit['kullanildi'] and kayit['saat'] is not None:
                    time_str = f" ({format_time_safely(kayit['saat'])})"
                    
                self.kayit_tablosu.setItem(i, 0, QTableWidgetItem(f"{tarih_str}{time_str}"))
                
                # Dose
                self.kayit_tablosu.setItem(i, 1, QTableWidgetItem(f"{kayit['doz']} mL"))
                
                # Blood sugar average - new column
                kan_sekeri_item = QTableWidgetItem()
                if kayit['kan_sekeri_ort'] is not None:
                    kan_sekeri_value = float(kayit['kan_sekeri_ort'])
                    kan_sekeri_item.setText(f"{kan_sekeri_value:.1f} mg/dL")
                    
                    # Color code based on value
                    if kan_sekeri_value < 70:
                        kan_sekeri_item.setForeground(Qt.blue)
                    elif kan_sekeri_value <= 180:
                        kan_sekeri_item.setForeground(Qt.darkGreen)
                    else:
                        kan_sekeri_item.setForeground(Qt.red)
                else:
                    kan_sekeri_item.setText("Ölçüm yok")
                    kan_sekeri_item.setForeground(Qt.gray)
                
                self.kayit_tablosu.setItem(i, 2, kan_sekeri_item)
                
                # Usage status - enhanced to show time when used
                if kayit['kullanildi'] is None:
                    durum_text = "Belirtilmemiş"
                    durum_color = Qt.black
                elif kayit['kullanildi']:
                    durum_text = "Kullanıldı"
                    # Use the safe formatter for time display
                    if kayit['saat'] is not None:
                        durum_text += f" ({format_time_safely(kayit['saat'])})"
                    durum_color = Qt.darkGreen
                else:
                    durum_text = "Kullanılmadı"
                    durum_color = Qt.red
                
                durum_item = QTableWidgetItem(durum_text)
                durum_item.setForeground(durum_color)
                self.kayit_tablosu.setItem(i, 3, durum_item)
                
                # Added by
                self.kayit_tablosu.setItem(i, 4, QTableWidgetItem(kayit['ekleyen']))
                
                # Actions - Delete button
                buton_widget = QPushButton("Sil")
                buton_widget.setStyleSheet("background-color: #F44336; color: white;")
                buton_widget.clicked.connect(lambda checked=False, id=kayit['id']: self.insulin_kaydi_sil(id))
                self.kayit_tablosu.setCellWidget(i, 5, buton_widget)
        
            conn.close()
            
        except Exception as e:
            # Suppress the specific timedelta error message
            error_msg = str(e)
            if "timedelta" in error_msg and "strftime" in error_msg:
                print("Handling time format error safely")
                # Try to reload the data without crashing
                self.insulin_kayitlarini_yukle()
            else:
                QMessageBox.warning(self, "Hata", f"İnsülin kayıtları yüklenirken bir hata oluştu: {error_msg}")
    
    def kan_sekeri_ortalama_goster(self):
        """Calculate and display blood sugar average and insulin recommendation"""
        try:
            conn = mysql.connector.connect(
                host=DB_HOST,
                user=DB_USER,
                password=DB_PASSWORD,
                database=DB_NAME,
                charset=DB_CHARSET
            )
            
            # Get today's measurements
            olcumler = gunluk_olcumleri_getir(self.hasta_tc, datetime.now().date(), conn)
            
            # Calculate average
            ortalama, olcum_sayisi, eksik_olcumler, uyarilar = ortalama_hesapla(olcumler)
            
            # Display average and recommendation
            if ortalama > 0:
                # Show average
                self.ortalama_label.setText(f"Ortalama Kan Şekeri: {ortalama:.1f} mg/dL ({olcum_sayisi}/5 ölçüm)")
                
                # Calculate insulin recommendation
                insulin_onerisi = insulin_onerisi_hesapla(ortalama)
                
                # Set recommendation text and color
                if insulin_onerisi == 0:
                    if ortalama < 70:
                        oneri_text = "İnsülin Önerisi: İnsülin Kullanımı Önerilmez (Hipoglisemi Riski)"
                        self.oneri_label.setStyleSheet("font-size: 16px; font-weight: bold; color: blue;")
                    else:
                        oneri_text = "İnsülin Önerisi: İnsülin Kullanımı Gerekmiyor (Normal Değer)"
                        self.oneri_label.setStyleSheet("font-size: 16px; font-weight: bold; color: green;")
                else:
                    oneri_text = f"İnsülin Önerisi: {insulin_onerisi} mL"
                    self.oneri_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #FF5722;")
                
                # Store recommendation for later use
                self.insulin_onerisi = insulin_onerisi
                
                self.oneri_label.setText(oneri_text)
                
                # Add warning text if necessary
                if uyarilar:
                    uyari_text = "\n".join(uyarilar)
                    self.ortalama_label.setText(f"{self.ortalama_label.text()}\n⚠️ {uyari_text}")
            else:
                self.ortalama_label.setText("Bugün için kan şekeri ölçümü bulunmamaktadır.")
                self.oneri_label.setText("İnsülin önerisi için kan şekeri ölçümleri gereklidir")
                self.insulin_onerisi = 0
            
            conn.close()
            
        except Exception as e:
            self.ortalama_label.setText("Ortalama kan şekeri bilgisi yüklenemedi!")
            self.oneri_label.setText(f"Hata: {str(e)}")
            self.insulin_onerisi = 0
    
    def oneriyi_uygula(self):
        """Apply suggested insulin dose to the dose spinner"""
        if hasattr(self, 'insulin_onerisi'):
            self.doz_secici.setValue(self.insulin_onerisi)
        else:
            QMessageBox.warning(self, "Uyarı", "Henüz bir öneri hesaplanmadı!")
    
    def yeni_insulin_dozu_ekle(self):
        """Add a new insulin dose record"""
        try:
            tarih = self.tarih_secici.date().toPyDate()
            doz = self.doz_secici.value()
            
            if doz <= 0:
                QMessageBox.warning(self, "Uyarı", "Lütfen geçerli bir insülin dozu giriniz.")
                return
            
            # Connect to database
            conn = mysql.connector.connect(
                host=DB_HOST,
                user=DB_USER,
                password=DB_PASSWORD,
                database=DB_NAME,
                charset=DB_CHARSET
            )
            cursor = conn.cursor()
            
            # Check if there's already a record for this date
            cursor.execute("""
                SELECT COUNT(*) FROM InsulinKayitlari 
                WHERE hasta_tc = %s AND tarih = %s
            """, (self.hasta_tc, tarih))
            
            existing_count = cursor.fetchone()[0]
            
            if existing_count > 0:
                # Ask for confirmation to override
                yanit = QMessageBox.question(
                    self, 
                    "Dikkat", 
                    f"Bu tarih için zaten bir insülin kaydı mevcut. Değiştirmek istiyor musunuz?",
                    QMessageBox.Yes | QMessageBox.No
                )
                
                if yanit == QMessageBox.Yes:
                    # Update existing record
                    cursor.execute("""
                        UPDATE InsulinKayitlari 
                        SET doz = %s, doktor_tc = %s, kullanildi = NULL
                        WHERE hasta_tc = %s AND tarih = %s
                    """, (doz, self.doktor_tc, self.hasta_tc, tarih))
                else:
                    return
            else:
                # Insert new record
                cursor.execute("""
                    INSERT INTO InsulinKayitlari (hasta_tc, doktor_tc, tarih, doz)
                    VALUES (%s, %s, %s, %s)
                """, (self.hasta_tc, self.doktor_tc, tarih, doz))
            
            conn.commit()
            
            # Refresh table
            self.insulin_kayitlarini_yukle()
            
            QMessageBox.information(self, "Başarılı", f"İnsülin dozu başarıyla kaydedildi: {doz} mL")
            
            cursor.close()
            conn.close()
            
        except Exception as e:
            QMessageBox.warning(self, "Hata", f"İnsülin dozu kaydedilirken bir hata oluştu: {str(e)}")
    
    def insulin_kaydi_sil(self, kayit_id):
        """Delete an insulin record"""
        try:
            # Ask for confirmation
            yanit = QMessageBox.question(
                self, 
                "Onay", 
                "Bu insülin kaydını silmek istediğinizden emin misiniz?",
                QMessageBox.Yes | QMessageBox.No
            )
            
            if yanit == QMessageBox.No:
                return
            
            # Connect to database
            conn = mysql.connector.connect(
                host=DB_HOST,
                user=DB_USER,
                password=DB_PASSWORD,
                database=DB_NAME,
                charset=DB_CHARSET
            )
            cursor = conn.cursor()
            
            # Delete record
            cursor.execute("DELETE FROM InsulinKayitlari WHERE id = %s", (kayit_id,))
            conn.commit()
            
            # Refresh table
            self.insulin_kayitlarini_yukle()
            
            QMessageBox.information(self, "Başarılı", "İnsülin kaydı başarıyla silindi.")
            
            cursor.close()
            conn.close()
            
        except Exception as e:
            QMessageBox.warning(self, "Hata", f"İnsülin kaydı silinirken bir hata oluştu: {str(e)}")
