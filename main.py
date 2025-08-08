import sys
import os
from PyQt6.QtWidgets import QApplication

from ui.main_window import LaggerGCS
from ui.theme import apply_theme

os.environ['QT_OPENGL'] = 'software'
os.environ['QT_QUICK_BACKEND'] = 'software'
os.environ['QTWEBENGINE_CHROMIUM_FLAGS'] = '--disable-gpu --disable-software-rasterizer'
os.environ['QTWEBENGINE_DISABLE_SANDBOX'] = '1'

def log_uncaught_exceptions(exctype, value, traceback):
    import datetime
    with open('uncaught_exceptions.log', 'a', encoding='utf-8') as f:
        f.write(f"[{datetime.datetime.now().isoformat()}] {exctype.__name__}: {value}\n")
    print(f"[EXCEPTION] {exctype.__name__}: {value}")
    sys.__excepthook__(exctype, value, traceback)

sys.excepthook = log_uncaught_exceptions

def main():
    """Ana uygulama giriş noktası."""
    app = QApplication(sys.argv)
    
    # Uygulama temasını uygula
    apply_theme(app)
    
    # Ana pencereyi oluştur ve göster
    window = LaggerGCS()
    window.show()
    
    # Uygulama döngüsünü başlat
    sys.exit(app.exec())

if __name__ == '__main__':  
    main()      