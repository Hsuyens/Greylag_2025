from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QGroupBox, QGridLayout, 
                             QLabel, QListWidget, QPushButton, QDialog, QDialogButtonBox, QFormLayout, QLineEdit)

from ui.theme import ThemeColors
from core.safety_manager import SafetyManager

class SafetyPanel(QWidget):
    def __init__(self, safety_manager: SafetyManager):
        super().__init__()
        self.safety_manager = safety_manager
        self.initUI()
        self.add_landing_btn.clicked.connect(self.open_add_landing_point_dialog)
        
    def initUI(self):
        layout = QVBoxLayout()
        
        # Geofence Group
        geofence_group = QGroupBox("Geofence")
        geofence_group.setStyleSheet(ThemeColors.PANEL_STYLE)
        geofence_layout = QVBoxLayout()
        self.geofence_status = QLabel("Durum: Tanımlanmamış")
        self.max_alt_label = QLabel("Max İrtifa: --")
        geofence_layout.addWidget(self.geofence_status)
        geofence_layout.addWidget(self.max_alt_label)
        geofence_group.setLayout(geofence_layout)
        
        # Weather Group
        weather_group = QGroupBox("Hava Durumu")
        weather_group.setStyleSheet(ThemeColors.PANEL_STYLE)
        weather_layout = QGridLayout()
        self.wind_label = QLabel("Rüzgar: --")
        self.temp_label = QLabel("Sıcaklık: --")
        self.visibility_label = QLabel("Görüş: --")
        self.weather_status = QLabel("Durum: Veri yok")
        weather_layout.addWidget(self.wind_label, 0, 0)
        weather_layout.addWidget(self.temp_label, 0, 1)
        weather_layout.addWidget(self.visibility_label, 1, 0)
        weather_layout.addWidget(self.weather_status, 1, 1)
        weather_group.setLayout(weather_layout)
        
        # Emergency Landing Points
        landing_group = QGroupBox("Acil İniş Noktaları")
        landing_group.setStyleSheet(ThemeColors.PANEL_STYLE)
        landing_layout = QVBoxLayout()
        self.landing_list = QListWidget()
        self.landing_list.setStyleSheet(ThemeColors.INPUT_STYLE)
        self.add_landing_btn = QPushButton("Yeni Nokta Ekle")
        self.add_landing_btn.setStyleSheet(ThemeColors.BUTTON_NORMAL)
        landing_layout.addWidget(self.landing_list)
        landing_layout.addWidget(self.add_landing_btn)
        landing_group.setLayout(landing_layout)
        
        layout.addWidget(geofence_group)
        layout.addWidget(weather_group)
        layout.addWidget(landing_group)
        layout.addStretch(1)
        self.setLayout(layout)
        
    def update_geofence_status(self, lat, lon, alt):
        if self.safety_manager.geofence:
            safe, message = self.safety_manager.check_geofence(lat, lon, alt)
            color = "green" if safe else "red"
            self.geofence_status.setText(f"Durum: {message}")
            self.geofence_status.setStyleSheet(f"color: {color}; font-weight: bold;")
            self.max_alt_label.setText(f"Max İrtifa: {self.safety_manager.geofence['max_alt']}m")
            
    def update_weather_info(self, weather_data):
        if weather_data:
            self.wind_label.setText(f"Rüzgar: {weather_data['wind_speed']:.1f} m/s @ {weather_data['wind_direction']}°")
            self.temp_label.setText(f"Sıcaklık: {weather_data['temperature']}°C")
            self.visibility_label.setText(f"Görüş: {weather_data['visibility']/1000:.1f} km")
            
            safe, message = self.safety_manager.check_weather_safety(weather_data)
            color = "green" if safe else "orange"
            self.weather_status.setText(f"Durum: {message if message else 'Uygun'}")
            self.weather_status.setStyleSheet(f"color: {color}; font-weight: bold;")
            
    def update_landing_points(self):
        self.landing_list.clear()
        for point in self.safety_manager.emergency_landing_points:
            self.landing_list.addItem(f"{point.get('name', 'İsimsiz')} ({point['lat']:.5f}, {point['lon']:.5f})")

    def open_add_landing_point_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Acil İniş Noktası Ekle")
        layout = QFormLayout(dialog)
        lat_input = QLineEdit()
        lon_input = QLineEdit()
        name_input = QLineEdit()
        notes_input = QLineEdit()
        layout.addRow("Enlem (lat):", lat_input)
        layout.addRow("Boylam (lon):", lon_input)
        layout.addRow("İsim:", name_input)
        layout.addRow("Not:", notes_input)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        layout.addWidget(buttons)
        def on_accept():
            try:
                lat = float(lat_input.text())
                lon = float(lon_input.text())
            except ValueError:
                lat_input.setStyleSheet("background: #ffcccc;")
                lon_input.setStyleSheet("background: #ffcccc;")
                return
            name = name_input.text()
            notes = notes_input.text()
            self.safety_manager.add_emergency_landing_point(lat, lon, name, notes)
            self.update_landing_points()
            dialog.accept()
        buttons.accepted.connect(on_accept)
        buttons.rejected.connect(dialog.reject)
        dialog.exec() 