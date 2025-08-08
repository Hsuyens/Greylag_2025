from PyQt6.QtWidgets import QWidget, QVBoxLayout, QGroupBox, QGridLayout, QPushButton, QTextEdit
from PyQt6.QtCore import pyqtSignal, QTimer
from datetime import datetime

from ui.theme import ThemeColors
from core.data_logger import DataLogger

class ControlPanel(QWidget):
    emergency_land_clicked = pyqtSignal()
    rtl_clicked = pyqtSignal()
    motor_cut_clicked = pyqtSignal()
    start_mission_clicked = pyqtSignal()
    pause_mission_clicked = pyqtSignal()
    abort_mission_clicked = pyqtSignal()
    
    def __init__(self, logger: DataLogger):
        super().__init__()
        self.logger = logger
        self.initUI()
        
    def initUI(self):
        layout = QVBoxLayout()
        layout.setSpacing(10)
        
        # Mission Control Group
        mission_group = QGroupBox("Görev Kontrolleri")
        mission_group.setStyleSheet(ThemeColors.PANEL_STYLE)
        mission_layout = QGridLayout()
        
        self.start_mission_btn = QPushButton("Görevi Başlat")
        self.start_mission_btn.setStyleSheet(ThemeColors.BUTTON_SUCCESS)
        self.start_mission_btn.setShortcut("F5")
        self.start_mission_btn.clicked.connect(self.start_mission_clicked.emit)
        
        self.pause_mission_btn = QPushButton("Görevi Duraklat")
        self.pause_mission_btn.setStyleSheet(ThemeColors.BUTTON_WARNING)
        self.pause_mission_btn.setShortcut("F6")
        self.pause_mission_btn.clicked.connect(self.pause_mission_clicked.emit)
        
        self.abort_mission_btn = QPushButton("Görevi İptal Et")
        self.abort_mission_btn.setStyleSheet(ThemeColors.BUTTON_DANGER)
        self.abort_mission_btn.setShortcut("F7")
        self.abort_mission_btn.clicked.connect(self.abort_mission_clicked.emit)
        
        mission_layout.addWidget(self.start_mission_btn, 0, 0)
        mission_layout.addWidget(self.pause_mission_btn, 0, 1)
        mission_layout.addWidget(self.abort_mission_btn, 0, 2)
        mission_group.setLayout(mission_layout)
        
        # Emergency Controls Group
        emergency_group = QGroupBox("Acil Durum Kontrolleri")
        emergency_group.setStyleSheet(ThemeColors.PANEL_STYLE)
        emergency_layout = QGridLayout()
        
        self.manual_mode_btn = QPushButton("Manuel Moda Geç")
        self.manual_mode_btn.setStyleSheet(ThemeColors.BUTTON_PRIMARY)
        self.manual_mode_btn.clicked.connect(self.switch_to_manual)
        self.return_home_btn = QPushButton("Eve Dön (RTH)")
        self.return_home_btn.setStyleSheet(ThemeColors.BUTTON_PRIMARY)
        self.return_home_btn.clicked.connect(self.return_home)
        self.release_payload_btn = QPushButton("Yükü Bırak")
        self.release_payload_btn.setStyleSheet(ThemeColors.BUTTON_WARNING)
        self.release_payload_btn.clicked.connect(self.release_payload)
        
        self.emergency_land_btn = QPushButton("Acil İniş")
        self.emergency_land_btn.setStyleSheet(ThemeColors.BUTTON_DANGER)
        self.emergency_land_btn.clicked.connect(self.emergency_land_clicked.emit)
        
        self.rtl_btn = QPushButton("Eve Dön (RTL)")
        self.rtl_btn.setStyleSheet(ThemeColors.BUTTON_WARNING)
        self.rtl_btn.clicked.connect(self.rtl_clicked.emit)
        
        self.motor_cut_btn = QPushButton("Motoru Kapat")
        self.motor_cut_btn.setStyleSheet(ThemeColors.BUTTON_DANGER)
        self.motor_cut_btn.clicked.connect(self.handle_motor_cut_confirm)
        self.motor_cut_confirm_pending = False
        self.motor_cut_confirm_timer = QTimer(self)
        self.motor_cut_confirm_timer.setSingleShot(True)
        self.motor_cut_confirm_timer.timeout.connect(self.reset_motor_cut_btn)
        
        emergency_layout.addWidget(self.manual_mode_btn, 0, 0)
        emergency_layout.addWidget(self.return_home_btn, 0, 1)
        emergency_layout.addWidget(self.release_payload_btn, 0, 2)
        emergency_layout.addWidget(self.emergency_land_btn, 1, 0)
        emergency_layout.addWidget(self.rtl_btn, 1, 1)
        emergency_layout.addWidget(self.motor_cut_btn, 1, 2)
        emergency_group.setLayout(emergency_layout)
        
        # Data Logging Group
        logging_group = QGroupBox("Veri Kaydı")
        logging_group.setStyleSheet(ThemeColors.PANEL_STYLE)
        logging_layout = QVBoxLayout()
        
        self.log_data_btn = QPushButton("Veri Kaydını Başlat")
        self.log_data_btn.setStyleSheet(ThemeColors.BUTTON_NORMAL)
        self.log_data_btn.clicked.connect(self.toggle_logging)
        
        logging_layout.addWidget(self.log_data_btn)
        logging_group.setLayout(logging_layout)
        
        # System Status Group
        status_group = QGroupBox("Sistem Mesajları")
        status_group.setStyleSheet(ThemeColors.PANEL_STYLE)
        status_layout = QVBoxLayout()
        
        self.status_text = QTextEdit()
        self.status_text.setReadOnly(True)
        self.status_text.setStyleSheet(ThemeColors.INPUT_STYLE)
        
        status_layout.addWidget(self.status_text)
        status_group.setLayout(status_layout)
        
        layout.addWidget(mission_group)
        layout.addWidget(emergency_group)
        layout.addWidget(logging_group)
        layout.addWidget(status_group)
        layout.addStretch(1)
        
        self.setLayout(layout)
        
    def start_mission(self):
        self.log_message("Görev başlatma komutu gönderildi.")

    def pause_mission(self):
        self.log_message("Görev duraklatma komutu gönderildi.")

    def abort_mission(self):
        self.log_message("Görev iptal komutu gönderildi.")

    def switch_to_manual(self):
        """Manuel moda geç"""
        self.log_message("Manuel moda geçiliyor...")
        # Ana pencereye sinyal gönder
        # self.manual_mode_clicked.emit()  # Bu sinyal henüz tanımlanmamış

    def return_home(self):
        self.log_message("Eve dönüş komutu gönderildi.")
    
    def release_payload(self):
        """Yük bırak"""
        self.log_message("Yük bırakma komutu gönderiliyor...")
        # Ana pencereye sinyal gönder
        # self.release_payload_clicked.emit()  # Bu sinyal henüz tanımlanmamış

    def toggle_logging(self):
        if not self.logger: return
        
        if self.logger.log_file is None:
            if self.logger.start_logging():
                self.log_data_btn.setText("Veri Kaydını Durdur")
                self.log_message("Veri kaydı başlatıldı.")
        else:
            if self.logger.stop_logging():
                self.log_data_btn.setText("Veri Kaydını Başlat")
                self.log_message("Veri kaydı durduruldu.")
                
    def log_message(self, message):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.status_text.append(f"[{timestamp}] {message}")
        
    def update_telemetry(self, telemetry_data):
        if self.logger and self.logger.log_file:
            self.logger.log_data(telemetry_data)

    def goto_altitude(self):
        """İrtifa değiştir"""
        self.log_message("İrtifa değiştirme komutu gönderiliyor...")
        # Ana pencereye sinyal gönder
        # self.goto_altitude_clicked.emit()  # Bu sinyal henüz tanımlanmamış 

    def handle_motor_cut_confirm(self):
        if not self.motor_cut_confirm_pending:
            self.motor_cut_btn.setText("Emin misiniz?")
            self.motor_cut_confirm_pending = True
            self.motor_cut_confirm_timer.start(5000)  # 5 saniye içinde onay bekle
        else:
            self.motor_cut_confirm_timer.stop()
            self.motor_cut_btn.setText("Motoru Kapat")
            self.motor_cut_confirm_pending = False
            self.motor_cut_clicked.emit()  # Gerçekten motoru kapat

    def reset_motor_cut_btn(self):
        self.motor_cut_btn.setText("Motoru Kapat")
        self.motor_cut_confirm_pending = False 