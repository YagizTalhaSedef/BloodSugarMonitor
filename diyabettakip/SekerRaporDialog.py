from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                           QTableWidget, QTableWidgetItem, QPushButton,
                           QHeaderView, QMessageBox, QDateEdit, QDoubleSpinBox, QWidget,QTabWidget)
from PyQt5.QtCore import Qt, QDate
from PyQt5.QtGui import QFont
import mysql.connector
from datetime import datetime
from seker_utils import insulin_onerisi_hesapla

# Import config
try:
    from config import DB_HOST, DB_USER, DB_PASSWORD, DB_NAME, DB_CHARSET
except ImportError:
    DB_HOST = "localhost"
    DB_USER = "root"
    DB_PASSWORD = "YOUR_PASSWORD"
    DB_NAME = "diyabet"
    DB_CHARSET = "utf8mb4"

class SekerRaporDialog(QDialog):
    def __init__(self, hasta_tc, hasta_isim, doktor_tc, parent=None):
        super().__init__(parent)
        self.hasta_tc = hasta_tc
        self.hasta_isim = hasta_isim
        self.doktor_tc = doktor_tc  # Doktor TC'sini ekledik
        self.setWindowTitle(f"Kan Şekeri Raporları - {hasta_isim}")
        self.resize(800, 600)
        self.arayuz_olustur()
        self.raporlari_yukle()
        
    def arayuz_olustur(self):
        layout = QVBoxLayout(self)
        
        # Başlık
        baslik = QLabel(f"{self.hasta_isim} - Kan Şekeri Raporları")
        baslik.setFont(QFont("Arial", 14, QFont.Bold))
        baslik.setAlignment(Qt.AlignCenter)
        layout.addWidget(baslik)
        
        # Tarih seçimi
        tarih_layout = QHBoxLayout()
        tarih_label = QLabel("Tarih:")
        self.tarih_secici = QDateEdit()
        self.tarih_secici.setDate(QDate.currentDate())
        self.tarih_secici.setDisplayFormat("dd.MM.yyyy")
        self.tarih_secici.setCalendarPopup(True)
        
        tarih_btn = QPushButton("Göster")
        tarih_btn.clicked.connect(self.raporlari_yukle)
        
        tarih_layout.addWidget(tarih_label)
        tarih_layout.addWidget(self.tarih_secici)
        tarih_layout.addWidget(tarih_btn)
        layout.addLayout(tarih_layout)
        
        # Tablo
        self.rapor_tablosu = QTableWidget()
        self.rapor_tablosu.setColumnCount(6)
        self.rapor_tablosu.setHorizontalHeaderLabels([
            "Ölçüm Zamanı", "Saat", "Değer (mg/dL)", "Seviye", "Uygun Zaman", "Ortalamaya Dahil"
        ])
        self.rapor_tablosu.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.rapor_tablosu)
        
        # Özet bilgisi
        self.ozet_label = QLabel()
        self.ozet_label.setWordWrap(True)
        layout.addWidget(self.ozet_label)
        
        # İnsülin önerisi
        self.insulin_grup = QVBoxLayout()
        self.insulin_label = QLabel()
        self.insulin_label.setFont(QFont("Arial", 12, QFont.Bold))
        self.insulin_label.setAlignment(Qt.AlignCenter)
        
        # İnsülin reçete etme alanı
        self.insulin_recete_layout = QHBoxLayout()
        self.insulin_doz_input = QDoubleSpinBox()
        self.insulin_doz_input.setRange(0, 10)
        self.insulin_doz_input.setDecimals(1)
        self.insulin_doz_input.setSingleStep(0.5)
        self.insulin_doz_input.setSuffix(" mL")
        
        self.insulin_kaydet_btn = QPushButton("İnsülin Kaydet")
        self.insulin_kaydet_btn.setStyleSheet("background-color: #4CAF50; color: white;")
        self.insulin_kaydet_btn.clicked.connect(self.insulin_kaydet)
        
        self.insulin_recete_layout.addWidget(QLabel("İnsülin Dozu:"))
        self.insulin_recete_layout.addWidget(self.insulin_doz_input)
        self.insulin_recete_layout.addWidget(self.insulin_kaydet_btn)
        
        self.insulin_grup.addWidget(self.insulin_label)
        self.insulin_grup.addLayout(self.insulin_recete_layout)
        layout.addLayout(self.insulin_grup)
        
        # Kapat butonu
        kapat_btn = QPushButton("Kapat")
        kapat_btn.clicked.connect(self.reject)
        layout.addWidget(kapat_btn)
        
        # Tab widget for different views
        self.tab_widget = QTabWidget()
        
        # Table tab
        table_tab = QWidget()
        table_layout = QVBoxLayout(table_tab)
        
        # Tarih seçimi
        tarih_label = QLabel("Tarih:")
        self.tarih_secici = QDateEdit()
        self.tarih_secici.setDate(QDate.currentDate())
        self.tarih_secici.setDisplayFormat("dd.MM.yyyy")
        self.tarih_secici.setCalendarPopup(True)
        
        tarih_btn = QPushButton("Göster")
        tarih_btn.clicked.connect(self.raporlari_yukle)
        
        tarih_layout = QHBoxLayout()
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
        
        self.tab_widget.addTab(table_tab, "Tablo")
        
        # Günlük grafik sekmesi
        graph_tab = QWidget()
        graph_layout = QVBoxLayout(graph_tab)
        
        # Grafiğin yerleştirileceği alan
        self.graph_container = QVBoxLayout()
        
        # Grafiği içeren bir widget oluştur
        graph_widget = QWidget()
        graph_widget.setLayout(self.graph_container)
        
        # Alanın genişlemesini sağlamak için boyut politikasını ayarla
        from PyQt5.QtWidgets import QSizePolicy
        graph_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        graph_layout.addWidget(graph_widget, 1)  # Genişletme faktörü 1 olarak ayarla
        
        self.tab_widget.addTab(graph_tab, "Günlük Grafik")
        
        # Haftalık grafik sekmesi
        weekly_tab = QWidget()
        weekly_layout = QVBoxLayout(weekly_tab)
        
        # Date range for weekly graph
        weekly_date_layout = QHBoxLayout()
        weekly_date_label = QLabel("Bitiş Tarihi:")
        
        # Define the weekly_date attribute that was missing
        self.weekly_date = QDateEdit()
        self.weekly_date.setDate(QDate.currentDate())
        self.weekly_date.setDisplayFormat("dd.MM.yyyy")
        self.weekly_date.setCalendarPopup(True)
        self.weekly_date.dateChanged.connect(self.update_weekly_graph)
        
        weekly_date_layout.addWidget(weekly_date_label)
        weekly_date_layout.addWidget(self.weekly_date)
        
        weekly_refresh_btn = QPushButton("Grafiği Güncelle")
        weekly_refresh_btn.clicked.connect(self.update_weekly_graph)
        weekly_date_layout.addWidget(weekly_refresh_btn)
        
        weekly_layout.addLayout(weekly_date_layout)
        
        # Placeholder for the weekly graph
        self.weekly_graph_container = QVBoxLayout()
        weekly_layout.addLayout(self.weekly_graph_container)
        
        self.tab_widget.addTab(weekly_tab, "Haftalık Grafik")
        
        layout.addWidget(self.tab_widget)
        
        # Günlük ve haftalık grafikler için başlangıçta boş mesajlar
        self.graph_container.addWidget(QLabel("Günlük grafik verisi yok."))
        self.weekly_graph_container.addWidget(QLabel("Haftalık grafik verisi yok."))
        
        # Veritabanı bağlantısı
        self.conn = None
        self.cursor = None
    
    def raporlari_yukle(self):
        try:
            secili_tarih = self.tarih_secici.date().toPyDate()
            
            # Veritabanı bağlantısı
            conn = mysql.connector.connect(
                host=DB_HOST,
                user=DB_USER,
                password=DB_PASSWORD,
                database=DB_NAME,
                charset=DB_CHARSET
            )
            cursor = conn.cursor(dictionary=True)
            
            # Seçili tarih için ölçümleri getir
            cursor.execute("""
                SELECT * FROM KanSekeriKayitlari 
                WHERE tc_kimlik_no = %s AND tarih = %s
                ORDER BY saat
            """, (self.hasta_tc, secili_tarih))
            
            olcumler = cursor.fetchall()
            
            # Tabloyu temizle
            self.rapor_tablosu.setRowCount(0)
            
            # Veri sayıları ve toplamlar için değişkenler
            toplam_deger = 0
            olcum_sayisi = 0
            dahil_sayisi = 0
            
            # Tabloyu doldur
            for i, olcum in enumerate(olcumler):
                self.rapor_tablosu.insertRow(i)
                
                # Ölçüm zamanı
                self.rapor_tablosu.setItem(i, 0, QTableWidgetItem(olcum['olcum_zamani']))
                
                # Saat - 24 saat formatında göster
                from ui_utils import saat_goruntu_formatla
                saat_str = saat_goruntu_formatla(olcum['saat'])
                self.rapor_tablosu.setItem(i, 1, QTableWidgetItem(saat_str))
                
                # Değer
                self.rapor_tablosu.setItem(i, 2, QTableWidgetItem(str(olcum['seker_seviyesi'])))
                
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
                self.rapor_tablosu.setItem(i, 3, seviye_item)
                
                # Uygun Zaman
                uygun_text = "Evet" if olcum['zaman_uygun'] else "Hayır"
                uygun_item = QTableWidgetItem(uygun_text)
                uygun_item.setForeground(Qt.darkGreen if olcum['zaman_uygun'] else Qt.red)
                self.rapor_tablosu.setItem(i, 4, uygun_item)
                
                # Ortalamaya Dahil
                dahil_text = "Evet" if olcum['ortalamaya_dahil'] else "Hayır"
                dahil_item = QTableWidgetItem(dahil_text)
                dahil_item.setForeground(Qt.darkGreen if olcum['ortalamaya_dahil'] else Qt.red)
                self.rapor_tablosu.setItem(i, 5, dahil_item)
                
                # İstatistikler için değerleri güncelle
                if olcum['ortalamaya_dahil']:
                    toplam_deger += olcum['seker_seviyesi']
                    dahil_sayisi += 1
                    
                olcum_sayisi += 1
            
            # İnsülin reçete alanını başlangıçta gizle
            self.insulin_doz_input.setVisible(False)
            self.insulin_kaydet_btn.setVisible(False)
            
            # Özet bilgilerini hazırla
            if olcum_sayisi > 0:
                if dahil_sayisi > 0:
                    ortalama = toplam_deger / dahil_sayisi
                    ozet_text = f"Gün Özeti: Toplam {olcum_sayisi} ölçüm, {dahil_sayisi} ölçüm ortalamaya dahil edildi."
                    ozet_text += f"\nOrtalama Kan Şekeri: {ortalama:.1f} mg/dL"
                    
                    # Uyarı mesajları
                    if dahil_sayisi <= 3:
                        ozet_text += "\n⚠️ Yetersiz veri! Ortalama hesaplaması güvenilir değildir."
                    
                    if dahil_sayisi < 5:
                        ozet_text += f"\n⚠️ Günlük ölçüm eksik! Sadece {dahil_sayisi}/5 ölçüm mevcut."
                    
                    self.ozet_label.setText(ozet_text)
                else:
                    self.ozet_label.setText("Ölçümler uygun zamanlarda yapılmadığı için ortalama hesaplanamadı.")
                    self.insulin_label.setText("İnsülin önerisi yapılamadı (Uygun ölçüm yok)")
                    self.insulin_doz_input.setVisible(False)
                    self.insulin_kaydet_btn.setVisible(False)
            else:
                self.ozet_label.setText("Bu tarih için ölçüm kaydı bulunmamaktadır.")
                self.insulin_label.setText("İnsülin önerisi yapılamadı (Ölçüm yok)")
                self.insulin_doz_input.setVisible(False)
                self.insulin_kaydet_btn.setVisible(False)
            
            # If no measurements exist, show special message for doctors
            if olcum_sayisi == 0:
                self.ozet_label.setText(
                    "Bu hasta için henüz kan şekeri ölçümü bulunmamaktadır.\n"
                    "Not: İlk ölçümlerin doktor tarafından girilmesi gerekmektedir."
                )
                self.ozet_label.setStyleSheet("color: #1976D2; font-weight: bold;")
                
                # Add button for doctor to enter first measurements
                if not hasattr(self, 'ilk_olcum_btn'):
                    self.ilk_olcum_btn = QPushButton("İlk Ölçümleri Gir")
                    self.ilk_olcum_btn.clicked.connect(self.ilk_olcumleri_gir)
                    self.layout().addWidget(self.ilk_olcum_btn)
            else:
                # Remove the button if it exists and there are already measurements
                if hasattr(self, 'ilk_olcum_btn') and self.ilk_olcum_btn in self.children():
                    self.layout().removeWidget(self.ilk_olcum_btn)
                    self.ilk_olcum_btn.setParent(None)
                    self.ilk_olcum_btn = None
            
            cursor.close()
            conn.close()
            
        except Exception as e:
            self.ozet_label.setText(f"Raporlar yüklenirken hata oluştu: {str(e)}")
            self.insulin_label.setText("")
    
    def insulin_kaydet(self):
        """İnsülin dozunu kaydet veya güncelle"""
        try:
            secili_tarih = self.tarih_secici.date().toPyDate()
            doz = self.insulin_doz_input.value()
            
            # Veritabanı bağlantısı
            conn = mysql.connector.connect(
                host=DB_HOST,
                user=DB_USER,
                password=DB_PASSWORD,
                database=DB_NAME,
                charset=DB_CHARSET
            )
            cursor = conn.cursor(dictionary=True)
            
            # İnsülin kaydı var mı kontrol et
            cursor.execute("""
            SELECT * FROM InsulinKayitlari 
            WHERE hasta_tc = %s AND tarih = %s
            """, (self.hasta_tc, secili_tarih))
            
            insulin_kaydi = cursor.fetchone()
            
            if insulin_kaydi:
                # Mevcut kaydı güncelle - bildirildi alanını kaldırdık
                cursor.execute("""
                UPDATE InsulinKayitlari 
                SET doz = %s, doktor_tc = %s
                WHERE id = %s
                """, (doz, self.doktor_tc, insulin_kaydi['id']))
            else:
                # Yeni kayıt oluştur - bildirildi alanını kaldırdık
                cursor.execute("""
                INSERT INTO InsulinKayitlari 
                (hasta_tc, doktor_tc, tarih, doz)
                VALUES (%s, %s, %s, %s)
                """, (self.hasta_tc, self.doktor_tc, secili_tarih, doz))
            
            conn.commit()
            cursor.close()
            conn.close()
            
            QMessageBox.information(self, "Başarılı", f"İnsülin dozu {doz} mL olarak kaydedildi.")
            
            # Verileri yenile
            self.raporlari_yukle()
            
        except Exception as e:
            QMessageBox.warning(self, "Hata", f"İnsülin kaydedilirken bir hata oluştu: {str(e)}")
    
    def update_blood_sugar_graph(self):
        """Update the blood sugar graph for the selected date"""
        try:
            selected_date = self.tarih_secici.date().toPyDate()
            
            # Create the graph using graph_utils
            from graph_utils import create_blood_sugar_graph, embed_matplotlib_figure
            
            # Create the graph
            fig = create_blood_sugar_graph(self.hasta_tc, selected_date)
            
            # Display the graph
            embed_matplotlib_figure(self.graph_container, fig)
        except Exception as e:
            print(f"Error updating blood sugar graph: {e}")
            import traceback
            traceback.print_exc()  # Print stack trace for debugging

    def update_weekly_graph(self):
        """Update the weekly blood sugar graph"""
        try:
            end_date = self.weekly_date.date().toPyDate()
            
            # Create the graph using graph_utils
            from graph_utils import create_weekly_graph, embed_matplotlib_figure
            
            # Create the graph
            fig = create_weekly_graph(self.hasta_tc, end_date)
            
            # Display the graph
            embed_matplotlib_figure(self.weekly_graph_container, fig)
        except Exception as e:
            print(f"Error updating weekly graph: {e}")
            import traceback
            traceback.print_exc()  # Print stack trace for debugging

    def raporlari_yukle(self):
        try:
            secili_tarih = self.tarih_secici.date().toPyDate()
            
            # Veritabanı bağlantısı
            conn = mysql.connector.connect(
                host=DB_HOST,
                user=DB_USER,
                password=DB_PASSWORD,
                database=DB_NAME,
                charset=DB_CHARSET
            )
            cursor = conn.cursor(dictionary=True)
            
            # Seçili tarih için ölçümleri getir
            cursor.execute("""
                SELECT * FROM KanSekeriKayitlari 
                WHERE tc_kimlik_no = %s AND tarih = %s
                ORDER BY saat
            """, (self.hasta_tc, secili_tarih))
            
            olcumler = cursor.fetchall()
            
            # Tabloyu temizle
            self.rapor_tablosu.setRowCount(0)
            
            # Veri sayıları ve toplamlar için değişkenler
            toplam_deger = 0
            olcum_sayisi = 0
            dahil_sayisi = 0
            
            # Tabloyu doldur
            for i, olcum in enumerate(olcumler):
                self.rapor_tablosu.insertRow(i)
                
                # Ölçüm zamanı
                self.rapor_tablosu.setItem(i, 0, QTableWidgetItem(olcum['olcum_zamani']))
                
                # Saat - 24 saat formatında göster
                from ui_utils import saat_goruntu_formatla
                saat_str = saat_goruntu_formatla(olcum['saat'])
                self.rapor_tablosu.setItem(i, 1, QTableWidgetItem(saat_str))
                
                # Değer
                self.rapor_tablosu.setItem(i, 2, QTableWidgetItem(str(olcum['seker_seviyesi'])))
                
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
                self.rapor_tablosu.setItem(i, 3, seviye_item)
                
                # Uygun Zaman
                uygun_text = "Evet" if olcum['zaman_uygun'] else "Hayır"
                uygun_item = QTableWidgetItem(uygun_text)
                uygun_item.setForeground(Qt.darkGreen if olcum['zaman_uygun'] else Qt.red)
                self.rapor_tablosu.setItem(i, 4, uygun_item)
                
                # Ortalamaya Dahil
                dahil_text = "Evet" if olcum['ortalamaya_dahil'] else "Hayır"
                dahil_item = QTableWidgetItem(dahil_text)
                dahil_item.setForeground(Qt.darkGreen if olcum['ortalamaya_dahil'] else Qt.red)
                self.rapor_tablosu.setItem(i, 5, dahil_item)
                
                # İstatistikler için değerleri güncelle
                if olcum['ortalamaya_dahil']:
                    toplam_deger += olcum['seker_seviyesi']
                    dahil_sayisi += 1
                    
                olcum_sayisi += 1
            
            # İnsülin reçete alanını başlangıçta gizle
            self.insulin_doz_input.setVisible(False)
            self.insulin_kaydet_btn.setVisible(False)
            
            # Özet bilgilerini hazırla
            if olcum_sayisi > 0:
                if dahil_sayisi > 0:
                    ortalama = toplam_deger / dahil_sayisi
                    ozet_text = f"Gün Özeti: Toplam {olcum_sayisi} ölçüm, {dahil_sayisi} ölçüm ortalamaya dahil edildi."
                    ozet_text += f"\nOrtalama Kan Şekeri: {ortalama:.1f} mg/dL"
                    
                    # Uyarı mesajları
                    if dahil_sayisi <= 3:
                        ozet_text += "\n⚠️ Yetersiz veri! Ortalama hesaplaması güvenilir değildir."
                    
                    if dahil_sayisi < 5:
                        ozet_text += f"\n⚠️ Günlük ölçüm eksik! Sadece {dahil_sayisi}/5 ölçüm mevcut."
                    
                    self.ozet_label.setText(ozet_text)
                else:
                    self.ozet_label.setText("Ölçümler uygun zamanlarda yapılmadığı için ortalama hesaplanamadı.")
                    self.insulin_label.setText("İnsülin önerisi yapılamadı (Uygun ölçüm yok)")
                    self.insulin_doz_input.setVisible(False)
                    self.insulin_kaydet_btn.setVisible(False)
            else:
                self.ozet_label.setText("Bu tarih için ölçüm kaydı bulunmamaktadır.")
                self.insulin_label.setText("İnsülin önerisi yapılamadı (Ölçüm yok)")
                self.insulin_doz_input.setVisible(False)
                self.insulin_kaydet_btn.setVisible(False)
            
            # If no measurements exist, show special message for doctors
            if olcum_sayisi == 0:
                self.ozet_label.setText(
                    "Bu hasta için henüz kan şekeri ölçümü bulunmamaktadır.\n"
                    "Not: İlk ölçümlerin doktor tarafından girilmesi gerekmektedir."
                )
                self.ozet_label.setStyleSheet("color: #1976D2; font-weight: bold;")
                
                # Add button for doctor to enter first measurements
                if not hasattr(self, 'ilk_olcum_btn'):
                    self.ilk_olcum_btn = QPushButton("İlk Ölçümleri Gir")
                    self.ilk_olcum_btn.clicked.connect(self.ilk_olcumleri_gir)
                    self.layout().addWidget(self.ilk_olcum_btn)
            else:
                # Remove the button if it exists and there are already measurements
                if hasattr(self, 'ilk_olcum_btn') and self.ilk_olcum_btn in self.children():
                    self.layout().removeWidget(self.ilk_olcum_btn)
                    self.ilk_olcum_btn.setParent(None)
                    self.ilk_olcum_btn = None
            
            cursor.close()
            conn.close()
            
            # Ayrıca, seçili tarih için grafiği güncelle
            try:
                if self.tab_widget.currentIndex() == 1:
                    self.update_blood_sugar_graph()
                elif self.tab_widget.currentIndex() == 2:
                    self.update_weekly_graph()
            except Exception as e:
                print(f"Error updating graphs: {e}")
            
        except Exception as e:
            self.ozet_label.setText(f"Raporlar yüklenirken hata oluştu: {str(e)}")
            self.insulin_label.setText("")
