import sys
from PyQt5.QtWidgets import QApplication
import ui_utils

# Import modules
from giris_ekrani import GirisEkrani

def main():
    # Set up Turkish locale
    ui_utils.set_turkish_locale()
    
    # Create application
    app = QApplication(sys.argv)
    
    # Load main login window
    giris = GirisEkrani()
    giris.show()
    
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()