import time
import cv2
import subprocess
import numpy as np
from PyQt6.QtCore import QThread, pyqtSignal, Qt
from PyQt6.QtGui import QImage

# Kullanıcının masaüstündeki dji video klasöründeki tam yollar
NODE_PATH = r'C:\Users\tavla\OneDrive\Masaüstü\dji video\node.exe'
FFMPEG_PATH = r'C:\Users\tavla\OneDrive\Masaüstü\dji video\ffmpeg.exe'
INDEX_JS_PATH = r'C:\Users\tavla\OneDrive\Masaüstü\dji video\index.js'

class FPVThread(QThread):
    frame_received = pyqtSignal(QImage)
    error_occurred = pyqtSignal(str)
    
    def __init__(self, width=1280, height=720):
        super().__init__()
        self.running = True
        self.width = width
        self.height = height
        self.node_proc = None
        self.ffmpeg_proc = None
        self.frame_size = self.width * self.height * 3
        
    def connect(self):
        try:
            # Node.js scriptini başlat (tam yol ile)
            self.node_proc = subprocess.Popen(
                [NODE_PATH, INDEX_JS_PATH, '-o'],
                stdout=subprocess.PIPE
            )
            # ffmpeg ile ham frame'lere çevir (tam yol ile)
            ffmpeg_cmd = [
                FFMPEG_PATH,
                '-i', '-',  # stdin'den oku
                '-f', 'rawvideo',
                '-pix_fmt', 'bgr24',
                '-s', f'{self.width}x{self.height}',
                '-'
            ]
            self.ffmpeg_proc = subprocess.Popen(
                ffmpeg_cmd,
                stdin=self.node_proc.stdout,
                stdout=subprocess.PIPE
            )
            # Başarılıysa True dön
            return True
        except Exception as e:
            self.error_occurred.emit(f"FPV akış başlatılamadı: {e}")
            return False
            
    def run(self):
        while self.running:
            if self.ffmpeg_proc and self.ffmpeg_proc.stdout:
                try:
                    raw_frame = self.ffmpeg_proc.stdout.read(self.frame_size)
                    if not raw_frame:
                        continue
                    frame = np.frombuffer(raw_frame, np.uint8).reshape((self.height, self.width, 3))
                    rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    h, w, ch = rgb_image.shape
                    bytes_per_line = ch * w
                    qt_image = QImage(rgb_image.tobytes(), w, h, bytes_per_line, QImage.Format.Format_RGB888)
                    self.frame_received.emit(qt_image.scaled(640, 480, Qt.AspectRatioMode.KeepAspectRatio))
                except Exception as e:
                    self.error_occurred.emit(f"FPV frame okuma hatası: {e}")
            time.sleep(0.01) # ~30 FPS
            
    def stop(self):
        self.running = False
        if self.ffmpeg_proc:
            self.ffmpeg_proc.terminate()
        if self.node_proc:
            self.node_proc.terminate() 