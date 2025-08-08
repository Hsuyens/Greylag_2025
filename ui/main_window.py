from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QTabWidget, QSplitter, QMessageBox, QScrollArea, QDialog)
from PyQt6.QtCore import Qt, QTimer
import time
import os
from datetime import datetime
from typing import Optional, Dict, Any
import math

# Core components
from core.mavlink_thread import MAVLinkThread
from core.fpv_thread import FPVThread
from core.data_logger import DataLogger
from core.safety_manager import SafetyManager
from core.log_replay_thread import LogReplayThread
from core.video_replay_thread import VideoReplayThread

# Mission components
from mission.mission_planner import MissionPlanner

# UI components
from ui.panels.flight_panel import FlightPanel
from ui.panels.control_panel import ControlPanel
from ui.panels.map_panel import MapPanel
from ui.panels.mission_panel import MissionPlannerPanel
from ui.panels.connection_panel import ConnectionPanel
from ui.panels.telemetry_panel import TelemetryPanel
from ui.panels.safety_panel import SafetyPanel
from ui.panels.otonomi_panel import OtonomiPanel
from ui.panels.teknofest_panel import TeknofestPanel
from ui.panels.loiter_dialog import LoiterDialog
from ui.panels.loglama_panel import LoglamaPanel
from bin_to_csv import bin_to_csv

class LaggerGCS(QMainWindow):
    # Güvenlik eşikleri - daha esnek değerler
    MAX_ALTITUDE = 3000  # 3000m maksimum irtifa (1000m yerine)
    MAX_WAYPOINT_ALTITUDE = 2000  # 2000m maksimum waypoint irtifası (400m yerine)
    PAYLOAD_DISTANCE_THRESHOLD = 25  # 25m mesafe eşiği (10m yerine)
    PAYLOAD_ALTITUDE_TOLERANCE = 5  # 5m irtifa toleransı (2m yerine)
    HALL_SENSOR_TIMEOUT = 30  # 30 saniye timeout (10s yerine)
    MAX_EVENT_HISTORY = 1000  # Maksimum olay geçmişi sayısı
    
    def __init__(self):
        super().__init__()
        self.last_position = None
        self.flight_start_time = None
        self.event_history = []  # Olay geçmişi - sınırlı boyut
        self.last_telemetry = {}  # <-- Son telemetri değerlerini sakla
        
        # Spam önleme için önceki uyarıları takip et
        self.previous_warnings = {}  # {warning_type: last_message}
        self.warning_cooldown = 30  # 30 saniye bekleme süresi
        
        # Managers and Loggers
        self.data_logger = DataLogger()
        self.mission_planner = MissionPlanner()
        
        # API anahtarını environment variable'dan al
        weather_api_key = os.getenv('WEATHER_API_KEY')
        if not weather_api_key:
            print("UYARI: WEATHER_API_KEY environment variable tanımlı değil!")
            
        self.safety_manager = SafetyManager(weather_api_key=weather_api_key)
        
        # Threads
        self.mavlink_thread = MAVLinkThread()
        self.fpv_thread = FPVThread()
        self.log_replay_thread = None
        self.video_replay_thread = None
        self.log_file_path = None
        self.video_file_path = None

        self.initUI()
        self.connect_signals()
        
    def initUI(self):
        self.setWindowTitle('Lagger GCS')
        self.setGeometry(100, 100, 1920, 1080)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)

        # Left Column
        left_column_widget = QWidget()
        left_column = QVBoxLayout(left_column_widget)
        self.flight_panel = FlightPanel()
        self.flight_panel.setFixedHeight(400)
        self.control_panel = ControlPanel(self.data_logger)
        left_column.addWidget(self.flight_panel, 3)
        left_column.addWidget(self.control_panel, 2)

        # Center Column
        center_column_widget = QWidget()
        center_column = QVBoxLayout(center_column_widget)
        self.map_panel = MapPanel()
        self.map_panel.setFixedHeight(400)
        self.mission_panel = MissionPlannerPanel(self.mission_planner)
        scroll_area = QScrollArea()
        scroll_area.setWidget(self.mission_panel)
        scroll_area.setWidgetResizable(True)
        center_column.addWidget(self.map_panel, 3)
        center_column.addWidget(scroll_area, 1)

        # Right Column
        right_column_tabs = QTabWidget()
        self.connection_panel = ConnectionPanel()
        self.telemetry_panel = TelemetryPanel()
        self.otonomi_panel = OtonomiPanel()
        self.teknofest_panel = TeknofestPanel()
        self.loglama_panel = LoglamaPanel()  # <-- yeni panel
        # self.safety_panel = SafetyPanel(self.safety_manager)  # <-- SafetyPanel kaldırıldı
        teknofest_scroll = QScrollArea()
        teknofest_scroll.setWidget(self.teknofest_panel)
        teknofest_scroll.setWidgetResizable(True)
        right_column_tabs.addTab(self.connection_panel, "Bağlantı")
        right_column_tabs.addTab(self.telemetry_panel, "Telemetri")
        right_column_tabs.addTab(self.otonomi_panel, "Eylemler")
        right_column_tabs.addTab(teknofest_scroll, "Teknofest")
        right_column_tabs.addTab(self.loglama_panel, "Loglama")  # <-- yeni sekme
        # Main Splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(left_column_widget)
        splitter.addWidget(center_column_widget)
        splitter.addWidget(right_column_tabs)
        splitter.setSizes([750, 750, 420])
        main_layout.addWidget(splitter)
        
        # Hava durumu güncelleme timer'ı - daha uzun aralık
        self.weather_timer = QTimer(self)
        self.weather_timer.timeout.connect(self.update_weather)
        self.weather_timer.start(600000)  # 10 dakika (5 dakika yerine)
        
        # Güvenlik kontrol timer'ı - daha uzun aralık
        self.safety_timer = QTimer(self)
        self.safety_timer.timeout.connect(self.check_safety_status)
        self.safety_timer.start(5000)  # 5 saniye (1 saniye yerine)
        
        # MissionPlanner'ın map_panel referansını ayarla
        self.mission_planner.map_panel = self.map_panel
        
        # Varsayılan waypoint listesi (altitude: 50m)
        default_waypoints = [
            {'lat': 41.0897, 'lon': 28.2008, 'alt': 50},
            {'lat': 41.0898477, 'lon': 28.2006602, 'alt': 50},
            {'lat': 41.0899953, 'lon': 28.2005203, 'alt': 50},
            {'lat': 41.0902177, 'lon': 28.200413, 'alt': 50},
            {'lat': 41.0904219, 'lon': 28.2004264, 'alt': 50},
            {'lat': 41.0905553, 'lon': 28.2004881, 'alt': 50},
            {'lat': 41.0906624, 'lon': 28.2005712, 'alt': 50},
            {'lat': 41.0907918, 'lon': 28.2006732, 'alt': 50},
            {'lat': 41.0908565, 'lon': 28.2007697, 'alt': 50},
            {'lat': 41.090905, 'lon': 28.2011721, 'alt': 50},
            {'lat': 41.0908, 'lon': 28.2017, 'alt': 50},
            {'lat': 41.0908, 'lon': 28.2025, 'alt': 50},
            {'lat': 41.0909272, 'lon': 28.2027717, 'alt': 50},
            {'lat': 41.0911476, 'lon': 28.2028833, 'alt': 50},
            {'lat': 41.0917, 'lon': 28.2031, 'alt': 50},
            {'lat': 41.0920471, 'lon': 28.2028994, 'alt': 50},
            {'lat': 41.0922, 'lon': 28.2025, 'alt': 50},
            {'lat': 41.0922, 'lon': 28.2019, 'alt': 50},
            {'lat': 41.0920815, 'lon': 28.2016039, 'alt': 50},
            {'lat': 41.0919178, 'lon': 28.2013115, 'alt': 50},
            {'lat': 41.0916711, 'lon': 28.2013008, 'alt': 50},
            {'lat': 41.0915356, 'lon': 28.2013504, 'alt': 50},
            {'lat': 41.0914, 'lon': 28.2014, 'alt': 50},
            {'lat': 41.0911313, 'lon': 28.2015932, 'alt': 50},
            {'lat': 41.0908626, 'lon': 28.2017863, 'alt': 50},
            {'lat': 41.0908, 'lon': 28.2019, 'alt': 50},
            {'lat': 41.0905654, 'lon': 28.202143, 'alt': 50},
            {'lat': 41.0903, 'lon': 28.2022, 'alt': 50},
            {'lat': 41.0900034, 'lon': 28.2021216, 'alt': 50},
            {'lat': 41.0898195, 'lon': 28.2020491, 'alt': 50},
            {'lat': 41.0897, 'lon': 28.2019, 'alt': 50},
            {'lat': 41.0897, 'lon': 28.2014, 'alt': 50},
            {'lat': 41.0897, 'lon': 28.2008, 'alt': 50},
            {'lat': 41.0898336, 'lon': 28.2005981, 'alt': 50},
            {'lat': 41.089832, 'lon': 28.2004774, 'alt': 50},
            {'lat': 41.0902258, 'lon': 28.2003379, 'alt': 50},
            {'lat': 41.0904502, 'lon': 28.2003459, 'alt': 50},
            {'lat': 41.0906078, 'lon': 28.2003915, 'alt': 50},
            {'lat': 41.090717, 'lon': 28.2004988, 'alt': 50},
            {'lat': 41.0908343, 'lon': 28.2005954, 'alt': 50},
            {'lat': 41.0909111, 'lon': 28.2007161, 'alt': 50},
            {'lat': 41.0909242, 'lon': 28.2008515, 'alt': 50},
            {'lat': 41.0909353, 'lon': 28.2010446, 'alt': 50},
            {'lat': 41.0909373, 'lon': 28.2012632, 'alt': 50},
            {'lat': 41.0908494, 'lon': 28.2016227, 'alt': 50},
            {'lat': 41.0907807, 'lon': 28.202228, 'alt': 50},
            {'lat': 41.0907989, 'lon': 28.202599, 'alt': 50},
            {'lat': 41.090907, 'lon': 28.2028055, 'alt': 50},
            {'lat': 41.0911466, 'lon': 28.2029597, 'alt': 50},
            {'lat': 41.0914073, 'lon': 28.2031073, 'alt': 50},
            {'lat': 41.0917025, 'lon': 28.2031381, 'alt': 50},
            {'lat': 41.0918885, 'lon': 28.2030456, 'alt': 50},
            {'lat': 41.0920633, 'lon': 28.2029597, 'alt': 50},
            {'lat': 41.0921806, 'lon': 28.2027532, 'alt': 50},
            {'lat': 41.0922644, 'lon': 28.2025172, 'alt': 50},
            {'lat': 41.0922665, 'lon': 28.2019378, 'alt': 50},
            {'lat': 41.0921543, 'lon': 28.2015891, 'alt': 50},
            {'lat': 41.0919552, 'lon': 28.2012485, 'alt': 50},
            {'lat': 41.0916853, 'lon': 28.2012217, 'alt': 50},
            {'lat': 41.0915418, 'lon': 28.201227, 'alt': 50},
            {'lat': 41.0913841, 'lon': 28.2012887, 'alt': 50},
            {'lat': 41.0911051, 'lon': 28.2014926, 'alt': 50},
            {'lat': 41.0907756, 'lon': 28.2018051, 'alt': 50},
            {'lat': 41.0905674, 'lon': 28.2020733, 'alt': 50},
            {'lat': 41.0903147, 'lon': 28.2021497, 'alt': 50},
            {'lat': 41.0901763, 'lon': 28.2021202, 'alt': 50},
            {'lat': 41.0900428, 'lon': 28.2020706, 'alt': 50},
            {'lat': 41.089875, 'lon': 28.202021, 'alt': 50},
            {'lat': 41.0897709, 'lon': 28.2018735, 'alt': 50},
            {'lat': 41.0897669, 'lon': 28.201455, 'alt': 50},
            {'lat': 41.089862, 'lon': 28.2005203, 'alt': 50},
            {'lat': 41.0895364, 'lon': 28.200016, 'alt': 50},
            {'lat': 41.0894313, 'lon': 28.1993669, 'alt': 50},
            {'lat': 41.0893464, 'lon': 28.1988305, 'alt': 50},
            {'lat': 41.0892049, 'lon': 28.1984979, 'alt': 50},
            {'lat': 41.0889583, 'lon': 28.1982565, 'alt': 50},
            {'lat': 41.0885499, 'lon': 28.198058, 'alt': 50},
            {'lat': 41.0881294, 'lon': 28.1980741, 'alt': 50},
            {'lat': 41.087899, 'lon': 28.1984979, 'alt': 50},
            {'lat': 41.0878545, 'lon': 28.198809, 'alt': 50},
            {'lat': 41.0878077, 'lon': 28.1990558, 'alt': 50},
            {'lat': 41.0879111, 'lon': 28.1993026, 'alt': 50},
            {'lat': 41.0880122, 'lon': 28.1995386, 'alt': 50},
            {'lat': 41.0881618, 'lon': 28.1995812, 'alt': 50},
            {'lat': 41.0885499, 'lon': 28.2000643, 'alt': 50},
            {'lat': 41.0893302, 'lon': 28.2006007, 'alt': 50},
            {'lat': 41.0899771, 'lon': 28.201029, 'alt': 50},
            {'lat': 41.0904663, 'lon': 28.2013464, 'alt': 50},
            {'lat': 41.0910324, 'lon': 28.2017373, 'alt': 50},
            {'lat': 41.0913877, 'lon': 28.2018346, 'alt': 50},
            {'lat': 41.0913477, 'lon': 28.2019311, 'alt': 50},
        ]
        self.mission_planner.set_waypoints(default_waypoints)
        self.map_panel.update_map()
        self.mission_panel.update_mission_info()

        # Bağlantı paneli başlangıç durumu
        self.connection_panel.connect_btn.setText("Bağlandı")
        from ui.theme import ThemeColors
        self.connection_panel.connect_btn.setStyleSheet(ThemeColors.BUTTON_DANGER)
        self.connection_panel.port_combo.clear()
        self.connection_panel.port_combo.addItem("COM8")
        self.connection_panel.port_combo.setCurrentText("COM8")
        self.connection_panel.port_combo.setEnabled(False)

    def connect_signals(self):
        # Connection Panel Signals
        self.connection_panel.connect_clicked.connect(self.try_connect)
        self.connection_panel.disconnect_clicked.connect(self.try_disconnect)
        self.connection_panel.simulation_clicked.connect(self.start_simulation_mode)
        self.connection_panel.start_payload_mission_btn.clicked.connect(self.start_payload_mission)
        
        # Control Panel Signals
        self.control_panel.emergency_land_clicked.connect(self.handle_emergency_land)
        self.control_panel.return_home_btn.clicked.disconnect()
        self.control_panel.return_home_btn.clicked.connect(self.handle_rth)
        self.control_panel.rtl_btn.clicked.disconnect()
        self.control_panel.rtl_btn.clicked.connect(self.handle_rtl)
        self.control_panel.motor_cut_clicked.connect(self.handle_motor_cut)
        self.control_panel.start_mission_clicked.connect(self.handle_start_mission)
        self.control_panel.pause_mission_clicked.connect(self.handle_pause_mission)
        self.control_panel.abort_mission_clicked.connect(self.handle_abort_mission)
        
        # Link mission panel and map panel
        self.mission_panel.map_panel = self.map_panel
        self.map_panel.mission_planner = self.mission_planner
        
        # Mission Panel Signals
        self.mission_panel.mission_upload_requested.connect(self.handle_mission_upload)
        
        # Map Panel Signals
        self.map_panel.map_clicked.connect(self.mission_panel.on_map_click)
        
        # MAVLink Thread Signals
        self.mavlink_thread.telemetry_received.connect(self.handle_telemetry)
        self.mavlink_thread.attitude_received.connect(self.handle_attitude)
        self.mavlink_thread.position_received.connect(self.handle_position)
        self.mavlink_thread.error_occurred.connect(self.handle_error)
        self.mavlink_thread.emergency_triggered.connect(self.handle_emergency)
        self.mavlink_thread.mission_completed.connect(self.handle_mission_completed)
        
        # FPV Thread Signals
        self.fpv_thread.frame_received.connect(self.flight_panel.hud.update_fpv)
        self.fpv_thread.error_occurred.connect(self.handle_error)
        
        # Flight Panel Signals (Harici pencere seçimi)
        self.flight_panel.external_window_selected.connect(self.handle_external_window_selected)
        
        # Otonomi Panel Sinyalleri
        self.otonomi_panel.arm_clicked.connect(self.handle_arm)
        self.otonomi_panel.disarm_clicked.connect(self.handle_disarm)
        self.otonomi_panel.takeoff_clicked.connect(self.handle_takeoff)
        self.otonomi_panel.land_clicked.connect(self.handle_land)
        self.otonomi_panel.rtl_clicked.connect(self.handle_rtl)
        self.otonomi_panel.emergency_land_clicked.connect(self.handle_emergency_land)
        self.otonomi_panel.start_mission_clicked.connect(self.handle_start_mission)
        self.otonomi_panel.abort_mission_clicked.connect(self.handle_abort_mission)
        
        # Loglama Panel Signals
        self.loglama_panel.log_file_selected.connect(self.on_log_file_selected)
        self.loglama_panel.video_file_selected.connect(self.on_video_file_selected)
        self.loglama_panel.play_clicked.connect(self.on_log_play)
        self.loglama_panel.pause_clicked.connect(self.on_log_pause)
        self.loglama_panel.stop_clicked.connect(self.on_log_stop)
        self.loglama_panel.seek_changed.connect(self.on_log_seek)
        self.loglama_panel.speed_changed.connect(self.on_log_speed)
        
    def try_connect(self, port: str, baud: int) -> None:
        """MAVLink bağlantısını dene"""
        self.control_panel.log_message("Bağlantı deneniyor...")
        
        # Port doğrulaması - daha esnek
        if not port or not port.strip():
            self.control_panel.log_message("HATA: Port adı boş olamaz!")
            return
            
        # Baud rate doğrulaması - daha fazla seçenek
        valid_baud_rates = [9600, 19200, 38400, 57600, 115200, 230400, 460800, 921600]
        if baud not in valid_baud_rates:
            self.control_panel.log_message(f"UYARI: Standart olmayan baud rate: {baud}")
            # Hata vermek yerine uyarı ver ve devam et
            
        if self.mavlink_thread.connect(port, baud):
            self.mavlink_thread.start()
            self.connection_panel.set_status(True)
            self.control_panel.log_message(f"MAVLink bağlantısı başarılı: {port}")
            self.flight_start_time = time.time()
            
            # FPV bağlantısını dene
            if self.fpv_thread.connect():
                self.fpv_thread.start()
                self.control_panel.log_message("FPV bağlantısı başarılı")
            else:
                self.control_panel.log_message("FPV bağlantısı başarısız")
        else:
            self.connection_panel.set_status(False)
            self.control_panel.log_message("MAVLink bağlantısı başarısız.")
            
    def try_disconnect(self) -> None:
        """Bağlantıyı kes"""
        self.mavlink_thread.stop()
        self.fpv_thread.stop()
        self.connection_panel.set_status(False)
        self.control_panel.log_message("Bağlantı kesildi.")
        
    def handle_telemetry(self, data: Dict[str, Any]) -> None:
        """Telemetri verilerini işle"""
        if not isinstance(data, dict):
            self.control_panel.log_message("HATA: Geçersiz telemetri verisi")
            return
        try:
            # Eksik voltage, current, battery, temp, cell_voltage, rssi, roll, pitch gibi değerleri son bilinenle tamamla
            for key in ["voltage", "current", "battery", "temperature", "rssi", "roll", "pitch"]:
                if key not in data and key in self.last_telemetry:
                    data[key] = self.last_telemetry[key]
            # Son telemetriyi güncelle
            self.last_telemetry.update(data)

            battery = data.get('battery', 100)
            voltage = data.get('voltage', 0)
            if battery == 0 and voltage == 0:
                data['battery'] = 100
                data['voltage'] = 12.0
                data['current'] = 0.0
            # Uçuş modu bilgisini hem HUD'a hem Telemetri Paneli'ne ilet
            if 'mode' in data:
                self.flight_panel.hud.update_telemetry({'mode': data['mode']})
                self.telemetry_panel.update_telemetry({'mode': data['mode']})
            self.telemetry_panel.update_telemetry(data)
            # Yeni kutucuklara veri aktarımı:
            if self.data_logger.log_file:
                self.data_logger.log_data(data)
            # HUD'u voltaj ve diğer telemetri ile güncelle
            hud_data = data.copy()
            if 'mode' not in hud_data and hasattr(self.flight_panel.hud, 'telemetry'):
                hud_data['mode'] = self.flight_panel.hud.telemetry.get('mode', 'UNKNOWN')
            self.flight_panel.hud.update_telemetry(hud_data)
        except Exception as e:
            self.control_panel.log_message(f'HATA (telemetry): {e}')

    def handle_attitude(self, data: Dict[str, Any]) -> None:
        """Attitude verilerini işle"""
        if not isinstance(data, dict):
            self.control_panel.log_message("HATA: Geçersiz attitude verisi")
            return
        try:
            import datetime
            print(f"[handle_attitude] {datetime.datetime.now().isoformat()} data: {data}")
            # HUD'a attitude verisini iletirken mevcut mod bilgisini koru
            if hasattr(self.flight_panel.hud, 'telemetry') and 'mode' in self.flight_panel.hud.telemetry:
                data = {**data, 'mode': self.flight_panel.hud.telemetry['mode']}
            self.flight_panel.hud.update_telemetry(data)
            # Sadece roll ve pitch varsa TelemetryPanel'e ilet
            roll = data.get('roll')
            pitch = data.get('pitch')
            update = {}
            if roll is not None:
                update['roll'] = roll
            if pitch is not None:
                update['pitch'] = pitch
            if update:
                self.telemetry_panel.update_telemetry(update)
        except Exception as e:
            self.control_panel.log_message(f'HATA (attitude): {e}')

    def handle_position(self, data: Dict[str, Any]) -> None:
        """Pozisyon verilerini işle"""
        if not isinstance(data, dict):
            self.control_panel.log_message("HATA: Geçersiz pozisyon verisi")
            return
        try:
            lat = data.get('lat')
            lon = data.get('lon')
            alt = data.get('alt', 0)
            # Koordinat doğrulaması - daha esnek
            if lat is None or lon is None:
                self.control_panel.log_message("HATA: Eksik koordinat verisi")
                return
            # GPS koordinat aralığı kontrolü - küçük sapmalara izin ver
            if not (-90.1 <= lat <= 90.1) or not (-180.1 <= lon <= 180.1):
                self.control_panel.log_message("HATA: Geçersiz koordinat değerleri")
                return
            # İrtifa kontrolü - daha yüksek limit
            if alt < -50 or alt > self.MAX_ALTITUDE:
                self.control_panel.log_message(f"HATA: Geçersiz irtifa değeri: {alt}m")
                return
            self.last_position = data
            self.map_panel.update_vehicle_position(lat, lon, data.get('heading', 0))
            # TelemetryPanel'e sadece konum verilerini gönder
            pos_data = {k: v for k, v in data.items() if k in ['lat', 'lon', 'heading', 'satellites']}
            self.telemetry_panel.update_telemetry(pos_data)
            # Ev konumunu ayarla (ilk pozisyon)
            if self.safety_manager.home_position is None:
                self.safety_manager.set_home_position(lat, lon, alt)
                self.map_panel.set_home_position(lat, lon)
                self.control_panel.log_message(f"Ev konumu ayarlandı: {lat:.5f}, {lon:.5f}")
            # Yük bırakma algoritması kontrolü
            if hasattr(self, 'payload_mission_active') and self.payload_mission_active and not self.payload_dropped:
                self.check_payload_mission(data)
            # Teknofest görev durumunu güncelle
            self.update_teknofest_mission_status(data)
        except Exception as e:
            self.control_panel.log_message(f'HATA (position): {e}')

    def handle_error(self, error_message: str) -> None:
        """Hata mesajlarını işle"""
        if not isinstance(error_message, str):
            error_message = str(error_message)
            
        # Spam önleme kontrolü
        current_time = time.time()
        if error_message in self.previous_warnings:
            last_time, _ = self.previous_warnings[error_message]
            if current_time - last_time < self.warning_cooldown:
                return  # Aynı hatayı tekrar verme
        
        # Yeni hatayı kaydet
        self.previous_warnings[error_message] = (current_time, error_message)
            
        self.control_panel.log_message(f"HATA: {error_message}")
        
        # Kritik hataları kaydet
        if any(keyword in error_message.lower() for keyword in ['kritik', 'critical', 'emergency', 'acil']):
            self.data_logger.log_error(f"KRİTİK HATA: {error_message}")
        
    def handle_emergency(self, emergency_data: Dict[str, Any]) -> None:
        """Acil durum verilerini işle"""
        if not isinstance(emergency_data, dict):
            self.control_panel.log_message("HATA: Geçersiz acil durum verisi")
            return
            
        try:
            conditions = emergency_data.get('conditions', [])
            if not conditions:
                return
                
            for condition in conditions:
                severity = condition.get('severity', 'bilinmiyor')
                message = condition.get('message', 'Bilinmeyen durum')
                warning_type = condition.get('type', 'unknown')
                
                # Spam önleme kontrolü
                current_time = time.time()
                if warning_type in self.previous_warnings:
                    last_time, last_message = self.previous_warnings[warning_type]
                    if (current_time - last_time < self.warning_cooldown and 
                        last_message == message):
                        continue  # Aynı uyarıyı tekrar verme
                
                # Yeni uyarıyı kaydet
                self.previous_warnings[warning_type] = (current_time, message)
                
                full_message = f"ACİL DURUM ({severity}): {message}"
                self.control_panel.log_message(full_message)
                # Popup uyarısı kaldırıldı - self.show_emergency_alert(full_message)
                self.data_logger.log_error(full_message)
                
                # Olay geçmişini sınırla
                self.event_history.append({
                    'timestamp': time.time(),
                    'message': full_message,
                    'type': 'emergency',
                    'severity': severity
                })
                
                # Maksimum olay sayısını aşarsa eski olayları sil
                if len(self.event_history) > self.MAX_EVENT_HISTORY:
                    self.event_history = self.event_history[-self.MAX_EVENT_HISTORY:]
                
                # Harita üzerinde acil durum işareti ekle
                if self.last_position:
                    self.map_panel.add_emergency_marker(
                        self.last_position['lat'],
                        self.last_position['lon'],
                        message
                    )
                    
        except Exception as e:
            self.control_panel.log_message(f'HATA (emergency): {e}')

    def check_safety_status(self) -> None:
        """Güvenlik durumunu kontrol et"""
        try:
            # SafetyManager'dan kritik durum kontrolü
            critical_error, error_message, automatic_action = self.safety_manager.get_critical_status()
            
            if critical_error and automatic_action:
                self.control_panel.log_message(f"OTOMATİK AKSİYON: {automatic_action} - {error_message}")
                self.mavlink_thread.handle_automatic_action(automatic_action)
                
        except Exception as e:
            self.control_panel.log_message(f'HATA (safety check): {e}')

    def handle_emergency_land(self) -> None:
        """Acil iniş komutu"""
        self.control_panel.log_message("Acil iniş komutu gönderiliyor...")
        result = self.mavlink_thread.land()
        if result:
            self.control_panel.log_message("Acil iniş komutu başarıyla gönderildi.")
            self.data_logger.log_action("Acil iniş komutu başarıyla gönderildi.")
        else:
            self.control_panel.log_message("Acil iniş komutu gönderilemedi!")
            self.data_logger.log_error("Acil iniş komutu gönderilemedi.")

    def handle_rth(self):
        # RTH: Ev koordinatına git, home yoksa iniş yap
        if hasattr(self.mavlink_thread, 'home_position') and self.mavlink_thread.home_position:
            # Home varsa RTH komutu gönder
            if (
                hasattr(self.mavlink_thread, 'connection') and 
                self.mavlink_thread.is_connected and 
                self.mavlink_thread.connection is not None and 
                hasattr(self.mavlink_thread.connection, 'mav')
            ):
                try:
                    self.mavlink_thread.connection.mav.command_long_send(
                        self.mavlink_thread.connection.target_system,
                        self.mavlink_thread.connection.target_component,
                        20,  # MAV_CMD_NAV_RETURN_TO_HOME
                        0, 0, 0, 0, 0, 0, 0, 0
                    )
                    self.control_panel.log_message("RTH (Ev koordinatına git) komutu gönderildi.")
                except Exception as e:
                    self.control_panel.log_message(f"RTH komutu hatası: {e}")
            else:
                self.control_panel.log_message("Bağlantı yok veya MAVLink nesnesi yok, RTH komutu gönderilemedi.")
        else:
            # Home yoksa LAND komutu gönder
            if hasattr(self.mavlink_thread, 'land'):
                result = self.mavlink_thread.land()
                if result:
                    self.control_panel.log_message("Ev konumu yok, iniş komutu gönderildi.")
                else:
                    self.control_panel.log_message("Ev konumu yok, iniş komutu başarısız.")
            else:
                self.control_panel.log_message("Ev konumu yok, land fonksiyonu bulunamadı!")

    def handle_rtl(self):
        # RTL: Kalkış noktasına dön (MAV_CMD_NAV_RETURN_TO_LAUNCH = 21)
        if hasattr(self.mavlink_thread, 'return_to_home'):
            result = self.mavlink_thread.return_to_home()
            if result:
                self.control_panel.log_message("RTL (Kalkış noktasına dön) komutu gönderildi.")
            else:
                self.control_panel.log_message("RTL komutu başarısız.")
        else:
            self.control_panel.log_message("RTL fonksiyonu bulunamadı!")

    def handle_motor_cut(self) -> None:
        """Motor kesme komutu"""
        self.control_panel.log_message("Motorları acil durdurma komutu gönderiliyor!")
        result = self.mavlink_thread.cut_motors()
        if result:
            self.control_panel.log_message("Motorları kesme komutu başarıyla gönderildi.")
            self.data_logger.log_action("Motorları kesme komutu başarıyla gönderildi.")
        else:
            self.control_panel.log_message("Motorları kesme komutu gönderilemedi!")
            self.data_logger.log_error("Motorları kesme komutu gönderilemedi.")

    def handle_switch_to_manual(self) -> None:
        """Manuel moda geçiş komutu"""
        self.control_panel.log_message("Manuel moda geçiş komutu gönderiliyor...")
        result = self.mavlink_thread.switch_to_manual()
        if result:
            self.control_panel.log_message("Manuel moda geçiş komutu başarıyla gönderildi.")

    def handle_release_payload(self) -> None:
        """Yük bırakma komutu"""
        self.control_panel.log_message("Yük bırakma komutu gönderiliyor...")
        result = self.mavlink_thread.release_payload()
        if result:
            self.control_panel.log_message("Yük bırakma komutu başarıyla gönderildi.")

    def handle_mission_upload(self, waypoints: list) -> None:
        """Görev yükleme"""
        if not waypoints:
            self.control_panel.log_message("HATA: Waypoint listesi boş!")
            return
            
        # Waypoint doğrulaması - daha esnek
        for i, wp in enumerate(waypoints):
            if not isinstance(wp, dict):
                self.control_panel.log_message(f"HATA: Geçersiz waypoint formatı: {i}")
                return
                
            lat = wp.get('lat')
            lon = wp.get('lon')
            alt = wp.get('alt', 0)
            
            if lat is None or lon is None:
                self.control_panel.log_message(f"HATA: Eksik waypoint koordinatları: {i}")
                return
                
            # GPS koordinat aralığı kontrolü - küçük sapmalara izin ver
            if not (-90.1 <= lat <= 90.1) or not (-180.1 <= lon <= 180.1):
                self.control_panel.log_message(f"HATA: Geçersiz waypoint koordinatları: {i}")
                return
                
            # İrtifa kontrolü - daha yüksek limit
            if alt < -50 or alt > self.MAX_WAYPOINT_ALTITUDE:
                self.control_panel.log_message(f"HATA: Geçersiz waypoint irtifası: {i} ({alt}m)")
                return
                
        self.control_panel.log_message(f"Görev yükleniyor: {len(waypoints)} waypoint...")
        
        # MAVLink thread'e görev yükleme komutu gönder
        if hasattr(self.mavlink_thread, 'upload_mission'):
            result = self.mavlink_thread.upload_mission(waypoints)
            if result:
                self.control_panel.log_message("Görev başarıyla araca yüklendi.")
                self.data_logger.log_action(f"Görev yüklendi: {len(waypoints)} waypoint")
                
                # Görev bilgilerini logla
                for i, wp in enumerate(waypoints):
                    self.control_panel.log_message(f"WP {i+1}: {wp['lat']:.6f}, {wp['lon']:.6f}, {wp['alt']}m")
            else:
                self.control_panel.log_message("Görev yükleme başarısız!")
                self.data_logger.log_error("Görev yükleme başarısız.")
        else:
            self.control_panel.log_message("HATA: MAVLink thread'de upload_mission fonksiyonu bulunamadı!")

    def handle_start_mission(self) -> None:
        """Görev başlatma"""
        self.control_panel.log_message("Görev başlatılıyor...")
        self.teknofest_panel.log_message("Görev başlatılıyor...")
        
        if hasattr(self.mavlink_thread, 'start_mission'):
            result = self.mavlink_thread.start_mission()
            if result:
                self.control_panel.log_message("Görev başlatma komutu başarıyla gönderildi.")
                self.teknofest_panel.log_message("Görev başlatma komutu başarıyla gönderildi.")
                self.data_logger.log_action("Görev başlatıldı")
            else:
                self.control_panel.log_message("Görev başlatma başarısız!")
                self.teknofest_panel.log_message("Görev başlatma başarısız!")
                self.data_logger.log_error("Görev başlatma başarısız.")
        else:
            self.control_panel.log_message("HATA: MAVLink thread'de start_mission fonksiyonu bulunamadı!")
            self.teknofest_panel.log_message("HATA: MAVLink thread'de start_mission fonksiyonu bulunamadı!")

    def handle_pause_mission(self):
        # LoiterDialog aç
        dialog = LoiterDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            radius, altitude = dialog.get_values()
            if radius is not None and altitude is not None:
                # Önce irtifaya git
                if hasattr(self.mavlink_thread, 'goto_altitude'):
                    self.mavlink_thread.goto_altitude(altitude)
                # Sonra loiter komutu gönder
                if (
                    hasattr(self.mavlink_thread, 'connection') and 
                    self.mavlink_thread.is_connected and 
                    self.mavlink_thread.connection is not None and 
                    hasattr(self.mavlink_thread.connection, 'mav')
                ):
                    try:
                        self.mavlink_thread.connection.mav.command_long_send(
                            self.mavlink_thread.connection.target_system,
                            self.mavlink_thread.connection.target_component,
                            31,  # MAV_CMD_NAV_LOITER_TURNS
                            0, 0, radius, 0, 0, 0, altitude, 0
                        )
                        self.control_panel.log_message(f"Loiter komutu gönderildi: {radius} m yarıçap, {altitude} m irtifa.")
                        self.teknofest_panel.log_message(f"Görev duraklatıldı. Loiter komutu gönderildi: {radius} m yarıçap, {altitude} m irtifa.")
                    except Exception as e:
                        self.control_panel.log_message(f"Loiter komutu hatası: {e}")
                        self.teknofest_panel.log_message(f"Loiter komutu hatası: {e}")
                else:
                    self.control_panel.log_message("Bağlantı yok veya MAVLink nesnesi yok, loiter komutu gönderilemedi.")
                    self.teknofest_panel.log_message("Bağlantı yok veya MAVLink nesnesi yok, loiter komutu gönderilemedi.")
            else:
                self.control_panel.log_message("Geçersiz yarıçap veya irtifa girdisi.")
                self.teknofest_panel.log_message("Geçersiz yarıçap veya irtifa girdisi.")
        else:
            self.control_panel.log_message("Loiter işlemi iptal edildi.")
            self.teknofest_panel.log_message("Görev duraklatma işlemi iptal edildi.")

    def handle_abort_mission(self) -> None:
        """Görev iptal etme"""
        self.control_panel.log_message("Görev iptal ediliyor...")
        self.teknofest_panel.log_message("Görev iptal ediliyor...")
        
        if hasattr(self.mavlink_thread, 'abort_mission'):
            result = self.mavlink_thread.abort_mission()
            if result:
                self.control_panel.log_message("Görev iptal komutu başarıyla gönderildi.")
                self.teknofest_panel.log_message("Görev iptal komutu başarıyla gönderildi.")
                self.teknofest_panel.update_mission_status("IDLE", 0, 0, 0)
                self.data_logger.log_action("Görev iptal edildi")
            else:
                self.control_panel.log_message("Görev iptal başarısız!")
                self.teknofest_panel.log_message("Görev iptal başarısız!")
                self.data_logger.log_error("Görev iptal başarısız.")
        else:
            self.control_panel.log_message("HATA: MAVLink thread'de abort_mission fonksiyonu bulunamadı!")
            self.teknofest_panel.log_message("HATA: MAVLink thread'de abort_mission fonksiyonu bulunamadı!")

    def closeEvent(self, event) -> None:
        """Uygulama kapatılırken kaynakları temizle"""
        try:
            # Timer'ları durdur
            if hasattr(self, 'weather_timer'):
                self.weather_timer.stop()
            if hasattr(self, 'safety_timer'):
                self.safety_timer.stop()
            if hasattr(self, 'sim_timer'):
                self.sim_timer.stop()
                
            # Thread'leri durdur
            self.mavlink_thread.stop()
            self.fpv_thread.stop()
            
            # Log dosyasını kapat
            if self.data_logger.log_file:
                self.data_logger.stop_logging()
                
        except Exception as e:
            print(f"Uygulama kapatma hatası: {e}")
            
        event.accept()

    def start_simulation_mode(self) -> None:
        """Simülasyon modunu başlat"""
        self.control_panel.log_message("Simülasyon modu başlatıldı.")
        self.sim_timer = QTimer(self)
        self.sim_timer.timeout.connect(self.send_fake_simulation_data)
        self.sim_time = 0
        self.sim_timer.start(1000)  # 1 saniye (500ms yerine)

    def send_fake_simulation_data(self) -> None:
        """Sahte simülasyon verisi gönder"""
        # Basit bir dairesel hareket ve değişen telemetri verisi simülasyonu
        self.sim_time += 1.0  # 1 saniye artır
        lat = 40.0 + 0.0001 * math.sin(self.sim_time)
        lon = 29.0 + 0.0001 * math.cos(self.sim_time)
        alt = 100 + 10 * math.sin(self.sim_time / 2)
        telemetry = {
            'lat': lat,
            'lon': lon,
            'alt': alt,
            'groundspeed': 10 + 2 * math.sin(self.sim_time),
            'verticalspeed': 0.5 * math.cos(self.sim_time),
            'heading': (self.sim_time * 36) % 360,
            'roll': 5 * math.sin(self.sim_time),
            'pitch': 2 * math.cos(self.sim_time),
            'yaw': (self.sim_time * 36) % 360,
            'voltage': 12.5 - 0.01 * self.sim_time,
            'current': 2.0 + 0.2 * math.sin(self.sim_time),
            'battery': max(0, 100 - self.sim_time),
            'rssi': -60 + 5 * math.sin(self.sim_time),
            'ping': 50 + 10 * math.cos(self.sim_time),
            'data_loss': 0,
            'gps_fix': 3,
            'satellites': 12,
            'system_status': 'SIM',
            'flight_mode': 'AUTO'
        }
        self.handle_telemetry(telemetry)
        self.handle_position(telemetry) 

    def start_payload_mission(self) -> None:
        """Yük bırakma görevini başlat"""
        try:
            # Giriş değerlerini al ve doğrula
            lat_text = self.connection_panel.payload_lat_input.text().strip()
            lon_text = self.connection_panel.payload_lon_input.text().strip()
            drop_alt_text = self.connection_panel.payload_drop_alt_input.text().strip()
            cruise_alt_text = self.connection_panel.cruise_alt_input.text().strip()
            
            if not all([lat_text, lon_text, drop_alt_text, cruise_alt_text]):
                self.connection_panel.payload_status_label.setText("Durum: Tüm alanları doldurun!")
                return
                
            lat = float(lat_text)
            lon = float(lon_text)
            drop_alt = float(drop_alt_text)
            cruise_alt = float(cruise_alt_text)
            
            # Değer doğrulaması - daha esnek
            if not (-90.1 <= lat <= 90.1) or not (-180.1 <= lon <= 180.1):
                self.connection_panel.payload_status_label.setText("Durum: Geçersiz koordinat değerleri!")
                return
                
            if drop_alt < -50 or drop_alt > self.MAX_WAYPOINT_ALTITUDE or cruise_alt < -50 or cruise_alt > self.MAX_WAYPOINT_ALTITUDE:
                self.connection_panel.payload_status_label.setText("Durum: Geçersiz irtifa değerleri!")
                return
                
            if drop_alt >= cruise_alt:
                self.connection_panel.payload_status_label.setText("Durum: Bırakma irtifası seyir irtifasından düşük olmalı!")
                return
                
        except ValueError:
            self.connection_panel.payload_status_label.setText("Durum: Hatalı giriş!")
            return
            
        self.connection_panel.payload_status_label.setText("Durum: Görev başlatıldı, hedefe ilerleniyor...")
        self.payload_mission_active = True
        self.payload_target = {'lat': lat, 'lon': lon, 'drop_alt': drop_alt, 'cruise_alt': cruise_alt}
        self.payload_dropped = False
        self.payload_goto_drop_alt_sent = False
        self.payload_goto_cruise_alt_sent = False
        
        # Hall effect sensör portu (gerekirse arayüzden alınabilir)
        self.hall_sensor_port = 'COM6'  # Gerekirse değiştir
        self.hall_sensor_threshold = 100  # Manyetik eşik (örnek)
        
        # Sensör bağlantısı
        if not hasattr(self.mavlink_thread, 'hall_serial_port') or self.mavlink_thread.hall_serial_port is None:
            self.mavlink_thread.connect_hall_sensor(self.hall_sensor_port)

    def check_payload_mission(self, pos_data: Dict[str, Any]) -> None:
        """Yük bırakma algoritmasının adımlarını kontrol eder"""
        try:
            lat = pos_data['lat']
            lon = pos_data['lon']
            alt = pos_data.get('alt', 0)
            target = self.payload_target
            
            # 1. Hedefe yaklaşma kontrolü - daha büyük mesafe eşiği
            dist = self.haversine(lat, lon, target['lat'], target['lon'])
            if dist > self.PAYLOAD_DISTANCE_THRESHOLD:
                self.connection_panel.payload_status_label.setText(f"Durum: Hedefe yaklaşılıyor ({dist:.1f} m)")
                return
                
            # 2. Yük bırakma irtifasına inme (otomatik komut) - daha büyük tolerans
            if abs(alt - target['drop_alt']) > self.PAYLOAD_ALTITUDE_TOLERANCE:
                self.connection_panel.payload_status_label.setText(f"Durum: Yük bırakma irtifasına iniliyor ({alt:.1f} m)")
                if not self.payload_goto_drop_alt_sent:
                    # Son konumu mavlink_thread'e aktar
                    self.mavlink_thread.last_lat = lat
                    self.mavlink_thread.last_lon = lon
                    self.mavlink_thread.goto_altitude(target['drop_alt'])
                    self.payload_goto_drop_alt_sent = True
                return
                
            # 3. Yükü bırak
            self.connection_panel.payload_status_label.setText("Durum: Yük bırakılıyor...")
            result = self.mavlink_thread.release_payload()
            if result:
                self.connection_panel.payload_status_label.setText("Durum: Yük bırakıldı, doğrulama bekleniyor...")
                self.payload_dropped = True
                # 4. Hall effect sensör doğrulaması başlat
                self.check_hall_effect_sensor()
            else:
                self.connection_panel.payload_status_label.setText("Durum: Yük bırakma komutu başarısız!")
                
        except Exception as e:
            self.control_panel.log_message(f"Yük bırakma algoritması hatası: {e}")

    def check_hall_effect_sensor(self) -> None:
        """Hall effect sensöründen manyetik değer okuma ve yük bırakma doğrulaması"""
        import threading
        def sensor_check_loop():
            import time
            timeout = self.HALL_SENSOR_TIMEOUT  # Daha uzun timeout
            start = time.time()
            while time.time() - start < timeout:
                value = self.mavlink_thread.read_hall_effect_value()
                if value is not None and value < self.hall_sensor_threshold:
                    # Başarılı
                    from PyQt6.QtCore import QTimer
                    QTimer.singleShot(0, self.on_payload_verified)
                    return
                time.sleep(1.0)  # 1 saniye bekle (0.5s yerine)
            # Zaman aşımı
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(0, lambda: self.connection_panel.payload_status_label.setText("Durum: Yük bırakma doğrulaması başarısız!"))
        threading.Thread(target=sensor_check_loop, daemon=True).start()

    def on_payload_verified(self) -> None:
        """Yük bırakma doğrulandı"""
        self.connection_panel.payload_status_label.setText("Durum: Yük bırakma doğrulandı! Seyir irtifasına çıkılıyor...")
        self.return_to_cruise_altitude()

    def return_to_cruise_altitude(self) -> None:
        """Seyir irtifasına çıkış komutu (otomatik)"""
        if not self.payload_goto_cruise_alt_sent and self.last_position:
            lat = self.last_position['lat']
            lon = self.last_position['lon']
            cruise_alt = self.payload_target['cruise_alt']
            self.mavlink_thread.last_lat = lat
            self.mavlink_thread.last_lon = lon
            self.mavlink_thread.goto_altitude(cruise_alt)
            self.payload_goto_cruise_alt_sent = True
        self.connection_panel.payload_status_label.setText("Durum: Seyir irtifasına çıkıldı. Görev tamamlandı.")
        self.payload_mission_active = False

    @staticmethod
    def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """İki GPS noktası arası mesafe (metre)"""
        R = 6371000  # Dünya yarıçapı (m)
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
        c = 2 * math.asin(math.sqrt(a))
        return R * c 

    def update_weather(self) -> None:
        """Hava durumu güncelle"""
        # Son konumdan hava durumu çek
        if self.last_position:
            weather = self.safety_manager.update_weather(self.last_position['lat'], self.last_position['lon'])
            # self.safety_panel.update_weather_info(weather) 

    def handle_arm(self):
        if hasattr(self.mavlink_thread, 'connection') and self.mavlink_thread.is_connected:
            try:
                self.mavlink_thread.connection.mav.command_long_send(
                    self.mavlink_thread.connection.target_system,
                    self.mavlink_thread.connection.target_component,
                    400,  # MAV_CMD_COMPONENT_ARM_DISARM
                    0, 1, 0, 0, 0, 0, 0, 0
                )
                self.control_panel.log_message("Arm komutu gönderildi.")
            except Exception as e:
                self.control_panel.log_message(f"Arm komutu hatası: {e}")
        else:
            self.control_panel.log_message("Bağlantı yok, arm komutu gönderilemedi.")

    def handle_disarm(self):
        if hasattr(self.mavlink_thread, 'connection') and self.mavlink_thread.is_connected:
            try:
                self.mavlink_thread.connection.mav.command_long_send(
                    self.mavlink_thread.connection.target_system,
                    self.mavlink_thread.connection.target_component,
                    400,  # MAV_CMD_COMPONENT_ARM_DISARM
                    0, 0, 0, 0, 0, 0, 0, 0
                )
                self.control_panel.log_message("Disarm komutu gönderildi.")
            except Exception as e:
                self.control_panel.log_message(f"Disarm komutu hatası: {e}")
        else:
            self.control_panel.log_message("Bağlantı yok, disarm komutu gönderilemedi.")

    def handle_takeoff(self):
        alt = 20  # Sabit kalkış irtifası
        if hasattr(self.mavlink_thread, 'arm_and_takeoff'):
            result = self.mavlink_thread.arm_and_takeoff(alt)
            if result:
                self.control_panel.log_message(f"Takeoff ({alt} m) komutu gönderildi.")
            else:
                self.control_panel.log_message("Takeoff komutu başarısız.")
        else:
            self.control_panel.log_message("Takeoff fonksiyonu bulunamadı!")

    def handle_land(self):
        if hasattr(self.mavlink_thread, 'land'):
            result = self.mavlink_thread.land()
            if result:
                self.control_panel.log_message("İniş komutu gönderildi.")
            else:
                self.control_panel.log_message("İniş komutu başarısız.")
        else:
            self.control_panel.log_message("Land fonksiyonu bulunamadı!")

    def handle_loiter(self):
        if (
            hasattr(self.mavlink_thread, 'connection') and 
            self.mavlink_thread.is_connected and 
            self.mavlink_thread.connection is not None and 
            hasattr(self.mavlink_thread.connection, 'mav')
        ):
            try:
                self.mavlink_thread.connection.mav.command_long_send(
                    self.mavlink_thread.connection.target_system,
                    self.mavlink_thread.connection.target_component,
                    17,  # MAV_CMD_NAV_LOITER_UNLIM
                    0, 0, 0, 0, 0, 0, 0, 0
                )
                self.control_panel.log_message("Loiter (bekle) komutu gönderildi.")
            except Exception as e:
                self.control_panel.log_message(f"Loiter komutu hatası: {e}")
        else:
            self.control_panel.log_message("Bağlantı yok veya MAVLink nesnesi yok, loiter komutu gönderilemedi.")

    def handle_goto_altitude(self, alt):
        if hasattr(self.mavlink_thread, 'goto_altitude'):
            result = self.mavlink_thread.goto_altitude(alt)
            if result:
                self.control_panel.log_message(f"{alt} m irtifaya git komutu gönderildi.")
            else:
                self.control_panel.log_message("İrtifaya git komutu başarısız.")
        else:
            self.control_panel.log_message("goto_altitude fonksiyonu bulunamadı!")

    def handle_goto_location(self, lat, lon, alt):
        if (
            hasattr(self.mavlink_thread, 'connection') and 
            self.mavlink_thread.is_connected and 
            self.mavlink_thread.connection is not None and 
            hasattr(self.mavlink_thread.connection, 'mav')
        ):
            try:
                self.mavlink_thread.connection.mav.command_long_send(
                    self.mavlink_thread.connection.target_system,
                    self.mavlink_thread.connection.target_component,
                    16,  # MAV_CMD_NAV_WAYPOINT
                    0, 0, 0, 0, 0, 0, alt, lat, lon
                )
                self.control_panel.log_message(f"Konuma git komutu gönderildi: {lat}, {lon}, {alt} m")
            except Exception as e:
                self.control_panel.log_message(f"Konuma git komutu hatası: {e}")
        else:
            self.control_panel.log_message("Bağlantı yok veya MAVLink nesnesi yok, konuma git komutu gönderilemedi.")
    
    # Teknofest Panel İşleyicileri
    def handle_figure8_mission(self, waypoints):
        """8 çizme görevini başlat"""
        try:
            self.teknofest_panel.update_mission_status("FIGURE8", 0, len(waypoints), 0)
            self.teknofest_panel.log_message(f"8 çizme görevi başlatıldı. {len(waypoints)} waypoint yüklendi.")
            
            # Waypoint'leri mission planner'a yükle
            if hasattr(self.mission_planner, 'set_waypoints'):
                self.mission_planner.set_waypoints(waypoints)
                self.teknofest_panel.log_message("Waypoint'ler mission planner'a yüklendi.")
            
            # Görevi başlat
            self.handle_start_mission()
            
        except Exception as e:
            self.teknofest_panel.log_message(f"8 çizme görevi hatası: {str(e)}")
            self.teknofest_panel.update_mission_status("ERROR")
    
    def handle_payload_mission(self, waypoints):
        """Yük bırakma görevini başlat"""
        try:
            self.teknofest_panel.update_mission_status("PAYLOAD", 0, len(waypoints), 0)
            self.teknofest_panel.log_message(f"Yük bırakma görevi başlatıldı. {len(waypoints)} waypoint yüklendi.")
            
            # Waypoint'leri mission planner'a yükle
            if hasattr(self.mission_planner, 'set_waypoints'):
                self.mission_planner.set_waypoints(waypoints)
                self.teknofest_panel.log_message("Waypoint'ler mission planner'a yüklendi.")
            
            # Görevi başlat
            self.handle_start_mission()
            
        except Exception as e:
            self.teknofest_panel.log_message(f"Yük bırakma görevi hatası: {str(e)}")
            self.teknofest_panel.update_mission_status("ERROR")
    
    def handle_resume_mission(self):
        """Görevi devam ettir"""
        try:
            if hasattr(self.mavlink_thread, 'resume_mission'):
                result = self.mavlink_thread.resume_mission()
                if result:
                    self.teknofest_panel.log_message("Görev devam ettiriliyor...")
                else:
                    self.teknofest_panel.log_message("Görev devam ettirme başarısız!")
            else:
                self.teknofest_panel.log_message("Resume mission fonksiyonu bulunamadı!")
        except Exception as e:
            self.teknofest_panel.log_message(f"Görev devam ettirme hatası: {str(e)}")
    
    def handle_activate_magnet1(self):
        """Elektromıknatıs 1'i aktifleştir"""
        try:
            if hasattr(self.mavlink_thread, 'activate_magnet1'):
                result = self.mavlink_thread.activate_magnet1()
                if result:
                    self.teknofest_panel.log_message("Elektromıknatıs 1 aktifleştirildi.")
                else:
                    self.teknofest_panel.log_message("Elektromıknatıs 1 aktifleştirme başarısız!")
            else:
                self.teknofest_panel.log_message("Elektromıknatıs 1 fonksiyonu bulunamadı!")
        except Exception as e:
            self.teknofest_panel.log_message(f"Elektromıknatıs 1 hatası: {str(e)}")
    
    def handle_deactivate_magnet1(self):
        """Elektromıknatıs 1'i deaktifleştir"""
        try:
            if hasattr(self.mavlink_thread, 'deactivate_magnet1'):
                result = self.mavlink_thread.deactivate_magnet1()
                if result:
                    self.teknofest_panel.log_message("Elektromıknatıs 1 deaktifleştirildi.")
                else:
                    self.teknofest_panel.log_message("Elektromıknatıs 1 deaktifleştirme başarısız!")
            else:
                self.teknofest_panel.log_message("Elektromıknatıs 1 deaktifleştirme fonksiyonu bulunamadı!")
        except Exception as e:
            self.teknofest_panel.log_message(f"Elektromıknatıs 1 deaktifleştirme hatası: {str(e)}")
    
    def handle_activate_magnet2(self):
        """Elektromıknatıs 2'yi aktifleştir"""
        try:
            if hasattr(self.mavlink_thread, 'activate_magnet2'):
                result = self.mavlink_thread.activate_magnet2()
                if result:
                    self.teknofest_panel.log_message("Elektromıknatıs 2 aktifleştirildi.")
                else:
                    self.teknofest_panel.log_message("Elektromıknatıs 2 aktifleştirme başarısız!")
            else:
                self.teknofest_panel.log_message("Elektromıknatıs 2 fonksiyonu bulunamadı!")
        except Exception as e:
            self.teknofest_panel.log_message(f"Elektromıknatıs 2 hatası: {str(e)}")
    
    def handle_deactivate_magnet2(self):
        """Elektromıknatıs 2'yi deaktifleştir"""
        try:
            if hasattr(self.mavlink_thread, 'deactivate_magnet2'):
                result = self.mavlink_thread.deactivate_magnet2()
                if result:
                    self.teknofest_panel.log_message("Elektromıknatıs 2 deaktifleştirildi.")
                else:
                    self.teknofest_panel.log_message("Elektromıknatıs 2 deaktifleştirme başarısız!")
            else:
                self.teknofest_panel.log_message("Elektromıknatıs 2 deaktifleştirme fonksiyonu bulunamadı!")
        except Exception as e:
            self.teknofest_panel.log_message(f"Elektromıknatıs 2 deaktifleştirme hatası: {str(e)}")
    
    def update_teknofest_mission_status(self, pos_data: Dict[str, Any]) -> None:
        """Teknofest görev durumunu güncelle"""
        try:
            # Görev aktif değilse güncelleme yapma
            if self.teknofest_panel.mission_status == "IDLE":
                return
            
            # Mevcut waypoint'leri al
            if not hasattr(self.mission_planner, 'waypoints') or not self.mission_planner.waypoints:
                return
            
            current_lat = pos_data.get('lat', 0)
            current_lon = pos_data.get('lon', 0)
            current_alt = pos_data.get('alt', 0)
            
            # En yakın waypoint'i bul
            min_distance = float('inf')
            closest_waypoint_index = 0
            
            for i, wp in enumerate(self.mission_planner.waypoints):
                distance = self.haversine(current_lat, current_lon, wp['lat'], wp['lon'])
                if distance < min_distance:
                    min_distance = distance
                    closest_waypoint_index = i
            
            # Progress hesapla
            total_waypoints = len(self.mission_planner.waypoints)
            progress = int((closest_waypoint_index / total_waypoints) * 100)
            
            # Teknofest panelini güncelle
            self.teknofest_panel.update_mission_status(
                self.teknofest_panel.mission_status,
                closest_waypoint_index + 1,
                total_waypoints,
                progress
            )
            
            # Waypoint'e yaklaştığında log mesajı
            if min_distance < 10:  # 10m yakınlık
                self.teknofest_panel.log_message(f"Waypoint {closest_waypoint_index + 1}/{total_waypoints} yaklaşıldı")
            
        except Exception as e:
            self.teknofest_panel.log_message(f"Görev durumu güncelleme hatası: {str(e)}")
    
    def handle_mission_completed(self):
        """Görev tamamlandığında çağrılır"""
        try:
            self.teknofest_panel.log_message("🎉 Görev başarıyla tamamlandı!")
            self.teknofest_panel.update_mission_status("COMPLETED", 100, 100, 100)
            self.control_panel.log_message("Görev tamamlandı.")
            self.data_logger.log_action("Görev tamamlandı")
        except Exception as e:
            self.teknofest_panel.log_message(f"Görev tamamlama hatası: {str(e)}") 

    def toggle_data_logging(self):
        if hasattr(self, 'data_logger') and self.data_logger:
            if self.data_logger.log_file is None:
                if self.data_logger.start_logging():
                    self.control_panel.log_message("Veri kaydı başlatıldı.")
            else:
                if self.data_logger.stop_logging():
                    self.control_panel.log_message("Veri kaydı durduruldu.")

    def handle_figure8_mission_btn(self):
        # Örnek: 8 çizme görevi başlat
        if hasattr(self, 'mission_planner') and hasattr(self, 'handle_figure8_mission'):
            waypoints = []  # Burada uygun şekilde waypoint oluşturulmalı veya kullanıcıdan alınmalı
            self.handle_figure8_mission(waypoints)
        else:
            self.control_panel.log_message("8 çizme görevi başlatılamadı.")

    def handle_payload_mission_btn(self):
        # Örnek: Yük bırakma görevi başlat
        if hasattr(self, 'mission_planner') and hasattr(self, 'handle_payload_mission'):
            waypoints = []  # Burada uygun şekilde waypoint oluşturulmalı veya kullanıcıdan alınmalı
            self.handle_payload_mission(waypoints)
        else:
            self.control_panel.log_message("Yük bırakma görevi başlatılamadı.")
            
    def handle_external_window_selected(self, title: str, hwnd: int):
        """Harici pencere seçildiğinde çağrılır"""
        try:
            self.control_panel.log_message(f"Harici pencere seçildi: {title}")
            # FPV thread'i durdur (harici pencere kullanılacak)
            if hasattr(self, 'fpv_thread') and self.fpv_thread.isRunning():
                self.fpv_thread.stop()
                self.control_panel.log_message("FPV thread durduruldu, harici pencere kullanılıyor")
        except Exception as e:
            self.control_panel.log_message(f"Harici pencere seçimi hatası: {e}") 

    def on_log_file_selected(self, path):
        self.log_file_path = path
        # Otomatik .bin'den .csv'ye çevirme
        if path.lower().endswith('.bin'):
            csv_path = os.path.splitext(path)[0] + '.csv'
            QMessageBox.information(self, 'Log Dönüştürülüyor', '.bin log dosyası CSV formatına çevrilecek. Lütfen bekleyin...')
            try:
                bin_to_csv(path, csv_path)
                self.log_file_path = csv_path
                QMessageBox.information(self, 'Dönüştürme Başarılı', f'Log dosyası CSV olarak kaydedildi:\n{csv_path}')
            except Exception as e:
                QMessageBox.critical(self, 'Dönüştürme Hatası', f'Log dosyası dönüştürülemedi:\n{e}')
                return
        self._try_prepare_replay()
    def on_video_file_selected(self, path):
        self.video_file_path = path
        self._try_prepare_replay()
    def _try_prepare_replay(self):
        # Sadece log dosyası seçildiyse log thread'i başlat
        if self.log_file_path and not self.log_replay_thread:
            self._init_log_replay_thread()
        # Sadece video dosyası seçildiyse video thread'i başlat
        if self.video_file_path and not self.video_replay_thread:
            self._init_video_replay_thread()
    def _init_log_replay_thread(self):
        if self.log_replay_thread:
            self.log_replay_thread.stop()
            # Use non-blocking wait with timeout to prevent UI freeze
            if not self.log_replay_thread.wait(1000):  # Wait max 1 second
                print("[WARNING] Log replay thread did not stop gracefully, forcing termination")
                self.log_replay_thread.terminate()
                self.log_replay_thread.wait(500)  # Give it 500ms to terminate
                
        # Verify log file exists and is readable before creating thread
        if not os.path.exists(self.log_file_path):
            QMessageBox.critical(self, 'Log Hatası', f'Log dosyası bulunamadı:\n{self.log_file_path}')
            return
            
        self.log_replay_thread = LogReplayThread(self.log_file_path)
        
        # Set the seek slider range based on log length
        self.loglama_panel.set_log_length(len(self.log_replay_thread._rows))
        
        # Connect signals
        self.log_replay_thread.telemetry_updated.connect(self.flight_panel.hud.update_telemetry)
        self.log_replay_thread.position_updated.connect(self.map_panel.update_vehicle_position)
        self.log_replay_thread.seek_updated.connect(self.loglama_panel.update_seek_position)
        self.log_replay_thread.finished.connect(self.on_log_replay_finished)
        
        # Enable replay mode for map centering
        self.map_panel.set_replay_mode(True)
    def _init_video_replay_thread(self):
        if self.video_replay_thread:
            self.video_replay_thread.stop()
            # Use non-blocking wait with timeout to prevent UI freeze
            if not self.video_replay_thread.wait(1000):  # Wait max 1 second
                print("[WARNING] Video replay thread did not stop gracefully, forcing termination")
                self.video_replay_thread.terminate()
                self.video_replay_thread.wait(500)  # Give it 500ms to terminate
        self.video_replay_thread = VideoReplayThread(self.video_file_path)
        self.video_replay_thread.frame_ready.connect(self.flight_panel.hud.update_fpv)
        self.video_replay_thread.finished.connect(self.on_video_replay_finished)
    def on_log_play(self):
        if not self.log_replay_thread and self.log_file_path:
            self._init_log_replay_thread()
        if not self.video_replay_thread and self.video_file_path:
            self._init_video_replay_thread()
        if self.log_replay_thread and not self.log_replay_thread.isRunning():
            self.log_replay_thread.start()
        elif self.log_replay_thread:
            self.log_replay_thread.resume()
        if self.video_replay_thread and not self.video_replay_thread.isRunning():
            self.video_replay_thread.start()
        elif self.video_replay_thread:
            self.video_replay_thread.resume()
    def on_log_pause(self):
        if self.log_replay_thread:
            self.log_replay_thread.pause()
        if self.video_replay_thread:
            self.video_replay_thread.pause()
    def on_log_stop(self):
        if self.log_replay_thread:
            self.log_replay_thread.stop()
        if self.video_replay_thread:
            self.video_replay_thread.stop()
        # Disable replay mode when stopping
        self.map_panel.set_replay_mode(False)
    def on_log_seek(self, idx):
        if self.log_replay_thread:
            self.log_replay_thread.seek(idx)
        if self.video_replay_thread:
            self.video_replay_thread.seek(idx)
    def on_log_speed(self, speed):
        if self.log_replay_thread:
            self.log_replay_thread.set_speed(speed)
        if self.video_replay_thread:
            self.video_replay_thread.set_speed(speed)
    def on_log_replay_finished(self):
        # Disable replay mode when replay finishes
        self.map_panel.set_replay_mode(False)
    def on_video_replay_finished(self):
        pass 