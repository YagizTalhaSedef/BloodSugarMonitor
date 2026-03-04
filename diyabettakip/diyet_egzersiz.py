from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, 
                           QCheckBox, QPushButton, QTableWidget, QTableWidgetItem,
                           QFormLayout, QGroupBox, QMessageBox, QDialog,QTabWidget ,QTextEdit,
                           QDateEdit, QHeaderView)
from PyQt5.QtCore import Qt, QDate
from PyQt5.QtGui import QFont, QColor
import mysql.connector
from datetime import datetime, date, timedelta

# Import config
try:
    from config import DB_HOST, DB_USER, DB_PASSWORD, DB_NAME, DB_CHARSET
except ImportError:
    DB_HOST = "localhost"
    DB_USER = "root"
    DB_PASSWORD = "YOUR_PASSWORD"
    DB_NAME = "diyabet"
    DB_CHARSET = "utf8mb4"

# Dictionary of symptoms
BELIRTILER = {
    "Poliüri": "Sık idrara çıkma",
    "Polifaji": "Aşırı açlık hissi",
    "Polidipsi": "Aşırı susama hissi",
    "Nöropati": "El ve ayaklarda karıncalanma veya uyuşma hissi",
    "Kilo Kaybı": "İstem dışı kilo kaybı",
    "Yorgunluk": "Sürekli yorgunluk hissi",
    "Yaraların Yavaş İyileşmesi": "Cilt yaralarının normalden uzun sürede iyileşmesi",
    "Bulanık Görme": "Net görememe, görüşte bulanıklık"
}

# Dictionary of diets
DIYETLER = {
    "Dengeli Beslenme": "Karbonhidrat, protein ve yağ oranları dengeli beslenme",
    "Az Şekerli Diyet": "Şeker ve işlenmiş karbonhidratların sınırlı tüketildiği diyet",
    "Şekersiz Diyet": "Şeker ve yüksek glisemik indeksli besinlerin tüketilmediği diyet"
}

# Dictionary of exercises
EGZERSIZLER = {
    "Yürüyüş": "Hafif tempolu, günlük yapılabilecek bir egzersiz",
    "Bisiklet": "Alt vücut kaslarını çalıştıran, dış mekanda veya sabit bisikletle uygulanabilen egzersiz",
    "Klinik Egzersiz": "Doktor tarafından verilen belirli hareketleri içeren planlı egzersizler"
}

# Recommendation mapping based on blood sugar levels and symptoms
RECOMMENDATIONS = [
    {
        "blood_sugar_range": "< 70 mg/dL",
        "blood_sugar_label": "Hipoglisemi",
        "symptoms": ["Nöropati", "Polifaji", "Yorgunluk"],
        "diet": "Dengeli Beslenme",
        "exercise": "Yok"
    },
    {
        "blood_sugar_range": "< 70 mg/dL",
        "blood_sugar_label": "Hipoglisemi",
        "symptoms": ["Yorgunluk", "Kilo Kaybı"],
        "diet": "Az Şekerli Diyet",
        "exercise": "Yürüyüş"
    },
    {
        "blood_sugar_range": "70-110 mg/dL",
        "blood_sugar_label": "Normal - Alt Düzey",
        "symptoms": ["Polifaji", "Polidipsi"],
        "diet": "Dengeli Beslenme",
        "exercise": "Yürüyüş"
    },
    {
        "blood_sugar_range": "70-110 mg/dL",
        "blood_sugar_label": "Normal - Alt Düzey",
        "symptoms": ["Bulanık Görme", "Nöropati"],
        "diet": "Az Şekerli Diyet",
        "exercise": "Klinik Egzersiz"
    },
    {
        "blood_sugar_range": "110-180 mg/dL",
        "blood_sugar_label": "Normal - Üst Düzey / Hafif Yüksek",
        "symptoms": ["Poliüri", "Polidipsi"],
        "diet": "Şekersiz Diyet",
        "exercise": "Klinik Egzersiz"
    },
    {
        "blood_sugar_range": "110-180 mg/dL",
        "blood_sugar_label": "Normal - Üst Düzey / Hafif Yüksek",
        "symptoms": ["Yorgunluk", "Nöropati", "Bulanık Görme"],
        "diet": "Az Şekerli Diyet",
        "exercise": "Yürüyüş"
    },
    {
        "blood_sugar_range": "≥ 180 mg/dL",
        "blood_sugar_label": "Hiperglisemi",
        "symptoms": ["Yaraların Yavaş İyileşmesi", "Polifaji", "Polidipsi"],
        "diet": "Şekersiz Diyet",
        "exercise": "Klinik Egzersiz"
    },
    {
        "blood_sugar_range": "≥ 180 mg/dL",
        "blood_sugar_label": "Hiperglisemi",
        "symptoms": ["Yaraların Yavaş İyileşmesi", "Kilo Kaybı"],
        "diet": "Şekersiz Diyet",
        "exercise": "Yürüyüş"
    }
]

# Database functions
def connect_database():
    """Connect to MySQL database"""
    return mysql.connector.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        charset=DB_CHARSET
    )

def create_diet_exercise_tables():
    """Create necessary tables for diet and exercise tracking if they don't exist"""
    conn = connect_database()
    cursor = conn.cursor()
    
    try:
        # Create Diyet ve Egzersiz Planlari table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS DiyetEgzersizPlanlari (
            id INT AUTO_INCREMENT PRIMARY KEY,
            hasta_tc CHAR(11) NOT NULL,
            doktor_tc CHAR(11) NOT NULL,
            baslangic_tarihi DATE NOT NULL,
            bitis_tarihi DATE NOT NULL,
            diyet_turu VARCHAR(100) NOT NULL,
            diyet_aciklama TEXT,
            egzersiz_turu VARCHAR(100),
            egzersiz_aciklama TEXT,
            ozel_notlar TEXT,
            olusturma_zamani DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (hasta_tc) REFERENCES Hastalar(tc_kimlik_no) ON DELETE CASCADE,
            FOREIGN KEY (doktor_tc) REFERENCES Doktorlar(tc_kimlik_no) ON DELETE CASCADE,
            INDEX (hasta_tc),
            INDEX (doktor_tc)
        ) CHARACTER SET utf8mb4 COLLATE utf8mb4_turkish_ci;
        """)
        
        # Create tracking table for daily adherence
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS DiyetEgzersizTakip (
            id INT AUTO_INCREMENT PRIMARY KEY,
            plan_id INT NOT NULL,
            hasta_tc CHAR(11) NOT NULL,
            tarih DATE NOT NULL,
            diyet_yapildi BOOLEAN DEFAULT FALSE,
            egzersiz_yapildi BOOLEAN DEFAULT FALSE,
            notlar TEXT,
            bildirim_zamani DATETIME DEFAULT CURRENT_TIMESTAMP,
            okundu BOOLEAN DEFAULT FALSE,
            FOREIGN KEY (plan_id) REFERENCES DiyetEgzersizPlanlari(id) ON DELETE CASCADE,
            FOREIGN KEY (hasta_tc) REFERENCES Hastalar(tc_kimlik_no) ON DELETE CASCADE,
            UNIQUE (hasta_tc, tarih),
            INDEX (hasta_tc),
            INDEX (tarih)
        ) CHARACTER SET utf8mb4 COLLATE utf8mb4_turkish_ci;
        """)
        
        conn.commit()
        return True
    except Exception as e:
        print(f"Error creating diet and exercise tables: {e}")
        return False
    finally:
        cursor.close()
        conn.close()

def get_active_plan(hasta_tc):
    """Get the active diet and exercise plan for the patient"""
    conn = connect_database()
    cursor = conn.cursor(dictionary=True)
    
    try:
        cursor.execute("""
        SELECT * FROM DiyetEgzersizPlanlari
        WHERE hasta_tc = %s AND baslangic_tarihi <= CURDATE() AND bitis_tarihi >= CURDATE()
        ORDER BY olusturma_zamani DESC
        LIMIT 1
        """, (hasta_tc,))
        
        plan = cursor.fetchone()
        return plan
    except Exception as e:
        print(f"Error fetching active plan: {e}")
        return None
    finally:
        cursor.close()
        conn.close()

def record_daily_adherence(hasta_tc, diyet_yapildi, egzersiz_yapildi, notlar=None):
    """Record patient's daily adherence to diet and exercise plan"""
    conn = connect_database()
    cursor = conn.cursor()
    
    try:
        # Get active plan
        active_plan = get_active_plan(hasta_tc)
        if not active_plan:
            return False, "Aktif diyet ve egzersiz planı bulunamadı."
        
        today = date.today()
        
        # Check if there's already a record for today
        cursor.execute("""
        SELECT id FROM DiyetEgzersizTakip
        WHERE hasta_tc = %s AND tarih = %s
        """, (hasta_tc, today))
        
        existing_record = cursor.fetchone()
        
        if existing_record:
            # Update existing record
            cursor.execute("""
            UPDATE DiyetEgzersizTakip
            SET diyet_yapildi = %s, egzersiz_yapildi = %s, notlar = %s, bildirim_zamani = NOW(), okundu = FALSE
            WHERE hasta_tc = %s AND tarih = %s
            """, (diyet_yapildi, egzersiz_yapildi, notlar, hasta_tc, today))
        else:
            # Create new record
            cursor.execute("""
            INSERT INTO DiyetEgzersizTakip
            (plan_id, hasta_tc, tarih, diyet_yapildi, egzersiz_yapildi, notlar, bildirim_zamani, okundu)
            VALUES (%s, %s, %s, %s, %s, %s, NOW(), FALSE)
            """, (active_plan['id'], hasta_tc, today, diyet_yapildi, egzersiz_yapildi, notlar))
        
        conn.commit()
        return True, "Diyet ve egzersiz durumu başarıyla kaydedildi."
    except Exception as e:
        print(f"Error recording adherence: {e}")
        return False, f"Kayıt sırasında bir hata oluştu: {e}"
    finally:
        cursor.close()
        conn.close()

def get_patient_adherence_history(hasta_tc, limit=30):
    """Get the patient's diet and exercise adherence history"""
    conn = connect_database()
    cursor = conn.cursor(dictionary=True)
    
    try:
        cursor.execute("""
        SELECT t.*, p.diyet_turu, p.egzersiz_turu
        FROM DiyetEgzersizTakip t
        JOIN DiyetEgzersizPlanlari p ON t.plan_id = p.id
        WHERE t.hasta_tc = %s
        ORDER BY t.tarih DESC
        LIMIT %s
        """, (hasta_tc, limit))
        
        history = cursor.fetchall()
        return history
    except Exception as e:
        print(f"Error fetching adherence history: {e}")
        return []
    finally:
        cursor.close()
        conn.close()

def create_plan_for_patient(hasta_tc, doktor_tc, baslangic_tarihi, bitis_tarihi, 
                           diyet_turu, diyet_aciklama, egzersiz_turu, egzersiz_aciklama, ozel_notlar=None):
    """Create a new diet and exercise plan for a patient"""
    conn = connect_database()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
        INSERT INTO DiyetEgzersizPlanlari
        (hasta_tc, doktor_tc, baslangic_tarihi, bitis_tarihi, diyet_turu, diyet_aciklama, 
         egzersiz_turu, egzersiz_aciklama, ozel_notlar)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (hasta_tc, doktor_tc, baslangic_tarihi, bitis_tarihi, diyet_turu, 
             diyet_aciklama, egzersiz_turu, egzersiz_aciklama, ozel_notlar))
        
        conn.commit()
        return True, "Diyet ve egzersiz planı başarıyla oluşturuldu."
    except Exception as e:
        print(f"Error creating plan: {e}")
        return False, f"Plan oluşturulurken bir hata oluştu: {e}"
    finally:
        cursor.close()
        conn.close()

def get_unread_adherence_reports(doktor_tc, limit=50):
    """Get unread adherence reports for the doctor's patients"""
    conn = connect_database()
    cursor = conn.cursor(dictionary=True)
    
    try:
        cursor.execute("""
        SELECT t.*, h.isim_soyisim as hasta_isim, p.diyet_turu, p.egzersiz_turu
        FROM DiyetEgzersizTakip t
        JOIN DiyetEgzersizPlanlari p ON t.plan_id = p.id
        JOIN Hastalar h ON t.hasta_tc = h.tc_kimlik_no
        WHERE p.doktor_tc = %s AND t.okundu = FALSE
        ORDER BY t.bildirim_zamani DESC
        LIMIT %s
        """, (doktor_tc, limit))
        
        reports = cursor.fetchall()
        return reports
    except Exception as e:
        print(f"Error fetching unread reports: {e}")
        return []
    finally:
        cursor.close()
        conn.close()

def mark_reports_as_read(report_ids):
    """Mark adherence reports as read"""
    if not report_ids:
        return True
        
    conn = connect_database()
    cursor = conn.cursor()
    
    try:
        # Convert list to comma-separated string
        id_list = ','.join(map(str, report_ids))
        
        cursor.execute(f"""
        UPDATE DiyetEgzersizTakip
        SET okundu = TRUE
        WHERE id IN ({id_list})
        """)
        
        conn.commit()
        return True
    except Exception as e:
        print(f"Error marking reports as read: {e}")
        return False
    finally:
        cursor.close()
        conn.close()

# Update this function to use SQL AVG() function directly
def get_patient_first_measurements_average(hasta_tc):
    """Get the average of the patient's first 5 measurements (doctor's initial measurements)"""
    conn = connect_database()
    cursor = conn.cursor(dictionary=True)
    
    try:
        # First check if first measurements exist in IlkOlcumKaydi
        cursor.execute("""
        SELECT olcum_tarihi FROM IlkOlcumKaydi
        WHERE hasta_tc = %s
        """, (hasta_tc,))
        
        result = cursor.fetchone()
        if not result:
            return None, "İlk ölçümler henüz yapılmamış."
        
        olcum_tarihi = result['olcum_tarihi']
        
        # Get average directly from database using SQL AVG function
        # This is more efficient than retrieving all records and calculating in Python
        cursor.execute("""
        SELECT AVG(seker_seviyesi) as ortalama, COUNT(*) as sayi 
        FROM KanSekeriKayitlari
        WHERE tc_kimlik_no = %s AND tarih = %s AND olcum_turu = 'Doktor'
        LIMIT 5
        """, (hasta_tc, olcum_tarihi))
        
        result = cursor.fetchone()
        
        if not result or result['ortalama'] is None:
            return None, "İlk ölçüm kayıtları bulunamadı."
        
        average = float(result['ortalama'])
        count = result['sayi']
        
        return average, f"{count} ölçümün ortalaması: {average:.1f} mg/dL"
    
    except Exception as e:
        return None, f"Ölçüm verileri alınırken hata oluştu: {str(e)}"
    finally:
        cursor.close()
        conn.close()

# UI Components for Doctors
class DiyetEgzersizPlanDialog(QDialog):
    """Dialog for creating a diet and exercise plan for a patient"""
    def __init__(self, hasta_tc, hasta_isim, doktor_tc, parent=None):
        super().__init__(parent)
        self.hasta_tc = hasta_tc
        self.hasta_isim = hasta_isim
        self.doktor_tc = doktor_tc
        
        self.setWindowTitle(f"Diyet ve Egzersiz Planı - {hasta_isim}")
        self.setMinimumWidth(700)  # Increased width for better display
        
        self.arayuz_olustur()
        self.aktif_plani_yukle()
        self.ilk_olcum_ortalamasi_yukle()
    
    def arayuz_olustur(self):
        layout = QVBoxLayout(self)
        
        # Title
        baslik = QLabel(f"{self.hasta_isim} - Diyet ve Egzersiz Planı")
        baslik.setFont(QFont("Arial", 14, QFont.Bold))
        baslik.setAlignment(Qt.AlignCenter)
        layout.addWidget(baslik)
        
        # First measurements info
        self.olcum_bilgi = QLabel("İlk ölçüm bilgisi yükleniyor...")
        self.olcum_bilgi.setAlignment(Qt.AlignCenter)
        self.olcum_bilgi.setStyleSheet("font-size: 16px; font-weight: bold; color: #1976D2;")
        layout.addWidget(self.olcum_bilgi)
        
        # Create tab widget for recommendation options
        self.tab_widget = QTabWidget()
        
        # Tab 1: Auto recommendations based on measurements
        self.auto_tab = QWidget()
        auto_layout = QVBoxLayout(self.auto_tab)
        
        # Container for recommendation options
        self.recommendation_container = QVBoxLayout()
        auto_layout.addLayout(self.recommendation_container)
        
        # Tab 2: Manual recommendation
        self.manual_tab = QWidget()
        manual_layout = QVBoxLayout(self.manual_tab)
        
        # Manual symptom selection
        semptom_grup = QGroupBox("Belirtiler")
        semptom_layout = QVBoxLayout()
        
        # Create checkboxes for symptoms
        self.semptom_checkboxes = {}
        for semptom, aciklama in BELIRTILER.items():
            checkbox = QCheckBox(f"{semptom} ({aciklama})")
            self.semptom_checkboxes[semptom] = checkbox
            semptom_layout.addWidget(checkbox)
        
        semptom_grup.setLayout(semptom_layout)
        manual_layout.addWidget(semptom_grup)
        
        # Diet selection
        diet_group = QGroupBox("Diyet")
        diet_layout = QVBoxLayout()
        
        self.diet_combo = QComboBox()
        for diyet in DIYETLER.keys():
            self.diet_combo.addItem(diyet)
        
        self.diet_description = QTextEdit()
        self.diet_description.setPlaceholderText("Diyet hakkında detaylı açıklama...")
        
        diet_layout.addWidget(self.diet_combo)
        diet_layout.addWidget(self.diet_description)
        diet_group.setLayout(diet_layout)
        manual_layout.addWidget(diet_group)
        
        # Exercise selection
        exercise_group = QGroupBox("Egzersiz")
        exercise_layout = QVBoxLayout()
        
        self.exercise_combo = QComboBox()
        self.exercise_combo.addItem("Yok")
        for egzersiz in EGZERSIZLER.keys():
            self.exercise_combo.addItem(egzersiz)
        
        self.exercise_description = QTextEdit()
        self.exercise_description.setPlaceholderText("Egzersiz hakkında detaylı açıklama...")
        
        exercise_layout.addWidget(self.exercise_combo)
        exercise_layout.addWidget(self.exercise_description)
        exercise_group.setLayout(exercise_layout)
        manual_layout.addWidget(exercise_group)
        
        # Add tabs
        self.tab_widget.addTab(self.auto_tab, "Ölçüme Göre Öneriler")
        self.tab_widget.addTab(self.manual_tab, "Manuel Öneriler")
        
        layout.addWidget(self.tab_widget)
        
        # Common plan details
        plan_grup = QGroupBox("Plan Detayları")
        plan_layout = QFormLayout()
        
        # Date range
        baslangic_layout = QHBoxLayout()
        baslangic_label = QLabel("Başlangıç Tarihi:")
        self.baslangic_date = QDateEdit()
        self.baslangic_date.setDate(QDate.currentDate())
        self.baslangic_date.setCalendarPopup(True)
        baslangic_layout.addWidget(baslangic_label)
        baslangic_layout.addWidget(self.baslangic_date)
        
        bitis_layout = QHBoxLayout()
        bitis_label = QLabel("Bitiş Tarihi:")
        self.bitis_date = QDateEdit()
        self.bitis_date.setDate(QDate.currentDate().addDays(30))  # Default to 30 days
        self.bitis_date.setCalendarPopup(True)
        bitis_layout.addWidget(bitis_label)
        bitis_layout.addWidget(self.bitis_date)
        
        plan_layout.addRow("Tarih Aralığı:", baslangic_layout)
        plan_layout.addRow("", bitis_layout)
        
        # Additional notes
        self.ozel_notlar = QTextEdit()
        self.ozel_notlar.setPlaceholderText("Hasta için özel notlar...")
        plan_layout.addRow("Özel Notlar:", self.ozel_notlar)
        
        plan_grup.setLayout(plan_layout)
        layout.addWidget(plan_grup)
        
        # Buttons
        buton_layout = QHBoxLayout()
        
        iptal_btn = QPushButton("İptal")
        iptal_btn.clicked.connect(self.reject)
        
        kaydet_btn = QPushButton("Planı Kaydet")
        kaydet_btn.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")
        kaydet_btn.clicked.connect(self.plan_kaydet)
        
        buton_layout.addWidget(iptal_btn)
        buton_layout.addWidget(kaydet_btn)
        
        layout.addLayout(buton_layout)
    
    def ilk_olcum_ortalamasi_yukle(self):
        """Load the average of first measurements and update recommendations"""
        average, message = get_patient_first_measurements_average(self.hasta_tc)
        
        if average is not None:
            self.olcum_bilgi.setText(f"İlk Ölçüm Ortalaması: {average:.1f} mg/dL")
            
            # Update recommendations based on average
            self.update_recommendations(average)
        else:
            self.olcum_bilgi.setText(message)
            self.olcum_bilgi.setStyleSheet("color: red; font-weight: bold;")
    
    def update_recommendations(self, average):
        """Update recommendation options based on blood sugar average"""
        # Clear current recommendations
        while self.recommendation_container.count():
            item = self.recommendation_container.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        
        # Filter recommendations based on blood sugar level
        matching_recommendations = []
        
        if average < 70:
            # Hypoglycemia recommendations (2 options)
            blood_sugar_range = "< 70 mg/dL"
            category = "Hipoglisemi"
        elif average <= 110:
            # Low normal recommendations (2 options)
            blood_sugar_range = "70-110 mg/dL"
            category = "Normal - Alt Düzey"
        elif average <= 180:
            # High normal / slightly high recommendations (2 options)
            blood_sugar_range = "110-180 mg/dL"
            category = "Normal - Üst Düzey / Hafif Yüksek"
        else:
            # Hyperglycemia recommendations (2 options)
            blood_sugar_range = "≥ 180 mg/dL" 
            category = "Hiperglisemi"
        
        # Find matching recommendations
        for rec in RECOMMENDATIONS:
            if rec["blood_sugar_range"] == blood_sugar_range:
                matching_recommendations.append(rec)
        
        # Add a category label
        category_label = QLabel(f"<h2>Kan Şekeri Kategorisi: {category} ({blood_sugar_range})</h2>")
        category_label.setAlignment(Qt.AlignCenter)
        self.recommendation_container.addWidget(category_label)
        
        # Add recommendations
        for i, rec in enumerate(matching_recommendations):
            # Create recommendation group
            rec_group = QGroupBox(f"Öneri {i+1}")
            rec_layout = QVBoxLayout()
            
            # Symptoms
            symptoms_label = QLabel("<b>Belirtiler:</b> " + ", ".join(rec["symptoms"]))
            symptoms_label.setWordWrap(True)
            rec_layout.addWidget(symptoms_label)
            
            # Diet
            diet_label = QLabel(f"<b>Diyet:</b> {rec['diet']}")
            diet_description = QLabel(f"<i>{DIYETLER.get(rec['diet'], '')}</i>")
            diet_description.setWordWrap(True)
            rec_layout.addWidget(diet_label)
            rec_layout.addWidget(diet_description)
            
            # Exercise
            exercise_label = QLabel(f"<b>Egzersiz:</b> {rec['exercise']}")
            exercise_description = QLabel(f"<i>{EGZERSIZLER.get(rec['exercise'], '')}</i>")
            exercise_description.setWordWrap(True)
            rec_layout.addWidget(exercise_label)
            rec_layout.addWidget(exercise_description)
            
            # Select button
            select_btn = QPushButton("Bu Öneriyi Seç")
            select_btn.setStyleSheet("background-color: #2196F3; color: white;")
            select_btn.clicked.connect(lambda checked=False, r=rec: self.select_recommendation(r))
            rec_layout.addWidget(select_btn)
            
            rec_group.setLayout(rec_layout)
            self.recommendation_container.addWidget(rec_group)
    
    def select_recommendation(self, recommendation):
        """Select a recommendation and switch to manual tab with prefilled data"""
        # Switch to manual tab
        self.tab_widget.setCurrentIndex(1)
        
        # Clear all symptom checkboxes first
        for checkbox in self.semptom_checkboxes.values():
            checkbox.setChecked(False)
        
        # Check symptoms from recommendation
        for symptom in recommendation["symptoms"]:
            if symptom in self.semptom_checkboxes:
                self.semptom_checkboxes[symptom].setChecked(True)
        
        # Set diet
        index = self.diet_combo.findText(recommendation["diet"])
        if index >= 0:
            self.diet_combo.setCurrentIndex(index)
            self.diet_description.setText(DIYETLER.get(recommendation["diet"], ""))
        
        # Set exercise
        index = self.exercise_combo.findText(recommendation["exercise"])
        if index >= 0:
            self.exercise_combo.setCurrentIndex(index)
            self.exercise_description.setText(EGZERSIZLER.get(recommendation["exercise"], ""))
    
    def aktif_plani_yukle(self):
        """Load active plan if exists"""
        active_plan = get_active_plan(self.hasta_tc)
        
        if active_plan:
            # Show message about existing plan
            QMessageBox.information(
                self,
                "Mevcut Plan",
                f"Hastanın {active_plan['baslangic_tarihi']} - {active_plan['bitis_tarihi']} tarihleri arasında "
                f"aktif bir diyet ve egzersiz planı bulunmaktadır.\n\n"
                f"Diyet: {active_plan['diyet_turu']}\n"
                f"Egzersiz: {active_plan['egzersiz_turu']}\n\n"
                f"Yeni plan oluşturursanız, eskisi aktif olarak kalacaktır."
            )
    
    def plan_kaydet(self):
        """Save the diet and exercise plan"""
        # Get form values
        baslangic_tarihi = self.baslangic_date.date().toPyDate()
        bitis_tarihi = self.bitis_date.date().toPyDate()
        
        # Get values based on active tab
        if self.tab_widget.currentIndex() == 0:  # Auto recommendations tab
            # No recommendation selected, show error
            QMessageBox.warning(self, "Hata", "Lütfen bir öneri seçin veya manuel öneri oluşturun.")
            return
        else:  # Manual tab
            # Get selected symptoms
            selected_symptoms = []
            for symptom, checkbox in self.semptom_checkboxes.items():
                if checkbox.isChecked():
                    selected_symptoms.append(symptom)
            
            # Get diet and exercise
            diyet_turu = self.diet_combo.currentText()
            diyet_aciklama = self.diet_description.toPlainText()
            
            egzersiz_turu = self.exercise_combo.currentText()
            egzersiz_aciklama = self.exercise_description.toPlainText()
        
        ozel_notlar = self.ozel_notlar.toPlainText()
        
        # Add selected symptoms to notes
        if selected_symptoms:
            if ozel_notlar:
                ozel_notlar += "\n\n"
            ozel_notlar += "Belirtiler: " + ", ".join(selected_symptoms)
        
        # Validate input
        if baslangic_tarihi > bitis_tarihi:
            QMessageBox.warning(self, "Hata", "Başlangıç tarihi bitiş tarihinden sonra olamaz.")
            return
        
        # Create plan
        basarili, mesaj = create_plan_for_patient(
            self.hasta_tc, self.doktor_tc, baslangic_tarihi, bitis_tarihi,
            diyet_turu, diyet_aciklama, egzersiz_turu, egzersiz_aciklama, ozel_notlar
        )
        
        if basarili:
            QMessageBox.information(self, "Başarılı", mesaj)
            self.accept()
        else:
            QMessageBox.warning(self, "Hata", mesaj)

class HastaDiyetEgzersizRaporDialog(QDialog):
    """Dialog for viewing a patient's diet and exercise adherence reports"""
    def __init__(self, hasta_tc, hasta_isim, parent=None):
        super().__init__(parent)
        self.hasta_tc = hasta_tc
        self.hasta_isim = hasta_isim
        
        self.setWindowTitle(f"Diyet ve Egzersiz Raporları - {hasta_isim}")
        self.setMinimumWidth(700)
        
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
        
        # Get adherence history
        history = get_patient_adherence_history(self.hasta_tc)
        
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
    
    def okundu_isaretle(self):
        """Mark selected reports as read"""
        selected_rows = set(item.row() for item in self.rapor_tablosu.selectedItems())
        
        if not selected_rows:
            QMessageBox.information(self, "Bilgi", "Lütfen işaretlenecek raporları seçin.")
            return
        
        # Get report IDs from table's rows
        report_ids = []
        for row in selected_rows:
            report_id = self.rapor_tablosu.item(row, 0).data(Qt.UserRole)
            if report_id:
                report_ids.append(report_id)
        
        if mark_reports_as_read(report_ids):
            # Refresh reports
            self.raporlari_yukle()
            QMessageBox.information(self, "Başarılı", "Seçili raporlar okundu olarak işaretlendi.")
        else:
            QMessageBox.warning(self, "Hata", "Raporlar işaretlenirken bir hata oluştu.")

# UI Components for Patients
class HastaDiyetEgzersizWidget(QWidget):
    """Widget for patients to view and track their diet and exercise plan"""
    def __init__(self, hasta_tc, hasta_isim):
        super().__init__()
        self.hasta_tc = hasta_tc
        self.hasta_isim = hasta_isim
        
        self.arayuz_olustur()
        self.plan_yukle()
    
    def arayuz_olustur(self):
        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(12)
        
        # Title with styling
        baslik = QLabel("Diyet ve Egzersiz Takibi")
        baslik.setFont(QFont("Arial", 16, QFont.Bold))
        baslik.setAlignment(Qt.AlignCenter)
        baslik.setStyleSheet("color: #2E7D32; margin-bottom: 10px; border-bottom: 2px solid #81C784; padding-bottom: 8px;")
        main_layout.addWidget(baslik)
        
        # Create horizontal split for top part
        top_layout = QHBoxLayout()
        
        # ===== LEFT PANEL: Plan information, Diet, Exercise, Symptoms =====
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 10, 0)  # Add right margin for spacing
        
        # Plan information with improved styling
        plan_grup = QGroupBox("Diyet ve Egzersiz Planım")
        plan_grup.setStyleSheet("""
            QGroupBox {
                background-color: #E8F5E9;
                border: 2px solid #81C784;
                border-radius: 8px;
                margin-top: 15px;
                font-weight: bold;
            }
            QGroupBox::title {
                background-color: #81C784;
                color: white;
                padding: 5px 10px;
                subcontrol-origin: margin;
                subcontrol-position: top center;
                border-radius: 3px;
            }
        """)
        
        plan_layout = QVBoxLayout()
        plan_layout.setContentsMargins(12, 25, 12, 12)
        
        self.plan_bilgi = QLabel("Plan bilgisi yükleniyor...")
        self.plan_bilgi.setWordWrap(True)
        self.plan_bilgi.setStyleSheet("font-size: 12px; background-color: white; padding: 12px; border-radius: 5px; border: 1px solid #C8E6C9;")
        plan_layout.addWidget(self.plan_bilgi)
        
        # Add symptom section (new)
        semptom_label = QLabel("Belirtileriniz:")
        semptom_label.setFont(QFont("Arial", 11, QFont.Bold))
        semptom_label.setStyleSheet("color: #2E7D32; margin-top: 10px;")
        plan_layout.addWidget(semptom_label)
        
        self.semptom_text = QTextEdit()
        self.semptom_text.setPlaceholderText("Bugün hissettiğiniz belirtileri buraya yazabilirsiniz...")
        self.semptom_text.setStyleSheet("background-color: white; border: 1px solid #E0E0E0; border-radius: 5px; padding: 5px;")
        self.semptom_text.setFixedHeight(60)
        plan_layout.addWidget(self.semptom_text)
        
        plan_grup.setLayout(plan_layout)
        left_layout.addWidget(plan_grup)
        
        # ===== RIGHT PANEL: Notes =====
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(10, 0, 0, 0)  # Add left margin for spacing
        
        # Notes with improved styling
        notlar_grup = QGroupBox("Notlar")
        notlar_grup.setStyleSheet("""
            QGroupBox {
                background-color: #FFF8E1;
                border: 2px solid #FFD54F;
                border-radius: 8px;
                margin-top: 15px;
                font-weight: bold;
            }
            QGroupBox::title {
                background-color: #FFD54F;
                color: #5D4037;
                padding: 5px 10px;
                subcontrol-origin: margin;
                subcontrol-position: top center;
                border-radius: 3px;
            }
        """)
        
        notlar_layout = QVBoxLayout()
        notlar_layout.setContentsMargins(12, 25, 12, 12)
        
        self.notlar_text = QTextEdit()
        self.notlar_text.setPlaceholderText("Bugünkü diyet ve egzersiz ile ilgili notlarınızı buraya yazabilirsiniz...")
        self.notlar_text.setStyleSheet("background-color: white; border: 1px solid #E0E0E0; border-radius: 5px; padding: 5px;")
        notlar_layout.addWidget(self.notlar_text)
        
        notlar_grup.setLayout(notlar_layout)
        right_layout.addWidget(notlar_grup)
        
        # Add panels to top layout
        top_layout.addWidget(left_panel, 6)  # 60% width
        top_layout.addWidget(right_panel, 4)  # 40% width
        
        # Add top layout to main layout
        main_layout.addLayout(top_layout)
        
        # ===== TRACKING: Daily checkboxes and submit button =====
        gunluk_grup = QGroupBox("Bugünkü Takip")
        gunluk_grup.setStyleSheet("""
            QGroupBox {
                background-color: #E3F2FD;
                border: 2px solid #64B5F6;
                border-radius: 8px;
                margin-top: 10px;
                font-weight: bold;
            }
            QGroupBox::title {
                background-color: #64B5F6;
                color: white;
                padding: 5px 10px;
                subcontrol-origin: margin;
                subcontrol-position: top center;
                border-radius: 3px;
            }
        """)
        
        gunluk_layout = QHBoxLayout()
        gunluk_layout.setContentsMargins(15, 25, 15, 15)
        
        # Left side - checkboxes
        check_layout = QVBoxLayout()
        
        # Diet checkbox with improved styling
        self.diyet_check = QCheckBox("Bugün diyet planıma uydum")
        self.diyet_check.setFont(QFont("Arial", 12))
        self.diyet_check.setStyleSheet("QCheckBox { padding: 5px; } QCheckBox::indicator { width: 20px; height: 20px; }")
        check_layout.addWidget(self.diyet_check)
        
        # Exercise checkbox with improved styling
        self.egzersiz_check = QCheckBox("Bugün egzersiz planımı yaptım")
        self.egzersiz_check.setFont(QFont("Arial", 12))
        self.egzersiz_check.setStyleSheet("QCheckBox { padding: 5px; } QCheckBox::indicator { width: 20px; height: 20px; }")
        check_layout.addWidget(self.egzersiz_check)
        
        # Right side - submit button
        submit_layout = QVBoxLayout()
        submit_layout.setAlignment(Qt.AlignCenter)
        
        # Submit button with improved styling
        gonder_btn = QPushButton("Bilgileri Gönder")
        gonder_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50; 
                color: white; 
                font-weight: bold;
                padding: 12px;
                border-radius: 5px;
                font-size: 13px;
                min-width: 150px;
            }
            QPushButton:hover {
                background-color: #388E3C;
            }
        """)
        gonder_btn.clicked.connect(self.bilgileri_gonder)
        submit_layout.addWidget(gonder_btn)
        
        # Info text with improved styling
        bilgi_label = QLabel("Bilgileriniz doktorunuza iletilecektir.")
        bilgi_label.setStyleSheet("color: #757575; font-style: italic; margin-top: 5px;")
        bilgi_label.setAlignment(Qt.AlignCenter)
        submit_layout.addWidget(bilgi_label)
        
        # Add to layout
        gunluk_layout.addLayout(check_layout, 7)  # 70% width
        gunluk_layout.addLayout(submit_layout, 3)  # 30% width
        
        gunluk_grup.setLayout(gunluk_layout)
        main_layout.addWidget(gunluk_grup)
        
        # ===== HISTORY: Past diet and exercise status =====
        gecmis_grup = QGroupBox("Geçmiş Takiplerim")
        gecmis_grup.setStyleSheet("""
            QGroupBox {
                background-color: #F3E5F5;
                border: 2px solid #BA68C8;
                border-radius: 8px;
                margin-top: 10px;
                font-weight: bold;
            }
            QGroupBox::title {
                background-color: #BA68C8;
                color: white;
                padding: 5px 10px;
                subcontrol-origin: margin;
                subcontrol-position: top center;
                border-radius: 3px;
            }
        """)
        
        gecmis_layout = QVBoxLayout()
        gecmis_layout.setContentsMargins(15, 25, 15, 15)
        
        self.gecmis_tablosu = QTableWidget()
        self.gecmis_tablosu.setColumnCount(4)
        self.gecmis_tablosu.setHorizontalHeaderLabels([
            "Tarih", "Diyet Yapıldı", "Egzersiz Yapıldı", "Notlar"
        ])
        self.gecmis_tablosu.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.gecmis_tablosu.setStyleSheet("""
            QTableWidget {
                background-color: white;
                gridline-color: #E0E0E0;
                border: 1px solid #BDBDBD;
                border-radius: 5px;
            }
            QHeaderView::section {
                background-color: #CE93D8;
                color: white;
                font-weight: bold;
                border: none;
                padding: 6px;
            }
            QTableWidget::item {
                padding: 5px;
            }
        """)
        
        # Set maximum height for history table
        self.gecmis_tablosu.setMaximumHeight(150)
        
        gecmis_layout.addWidget(self.gecmis_tablosu)
        
        # Add refresh button in a horizontal layout
        btn_layout = QHBoxLayout()
        btn_layout.setAlignment(Qt.AlignRight)
        
        yenile_btn = QPushButton("Geçmiş Takipleri Yenile")
        yenile_btn.setStyleSheet("""
            QPushButton {
                background-color: #9C27B0; 
                color: white; 
                font-weight: bold;
                padding: 8px;
                border-radius: 5px;
                max-width: 200px;
            }
            QPushButton:hover {
                background-color: #7B1FA2;
            }
        """)
        yenile_btn.clicked.connect(self.gecmis_yukle)
        btn_layout.addWidget(yenile_btn)
        
        gecmis_layout.addLayout(btn_layout)
        
        gecmis_grup.setLayout(gecmis_layout)
        main_layout.addWidget(gecmis_grup)
        
        # Add a spacer at the bottom
        main_layout.addStretch(1)
    
    def plan_yukle(self):
        """Load the active diet and exercise plan"""
        active_plan = get_active_plan(self.hasta_tc)
        
        if active_plan:
            self.plan_bilgi.setText(
                f"Plan Tarihleri: {active_plan['baslangic_tarihi'].strftime('%d.%m.%Y')} - "
                f"{active_plan['bitis_tarihi'].strftime('%d.%m.%Y')}\n\n"
                f"Diyet Türü: {active_plan['diyet_turu']}\n"
                f"Diyet Açıklaması: {active_plan['diyet_aciklama']}\n\n"
                f"Egzersiz Türü: {active_plan['egzersiz_turu']}\n"
                f"Egzersiz Açıklaması: {active_plan['egzersiz_aciklama']}\n\n"
                f"Doktor Notları: {active_plan['ozel_notlar'] if active_plan['ozel_notlar'] else 'Yok'}"
            )
            
            # Enable adherence inputs
            self.diyet_check.setEnabled(True)
            self.egzersiz_check.setEnabled(True)
            self.notlar_text.setEnabled(True)
        else:
            self.plan_bilgi.setText(
                "Şu anda aktif bir diyet ve egzersiz planınız bulunmamaktadır.\n"
                "Lütfen doktorunuzla iletişime geçerek bir plan oluşturmasını talep edin."
            )
            
            # Disable adherence inputs
            self.diyet_check.setEnabled(False)
            self.egzersiz_check.setEnabled(False)
            self.notlar_text.setEnabled(False)
        
        # Load history
        self.gecmis_yukle()
        
        # Check if already reported today
        self.bugun_rapor_kontrol()
    
    def bugun_rapor_kontrol(self):
        """Check if the patient has already reported for today"""
        conn = connect_database()
        cursor = conn.cursor(dictionary=True)
        
        try:
            today = date.today()
            
            cursor.execute("""
            SELECT * FROM DiyetEgzersizTakip
            WHERE hasta_tc = %s AND tarih = %s
            """, (self.hasta_tc, today))
            
            today_report = cursor.fetchone()
            
            if today_report:
                # Already reported today, set values
                self.diyet_check.setChecked(today_report['diyet_yapildi'])
                self.egzersiz_check.setChecked(today_report['egzersiz_yapildi'])
                
                if today_report['notlar']:
                    self.notlar_text.setText(today_report['notlar'])
        except Exception as e:
            print(f"Error checking today's report: {e}")
        finally:
            cursor.close()
            conn.close()
    
    def gecmis_yukle(self):
        """Load the patient's adherence history"""
        history = get_patient_adherence_history(self.hasta_tc)
        
        # Clear table
        self.gecmis_tablosu.setRowCount(0)
        
        # Fill table with history - improved visual indicators
        for i, report in enumerate(history):
            self.gecmis_tablosu.insertRow(i)
            
            # Date with better formatting
            tarih_item = QTableWidgetItem(report['tarih'].strftime("%d.%m.%Y"))
            tarih_item.setTextAlignment(Qt.AlignCenter)
            self.gecmis_tablosu.setItem(i, 0, tarih_item)
            
            # Diet status with icons
            diyet_item = QTableWidgetItem()
            if report['diyet_yapildi']:
                diyet_item.setText("✓")
                diyet_item.setForeground(Qt.darkGreen)
            else:
                diyet_item.setText("✗")
                diyet_item.setForeground(Qt.red)
            diyet_item.setTextAlignment(Qt.AlignCenter)
            self.gecmis_tablosu.setItem(i, 1, diyet_item)
            
            # Exercise status with icons
            egzersiz_item = QTableWidgetItem()
            if report['egzersiz_yapildi']:
                egzersiz_item.setText("✓")
                egzersiz_item.setForeground(Qt.darkGreen)
            else:
                egzersiz_item.setText("✗")
                egzersiz_item.setForeground(Qt.red)
            egzersiz_item.setTextAlignment(Qt.AlignCenter)
            self.gecmis_tablosu.setItem(i, 2, egzersiz_item)
            
            # Notes
            notlar_item = QTableWidgetItem(report['notlar'] if report['notlar'] else "-")
            self.gecmis_tablosu.setItem(i, 3, notlar_item)
            
            # Alternate row colors for better readability
            if i % 2 == 0:
                for col in range(4):
                    self.gecmis_tablosu.item(i, col).setBackground(QColor("#F5F5F5"))
    
    def bilgileri_gonder(self):
        """Send diet and exercise adherence information"""
        # Check if there's an active plan
        active_plan = get_active_plan(self.hasta_tc)
        if not active_plan:
            QMessageBox.warning(
                self,
                "Uyarı",
                "Aktif bir diyet ve egzersiz planınız bulunmamaktadır.\n"
                "Lütfen doktorunuzla iletişime geçerek bir plan oluşturmasını talep edin."
            )
            return
        
        # Get form values
        diyet_yapildi = self.diyet_check.isChecked()
        egzersiz_yapildi = self.egzersiz_check.isChecked()
        notlar = self.notlar_text.toPlainText()
        
        # Record adherence
        basarili, mesaj = record_daily_adherence(self.hasta_tc, diyet_yapildi, egzersiz_yapildi, notlar)
        
        if basarili:
            QMessageBox.information(self, "Başarılı", mesaj)
            # Refresh history
            self.gecmis_yukle()
        else:
            QMessageBox.warning(self, "Hata", mesaj)

def ensure_diet_exercise_tables_exist():
    """Make sure the diet and exercise tracking tables exist before using them"""
    conn = connect_database()
    cursor = conn.cursor()
    
    try:
        # Create DiyetEgzersizPlanlari table if it doesn't exist
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS DiyetEgzersizPlanlari (
            id INT AUTO_INCREMENT PRIMARY KEY,
            hasta_tc CHAR(11) NOT NULL,
            doktor_tc CHAR(11) NOT NULL,
            baslangic_tarihi DATE NOT NULL,
            bitis_tarihi DATE NOT NULL,
            diyet_turu VARCHAR(100) NOT NULL,
            diyet_aciklama TEXT,
            egzersiz_turu VARCHAR(100),
            egzersiz_aciklama TEXT,
            ozel_notlar TEXT,
            olusturma_zamani DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (hasta_tc) REFERENCES Hastalar(tc_kimlik_no) ON DELETE CASCADE,
            FOREIGN KEY (doktor_tc) REFERENCES Doktorlar(tc_kimlik_no) ON DELETE CASCADE,
            INDEX (hasta_tc),
            INDEX (doktor_tc)
        ) CHARACTER SET utf8mb4 COLLATE utf8mb4_turkish_ci;
        """)
        
        # Create DiyetEgzersizTakip table if it doesn't exist
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS DiyetEgzersizTakip (
            id INT AUTO_INCREMENT PRIMARY KEY,
            plan_id INT NOT NULL,
            hasta_tc CHAR(11) NOT NULL,
            tarih DATE NOT NULL,
            diyet_yapildi BOOLEAN DEFAULT FALSE,
            egzersiz_yapildi BOOLEAN DEFAULT FALSE,
            notlar TEXT,
            bildirim_zamani DATETIME DEFAULT CURRENT_TIMESTAMP,
            okundu BOOLEAN DEFAULT FALSE,
            FOREIGN KEY (plan_id) REFERENCES DiyetEgzersizPlanlari(id) ON DELETE CASCADE,
            FOREIGN KEY (hasta_tc) REFERENCES Hastalar(tc_kimlik_no) ON DELETE CASCADE,
            UNIQUE (hasta_tc, tarih),
            INDEX (hasta_tc),
            INDEX (tarih)
        ) CHARACTER SET utf8mb4 COLLATE utf8mb4_turkish_ci;
        """)
        
        conn.commit()
        return True
    except Exception as e:
        print(f"Error ensuring diet and exercise tables exist: {e}")
        return False
    finally:
        cursor.close()
        conn.close()

# Call this function when the module is imported
ensure_diet_exercise_tables_exist()
