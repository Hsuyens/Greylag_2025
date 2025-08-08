import time
import math
import numpy as np
import pyqtgraph as pg
import pyqtgraph.opengl as gl
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QGridLayout, QLabel, QGroupBox
from PyQt6.QtCore import Qt

from ui.theme import ThemeColors

class AdvancedTelemetryPanel(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()
        
    def initUI(self):
        layout = QVBoxLayout()
        grid = QGridLayout()
        self.value_labels = {}

        # Kutucuk tanımları: (Başlık, key)
        boxes = [
            ("Batarya Voltajı (V)", "voltage"),
            ("Batarya Akımı (A)", "current"),
            ("Sıcaklık (°C)", "temperature"),
            ("Yükseklik (m)", "altitude"),
            ("Hız (m/s)", "speed"),
            ("GPS Uydu Sayısı", "gps_sat"),
            ("Konum (Lat/Lon)", "location"),
            ("Uçuş Süresi", "flight_time"),
        ]

        for i, (title, key) in enumerate(boxes):
            group = QGroupBox(title)
            group.setStyleSheet(ThemeColors.PANEL_STYLE)
            vbox = QVBoxLayout()
            value_label = QLabel("0")
            value_label.setStyleSheet("font-size: 28px; font-weight: bold; color: #fff;")
            value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            vbox.addWidget(value_label)
            group.setLayout(vbox)
            grid.addWidget(group, i // 2, i % 2)
            self.value_labels[key] = value_label

        layout.addLayout(grid)
        self.setLayout(layout)

    # Paneldeki kutucukları güncellemek için fonksiyonlar
    def set_voltage(self, value):
        if value is None:
            value = 0.0
        self.value_labels["voltage"].setText(f"{value:.2f}")
    def set_current(self, value):
        if value is None:
            value = 0.0
        self.value_labels["current"].setText(f"{value:.2f}")
    def set_temperature(self, value):
        if value is None:
            value = 0.0
        self.value_labels["temperature"].setText(f"{value:.1f}")
    def set_altitude(self, value):
        if value is None:
            value = 0.0
        self.value_labels["altitude"].setText(f"{value:.1f}")
    def set_speed(self, value):
        if value is None:
            value = 0.0
        self.value_labels["speed"].setText(f"{value:.1f}")
    def set_gps_sat(self, value):
        if value is None:
            value = 0
        self.value_labels["gps_sat"].setText(str(value))
    def set_location(self, lat, lon):
        if lat is None or lon is None:
            self.value_labels["location"].setText("0.00000, 0.00000")
        else:
            self.value_labels["location"].setText(f"{lat:.5f}, {lon:.5f}")
    def set_flight_time(self, seconds):
        if seconds is None:
            seconds = 0
        m, s = divmod(int(seconds), 60)
        self.value_labels["flight_time"].setText(f"{m:02d}:{s:02d}") 

    def update_telemetry(self, data):
        self.set_voltage(data.get('voltage'))
        self.set_current(data.get('current'))
        self.set_temperature(data.get('temperature'))
        self.set_altitude(data.get('altitude'))
        self.set_speed(data.get('speed'))
        self.set_gps_sat(data.get('gps_sat'))
        loc = data.get('location')
        if isinstance(loc, (tuple, list)) and len(loc) == 2:
            self.set_location(loc[0], loc[1])
        else:
            self.set_location(data.get('lat'), data.get('lon'))
        self.set_flight_time(data.get('flight_time')) 