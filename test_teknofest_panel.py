#!/usr/bin/env python3
"""
Teknofest Panel Test Script
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from PyQt6.QtWidgets import QApplication
from ui.panels.teknofest_panel import TeknofestPanel

def test_teknofest_panel():
    """Teknofest panelini test et"""
    app = QApplication(sys.argv)
    
    # Panel oluştur
    panel = TeknofestPanel()
    panel.show()
    
    # Test mesajları
    panel.log_message("Teknofest panel test başlatıldı")
    panel.log_message("8 çizme görevi test ediliyor...")
    panel.log_message("Yük bırakma görevi test ediliyor...")
    
    # Test koordinatları
    panel.pole1_lat.setValue(40.0)
    panel.pole1_lon.setValue(29.0)
    panel.pole2_lat.setValue(40.001)
    panel.pole2_lon.setValue(29.001)
    
    panel.takeoff_lat.setValue(40.0015)
    panel.takeoff_lon.setValue(29.0005)
    panel.drop1_lat.setValue(40.002)
    panel.drop1_lon.setValue(29.002)
    panel.drop2_lat.setValue(40.003)
    panel.drop2_lon.setValue(29.003)
    
    print("Teknofest panel test başlatıldı. Pencereyi kapatmak için Ctrl+C kullanın.")
    
    sys.exit(app.exec())

if __name__ == "__main__":
    test_teknofest_panel() 