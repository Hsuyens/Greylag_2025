import cv2
import time
from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtGui import QImage

class VideoReplayThread(QThread):
    frame_ready = pyqtSignal(bytes, int, int)
    finished = pyqtSignal()
    error_occurred = pyqtSignal(str)

    def __init__(self, video_path, speed=1.0, parent=None):
        super().__init__(parent)
        self.video_path = video_path
        self.speed = speed
        self._running = False
        self._paused = False
        self._requested_seek = None
        self._requested_speed = None
        self._frame_count = 0
        self._fps = 30
        self._load_video()

    def _load_video(self):
        self.cap = cv2.VideoCapture(self.video_path)
        if self.cap.isOpened():
            self._frame_count = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
            self._fps = self.cap.get(cv2.CAP_PROP_FPS)
        else:
            self._frame_count = 0
            self._fps = 30

    def run(self):
        self._running = True
        idx = 0
        while self._running and self.cap.isOpened() and idx < self._frame_count:
            if self._paused:
                time.sleep(0.05)
                continue
            if self._requested_seek is not None:
                idx = self._requested_seek
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
                self._requested_seek = None
            if self._requested_speed is not None:
                self.speed = self._requested_speed
                self._requested_speed = None
            ret, frame = self.cap.read()
            if not ret:
                break
            try:
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                h, w, ch = rgb.shape
                self.frame_ready.emit(rgb.tobytes(), w, h)
            except Exception as e:
                self.error_occurred.emit(f"Video frame işleme hatası: {e}")
                break
            idx += 1
            # Frame arası bekleme (log ile senkronize için dışarıdan kontrol edilecek)
            time.sleep(1.0 / (self._fps * self.speed))
        self.finished.emit()

    def pause(self):
        self._paused = True
    def resume(self):
        self._paused = False
    def stop(self):
        self._running = False
        if hasattr(self, 'cap') and self.cap:
            self.cap.release()
    def seek(self, idx):
        self._requested_seek = idx
    def set_speed(self, speed):
        self._requested_speed = speed 