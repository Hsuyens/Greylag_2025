from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QPushButton, QGroupBox, QFormLayout, 
                             QTextEdit, QLabel, QHBoxLayout, QSpinBox, QDoubleSpinBox, QProgressBar, QSizePolicy)
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QFont
from ui.theme import ThemeColors
import math

class TeknofestPanel(QWidget):
    # Görev sinyalleri
    start_figure8_mission = pyqtSignal(list)  # 8 çizme görevi için waypoint listesi
    start_payload_mission = pyqtSignal(list)  # Yük bırakma görevi için waypoint listesi
    start_cargo_mission = pyqtSignal(list)    # Kargo Operasyonu için waypoint listesi
    abort_mission = pyqtSignal()
    pause_mission = pyqtSignal()
    resume_mission = pyqtSignal()
    
    # Elektromıknatıs kontrol sinyalleri
    activate_magnet1 = pyqtSignal()
    deactivate_magnet1 = pyqtSignal()
    activate_magnet2 = pyqtSignal()
    deactivate_magnet2 = pyqtSignal()
    
    def __init__(self):
        super().__init__()
        self.mission_status = "IDLE"  # IDLE, FIGURE8, PAYLOAD, COMPLETED, ERROR
        self.current_waypoint = 0
        self.total_waypoints = 0
        self.mission_progress = 0
        self.initUI()
        
    def initUI(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(10)
        layout.setSizeConstraint(QVBoxLayout.SizeConstraint.SetMinimumSize)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
        
        # Başlık
        title = QLabel("TEKNOFEST GÖREV KONTROLÜ")
        title.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        title.setStyleSheet("color: #2c3e50; margin: 10px;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        # Görev Durumu
        self.status_group = QGroupBox("Görev Durumu")
        self.status_group.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)
        status_layout = QVBoxLayout()
        
        self.status_label = QLabel("Durum: HAZIR")
        self.status_label.setStyleSheet("font-weight: bold; color: #27ae60;")
        status_layout.addWidget(self.status_label)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        status_layout.addWidget(self.progress_bar)
        
        self.waypoint_info = QLabel("Waypoint: 0/0")
        status_layout.addWidget(self.waypoint_info)
        
        self.status_group.setLayout(status_layout)
        layout.addWidget(self.status_group)
        
        # 8 Çizme Görevi Konfigürasyonu
        self.figure8_group = QGroupBox("8 Çizme Görevi")
        self.figure8_group.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)
        figure8_layout = QFormLayout()
        figure8_layout.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)
        figure8_layout.setFormAlignment(Qt.AlignmentFlag.AlignLeft)
        figure8_layout.setHorizontalSpacing(12)
        figure8_layout.setVerticalSpacing(6)
        figure8_layout.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
        
        # Direk koordinatları
        self.pole1_lat = QDoubleSpinBox()
        self.pole1_lat.setRange(-90, 90)
        self.pole1_lat.setDecimals(6)
        self.pole1_lat.setSuffix("°")
        figure8_layout.addRow("Direk 1 Enlem:", self.pole1_lat)
        
        self.pole1_lon = QDoubleSpinBox()
        self.pole1_lon.setRange(-180, 180)
        self.pole1_lon.setDecimals(6)
        self.pole1_lon.setSuffix("°")
        figure8_layout.addRow("Direk 1 Boylam:", self.pole1_lon)
        
        self.pole2_lat = QDoubleSpinBox()
        self.pole2_lat.setRange(-90, 90)
        self.pole2_lat.setDecimals(6)
        self.pole2_lat.setSuffix("°")
        figure8_layout.addRow("Direk 2 Enlem:", self.pole2_lat)
        
        self.pole2_lon = QDoubleSpinBox()
        self.pole2_lon.setRange(-180, 180)
        self.pole2_lon.setDecimals(6)
        self.pole2_lon.setSuffix("°")
        figure8_layout.addRow("Direk 2 Boylam:", self.pole2_lon)
        
        # Uçuş parametreleri
        self.figure8_altitude = QSpinBox()
        self.figure8_altitude.setRange(10, 500)
        self.figure8_altitude.setValue(50)
        self.figure8_altitude.setSuffix(" m")
        figure8_layout.addRow("Uçuş İrtifası:", self.figure8_altitude)
        
        # 8 çizme başlat butonu
        self.start_figure8_btn = QPushButton("8 Çizme Görevini Başlat")
        self.start_figure8_btn.setStyleSheet(ThemeColors.BUTTON_PRIMARY)
        self.start_figure8_btn.clicked.connect(self.start_figure8_mission_handler)
        figure8_layout.addRow(self.start_figure8_btn)
        
        self.figure8_group.setLayout(figure8_layout)
        layout.addWidget(self.figure8_group)
        
        # Yük Bırakma Görevi Konfigürasyonu
        self.payload_group = QGroupBox("Yük Bırakma Görevi")
        self.payload_group.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)
        payload_layout = QFormLayout()
        payload_layout.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)
        payload_layout.setFormAlignment(Qt.AlignmentFlag.AlignLeft)
        payload_layout.setHorizontalSpacing(12)
        payload_layout.setVerticalSpacing(6)
        payload_layout.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
        
        # Kalkış noktası
        self.takeoff_lat = QDoubleSpinBox()
        self.takeoff_lat.setRange(-90, 90)
        self.takeoff_lat.setDecimals(6)
        self.takeoff_lat.setSuffix("°")
        payload_layout.addRow("Kalkış Enlem:", self.takeoff_lat)
        
        self.takeoff_lon = QDoubleSpinBox()
        self.takeoff_lon.setRange(-180, 180)
        self.takeoff_lon.setDecimals(6)
        self.takeoff_lon.setSuffix("°")
        payload_layout.addRow("Kalkış Boylam:", self.takeoff_lon)
        
        # Yük bırakma noktaları
        self.drop1_lat = QDoubleSpinBox()
        self.drop1_lat.setRange(-90, 90)
        self.drop1_lat.setDecimals(6)
        self.drop1_lat.setSuffix("°")
        payload_layout.addRow("Yük 1 Bırakma Enlem:", self.drop1_lat)
        
        self.drop1_lon = QDoubleSpinBox()
        self.drop1_lon.setRange(-180, 180)
        self.drop1_lon.setDecimals(6)
        self.drop1_lon.setSuffix("°")
        payload_layout.addRow("Yük 1 Bırakma Boylam:", self.drop1_lon)
        
        self.drop2_lat = QDoubleSpinBox()
        self.drop2_lat.setRange(-90, 90)
        self.drop2_lat.setDecimals(6)
        self.drop2_lat.setSuffix("°")
        payload_layout.addRow("Yük 2 Bırakma Enlem:", self.drop2_lat)
        
        self.drop2_lon = QDoubleSpinBox()
        self.drop2_lon.setRange(-180, 180)
        self.drop2_lon.setDecimals(6)
        self.drop2_lon.setSuffix("°")
        payload_layout.addRow("Yük 2 Bırakma Boylam:", self.drop2_lon)
        
        # Yük bırakma parametreleri
        self.payload_altitude = QSpinBox()
        self.payload_altitude.setRange(10, 200)
        self.payload_altitude.setValue(30)
        self.payload_altitude.setSuffix(" m")
        payload_layout.addRow("Yük Bırakma İrtifası:", self.payload_altitude)
        
        # Yük bırakma başlat butonu
        self.start_payload_btn = QPushButton("Yük Bırakma Görevini Başlat")
        self.start_payload_btn.setStyleSheet(ThemeColors.BUTTON_PRIMARY)
        self.start_payload_btn.clicked.connect(self.start_payload_mission_handler)
        payload_layout.addRow(self.start_payload_btn)
        
        self.payload_group.setLayout(payload_layout)
        layout.addWidget(self.payload_group)
        
        # Elektromıknatıs Kontrolü
        self.magnet_group = QGroupBox("Elektromıknatıs Kontrolü")
        self.magnet_group.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)
        magnet_layout = QHBoxLayout()
        
        # Magnet 1 kontrolü
        magnet1_layout = QVBoxLayout()
        magnet1_layout.addWidget(QLabel("Elektromıknatıs 1"))
        self.magnet1_activate_btn = QPushButton("Aktifleştir")
        self.magnet1_activate_btn.setStyleSheet(ThemeColors.BUTTON_SUCCESS)
        self.magnet1_activate_btn.clicked.connect(self.activate_magnet1.emit)
        magnet1_layout.addWidget(self.magnet1_activate_btn)
        
        self.magnet1_deactivate_btn = QPushButton("Deaktifleştir")
        self.magnet1_deactivate_btn.setStyleSheet(ThemeColors.BUTTON_DANGER)
        self.magnet1_deactivate_btn.clicked.connect(self.deactivate_magnet1.emit)
        magnet1_layout.addWidget(self.magnet1_deactivate_btn)
        
        # Magnet 2 kontrolü
        magnet2_layout = QVBoxLayout()
        magnet2_layout.addWidget(QLabel("Elektromıknatıs 2"))
        self.magnet2_activate_btn = QPushButton("Aktifleştir")
        self.magnet2_activate_btn.setStyleSheet(ThemeColors.BUTTON_SUCCESS)
        self.magnet2_activate_btn.clicked.connect(self.activate_magnet2.emit)
        magnet2_layout.addWidget(self.magnet2_activate_btn)
        
        self.magnet2_deactivate_btn = QPushButton("Deaktifleştir")
        self.magnet2_deactivate_btn.setStyleSheet(ThemeColors.BUTTON_DANGER)
        self.magnet2_deactivate_btn.clicked.connect(self.deactivate_magnet2.emit)
        magnet2_layout.addWidget(self.magnet2_deactivate_btn)
        
        magnet_layout.addLayout(magnet1_layout)
        magnet_layout.addLayout(magnet2_layout)
        self.magnet_group.setLayout(magnet_layout)
        layout.addWidget(self.magnet_group)
        
        # Görev Kontrolü
        self.control_group = QGroupBox("Görev Kontrolü")
        self.control_group.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)
        control_layout = QHBoxLayout()
        
        self.pause_btn = QPushButton("Duraklat")
        self.pause_btn.setStyleSheet(ThemeColors.BUTTON_WARNING)
        self.pause_btn.clicked.connect(self.pause_mission.emit)
        control_layout.addWidget(self.pause_btn)
        
        self.resume_btn = QPushButton("Devam Et")
        self.resume_btn.setStyleSheet(ThemeColors.BUTTON_PRIMARY)
        self.resume_btn.clicked.connect(self.resume_mission.emit)
        control_layout.addWidget(self.resume_btn)
        
        self.abort_btn = QPushButton("Görevi İptal Et")
        self.abort_btn.setStyleSheet(ThemeColors.BUTTON_DANGER)
        self.abort_btn.clicked.connect(self.abort_mission.emit)
        control_layout.addWidget(self.abort_btn)
        
        self.control_group.setLayout(control_layout)
        layout.addWidget(self.control_group)
        
        # Log Alanı
        self.log_group = QGroupBox("Görev Logları")
        self.log_group.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
        log_layout = QVBoxLayout()
        
        self.log_text = QTextEdit()
        self.log_text.setMaximumHeight(150)
        self.log_text.setReadOnly(True)
        log_layout.addWidget(self.log_text)
        
        self.log_group.setLayout(log_layout)
        layout.addWidget(self.log_group)
        
        # --- KARGO OPERASYONU GÖREVİ ---
        self.cargo_group = QGroupBox("Kargo Operasyonu")
        self.cargo_group.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)
        cargo_layout = QFormLayout()
        cargo_layout.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)
        cargo_layout.setFormAlignment(Qt.AlignmentFlag.AlignLeft)
        cargo_layout.setHorizontalSpacing(12)
        cargo_layout.setVerticalSpacing(6)
        cargo_layout.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)

        # Direk 1 koordinatları
        self.cargo_pole1_lat = QDoubleSpinBox()
        self.cargo_pole1_lat.setRange(-90, 90)
        self.cargo_pole1_lat.setDecimals(6)
        self.cargo_pole1_lat.setSuffix("°")
        cargo_layout.addRow("Direk 1 Enlem:", self.cargo_pole1_lat)

        self.cargo_pole1_lon = QDoubleSpinBox()
        self.cargo_pole1_lon.setRange(-180, 180)
        self.cargo_pole1_lon.setDecimals(6)
        self.cargo_pole1_lon.setSuffix("°")
        cargo_layout.addRow("Direk 1 Boylam:", self.cargo_pole1_lon)

        # Direk 2 koordinatları
        self.cargo_pole2_lat = QDoubleSpinBox()
        self.cargo_pole2_lat.setRange(-90, 90)
        self.cargo_pole2_lat.setDecimals(6)
        self.cargo_pole2_lat.setSuffix("°")
        cargo_layout.addRow("Direk 2 Enlem:", self.cargo_pole2_lat)

        self.cargo_pole2_lon = QDoubleSpinBox()
        self.cargo_pole2_lon.setRange(-180, 180)
        self.cargo_pole2_lon.setDecimals(6)
        self.cargo_pole2_lon.setSuffix("°")
        cargo_layout.addRow("Direk 2 Boylam:", self.cargo_pole2_lon)

        # Sekiz yarıçapı
        self.cargo_radius = QDoubleSpinBox()
        self.cargo_radius.setRange(5, 200)
        self.cargo_radius.setDecimals(2)
        self.cargo_radius.setSuffix(" m")
        self.cargo_radius.setValue(20)
        cargo_layout.addRow("Sekiz Yarıçapı:", self.cargo_radius)

        # Kalkış irtifası
        self.cargo_altitude = QSpinBox()
        self.cargo_altitude.setRange(10, 500)
        self.cargo_altitude.setValue(50)
        self.cargo_altitude.setSuffix(" m")
        cargo_layout.addRow("Kalkış İrtifası:", self.cargo_altitude)

        # İniş noktası koordinatları
        self.cargo_land_lat = QDoubleSpinBox()
        self.cargo_land_lat.setRange(-90, 90)
        self.cargo_land_lat.setDecimals(6)
        self.cargo_land_lat.setSuffix("°")
        cargo_layout.addRow("İniş Enlem:", self.cargo_land_lat)

        self.cargo_land_lon = QDoubleSpinBox()
        self.cargo_land_lon.setRange(-180, 180)
        self.cargo_land_lon.setDecimals(6)
        self.cargo_land_lon.setSuffix("°")
        cargo_layout.addRow("İniş Boylam:", self.cargo_land_lon)

        # Görev başlat butonu
        self.start_cargo_btn = QPushButton("Kargo Operasyonunu Başlat")
        self.start_cargo_btn.setStyleSheet(ThemeColors.BUTTON_PRIMARY)
        self.start_cargo_btn.clicked.connect(self.start_cargo_mission_handler)
        cargo_layout.addRow(self.start_cargo_btn)

        self.cargo_group.setLayout(cargo_layout)
        layout.addWidget(self.cargo_group)
        
        self.setLayout(layout)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
        
    def start_figure8_mission_handler(self):
        """8 çizme görevini başlat"""
        try:
            # Direk koordinatlarını al
            pole1_lat = self.pole1_lat.value()
            pole1_lon = self.pole1_lon.value()
            pole2_lat = self.pole2_lat.value()
            pole2_lon = self.pole2_lon.value()
            
            # 8 şekli için waypoint'leri hesapla
            waypoints = self.calculate_figure8_waypoints(
                pole1_lat, pole1_lon, pole2_lat, pole2_lon,
                self.figure8_altitude.value()
            )
            
            self.log_message("8 çizme görevi başlatılıyor...")
            self.start_figure8_mission.emit(waypoints)
            
        except Exception as e:
            self.log_message(f"Hata: {str(e)}")
    
    def start_payload_mission_handler(self):
        """Yük bırakma görevini başlat"""
        try:
            # Yük bırakma noktalarını al
            drop1_lat = self.drop1_lat.value()
            drop1_lon = self.drop1_lon.value()
            drop2_lat = self.drop2_lat.value()
            drop2_lon = self.drop2_lon.value()
            
            # Yük bırakma görevi için waypoint'leri hesapla
            waypoints = self.calculate_payload_waypoints(
                drop1_lat, drop1_lon, drop2_lat, drop2_lon,
                self.payload_altitude.value()
            )
            
            self.log_message("Yük bırakma görevi başlatılıyor...")
            self.start_payload_mission.emit(waypoints)
            
        except Exception as e:
            self.log_message(f"Hata: {str(e)}")
    
    def start_cargo_mission_handler(self):
        """Kargo Operasyonu görevini başlat"""
        try:
            pole1_lat = self.cargo_pole1_lat.value()
            pole1_lon = self.cargo_pole1_lon.value()
            pole2_lat = self.cargo_pole2_lat.value()
            pole2_lon = self.cargo_pole2_lon.value()
            radius = self.cargo_radius.value()
            altitude = self.cargo_altitude.value()
            land_lat = self.cargo_land_lat.value()
            land_lon = self.cargo_land_lon.value()
            waypoints = self.calculate_cargo_waypoints(
                pole1_lat, pole1_lon, pole2_lat, pole2_lon, radius, altitude, land_lat, land_lon
            )
            self.log_message("Kargo Operasyonu başlatılıyor...")
            self.start_cargo_mission.emit(waypoints)
        except Exception as e:
            self.log_message(f"Hata: {str(e)}")
    
    def calculate_figure8_waypoints(self, pole1_lat, pole1_lon, pole2_lat, pole2_lon, altitude):
        """8 şekli için waypoint'leri hesapla"""
        waypoints = []
        
        # Direkler arası mesafeyi hesapla
        distance = self.haversine_distance(pole1_lat, pole1_lon, pole2_lat, pole2_lon)
        
        # 8 şeklinin merkezi
        center_lat = (pole1_lat + pole2_lat) / 2
        center_lon = (pole1_lon + pole2_lon) / 2
        
        # 8 şeklinin boyutları
        width = distance * 0.8  # Direkler arası mesafenin %80'i
        height = distance * 0.6  # Direkler arası mesafenin %60'ı
        
        # 8 şekli için noktalar (saat yönünde)
        num_points = 16
        for i in range(num_points):
            angle = (2 * math.pi * i) / num_points
            
            # 8 şekli parametrik denklemi
            if angle <= math.pi:
                # Üst döngü
                x = width * math.cos(angle) / 2
                y = height * math.sin(angle) / 2
            else:
                # Alt döngü
                x = width * math.cos(angle) / 2
                y = -height * math.sin(angle) / 2
            
            # Koordinatları merkeze göre hesapla
            lat_offset = y / 111000  # Yaklaşık metre-enlem dönüşümü
            lon_offset = x / (111000 * math.cos(math.radians(center_lat)))
            
            waypoint = {
                'lat': center_lat + lat_offset,
                'lon': center_lon + lon_offset,
                'alt': altitude,
                'action': 'NAV_WAYPOINT'
            }
            waypoints.append(waypoint)
        
        return waypoints
    
    def calculate_payload_waypoints(self, drop1_lat, drop1_lon, drop2_lat, drop2_lon, altitude):
        """Yük bırakma görevi için waypoint'leri hesapla"""
        waypoints = []
        
        # Kalkış noktası
        takeoff_lat = self.takeoff_lat.value()
        takeoff_lon = self.takeoff_lon.value()
        
        # 1. Kalkış
        waypoints.append({
            'lat': takeoff_lat,
            'lon': takeoff_lon,
            'alt': altitude,
            'action': 'NAV_TAKEOFF'
        })
        
        # 2. İlk yük bırakma noktasına git
        waypoints.append({
            'lat': drop1_lat,
            'lon': drop1_lon,
            'alt': altitude,
            'action': 'NAV_WAYPOINT'
        })
        
        # 3. İlk yükü bırak (magnet1 deaktifleştir)
        waypoints.append({
            'lat': drop1_lat,
            'lon': drop1_lon,
            'alt': altitude,
            'action': 'RELEASE_PAYLOAD_1'
        })
        
        # 4. İkinci yük bırakma noktasına git
        waypoints.append({
            'lat': drop2_lat,
            'lon': drop2_lon,
            'alt': altitude,
            'action': 'NAV_WAYPOINT'
        })
        
        # 5. İkinci yükü bırak (magnet2 deaktifleştir)
        waypoints.append({
            'lat': drop2_lat,
            'lon': drop2_lon,
            'alt': altitude,
            'action': 'RELEASE_PAYLOAD_2'
        })
        
        # 6. Kalkış noktasına geri dön
        waypoints.append({
            'lat': takeoff_lat,
            'lon': takeoff_lon,
            'alt': altitude,
            'action': 'NAV_WAYPOINT'
        })
        
        # 7. İniş
        waypoints.append({
            'lat': takeoff_lat,
            'lon': takeoff_lon,
            'alt': 0,
            'action': 'NAV_LAND'
        })
        
        return waypoints
    
    def calculate_cargo_waypoints(self, pole1_lat, pole1_lon, pole2_lat, pole2_lon, radius, altitude, land_lat, land_lon):
        """Kargo Operasyonu için waypoint'leri hesapla: Kalkış, 2x sekiz, iniş (LIDAR ile)"""
        waypoints = []
        # Kalkış noktası (direk 1'in hemen yakınında başlat)
        start_lat = pole1_lat
        start_lon = pole1_lon
        waypoints.append({
            'lat': start_lat,
            'lon': start_lon,
            'alt': altitude,
            'action': 'NAV_TAKEOFF'
        })
        # İki defa sekiz çizdir
        num_loops = 2
        num_points = 16
        # Direkler arası mesafe ve merkez
        distance = self.haversine_distance(pole1_lat, pole1_lon, pole2_lat, pole2_lon)
        center_lat = (pole1_lat + pole2_lat) / 2
        center_lon = (pole1_lon + pole2_lon) / 2
        for loop in range(num_loops):
            for i in range(num_points):
                angle = (2 * math.pi * i) / num_points
                if angle <= math.pi:
                    x = radius * math.cos(angle)
                    y = radius * math.sin(angle)
                else:
                    x = radius * math.cos(angle)
                    y = -radius * math.sin(angle)
                lat_offset = y / 111000
                lon_offset = x / (111000 * math.cos(math.radians(center_lat)))
                waypoint = {
                    'lat': center_lat + lat_offset,
                    'lon': center_lon + lon_offset,
                    'alt': altitude,
                    'action': 'NAV_WAYPOINT'
                }
                waypoints.append(waypoint)
        # İniş noktasına git
        waypoints.append({
            'lat': land_lat,
            'lon': land_lon,
            'alt': altitude,
            'action': 'NAV_WAYPOINT'
        })
        # LIDAR ile iniş (12.5cm offset)
        waypoints.append({
            'lat': land_lat,
            'lon': land_lon,
            'alt': 0,
            'action': 'NAV_LAND_LIDAR',
            'lidar_offset': 0.125
        })
        return waypoints
    
    def haversine_distance(self, lat1, lon1, lat2, lon2):
        """İki nokta arası mesafeyi hesapla (metre)"""
        R = 6371000  # Dünya yarıçapı (metre)
        
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lat = math.radians(lat2 - lat1)
        delta_lon = math.radians(lon2 - lon1)
        
        a = (math.sin(delta_lat / 2) ** 2 + 
             math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon / 2) ** 2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        
        return R * c
    
    def update_mission_status(self, status, current_waypoint=0, total_waypoints=0, progress=0):
        """Görev durumunu güncelle"""
        self.mission_status = status
        self.current_waypoint = current_waypoint
        self.total_waypoints = total_waypoints
        self.mission_progress = progress
        
        # Durum etiketini güncelle
        status_text = f"Durum: {status}"
        if status == "IDLE":
            self.status_label.setStyleSheet("font-weight: bold; color: #27ae60;")
        elif status == "FIGURE8":
            self.status_label.setStyleSheet("font-weight: bold; color: #3498db;")
        elif status == "PAYLOAD":
            self.status_label.setStyleSheet("font-weight: bold; color: #f39c12;")
        elif status == "COMPLETED":
            self.status_label.setStyleSheet("font-weight: bold; color: #27ae60;")
        elif status == "ERROR":
            self.status_label.setStyleSheet("font-weight: bold; color: #e74c3c;")
        
        self.status_label.setText(status_text)
        
        # Progress bar'ı güncelle
        self.progress_bar.setValue(progress)
        
        # Waypoint bilgisini güncelle
        self.waypoint_info.setText(f"Waypoint: {current_waypoint}/{total_waypoints}")
    
    def log_message(self, message):
        """Log mesajı ekle"""
        from datetime import datetime
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.append(f"[{timestamp}] {message}")
        
        # Log alanını otomatik olarak en alta kaydır
        scrollbar = self.log_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
