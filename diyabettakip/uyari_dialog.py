from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                           QTableWidget, QTableWidgetItem, QPushButton, 
                           QHeaderView, QMessageBox, QDateEdit, QSplitter,QWidget)
from PyQt5.QtCore import Qt, QDate
from PyQt5.QtGui import QFont
import mysql.connector
from datetime import datetime, timedelta
from graph_utils import create_blood_sugar_graph, embed_matplotlib_figure

# Import config
try:
    from config import DB_HOST, DB_USER, DB_PASSWORD, DB_NAME, DB_CHARSET
except ImportError:
    DB_HOST = "localhost"
    DB_USER = "root"
    DB_PASSWORD = "YOUR_PASSWORD"
    DB_NAME = "diyabet"
    DB_CHARSET = "utf8mb4"

class HastaUyariDialog(QDialog):
    """Dialog for displaying and managing patient alerts/warnings"""
    
    def __init__(self, hasta_tc, hasta_isim, parent=None):
        super().__init__(parent)
        self.hasta_tc = hasta_tc
        self.hasta_isim = hasta_isim
        
        self.setWindowTitle(f"Hasta Uyarıları - {self.hasta_isim}")
        self.setMinimumSize(900, 600)
        
        self.arayuz_olustur()
        self.uyarilari_yukle()
    
    def arayuz_olustur(self):
        """Create the UI elements"""
        layout = QVBoxLayout(self)
        
        # Title
        baslik = QLabel(f"{self.hasta_isim} - Uyarılar")
        baslik.setFont(QFont("Arial", 14, QFont.Bold))
        baslik.setAlignment(Qt.AlignCenter)
        layout.addWidget(baslik)
        
        # Create a splitter for alerts and graph
        splitter = QSplitter(Qt.Vertical)
        
        # Alerts table section
        uyari_widget = QWidget()
        uyari_layout = QVBoxLayout(uyari_widget)
        
        # Date filter controls
        tarih_layout = QHBoxLayout()
        
        baslangic_label = QLabel("Başlangıç:")
        self.baslangic_tarihi = QDateEdit()
        self.baslangic_tarihi.setDate(QDate.currentDate().addDays(-30))
        self.baslangic_tarihi.setCalendarPopup(True)
        
        bitis_label = QLabel("Bitiş:")
        self.bitis_tarihi = QDateEdit()
        self.bitis_tarihi.setDate(QDate.currentDate())
        self.bitis_tarihi.setCalendarPopup(True)
        
        filtrele_btn = QPushButton("Filtrele")
        filtrele_btn.clicked.connect(self.uyarilari_yukle)
        
        tarih_layout.addWidget(baslangic_label)
        tarih_layout.addWidget(self.baslangic_tarihi)
        tarih_layout.addWidget(bitis_label)
        tarih_layout.addWidget(self.bitis_tarihi)
        tarih_layout.addWidget(filtrele_btn)
        
        uyari_layout.addLayout(tarih_layout)
        
        # Alerts table
        self.uyari_tablosu = QTableWidget()
        self.uyari_tablosu.setColumnCount(6)
        self.uyari_tablosu.setHorizontalHeaderLabels([
            "Tarih", "Uyarı Tipi", "Kan Şekeri", "Açıklama", "Okundu", "İşlemler"
        ])
        self.uyari_tablosu.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.uyari_tablosu.setSelectionBehavior(QTableWidget.SelectRows)
        self.uyari_tablosu.itemSelectionChanged.connect(self.uyari_secildi)
        
        uyari_layout.addWidget(self.uyari_tablosu)
        
        # Graph section
        grafik_widget = QWidget()
        grafik_layout = QVBoxLayout(grafik_widget)
        
        grafik_baslik = QLabel("Seçili Uyarı İçin Kan Şekeri Grafiği")
        grafik_baslik.setAlignment(Qt.AlignCenter)
        grafik_layout.addWidget(grafik_baslik)
        
        self.graph_container = QVBoxLayout()
        self.graph_info = QLabel("Uyarı seçtiğinizde ilgili günün grafiği burada gösterilecektir.")
        self.graph_info.setAlignment(Qt.AlignCenter)
        self.graph_container.addWidget(self.graph_info)
        
        grafik_layout.addLayout(self.graph_container)
        
        # Add both sections to splitter
        splitter.addWidget(uyari_widget)
        splitter.addWidget(grafik_widget)
        splitter.setSizes([300, 300])  # Equal sizes initially
        
        layout.addWidget(splitter)
        
        # Bottom buttons
        buton_layout = QHBoxLayout()
        
        self.tumunu_okundu_btn = QPushButton("Tümünü Okundu İşaretle")
        self.tumunu_okundu_btn.clicked.connect(self.tumunu_okundu_isaretle)
        
        kapat_btn = QPushButton("Kapat")
        kapat_btn.clicked.connect(self.accept)
        
        buton_layout.addWidget(self.tumunu_okundu_btn)
        buton_layout.addStretch()
        buton_layout.addWidget(kapat_btn)
        
        layout.addLayout(buton_layout)
    
    def uyarilari_yukle(self):
        """Load patient warnings from database with filters applied"""
        try:
            baslangic = self.baslangic_tarihi.date().toPyDate()
            bitis = self.bitis_tarihi.date().toPyDate()
            
            conn = mysql.connector.connect(
                host=DB_HOST,
                user=DB_USER,
                password=DB_PASSWORD,
                database=DB_NAME,
                charset=DB_CHARSET
            )
            cursor = conn.cursor(dictionary=True)
            
            # Get alerts for this patient in date range
            cursor.execute("""
                SELECT * FROM Uyarilar 
                WHERE tc_kimlik_no = %s AND DATE(tarih_zaman) BETWEEN %s AND %s
                ORDER BY tarih_zaman DESC
            """, (self.hasta_tc, baslangic, bitis))
            
            uyarilar = cursor.fetchall()
            
            # Clear table
            self.uyari_tablosu.setRowCount(0)
            
            for i, uyari in enumerate(uyarilar):
                self.uyari_tablosu.insertRow(i)
                
                # Date and time
                tarih_str = uyari['tarih_zaman'].strftime("%d.%m.%Y %H:%M")
                self.uyari_tablosu.setItem(i, 0, QTableWidgetItem(tarih_str))
                
                # Alert type with color
                uyari_tipi = self.format_uyari_tipi(uyari['uyari_tipi'])
                uyari_tipi_item = QTableWidgetItem(uyari_tipi['text'])
                uyari_tipi_item.setForeground(uyari_tipi['color'])
                self.uyari_tablosu.setItem(i, 1, uyari_tipi_item)
                
                # Blood sugar level (if available)
                seker_seviyesi = str(uyari['seker_seviyesi']) if uyari['seker_seviyesi'] else "-"
                self.uyari_tablosu.setItem(i, 2, QTableWidgetItem(seker_seviyesi))
                
                # Description
                self.uyari_tablosu.setItem(i, 3, QTableWidgetItem(uyari['aciklama']))
                
                # Read status
                okundu = "Evet" if uyari['okundu'] else "Hayır"
                okundu_item = QTableWidgetItem(okundu)
                okundu_item.setForeground(Qt.green if uyari['okundu'] else Qt.red)
                self.uyari_tablosu.setItem(i, 4, QTableWidgetItem(okundu_item))
                
                # Actions
                islem_btn = QPushButton("Okundu İşaretle")
                islem_btn.setEnabled(not uyari['okundu'])
                islem_btn.clicked.connect(lambda checked=False, id=uyari['id']: self.okundu_isaretle(id))
                self.uyari_tablosu.setCellWidget(i, 5, islem_btn)
            
            conn.close()
            
        except Exception as e:
            QMessageBox.warning(self, "Hata", f"Uyarılar yüklenirken bir hata oluştu: {str(e)}")
    
    def format_uyari_tipi(self, uyari_tipi):
        """Format alert type with readable text and color"""
        if uyari_tipi == 'OlcumEksik':
            return {'text': "Ölçüm Eksik", 'color': Qt.darkYellow}
        elif uyari_tipi == 'OlcumYetersiz':
            return {'text': "Yetersiz Ölçüm", 'color': Qt.darkYellow}
        elif uyari_tipi == 'KritikDusuk':
            return {'text': "KRİTİK DÜŞÜK", 'color': Qt.blue}
        elif uyari_tipi == 'KritikYuksek':
            return {'text': "KRİTİK YÜKSEK", 'color': Qt.red}
        elif uyari_tipi == 'OrtaYuksek':
            return {'text': "Orta Yüksek", 'color': Qt.darkYellow}
        elif uyari_tipi == 'Yuksek':
            return {'text': "Yüksek", 'color': Qt.darkRed}
        else:
            return {'text': uyari_tipi, 'color': Qt.black}
    
    def okundu_isaretle(self, uyari_id):
        """Mark an alert as read"""
        try:
            conn = mysql.connector.connect(
                host=DB_HOST,
                user=DB_USER,
                password=DB_PASSWORD,
                database=DB_NAME,
                charset=DB_CHARSET
            )
            cursor = conn.cursor()
            
            # Update alert status
            cursor.execute("""
                UPDATE Uyarilar SET okundu = TRUE
                WHERE id = %s
            """, (uyari_id,))
            
            conn.commit()
            conn.close()
            
            # Refresh alerts
            self.uyarilari_yukle()
            
        except Exception as e:
            QMessageBox.warning(self, "Hata", f"Uyarı durumu güncellenirken bir hata oluştu: {str(e)}")
    
    def tumunu_okundu_isaretle(self):
        """Mark all alerts as read"""
        try:
            conn = mysql.connector.connect(
                host=DB_HOST,
                user=DB_USER,
                password=DB_PASSWORD,
                database=DB_NAME,
                charset=DB_CHARSET
            )
            cursor = conn.cursor()
            
            # Update all alerts for this patient
            cursor.execute("""
                UPDATE Uyarilar SET okundu = TRUE
                WHERE tc_kimlik_no = %s AND okundu = FALSE
            """, (self.hasta_tc,))
            
            updated = cursor.rowcount
            
            conn.commit()
            conn.close()
            
            # Show message and refresh
            QMessageBox.information(self, "Bilgi", f"{updated} uyarı okundu olarak işaretlendi.")
            self.uyarilari_yukle()
            
        except Exception as e:
            QMessageBox.warning(self, "Hata", f"Uyarılar güncellenirken bir hata oluştu: {str(e)}")
    
    def uyari_secildi(self):
        """Handle when an alert is selected - display the graph for that day"""
        try:
            selected_items = self.uyari_tablosu.selectedItems()
            if not selected_items:
                return
            
            # Get date from first column (date) of selected row
            row = selected_items[0].row()
            date_str = self.uyari_tablosu.item(row, 0).text().split()[0]  # Get just the date part
            
            # Convert to Python date
            alert_date = datetime.strptime(date_str, "%d.%m.%Y").date()
            
            # Clear existing widgets
            while self.graph_container.count():
                item = self.graph_container.takeAt(0)
                widget = item.widget()
                if widget:
                    widget.deleteLater()
            
            # Create the graph for the alert date
            fig = create_blood_sugar_graph(self.hasta_tc, alert_date)
            
            # Display the graph
            embed_matplotlib_figure(self.graph_container, fig)
            
        except Exception as e:
            self.graph_info = QLabel(f"Grafik oluşturulurken hata: {str(e)}")
            self.graph_info.setAlignment(Qt.AlignCenter)
            self.graph_container.addWidget(self.graph_info)
