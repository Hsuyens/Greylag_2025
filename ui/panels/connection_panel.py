from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QGroupBox, QHBoxLayout, 
                             QComboBox, QLabel, QPushButton, QGridLayout, 
                             QListWidget, QListWidgetItem, QLineEdit, QMessageBox)
from PyQt6.QtCore import pyqtSignal, Qt
import serial.tools.list_ports

from ..theme import ThemeColors

class ConnectionPanel(QWidget):
    connect_clicked = pyqtSignal(str, int)
    disconnect_clicked = pyqtSignal()
    simulation_clicked = pyqtSignal()
    
    def __init__(self):
        super().__init__()
        self.initUI()
        
    def initUI(self):
        layout = QVBoxLayout()
        layout.setSpacing(10)
        
        # Connection controls
        controls_group = QGroupBox("Bağlantı Kontrolleri")
        controls_group.setStyleSheet(ThemeColors.PANEL_STYLE)
        controls_layout = QGridLayout()
        
        self.port_combo = QComboBox()
        self.port_combo.setStyleSheet(ThemeColors.INPUT_STYLE)
        
        self.refresh_ports_btn = QPushButton("Yenile")
        self.refresh_ports_btn.setStyleSheet(ThemeColors.BUTTON_NORMAL)
        self.refresh_ports_btn.clicked.connect(self.refresh_ports)
        
        self.baud_combo = QComboBox()
        self.baud_combo.setStyleSheet(ThemeColors.INPUT_STYLE)
        self.baud_combo.addItems(['9600', '57600', '115200', '230400', '460800', '921600'])
        self.baud_combo.setCurrentText('57600')
        
        self.connect_btn = QPushButton("Bağlan")
        self.connect_btn.setStyleSheet(ThemeColors.BUTTON_SUCCESS)
        self.connect_btn.clicked.connect(self.on_connect)
        
        self.sim_btn = QPushButton("Simülasyon")
        self.sim_btn.setStyleSheet(ThemeColors.BUTTON_PRIMARY)
        self.sim_btn.clicked.connect(self.on_simulation)
        
        controls_layout.addWidget(QLabel("Port:"), 0, 0)
        controls_layout.addWidget(self.port_combo, 0, 1)
        controls_layout.addWidget(self.refresh_ports_btn, 0, 2)
        controls_layout.addWidget(QLabel("Baud:"), 1, 0)
        controls_layout.addWidget(self.baud_combo, 1, 1)
        controls_layout.addWidget(self.connect_btn, 2, 0, 1, 2)
        controls_layout.addWidget(self.sim_btn, 2, 2)
        controls_group.setLayout(controls_layout)
        
        # Connection status indicators
        status_group = QGroupBox("Bağlantı Durumu")
        status_group.setStyleSheet(ThemeColors.PANEL_STYLE)
        status_layout = QGridLayout()
        
        self.rssi_label = QLabel("RSSI:")
        self.rssi_value = QLabel("N/A")
        
        self.ping_label = QLabel("Ping:")
        self.ping_value = QLabel("N/A")
        
        self.loss_label = QLabel("Veri Kaybı:")
        self.loss_value = QLabel("N/A")
        
        status_layout.addWidget(self.rssi_label, 0, 0)
        status_layout.addWidget(self.rssi_value, 0, 1)
        status_layout.addWidget(self.ping_label, 1, 0)
        status_layout.addWidget(self.ping_value, 1, 1)
        status_layout.addWidget(self.loss_label, 2, 0)
        status_layout.addWidget(self.loss_value, 2, 1)
        status_group.setLayout(status_layout)
        
        # Checklist Group
        checklist_group = QGroupBox("Uçuş Öncesi Kontrol Listesi")
        checklist_group.setStyleSheet(ThemeColors.PANEL_STYLE)
        checklist_layout = QVBoxLayout()
        self.checklist = QListWidget()
        self.checklist.setStyleSheet(ThemeColors.INPUT_STYLE)
        checklist_items = [
            "Pervaneler güvenli mi?",
            "Batarya dolu mu?",
            "GPS bağlantısı var mı?",
            "Kumanda bağlantısı tamam mı?",
            "Uçuş alanı temiz mi?"
        ]
        for item_text in checklist_items:
            item = QListWidgetItem(item_text)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Unchecked)
            self.checklist.addItem(item)
        checklist_layout.addWidget(self.checklist)
        checklist_group.setLayout(checklist_layout)

        layout.addWidget(controls_group)
        layout.addWidget(status_group)
        layout.addWidget(checklist_group)
        
        # Görev Mekanizması Paneli
        self.mission_mechanism_group = QGroupBox("Görev Mekanizması")
        self.mission_mechanism_group.setStyleSheet(ThemeColors.PANEL_STYLE)
        mission_mechanism_layout = QVBoxLayout()
        
        # Nokta ve irtifa girişleri
        self.payload_lat_input = QLineEdit()
        self.payload_lat_input.setPlaceholderText("Yük bırakma enlemi (lat)")
        self.payload_lon_input = QLineEdit()
        self.payload_lon_input.setPlaceholderText("Yük bırakma boylamı (lon)")
        self.payload_drop_alt_input = QLineEdit()
        self.payload_drop_alt_input.setPlaceholderText("Yük bırakma irtifası (m)")
        self.cruise_alt_input = QLineEdit()
        self.cruise_alt_input.setPlaceholderText("Seyir irtifası (m)")
        
        # Başlat butonu
        self.start_payload_mission_btn = QPushButton("Yük Bırakma Görevini Başlat")
        self.start_payload_mission_btn.setStyleSheet(ThemeColors.BUTTON_PRIMARY)
        # Sinyal bağlantısı ana pencerede yapılacak
        
        # Durum etiketi
        self.payload_status_label = QLabel("Durum: Beklemede")
        
        mission_mechanism_layout.addWidget(self.payload_lat_input)
        mission_mechanism_layout.addWidget(self.payload_lon_input)
        mission_mechanism_layout.addWidget(self.payload_drop_alt_input)
        mission_mechanism_layout.addWidget(self.cruise_alt_input)
        mission_mechanism_layout.addWidget(self.start_payload_mission_btn)
        mission_mechanism_layout.addWidget(self.payload_status_label)
        self.mission_mechanism_group.setLayout(mission_mechanism_layout)
        layout.addWidget(self.mission_mechanism_group)
        layout.addStretch(1)
        self.setLayout(layout)

        self.refresh_ports()
        
    def refresh_ports(self):
        self.port_combo.clear()
        ports = [port.device for port in serial.tools.list_ports.comports()]
        if ports:
            self.port_combo.addItems(ports)
            self.connect_btn.setEnabled(True)
        else:
            self.port_combo.addItem("Port bulunamadı")
            self.connect_btn.setEnabled(False)

    def on_connect(self):
        if self.connect_btn.text() == "Bağlan":
            # Checklist kontrolü
            for i in range(self.checklist.count()):
                item = self.checklist.item(i)
                if item is None:
                    continue
                if item.checkState() != Qt.CheckState.Checked:
                    QMessageBox.warning(self, "Checklist Eksik", "Tüm uçuş öncesi kontrol maddeleri işaretlenmeden bağlantı kurulamaz!")
                    return
            port = self.port_combo.currentText()
            if port and "bulunamadı" not in port:
                baud = int(self.baud_combo.currentText())
                self.connect_clicked.emit(port, baud)
        else:
            self.disconnect_clicked.emit()
            
    def set_status(self, connected):
        if connected:
            self.connect_btn.setText("Bağlantıyı Kes")
            self.connect_btn.setStyleSheet(ThemeColors.BUTTON_DANGER)
            self.port_combo.setEnabled(False)
            self.baud_combo.setEnabled(False)
            self.refresh_ports_btn.setEnabled(False)
        else:
            self.connect_btn.setText("Bağlan")
            self.connect_btn.setStyleSheet(ThemeColors.BUTTON_SUCCESS)
            self.port_combo.setEnabled(True)
            self.baud_combo.setEnabled(True)
            self.refresh_ports_btn.setEnabled(True)
            self.update_connection_stats({'rssi': 'N/A', 'ping': 'N/A', 'loss': 'N/A'})
            
    def update_connection_stats(self, stats):
        self.rssi_value.setText(str(stats.get('rssi', 'N/A')))
        self.ping_value.setText(str(stats.get('ping', 'N/A')))
        self.loss_value.setText(f"%{stats.get('loss', 'N/A')}")

    def on_simulation(self):
        self.simulation_clicked.emit() 