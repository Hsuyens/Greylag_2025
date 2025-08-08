from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel
from PyQt6.QtCore import pyqtSignal, QTimer
from ui.widgets.hud import HUD
from ui.panels.window_selector_dialog import WindowSelectorDialog
from core.external_window_capture import ExternalWindowCapture

class FlightPanel(QWidget):
    external_window_selected = pyqtSignal(str, int)  # window_title, window_handle
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Flight Panel')
        
        # Create HUD first
        self.hud = HUD()
        
        # Harici pencere yakalama sistemi
        self.external_capture = ExternalWindowCapture()
        self.external_capture.frame_captured.connect(self.hud.update_fpv)
        self.external_capture.error_occurred.connect(self.handle_capture_error)
        
        # Manuel yakalama timer'ı
        self.capture_timer = QTimer()
        self.capture_timer.timeout.connect(self.manual_capture)
        
        # Create layout
        layout = QVBoxLayout()
        layout.setContentsMargins(0,0,0,0)
        
        layout.addWidget(self.hud)
        self.setLayout(layout)
        
    def select_external_window(self):
        """Harici pencere seçimi dialog'unu aç"""
        dialog = WindowSelectorDialog(self)
        dialog.window_selected.connect(self.on_window_selected)
        dialog.exec()
        
    def on_window_selected(self, title, hwnd):
        """Harici pencere seçildiğinde çağrılır"""
        try:
            # Önceki yakalamayı durdur
            if self.external_capture.is_capturing():
                self.external_capture.stop_capture()
                self.capture_timer.stop()
                
            # Yeni pencereyi ayarla
            self.external_capture.set_target_window(title, hwnd)
            
            # Yakalamayı başlat
            if self.external_capture.start_capture():
                self.hud.update_fpv(None, 0, 0)
                self.external_window_selected.emit(title, hwnd)
                # Manuel yakalama timer'ını başlat
                self.capture_timer.start(1000)  # 1 saniye
            else:
                self.hud.update_fpv(None, 0, 0)
        except Exception as e:
            self.hud.update_fpv(None, 0, 0)
            print(f"[FlightPanel] Harici pencere seçimi hatası: {e}")
            
    def manual_capture(self):
        """Manuel frame yakalama"""
        if self.external_capture.is_capturing():
            success = self.external_capture.capture_frame()
            if not success:
                print("[FlightPanel] Frame yakalama başarısız")
            
    def stop_external_window(self):
        """Harici pencere yakalamasını durdur"""
        try:
            self.external_capture.stop_capture()
            self.capture_timer.stop()
            self.hud.update_fpv(None, 0, 0)
            
        except Exception as e:
            print(f"[FlightPanel] Harici pencere durdurma hatası: {e}")
            
    def handle_capture_error(self, error_msg):
        """Yakalama hatası durumunda"""
        self.hud.update_fpv(None, 0, 0)
        print(f"[FlightPanel] Yakalama hatası: {error_msg}")
        
    def closeEvent(self, event):
        """Panel kapatılırken temizlik yap"""
        if self.external_capture.is_capturing():
            self.external_capture.stop_capture()
        event.accept() 