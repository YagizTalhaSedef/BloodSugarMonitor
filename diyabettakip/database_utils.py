"""
Database Utility Module for Diyabet Takip Sistemi

This module combines table creation and database checking functionality.
It provides tools to:
- Create database tables with appropriate structure
- Check database integrity
- Repair tables if needed
- Verify and add missing columns
"""
import mysql.connector
from datetime import datetime, timedelta
import sys

# Import config
try:
    from config import DB_HOST, DB_USER, DB_PASSWORD, DB_NAME, DB_CHARSET
except ImportError:
    DB_HOST = "localhost"
    DB_USER = "root"
    DB_PASSWORD = "YOUR_PASSWORD"
    DB_NAME = "diyabet"
    DB_CHARSET = "utf8mb4"

# Database connection functions
def connect_database():
    """Connect to the database with error handling"""
    try:
        conn = mysql.connector.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME,
            charset=DB_CHARSET
        )
        return conn
    except mysql.connector.Error as e:
        print(f"Database connection error: {e}")
        return None
    except Exception as e:
        print(f"Unexpected error: {e}")
        return None

def create_database_if_not_exists():
    """Create the database if it doesn't exist"""
    try:
        conn = mysql.connector.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD
        )
        cursor = conn.cursor()
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {DB_NAME} CHARACTER SET utf8mb4 COLLATE utf8mb4_turkish_ci;")
        conn.commit()
        cursor.close()
        conn.close()
        print(f"Database '{DB_NAME}' checked/created successfully.")
        return True
    except mysql.connector.Error as e:
        print(f"Database creation error: {e}")
        return False

# Table creation function from database.py
def create_tables():
    """Create all required tables if they don't exist"""
    conn = None
    cursor = None
    
    try:
        conn = connect_database()
        if not conn:
            return False
            
        cursor = conn.cursor()

        # Create tables in the correct order for foreign keys
        # First, create tables with no dependencies
        
        # Doktorlar tablosu (no foreign keys)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS Doktorlar (
            tc_kimlik_no CHAR(11) PRIMARY KEY,
            sifre VARCHAR(64) NOT NULL, 
            isim_soyisim VARCHAR(100) NOT NULL,
            cinsiyet CHAR(1),
            mail VARCHAR(100),
            uzmanlik VARCHAR(100),
            profil_foto LONGBLOB NULL
        ) CHARACTER SET utf8mb4 COLLATE utf8mb4_turkish_ci;
        """)

        # Kullanicilar tablosu (no foreign keys)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS Kullanicilar (
            tc_kimlik_no CHAR(11) PRIMARY KEY,
            ad VARCHAR(50),
            soyad VARCHAR(50),
            dogum_tarihi DATE,
            cinsiyet CHAR(1),
            sifre VARCHAR(64)
        ) CHARACTER SET utf8mb4 COLLATE utf8mb4_turkish_ci;
        """)

        # Hastalar tablosu - depends on Doktorlar
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS Hastalar (
            tc_kimlik_no CHAR(11) PRIMARY KEY,
            sifre VARCHAR(64) NOT NULL,
            isim_soyisim VARCHAR(100) NOT NULL,
            cinsiyet CHAR(1),
            mail VARCHAR(100),
            doktor_tc CHAR(11),
            kayit_tarihi DATETIME DEFAULT CURRENT_TIMESTAMP,
            son_giris_tarihi DATETIME,
            gecerlimi BOOLEAN DEFAULT TRUE,  
            profil_foto LONGBLOB NULL,
            FOREIGN KEY (doktor_tc) REFERENCES Doktorlar(tc_kimlik_no) ON DELETE SET NULL
        ) CHARACTER SET utf8mb4 COLLATE utf8mb4_turkish_ci;
        """)

        # Now create tables that depend on Hastalar
        
        # Kan Şekeri Kayıtları - depends on Hastalar
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS KanSekeriKayitlari (
            id INT AUTO_INCREMENT PRIMARY KEY,
            tc_kimlik_no CHAR(11),
            tarih DATE NOT NULL COMMENT 'YYYY-MM-DD format',
            saat TIME NOT NULL COMMENT 'HH:MM:SS 24-hour format',
            olcum_zamani ENUM('Sabah', 'Ogle', 'Ikindi', 'Aksam', 'Gece') NOT NULL,
            seker_seviyesi DECIMAL(5,2) NOT NULL,
            olcum_turu VARCHAR(20) DEFAULT 'Hasta',
            zaman_uygun BOOLEAN DEFAULT FALSE,
            seviye_durumu ENUM('Dusuk', 'Normal', 'Orta', 'Yuksek', 'CokYuksek'),
            insülin_onerisi DECIMAL(3,1) DEFAULT 0,
            ortalamaya_dahil BOOLEAN DEFAULT TRUE,
            doktor_tc CHAR(11),
            FOREIGN KEY (tc_kimlik_no) REFERENCES Hastalar(tc_kimlik_no) ON DELETE CASCADE,
            FOREIGN KEY (doktor_tc) REFERENCES Doktorlar(tc_kimlik_no) ON DELETE SET NULL
        ) CHARACTER SET utf8mb4 COLLATE utf8mb4_turkish_ci;
        """)

        # İlk Ölçüm Kaydı tablosu - depends on Hastalar and Doktorlar
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS IlkOlcumKaydi (
            hasta_tc CHAR(11) PRIMARY KEY,
            doktor_tc CHAR(11) NOT NULL,
            olcum_tarihi DATE NOT NULL COMMENT 'YYYY-MM-DD format',
            FOREIGN KEY (hasta_tc) REFERENCES Hastalar(tc_kimlik_no) ON DELETE CASCADE,
            FOREIGN KEY (doktor_tc) REFERENCES Doktorlar(tc_kimlik_no) ON DELETE CASCADE
        ) CHARACTER SET utf8mb4 COLLATE utf8mb4_turkish_ci;
        """)

        # İnsülin Kayıtları tablosu
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS InsulinKayitlari (
            id INT AUTO_INCREMENT PRIMARY KEY,
            hasta_tc CHAR(11),
            doktor_tc CHAR(11),
            tarih DATE NOT NULL,
            doz DECIMAL(3,1) NOT NULL COMMENT 'ml cinsinden insülin dozu',
            kullanildi BOOLEAN DEFAULT NULL COMMENT 'NULL:Belirtilmemiş, 0:Kullanılmadı, 1:Kullanıldı',
            okundu BOOLEAN DEFAULT FALSE COMMENT 'Doktor tarafından okundu mu',
            FOREIGN KEY (hasta_tc) REFERENCES Hastalar(tc_kimlik_no) ON DELETE CASCADE,
            FOREIGN KEY (doktor_tc) REFERENCES Doktorlar(tc_kimlik_no) ON DELETE SET NULL
        ) CHARACTER SET utf8mb4 COLLATE utf8mb4_turkish_ci;
        """)

        # Uyarılar tablosu - depends on Hastalar and Doktorlar
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS Uyarilar (
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
        print("Tables checked/created successfully.")
        return True
        
    except mysql.connector.Error as e:
        print(f"Error creating tables: {e}")
        return False
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

# Database checking functions from database_checker.py
def check_database_structure():
    """Check if database structure is intact and report issues"""
    conn = None
    cursor = None
    
    try:
        conn = connect_database()
        if not conn:
            return False
            
        cursor = conn.cursor()
        
        # Check if essential tables exist
        print("Checking database tables structure...")
        
        essential_tables = ["Doktorlar", "Hastalar", "KanSekeriKayitlari", "IlkOlcumKaydi", "Uyarilar", "InsulinKayitlari"]
        
        # Get all tables
        cursor.execute("SHOW TABLES")
        tables = [table[0] for table in cursor.fetchall()]
        
        print(f"\nDatabase contains {len(tables)} tables:")
        for table in tables:
            print(f"  - {table}")
        
        # Check missing tables
        missing_tables = [table for table in essential_tables if table not in tables]
        if missing_tables:
            print(f"\n⚠️ Missing tables: {', '.join(missing_tables)}")
            print("These tables will be created when the application runs.")
        else:
            print("\n✓ All essential tables exist")
        
        # Check table structures
        print("\nChecking table structures:")
        for table in tables:
            try:
                cursor.execute(f"DESCRIBE {table}")
                columns = cursor.fetchall()
                print(f"  ✓ {table}: {len(columns)} columns")
            except Exception as e:
                print(f"  ❌ {table}: Error - {e}")
        
        # Check data
        print("\nChecking data in tables:")
        for table in tables:
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                print(f"  - {table}: {count} records")
            except Exception as e:
                print(f"  ❌ {table}: Error - {e}")
        
        return len(missing_tables) == 0
        
    except Exception as e:
        print(f"Error checking database structure: {e}")
        return False
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

def fix_kan_sekeri_table():
    """Repair KanSekeriKayitlari table structure"""
    conn = None
    cursor = None
    
    try:
        conn = connect_database()
        if not conn:
            return False, "Failed to connect to database"
            
        cursor = conn.cursor()
        
        try:
            # Check if table exists
            cursor.execute("SHOW TABLES LIKE 'KanSekeriKayitlari'")
            table_exists = cursor.fetchone()
            
            if table_exists:
                # Check if doktor_tc column exists
                cursor.execute("SHOW COLUMNS FROM KanSekeriKayitlari LIKE 'doktor_tc'")
                column_exists = cursor.fetchone()
                
                if not column_exists:
                    print("KanSekeriKayitlari table is missing doktor_tc column, adding it...")
                    cursor.execute("""
                    ALTER TABLE KanSekeriKayitlari
                    ADD COLUMN doktor_tc CHAR(11),
                    ADD FOREIGN KEY (doktor_tc) REFERENCES Doktorlar(tc_kimlik_no) ON DELETE SET NULL
                    """)
                    print("Added doktor_tc column to KanSekeriKayitlari table")
                else:
                    print("KanSekeriKayitlari table already has doktor_tc column")
                
                # Update missing doktor_tc values
                cursor.execute("""
                UPDATE KanSekeriKayitlari k
                JOIN Hastalar h ON k.tc_kimlik_no = h.tc_kimlik_no
                SET k.doktor_tc = h.doktor_tc
                WHERE k.doktor_tc IS NULL AND h.doktor_tc IS NOT NULL
                """)
                rows_updated = cursor.rowcount
                conn.commit()
                print(f"{rows_updated} records updated with doktor_tc values")
                
                return True, "KanSekeriKayitlari table checked/fixed successfully"
            else:
                print("KanSekeriKayitlari table doesn't exist, will be created later")
                return False, "Table doesn't exist"
                
        except Exception as e:
            print(f"Error checking/fixing KanSekeriKayitlari: {e}")
            return False, f"Error: {e}"
            
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

def fix_uyarilar_table():
    """Fix structure of the Uyarilar table"""
    conn = None
    cursor = None
    
    try:
        conn = connect_database()
        if not conn:
            return False, "Failed to connect to database"
            
        cursor = conn.cursor()
        
        try:
            # Check if table exists
            cursor.execute("SHOW TABLES LIKE 'Uyarilar'")
            table_exists = cursor.fetchone()
            
            if table_exists:
                # Check if okundu column exists
                cursor.execute("SHOW COLUMNS FROM Uyarilar LIKE 'okundu'")
                column_exists = cursor.fetchone()
                
                if not column_exists:
                    print("Uyarilar table is missing okundu column, adding it...")
                    cursor.execute("ALTER TABLE Uyarilar ADD COLUMN okundu BOOLEAN DEFAULT FALSE")
                    print("Added okundu column to Uyarilar table")
                else:
                    print("Uyarilar table already has okundu column")
                    
                # Check if seker_seviyesi column exists
                cursor.execute("SHOW COLUMNS FROM Uyarilar LIKE 'seker_seviyesi'")
                column_exists = cursor.fetchone()
                
                if not column_exists:
                    print("Uyarilar table is missing seker_seviyesi column, adding it...")
                    cursor.execute("ALTER TABLE Uyarilar ADD COLUMN seker_seviyesi DECIMAL(5,2) NULL")
                    print("Added seker_seviyesi column to Uyarilar table")
                
                conn.commit()
                return True, "Uyarilar table checked/fixed successfully"
            else:
                print("Uyarilar table doesn't exist, will be created later")
                return False, "Table doesn't exist"
                
        except Exception as e:
            print(f"Error checking/fixing Uyarilar table: {e}")
            return False, f"Error: {e}"
            
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

def fix_insulin_kayitlari_table():
    """Check and fix InsulinKayitlari table structure"""
    conn = None
    cursor = None
    
    try:
        conn = connect_database()
        if not conn:
            return False, "Failed to connect to database"
            
        cursor = conn.cursor()
        
        try:
            # Check if table exists
            cursor.execute("SHOW TABLES LIKE 'InsulinKayitlari'")
            table_exists = cursor.fetchone()
            
            if table_exists:
                # Check if saat column exists
                cursor.execute("SHOW COLUMNS FROM InsulinKayitlari LIKE 'saat'")
                column_exists = cursor.fetchone()
                
                if not column_exists:
                    print("InsulinKayitlari table is missing saat column, adding it...")
                    cursor.execute("ALTER TABLE InsulinKayitlari ADD COLUMN saat TIME DEFAULT NULL COMMENT 'İnsülin kullanım saati' AFTER tarih")
                    print("Added saat column to InsulinKayitlari table")
                else:
                    print("InsulinKayitlari table already has saat column")
                
                # Add a helper function to convert timedelta to string format safely
                # This helps avoid the strftime error with TIME fields
                cursor.execute("""
                CREATE OR REPLACE FUNCTION format_time_safely(t TIME) 
                RETURNS VARCHAR(8) DETERMINISTIC
                RETURN TIME_FORMAT(t, '%H:%i:%s')
                """)
                print("Created time formatting helper function")
                
                conn.commit()
                return True, "InsulinKayitlari table checked/fixed successfully"
            else:
                print("InsulinKayitlari table doesn't exist, will be created later")
                return False, "Table doesn't exist"
                
        except Exception as e:
            print(f"Error checking/fixing InsulinKayitlari: {e}")
            return False, f"Error: {e}"
            
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

def check_missing_warnings():
    """Check for missing warnings based on insufficient measurements"""
    conn = None
    cursor = None
    
    try:
        conn = connect_database()
        if not conn:
            return False, "Failed to connect to database"
            
        cursor = conn.cursor()
        
        try:
            # Get recent dates with insufficient measurements
            end_date = datetime.now().date()
            start_date = end_date - timedelta(days=7)
            
            cursor.execute("""
            SELECT 
                k.tc_kimlik_no, 
                h.doktor_tc,
                h.isim_soyisim,
                k.tarih, 
                COUNT(*) as olcum_sayisi
            FROM 
                KanSekeriKayitlari k
            JOIN 
                Hastalar h ON k.tc_kimlik_no = h.tc_kimlik_no
            WHERE 
                k.tarih BETWEEN %s AND %s
            GROUP BY 
                k.tc_kimlik_no, k.tarih
            HAVING 
                COUNT(*) < 3
            ORDER BY 
                k.tarih DESC
            """, (start_date, end_date))
            
            insufficient_measurements = cursor.fetchall()
            
            if insufficient_measurements:
                print(f"\nFound {len(insufficient_measurements)} days with insufficient measurements:")
                for tc, doktor_tc, name, day, count in insufficient_measurements:
                    print(f"  - {name}: {day} ({count} measurements)")
                    
                    # Check if warning already exists
                    cursor.execute("""
                    SELECT COUNT(*) FROM Uyarilar 
                    WHERE tc_kimlik_no = %s AND DATE(tarih_zaman) = %s AND uyari_tipi = 'OlcumYetersiz'
                    """, (tc, day))
                    
                    warning_exists = cursor.fetchone()[0] > 0
                    
                    if not warning_exists:
                        print(f"    Creating warning for {name} on {day}")
                        
                        message = f"Hasta {name} {day.strftime('%d.%m.%Y')} tarihinde sadece {count} kan şekeri ölçümü yaptı. " \
                                f"Hastanın günlük kan şekeri ölçüm sayısı yetersiz (<3). Durum izlenmelidir."
                        
                        # Create warning
                        cursor.execute("""
                        INSERT INTO Uyarilar (tc_kimlik_no, doktor_tc, uyari_tipi, aciklama)
                        VALUES (%s, %s, %s, %s)
                        """, (tc, doktor_tc, 'OlcumYetersiz', message))
                    else:
                        print(f"    Warning already exists for {name} on {day}")
                
                conn.commit()
                return True, "Missing warnings checked and created"
            else:
                print("No days with insufficient measurements found")
                return True, "No missing warnings needed"
                
        except Exception as e:
            print(f"Error checking missing warnings: {e}")
            return False, f"Error: {e}"
            
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

def check_and_add_patient_physical_data_columns():
    """Check and add physical data columns to Hastalar table if they don't exist"""
    conn = None
    cursor = None
    
    try:
        conn = connect_database()
        if not conn:
            return False, "Failed to connect to database"
            
        cursor = conn.cursor()
        
        # Check for each column and add if missing
        columns_to_check = [
            ("yas", "INT NULL"),
            ("boy", "INT NULL COMMENT 'Boy (cm cinsinden)'"),
            ("kilo", "DECIMAL(5,2) NULL COMMENT 'Kilo (kg cinsinden)'"),
            ("vki", "DECIMAL(4,2) NULL COMMENT 'Vücut Kitle İndeksi'")
        ]
        
        for column_name, column_def in columns_to_check:
            cursor.execute(f"SHOW COLUMNS FROM Hastalar LIKE '{column_name}'")
            column_exists = cursor.fetchone()
            
            if not column_exists:
                print(f"Hastalar table is missing {column_name} column, adding it...")
                cursor.execute(f"ALTER TABLE Hastalar ADD COLUMN {column_name} {column_def}")
                print(f"Added {column_name} column to Hastalar table")
        
        conn.commit()
        return True, "Patient physical data columns checked/added successfully"
                
    except Exception as e:
        print(f"Error checking/adding patient physical data columns: {e}")
        return False, f"Error: {e}"
            
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

# Combined initialization function
def initialize_database():
    """Initialize database: create if needed, check structure, fix issues"""
    print("="*50)
    print("Diyabet Takip Sistemi - Database Initialization")
    print("="*50)
    
    # Step 1: Create database if it doesn't exist
    if not create_database_if_not_exists():
        print("Failed to create database!")
        return False
    
    # Step 2: Create tables if they don't exist
    if not create_tables():
        print("Failed to create tables!")
        return False
    
    # Step 3: Check database structure
    print("\n" + "="*50)
    print("Database Structure Check")
    print("="*50)
    check_database_structure()
    
    # Step 4: Fix known issues
    print("\n" + "="*50)
    print("Fixing Known Issues")
    print("="*50)
    fix_kan_sekeri_table()
    fix_uyarilar_table()
    fix_insulin_kayitlari_table()  # Add this line
    check_and_add_patient_physical_data_columns()
    
    # Step 5: Check for missing warnings
    print("\n" + "="*50)
    print("Checking Missing Warnings")
    print("="*50)
    check_missing_warnings()
    
    print("\n" + "="*50)
    print("Database initialization complete")
    print("="*50)
    return True

# Run as standalone script
if __name__ == "__main__":
    print("Database Utility for Diyabet Takip Sistemi")
    print("-" * 50)
    print("1. Initialize database (create and check)")
    print("2. Check database structure only")
    print("3. Fix KanSekeriKayitlari table")
    print("4. Fix Uyarilar table")
    print("5. Check for missing warnings")
    print("0. Exit")
    
    choice = input("\nSelect an option: ")
    
    if choice == '1':
        initialize_database()
    elif choice == '2':
        check_database_structure()
    elif choice == '3':
        fix_kan_sekeri_table()
    elif choice == '4':
        fix_uyarilar_table()
    elif choice == '5':
        check_missing_warnings()
    elif choice == '0':
        sys.exit(0)
    else:
        print("Invalid option!")
