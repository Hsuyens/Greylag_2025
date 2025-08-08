import time
import win32gui
import numpy as np
from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtGui import QImage
from PIL import ImageGrab, Image

class ExternalWindowCapture(QObject):
    frame_captured = pyqtSignal(QImage)
    error_occurred = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self.target_hwnd = None
        self.target_title = ""
        
    def set_target_window(self, title, hwnd):
        self.target_title = title
        self.target_hwnd = hwnd
        print(f"[ExternalWindowCapture] Hedef pencere ayarlandı: {title} (HWND: {hwnd})")
        
    def start_capture(self):
        if not self.target_hwnd:
            self.error_occurred.emit("Hedef pencere ayarlanmamış!")
            return False
        if not win32gui.IsWindow(self.target_hwnd):
            self.error_occurred.emit("Hedef pencere artık mevcut değil!")
            return False
        print(f"[ExternalWindowCapture] Yakalama başlatıldı: {self.target_title}")
        return True
    
    def stop_capture(self):
        self.target_hwnd = None
        self.target_title = ""
        print(f"[ExternalWindowCapture] Yakalama durduruldu")
    
    def capture_frame(self):
        """Manuel frame yakalama - thread yok"""
        if not self.target_hwnd:
            return False
            
        try:
            # Pencere hala mevcut mu kontrol et
            if not win32gui.IsWindow(self.target_hwnd):
                print("[ExternalWindowCapture] Hedef pencere artık mevcut değil")
                return False
                
            # Pencere pozisyonunu al - ClientRect kullan (frame olmadan)
            left, top, right, bottom = win32gui.GetClientRect(self.target_hwnd)
            width = right - left
            height = bottom - top
            
            # Pencere ekrandaki mutlak pozisyonunu al
            abs_left, abs_top = win32gui.ClientToScreen(self.target_hwnd, (left, top))
            abs_right, abs_bottom = win32gui.ClientToScreen(self.target_hwnd, (right, bottom))
            
            print(f"[ExternalWindowCapture] Client koordinatları: ({left}, {top}, {right}, {bottom}) = {width}x{height}")
            print(f"[ExternalWindowCapture] Ekran koordinatları: ({abs_left}, {abs_top}, {abs_right}, {abs_bottom})")
            
            if width <= 0 or height <= 0:
                print("[ExternalWindowCapture] Geçersiz pencere boyutu")
                return False
                
            # Çok büyük pencereler için güvenlik kontrolü
            if width > 1000 or height > 1000:
                print(f"[ExternalWindowCapture] Pencere çok büyük ({width}x{height}), boyut küçültülüyor")
                width = min(width, 800)
                height = min(height, 600)
            
            print(f"[ExternalWindowCapture] Gerçek pencere yakalanıyor: {width}x{height}")
            
            # PIL ile ekran yakalama - mutlak koordinatları kullan
            bbox = (abs_left, abs_top, abs_right, abs_bottom)
            pil_image = ImageGrab.grab(bbox=bbox)
            
            # Boyutu küçült (güvenlik için)
            target_width = min(width, 640)
            target_height = min(height, 480)
            pil_image = pil_image.resize((target_width, target_height), Image.Resampling.LANCZOS)
            
            # PIL görüntüsünü RGB formatına çevir
            if pil_image.mode != 'RGB':
                pil_image = pil_image.convert('RGB')
            
            # PIL görüntüsünü numpy array'e çevir
            img_array = np.array(pil_image)
            
            # Boyut kontrolü
            if len(img_array.shape) != 3 or img_array.shape[2] != 3:
                print(f"[ExternalWindowCapture] Geçersiz görüntü formatı: {img_array.shape}")
                return False
            
            # QImage oluştur
            bytes_per_line = 3 * target_width
            q_img = QImage(img_array.tobytes(), target_width, target_height, bytes_per_line, QImage.Format.Format_RGB888)
            
            # QImage geçerli mi kontrol et
            if q_img.isNull():
                print("[ExternalWindowCapture] QImage oluşturulamadı")
                return False
                
            # Frame'i gönder
            self.frame_captured.emit(q_img)
            print(f"[ExternalWindowCapture] Görüntü gönderildi: {target_width}x{target_height}")
            return True
                
        except Exception as e:
            print(f"[ExternalWindowCapture] Frame yakalama hatası: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def get_window_info(self):
        if not self.target_hwnd:
            return None
        try:
            if not win32gui.IsWindow(self.target_hwnd):
                return None
            left, top, right, bottom = win32gui.GetWindowRect(self.target_hwnd)
            title = win32gui.GetWindowText(self.target_hwnd)
            return {
                'title': title,
                'hwnd': self.target_hwnd,
                'position': (left, top, right, bottom),
                'size': (right - left, bottom - top),
                'visible': win32gui.IsWindowVisible(self.target_hwnd)
            }
        except:
            return None
            
    def is_capturing(self):
        return self.target_hwnd is not None 