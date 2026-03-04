from PyQt5.QtCore import QDateTime, Qt
from PyQt5.QtGui import QPixmap, QImage
import locale

# Try to set Turkish locale for date/time formatting
def set_turkish_locale():
    """Set up Turkish locale for date/time formatting"""
    import locale
    try:
        locale.setlocale(locale.LC_ALL, 'tr_TR.UTF-8')
    except locale.Error:
        try:
            locale.setlocale(locale.LC_ALL, 'Turkish_Turkey.1254')
        except locale.Error:
            # If Turkish locale is not available, use default
            locale.setlocale(locale.LC_ALL, '')

# Convert English day names to Turkish
def gun_cevirici(ingilizce_gun):
    gun_ceviri = {
        "monday": "Pazartesi",
        "tuesday": "Salı",
        "wednesday": "Çarşamba",
        "thursday": "Perşembe",
        "friday": "Cuma",
        "saturday": "Cumartesi",
        "sunday": "Pazar"
    }
    return gun_ceviri.get(ingilizce_gun.lower(), ingilizce_gun)

# Format a QDateTime object to Turkish date string (DD.MM.YYYY)
def tarih_formatla(qdatetime):
    gun = gun_cevirici(qdatetime.toString('dddd'))
    tarih = qdatetime.toString('dd.MM.yyyy')
    return f"{gun}, {tarih}"

# Format a QDateTime object to 24-hour time string (HH:MM)
def saat_formatla(qdatetime):
    return qdatetime.toString('HH:mm')

# Format date for display in the application (DD.MM.YYYY)
def tarih_goruntu_formatla(tarih):
    """Format a date object to DD.MM.YYYY string for display"""
    return tarih.strftime('%d.%m.%Y')

# Format time for display in the application (24-hour format HH:MM)
def saat_goruntu_formatla(saat_obj):
    """
    Format a time object for display
    
    Args:
        saat_obj: Time object (can be time, datetime, timedelta or string)
        
    Returns:
        str: Formatted time string
    """
    from datetime import time, timedelta
    
    if isinstance(saat_obj, time):
        return saat_obj.strftime('%H:%M')
    elif isinstance(saat_obj, timedelta):
        total_seconds = int(saat_obj.total_seconds())
        hours, remainder = divmod(total_seconds, 3600)
        minutes, _ = divmod(remainder, 60)
        return f"{hours:02d}:{minutes:02d}"
    elif isinstance(saat_obj, str):
        # Try to extract just the time part if it's a string
        if len(saat_obj) >= 5:
            return saat_obj[:5]  # Take first 5 chars (HH:MM)
        return saat_obj
    else:
        return "—"

# Create a rounded profile photo from pixmap
def yuvarlak_foto_olustur(pixmap, size=200):
    # Create a rounded mask for the profile photo
    output = QPixmap(size, size)
    output.fill(Qt.transparent)
    
    # Scale the input pixmap
    scaled_pixmap = pixmap.scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
    
    # TODO: Create circular mask with QPainter
    
    return scaled_pixmap

def open_report_dialog(tc_kimlik_no, isim_soyisim, doktor_tc=None, parent=None):
    """
    Open the comprehensive blood sugar report dialog
    
    Args:
        tc_kimlik_no: Patient's TC number
        isim_soyisim: Patient's name
        doktor_tc: Doctor's TC number (optional)
        parent: Parent widget
        
    Returns:
        None
    """
    try:
        from SekerRaporDialog import SekerRaporDialog
        
        dialog = SekerRaporDialog(tc_kimlik_no, isim_soyisim, doktor_tc, parent)
        
        # Set initial tab to graph view
        dialog.tab_widget.setCurrentIndex(1)
        
        # Update graphs
        dialog.update_blood_sugar_graph()
        dialog.update_weekly_graph()
        
        dialog.exec_()
    except Exception as e:
        from PyQt5.QtWidgets import QMessageBox
        QMessageBox.warning(parent, "Hata", f"Kan şekeri raporları yüklenirken hata oluştu: {str(e)}")

def format_time_safely(time_value):
    """
    Safely format a time value regardless of its type (time, timedelta, etc.)
    Returns a formatted string like "HH:MM"
    """
    if time_value is None:
        return "-"
    
    try:
        # If it has strftime method (datetime.time objects)
        if hasattr(time_value, 'strftime'):
            return time_value.strftime('%H:%M')
        
        # If it's a timedelta object (has total_seconds method)
        elif hasattr(time_value, 'total_seconds'):
            total_seconds = int(time_value.total_seconds())
            hours, remainder = divmod(total_seconds, 3600)
            minutes = remainder // 60
            return f"{hours:02d}:{minutes:02d}"
        
        # If it's something else, convert to string
        else:
            return str(time_value)
    except Exception:
        # If all else fails, just return a dash
        return "-"
