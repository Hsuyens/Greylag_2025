from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt, QTimer, QRect
from PyQt6.QtGui import QPainter, QColor, QPen, QFont, QPixmap, QImage
import datetime

class HUD(QWidget):
    def __init__(self):
        super().__init__()
        self.fpv_image = None
        self.telemetry = {
            'lat': 0.0, 'lon': 0.0, 'alt': 0.0, 'speed': 0.0, 'heading': 0,
            'battery': 100, 'voltage': 0.0, 'current': 0.0, 'rssi': 100,
            'mode': 'Otonom', 'climb': 0.0, 'time': '00:00', 'sat': 0,
            'roll': 0.0, 'pitch': 0.0, 'yaw': 0.0,
            'armed': False  # <-- ARM durumu
        }
        
        # Update timer for smoother display
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update)
        self.update_timer.start(100)  # 10 FPS (daha yavaş)

    def update_fpv(self, frame_bytes, w, h):
        if frame_bytes is None or w <= 0 or h <= 0:
            return
        try:
            qt_image = QImage(frame_bytes, w, h, w * 3, QImage.Format.Format_RGB888)
            if not hasattr(self, '_last_size') or self._last_size != (w, h):
                print(f"[HUD.update_fpv] Görüntü alındı: {w}x{h}")
                self._last_size = (w, h)
            self.fpv_image = qt_image
            self.update()
        except Exception as e:
            print(f"[HUD.update_fpv] QImage oluşturma hatası: {e}")

    def update_telemetry(self, data):
        print(f"[HUD.update_telemetry] {datetime.datetime.now().isoformat()} data: {data}")
        # Update only the provided values, eski alt'ı koru
        for key, value in data.items():
            if key in self.telemetry:
                if key == 'alt':
                    # Eğer yeni alt değeri None veya 0 ise, eski değeri koru
                    if value is not None and value != 0:
                        self.telemetry[key] = value
                    # value 0 veya None ise, eski değer kalır
                else:
                    self.telemetry[key] = value
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Draw FPV image if available and valid, otherwise fill with black
        fpv_drawn = False
        if self.fpv_image and not self.fpv_image.isNull():
            try:
                # Görüntü boyutunu kontrol et
                img_width = self.fpv_image.width()
                img_height = self.fpv_image.height()
                
                if img_width > 0 and img_height > 0:
                    # QImage'i QPixmap'e çevir
                    pixmap = QPixmap.fromImage(self.fpv_image)
                    if not pixmap.isNull():
                        # QPixmap'i widget boyutuna ölçekle
                        scaled_pixmap = pixmap.scaled(self.rect().size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                        painter.drawPixmap(self.rect(), scaled_pixmap)
                        fpv_drawn = True
                        print(f"[HUD.paintEvent] FPV görüntüsü çizildi: {img_width}x{img_height}")
                    else:
                        print("[HUD.paintEvent] QPixmap oluşturulamadı")
                else:
                    print(f"[HUD.paintEvent] Geçersiz görüntü boyutu: {img_width}x{img_height}")
                    
            except Exception as e:
                print(f"[HUD.paintEvent] FPV çizim hatası: {e}")
                
        if not fpv_drawn:
            # Fallback: koyu gri arka plan
            painter.fillRect(self.rect(), QColor(30, 30, 30))
            
        # OSD overlay and artificial horizon should always be drawn
        # Yapay ufuk çizgisini her zaman çiz
        self.draw_osd(painter)

    def draw_osd(self, painter):
        t = self.telemetry
        w, h = self.width(), self.height()
        font = QFont('Consolas', 12, QFont.Weight.Bold)
        painter.setFont(font)
        
        pen = QPen(QColor(0, 255, 127, 200), 2) # Mint green, slightly transparent
        painter.setPen(pen)

        # --- ARTIFICIAL HORIZON ---
        cx, cy = w // 2, h // 2
        roll = t.get('roll', 0.0)
        pitch = t.get('pitch', 0.0)
        
        painter.save()
        painter.translate(cx, cy)
        painter.rotate(-roll)  # Reverse roll direction
        painter.translate(0, pitch * 4) # 4 pixels per degree of pitch

        # --- ATTITUDE INDICATOR BACKGROUND ---
        # Pitch çok büyük/küçükse ekranı tamamen doldur
        if pitch > 60:
            painter.fillRect(QRect(-w//2-50, -h//2-50, w+100, h+100), QColor(80, 180, 255))  # Tamamen gökyüzü
        elif pitch < -60:
            painter.fillRect(QRect(-w//2-50, -h//2-50, w+100, h+100), QColor(180, 120, 60))  # Tamamen yer
        else:
            # Büyük dikdörtgenler çiz, ekranı dolduracak kadar
            bg_width = w * 4
            bg_height = h * 4
            # Gökyüzü (üst)
            sky_rect = QRect(-bg_width//2, -bg_height//2, bg_width, bg_height//2)
            painter.fillRect(sky_rect, QColor(80, 180, 255))  # Açık mavi
            # Yer (alt)
            ground_rect = QRect(-bg_width//2, 0, bg_width, bg_height//2)
            painter.fillRect(ground_rect, QColor(180, 120, 60))  # Açık kahverengi
        # Ufuk çizgisi (beyaz)
        pen.setColor(QColor(255, 255, 255, 220))
        pen.setWidth(2)
        painter.setPen(pen)
        painter.drawLine(-w // 2, 0, w // 2, 0)

        # Pitch Ladder
        pen.setColor(QColor(255, 255, 255, 180))
        pen.setWidth(1)
        painter.setPen(pen)
        for p in range(-40, 50, 10):
            if p == 0: continue
            y = -p * 4
            length = 30 if p % 20 == 0 else 15
            painter.drawLine(-length, y, length, y)
            painter.drawText(length + 5, y + 5, f"{p}")
            painter.drawText(-length - 30, y + 5, f"{p}")

        painter.restore()
        # --- END ARTIFICIAL HORIZON ---

        # Reset pen for text
        pen.setColor(QColor(255,255,255, 220))
        pen.setWidth(2)
        painter.setPen(pen)

        # Top Info
        painter.drawText(20, 30, f"LON: {t['lon']:.6f}")
        painter.drawText(w - 200, 30, f"LAT: {t['lat']:.6f}")
        
        # Heading Indicator
        yaw_val = t.get('yaw', 0)
        # reversed_yaw = (360 - yaw_val) % 360  # Remove this reversal
        heading_text = f"{int(yaw_val)%360:03d}°"
        painter.drawText(cx - 20, 30, heading_text)
        painter.drawText(cx - 15, 50, "N" if 315 < yaw_val <= 360 or 0 <= yaw_val <= 45 else "")
        
        # Center Crosshair
        painter.drawLine(cx - 10, cy, cx - 2, cy)
        painter.drawLine(cx + 2, cy, cx + 10, cy)
        painter.drawLine(cx, cy - 10, cx, cy - 2)
        painter.drawLine(cx, cy + 2, cx, cy + 10)

        # Left: Altitude
        painter.drawText(20, h - 30, f"ALT: {t['alt']:.1f} m")

        # Right: Ground Speed
        painter.drawText(w - 150, h - 30, f"SPD: {t['speed']:.1f} m/s")

        # Bottom: Mode and Status
        arm_text = "ARMED" if t.get('armed', False) else "DISARMED"
        painter.drawText(20, h - 10, f"Mode: {t['mode']} | {arm_text}")
        # Batarya yüzdesi -1 ise '--' göster
        battery_val = t['battery']
        battery_str = f"{battery_val}%" if isinstance(battery_val, (int, float)) and battery_val >= 0 else "--"
        painter.drawText(w - 250, h - 10, f"BAT: {battery_str} | V: {t['voltage']:.1f} | A: {t['current']:.1f}")

    def closeEvent(self, event):
        self.update_timer.stop()
        event.accept() 