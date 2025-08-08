from PyQt6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QLabel, QFileDialog, QHBoxLayout, QSlider
from PyQt6.QtCore import pyqtSignal, Qt

class LoglamaPanel(QWidget):
    log_file_selected = pyqtSignal(str)
    video_file_selected = pyqtSignal(str)
    play_clicked = pyqtSignal()
    pause_clicked = pyqtSignal()
    stop_clicked = pyqtSignal()
    seek_changed = pyqtSignal(int)
    speed_changed = pyqtSignal(float)

    def __init__(self):
        super().__init__()
        self.setMinimumWidth(350)
        self.setMaximumWidth(400)
        self._updating_slider = False  # Flag to prevent signal loops
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout()
        # Dosya seçiciler
        file_layout = QHBoxLayout()
        self.log_btn = QPushButton('Log (.bin) Seç')
        self.log_btn.clicked.connect(self.select_log_file)
        self.log_label = QLabel('Seçili log: -')
        self.video_btn = QPushButton('FPV Video (mp4) Seç')
        self.video_btn.clicked.connect(self.select_video_file)
        self.video_label = QLabel('Seçili video: -')
        file_layout.addWidget(self.log_btn)
        file_layout.addWidget(self.log_label)
        file_layout.addWidget(self.video_btn)
        file_layout.addWidget(self.video_label)
        layout.addLayout(file_layout)
        # Kontroller
        control_layout = QHBoxLayout()
        self.play_btn = QPushButton('Oynat')
        self.pause_btn = QPushButton('Duraklat')
        self.stop_btn = QPushButton('Durdur')
        self.play_btn.clicked.connect(self.play_clicked.emit)
        self.pause_btn.clicked.connect(self.pause_clicked.emit)
        self.stop_btn.clicked.connect(self.stop_clicked.emit)
        control_layout.addWidget(self.play_btn)
        control_layout.addWidget(self.pause_btn)
        control_layout.addWidget(self.stop_btn)
        # Hız ayarı
        self.speed_slider = QSlider(Qt.Orientation.Horizontal)
        self.speed_slider.setMinimum(5)
        self.speed_slider.setMaximum(20)
        self.speed_slider.setValue(10)
        self.speed_slider.setTickInterval(1)
        self.speed_slider.valueChanged.connect(self.on_speed_changed)
        control_layout.addWidget(QLabel('Hız'))
        control_layout.addWidget(self.speed_slider)
        layout.addLayout(control_layout)
        # Seek bar
        seek_layout = QVBoxLayout()
        self.seek_label = QLabel('Zaman: 0 / 0')
        self.seek_slider = QSlider(Qt.Orientation.Horizontal)
        self.seek_slider.setMinimum(0)
        self.seek_slider.setMaximum(100)  # Will be updated when log is loaded
        self.seek_slider.setValue(0)
        self.seek_slider.sliderMoved.connect(self.on_seek_moved)
        self.seek_slider.sliderPressed.connect(self.on_seek_pressed)
        self.seek_slider.sliderReleased.connect(self.on_seek_released)
        seek_layout.addWidget(self.seek_label)
        seek_layout.addWidget(self.seek_slider)
        layout.addLayout(seek_layout)
        self.setLayout(layout)

    def select_log_file(self):
        file, _ = QFileDialog.getOpenFileName(self, 'Log Dosyası Seç', '', 'Pixhawk Logları (*.bin *.csv)')
        if file:
            self.log_label.setText(f'Seçili log: {file}')
            self.log_file_selected.emit(file)

    def select_video_file(self):
        file, _ = QFileDialog.getOpenFileName(self, 'Video Dosyası Seç', '', 'Video Dosyaları (*.mp4)')
        if file:
            self.video_label.setText(f'Seçili video: {file}')
            self.video_file_selected.emit(file)

    def on_speed_changed(self, value):
        speed = value / 10.0
        self.speed_changed.emit(speed)
    
    def on_seek_moved(self, value):
        """Called when user drags the slider"""
        if not self._updating_slider:
            self.update_seek_label(value)
    
    def on_seek_pressed(self):
        """Called when user starts dragging"""
        self._updating_slider = True
    
    def on_seek_released(self):
        """Called when user releases the slider"""
        self._updating_slider = False
        self.seek_changed.emit(self.seek_slider.value())
    
    def set_log_length(self, length):
        """Set the maximum value for the seek slider"""
        self.seek_slider.setMaximum(max(0, length - 1))
        self.update_seek_label(0)
        print(f"[LoglamaPanel] Set seek slider range: 0 to {length - 1}")
    
    def update_seek_position(self, position):
        """Update seek slider position (called from thread)"""
        if not self._updating_slider:  # Only update if user isn't dragging
            self.seek_slider.setValue(position)
        self.update_seek_label(position)
    
    def update_seek_label(self, position):
        """Update the time label"""
        maximum = self.seek_slider.maximum()
        self.seek_label.setText(f'Zaman: {position} / {maximum}') 