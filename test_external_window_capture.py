#!/usr/bin/env python3
"""
Harici Pencere Yakalama Sistemi Test Dosyası
Bu dosya, yeni eklenen harici pencere seçimi ve yakalama özelliğini test eder.
"""

import sys
import os
from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton, QLabel
from PyQt6.QtCore import QTimer
from PyQt6.QtGui import QPixmap

# Proje modüllerini import et
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from ui.panels.window_selector_dialog import WindowSelectorDialog
from core.external_window_capture import ExternalWindowCapture
from ui.widgets.hud import HUD

class TestWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Harici Pencere Yakalama Test")
        self.setGeometry(100, 100, 800, 600)
        
        # Ana widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Test butonları
        self.test_btn = QPushButton("Pencere Seç Dialog'unu Test Et")
        self.test_btn.clicked.connect(self.test_dialog)
        layout.addWidget(self.test_btn)
        
        self.capture_btn = QPushButton("Yakalama Sistemini Test Et")
        self.capture_btn.clicked.connect(self.test_capture)
        layout.addWidget(self.capture_btn)
        
        # HUD widget'ı
        self.hud = HUD()
        layout.addWidget(self.hud)
        
        # Durum etiketi
        self.status_label = QLabel("Test hazır")
        layout.addWidget(self.status_label)
        
        # Harici pencere yakalama sistemi
        self.external_capture = ExternalWindowCapture()
        self.external_capture.frame_captured.connect(self.hud.update_fpv)
        self.external_capture.error_occurred.connect(self.handle_error)
        
        # Test için sahte telemetri verisi
        self.fake_telemetry_timer = QTimer()
        self.fake_telemetry_timer.timeout.connect(self.send_fake_telemetry)
        self.fake_telemetry_timer.start(100)  # 10 FPS
        
    def test_dialog(self):
        """Pencere seçimi dialog'unu test et"""
        try:
            dialog = WindowSelectorDialog(self)
            dialog.window_selected.connect(self.on_window_selected)
            result = dialog.exec()
            
            if result == WindowSelectorDialog.DialogCode.Accepted:
                self.status_label.setText("Dialog başarıyla çalıştı")
            else:
                self.status_label.setText("Dialog iptal edildi")
                
        except Exception as e:
            self.status_label.setText(f"Dialog hatası: {e}")
            print(f"Dialog test hatası: {e}")
            
    def test_capture(self):
        """Yakalama sistemini test et"""
        try:
            # Önce dialog aç
            dialog = WindowSelectorDialog(self)
            dialog.window_selected.connect(self.start_capture_test)
            dialog.exec()
            
        except Exception as e:
            self.status_label.setText(f"Yakalama test hatası: {e}")
            print(f"Yakalama test hatası: {e}")
            
    def start_capture_test(self, title, hwnd):
        """Yakalama testini başlat"""
        try:
            self.external_capture.set_target_window(title, hwnd)
            
            if self.external_capture.start_capture():
                self.status_label.setText(f"Yakalama başlatıldı: {title}")
                print(f"Yakalama başlatıldı: {title}")
            else:
                self.status_label.setText("Yakalama başlatılamadı")
                print("Yakalama başlatılamadı")
                
        except Exception as e:
            self.status_label.setText(f"Yakalama başlatma hatası: {e}")
            print(f"Yakalama başlatma hatası: {e}")
            
    def on_window_selected(self, title, hwnd):
        """Pencere seçildiğinde"""
        self.status_label.setText(f"Seçilen pencere: {title}")
        print(f"Seçilen pencere: {title} (HWND: {hwnd})")
        
    def handle_error(self, error_msg):
        """Hata durumunda"""
        self.status_label.setText(f"Hata: {error_msg}")
        print(f"Yakalama hatası: {error_msg}")
        
    def send_fake_telemetry(self):
        """Sahte telemetri verisi gönder"""
        import math
        import time
        
        current_time = time.time()
        
        # Sahte telemetri verisi
        telemetry = {
            'lat': 41.0082 + 0.0001 * math.sin(current_time * 0.1),
            'lon': 28.9784 + 0.0001 * math.cos(current_time * 0.1),
            'alt': 100 + 10 * math.sin(current_time * 0.05),
            'speed': 15 + 5 * math.sin(current_time * 0.2),
            'heading': int((current_time * 10) % 360),
            'battery': 85,
            'voltage': 12.5,
            'current': 2.1,
            'rssi': 95,
            'mode': 'AUTO',
            'climb': 0.5,
            'time': f"{int(current_time // 60):02d}:{int(current_time % 60):02d}",
            'sat': 12,
            'roll': 5 * math.sin(current_time * 0.3),
            'pitch': 3 * math.cos(current_time * 0.2),
            'yaw': (current_time * 10) % 360,
            'armed': True
        }
        
        self.hud.update_telemetry(telemetry)
        
    def closeEvent(self, event):
        """Pencere kapatılırken temizlik"""
        if self.external_capture.is_capturing():
            self.external_capture.stop_capture()
        event.accept()

def main():
    """Test uygulamasını başlat"""
    app = QApplication(sys.argv)
    
    # Test penceresi oluştur
    test_window = TestWindow()
    test_window.show()
    
    print("Harici Pencere Yakalama Test Uygulaması başlatıldı")
    print("1. 'Pencere Seç Dialog'unu Test Et' butonuna basarak dialog'u test edin")
    print("2. 'Yakalama Sistemini Test Et' butonuna basarak yakalama sistemini test edin")
    print("3. HUD üzerinde sahte telemetri verilerini görebilirsiniz")
    
    sys.exit(app.exec())

if __name__ == '__main__':
    main() 