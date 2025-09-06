import time
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QGroupBox, QGridLayout, QLabel, QFrame, QHBoxLayout, QScrollArea, QPushButton
import pyqtgraph as pg
from PyQt6.QtCore import Qt

from ui.theme import ThemeColors

class TelemetryPanel(QWidget):
    def __init__(self):
        super().__init__()
        # Data storage for graphs
        self.max_data_points = 300
        self.time_data = []
        self.alt_data = []
        self.speed_data = []
        self.last_roll = None  # Son roll değeri
        self.last_pitch = None  # Son pitch değeri
        self.last_alt = None
        self.last_heading = None  # Son geçerli heading
        self.last_mode = None  # Son geçerli mod metni
        self.flight_time = 0
        self.arm_start_time = None
        self.armed = False
        self.initUI()
        
    def initUI(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        content = QWidget()
        layout = QVBoxLayout(content)
        self.labels = {}

        # Kategoriler ve altındaki veriler (tekrarlar kaldırıldı, optimize edildi)
        categories = [
            ("Konum Bilgileri", [
                ("Enlem", 'lat'),
                ("Boylam", 'lon'),
                ("Yön", 'heading'),
                ("İrtifa (m)", 'alt'),
            ]),
            ("Uçuş Verileri", [
                ("Hız (m/s)", 'speed'),
                ("Tırmanış (m/s)", 'climb'),
                ("Yatış (°)", 'roll'),
                ("Yunuslama (°)", 'pitch'),
                ("Uçuş Süresi", 'flight_time'),
            ]),
            ("Sistem Durumu", [
                ("Batarya (%)", 'battery'),
                ("Voltaj (V)", 'voltage'),
                ("Akım (A)", 'current'),
                ("Hücre Voltajı (V)", 'cell_voltage'),  # Yeni kutucuk
            ]),
            ("Haberleşme", [
                ("Uydu", 'sat'),
                ("Mod", 'mode'),
            ]),
            ("Hava Durumu", [
                ("Rüzgar", 'wind'),
                ("Sıcaklık", 'weather_temp'),
                ("Görüş", 'visibility'),
                ("Durum", 'weather_status'),
            ]),
            ("Sensör Verileri", [
                ("Hall Effect", 'hall_effect'),
                ("Manyetik Alan", 'magnetic_field'),
            ]),
        ]

        for cat_title, items in categories:
            # Hava Durumu kategorisi için özel işlem
            if cat_title == "Hava Durumu":
                weather_container = QWidget()
                weather_layout = QVBoxLayout(weather_container)
                
                # Switch header
                header_widget = QWidget()
                header_layout = QHBoxLayout(header_widget)
                header_layout.setContentsMargins(10, 5, 10, 5)
                
                weather_label = QLabel("Hava Durumu")
                weather_label.setStyleSheet("font-size: 16px; color: #fff; font-weight: bold;")
                
                self.weather_toggle = QPushButton("Kapalı")
                self.weather_toggle.setCheckable(True)
                self.weather_toggle.setStyleSheet("""
                    QPushButton {
                        background: #444; color: #fff; border: 2px solid #666; 
                        border-radius: 15px; padding: 5px 15px; font-weight: bold;
                    }
                    QPushButton:checked {
                        background: #0d7377; border-color: #14a085;
                    }
                """)
                self.weather_toggle.clicked.connect(self.toggle_weather)
                
                header_layout.addWidget(weather_label)
                header_layout.addStretch()
                header_layout.addWidget(self.weather_toggle)
                
                # Weather content group (başlangıçta gizli)
                self.weather_group = QGroupBox()
                self.weather_group.setStyleSheet(ThemeColors.PANEL_STYLE)
                cat_layout = QGridLayout()
                for i, (label_text, key) in enumerate(items):
                    box = QFrame()
                    box.setFrameShape(QFrame.Shape.Box)
                    box.setLineWidth(2)
                    box.setStyleSheet("background: #222; border-radius: 12px; border: 2px solid #444;")
                    vbox = QVBoxLayout()
                    title = QLabel(label_text)
                    title.setAlignment(Qt.AlignmentFlag.AlignCenter)
                    title.setStyleSheet("font-size: 14px; color: #fff; font-weight: bold;")
                    value = QLabel("--")
                    value.setAlignment(Qt.AlignmentFlag.AlignCenter)
                    value.setStyleSheet("font-size: 32px; font-weight: bold; color: #fff;")
                    vbox.addWidget(title)
                    vbox.addWidget(value)
                    box.setLayout(vbox)
                    cat_layout.addWidget(box, i // 2, i % 2)
                    self.labels[key] = value
                self.weather_group.setLayout(cat_layout)
                self.weather_group.hide()  # Başlangıçta gizli
                
                weather_layout.addWidget(header_widget)
                weather_layout.addWidget(self.weather_group)
                layout.addWidget(weather_container)
            else:
                # Normal kategoriler
                cat_group = QGroupBox(cat_title)
                cat_group.setStyleSheet(ThemeColors.PANEL_STYLE)
                cat_layout = QGridLayout()
                for i, (label_text, key) in enumerate(items):
                    box = QFrame()
                    box.setFrameShape(QFrame.Shape.Box)
                    box.setLineWidth(2)
                    box.setStyleSheet("background: #222; border-radius: 12px; border: 2px solid #444;")
                    vbox = QVBoxLayout()
                    title = QLabel(label_text)
                    title.setAlignment(Qt.AlignmentFlag.AlignCenter)
                    title.setStyleSheet("font-size: 14px; color: #fff; font-weight: bold;")
                    value = QLabel("--")
                    value.setAlignment(Qt.AlignmentFlag.AlignCenter)
                    # Mod kutucuğu için daha küçük font
                    if key == 'mode':
                        value.setStyleSheet("font-size: 18px; font-weight: bold; color: #fff;")
                    else:
                        value.setStyleSheet("font-size: 32px; font-weight: bold; color: #fff;")
                    vbox.addWidget(title)
                    vbox.addWidget(value)
                    box.setLayout(vbox)
                    cat_layout.addWidget(box, i // 2, i % 2)
                    self.labels[key] = value
                cat_group.setLayout(cat_layout)
                layout.addWidget(cat_group)

        layout.addStretch(1)
        scroll.setWidget(content)
        main_layout = QVBoxLayout(self)
        main_layout.addWidget(scroll)
        self.setLayout(main_layout)

    def toggle_weather(self):
        """Hava durumu panelini aç/kapat"""
        if self.weather_toggle.isChecked():
            self.weather_group.show()
            self.weather_toggle.setText("Açık")
        else:
            self.weather_group.hide()
            self.weather_toggle.setText("Kapalı")

    def create_group(self, title, widgets):
        group = QGroupBox(title)
        group.setStyleSheet(ThemeColors.PANEL_STYLE)
        layout = QGridLayout()
        for r, row_widgets in enumerate(widgets):
            for c, widget in enumerate(row_widgets):
                layout.addWidget(widget, r, c)
        group.setLayout(layout)
        return group

    def create_plot(self, title, color):
        plot = pg.PlotWidget()
        plot.setBackground(ThemeColors.GRAPH_BG)
        plot.setTitle(title, color=ThemeColors.TEXT_PRIMARY)
        plot.showGrid(x=True, y=True, alpha=0.3)
        plot.getAxis('left').setPen(pg.mkPen(color=ThemeColors.TEXT_SECONDARY))
        plot.getAxis('bottom').setPen(pg.mkPen(color=ThemeColors.TEXT_SECONDARY))
        plot.getAxis('left').setTextPen(pg.mkPen(color=ThemeColors.TEXT_SECONDARY))
        plot.getAxis('bottom').setTextPen(pg.mkPen(color=ThemeColors.TEXT_SECONDARY))
        return plot

    def update_telemetry(self, data):
        # Mod bilgisini stabilize et: boş/0 gelirse son geçerli metni koru
        mode_val = data.get('mode')
        if isinstance(mode_val, str) and mode_val.strip():
            self.last_mode = mode_val
        elif isinstance(mode_val, (int, float)) and mode_val != 0:
            # Sayı gelirse metne çevir ve sakla
            self.last_mode = str(mode_val)
        elif mode_val in (None, 0, "0", "") and self.last_mode is not None:
            data['mode'] = self.last_mode

        # Heading'i stabilize et: anlık 0 değerlerini filtrele
        heading_val = data.get('heading')
        if heading_val is not None:
            try:
                heading_num = float(heading_val)
                if heading_num == 0 and self.last_heading is not None:
                    data['heading'] = self.last_heading
                else:
                    self.last_heading = heading_num
            except Exception:
                pass

        # Sadece roll ve pitch için son değeri sakla ve tamamla
        if 'roll' in data and data['roll'] is not None:
            self.last_roll = data['roll']
        if 'pitch' in data and data['pitch'] is not None:
            self.last_pitch = data['pitch']
        if 'roll' not in data and self.last_roll is not None:
            data['roll'] = self.last_roll
        if 'pitch' not in data and self.last_pitch is not None:
            data['pitch'] = self.last_pitch
        # ARM durumu kontrolü ve uçuş süresi sayaç mantığı
        if 'armed' in data:
            if data['armed'] and not self.armed:
                self.arm_start_time = time.time()
                self.flight_time = 0
                self.armed = True
            elif not data['armed'] and self.armed:
                if self.arm_start_time is not None:
                    self.flight_time = int(time.time() - self.arm_start_time)
                self.arm_start_time = None
                self.armed = False
        if self.armed and self.arm_start_time is not None:
            data['flight_time'] = int(time.time() - self.arm_start_time)
        else:
            data['flight_time'] = self.flight_time
        # Son bilinen değerleri sakla ve eksikse onları kullan
        if not hasattr(self, 'last_values'):
            self.last_values = {}
        for key in ['alt', 'climb', 'speed', 'voltage', 'current', 'battery', 'temp', 'rssi', 'lat', 'lon', 'heading', 'hall_effect', 'magnetic_field']:
            if key in data and data[key] is not None:
                self.last_values[key] = data[key]
            elif key in self.last_values:
                data[key] = self.last_values[key]
        format_map = {
            'lat': "{:.6f}", 'lon': "{:.6f}", 'alt': "{:.1f}", 'heading': "{}°",
            'speed': "{:.1f}", 'climb': "{:.1f}", 'roll': "{:.1f}", 'pitch': "{:.1f}",
            'battery': "{}%", 'voltage': "{:.1f}", 'current': "{:.1f}", 'temp': "{:.1f}",
            'cell_voltage': "{:.2f}",
            'rssi': "{}", 'sat': "{}", 'mode': "{}", 'status': "{}", 'flight_time': "{} sn",
            'hall_effect': "{}", 'magnetic_field': "{}"
        }
        for key, label in self.labels.items():
            if key == 'cell_voltage':
                voltage = data.get('voltage')
                value = (voltage / 4) if voltage is not None else 0
                label.setText(format_map['cell_voltage'].format(value))
            elif key == 'rssi':
                value = data.get('rssi')
                if value is None or value == 0:
                    label.setText('--')
                else:
                    label.setText(format_map['rssi'].format(value))
            elif key == 'climb':
                value = data.get('climb')
                if value is not None and abs(value) < 0.1:
                    value = 0
                elif value is None:
                    value = 0
                label.setText(format_map['climb'].format(value))
            elif key == 'alt':
                value = data.get('alt')
                # NoneType ve float çıkarma hatasını engelle
                if value is not None and hasattr(self, 'last_alt') and self.last_alt is not None:
                    if abs(value - self.last_alt) < 0.5:
                        value = self.last_alt
                    else:
                        self.last_alt = value
                elif value is not None:
                    self.last_alt = value
                else:
                    value = self.last_alt if hasattr(self, 'last_alt') and self.last_alt is not None else 0
                label.setText(format_map['alt'].format(value))
            elif key == 'flight_time':
                value = data.get('flight_time', 0)
                label.setText(format_map['flight_time'].format(value))
            elif key == 'hall_effect':
                value = data.get('hall_effect', 0)
                label.setText(format_map['hall_effect'].format(value))
            elif key == 'magnetic_field':
                value = data.get('magnetic_field', 0)
                label.setText(format_map['magnetic_field'].format(value))
            else:
                value = data.get(key)
                if value is None:
                    value = 0
                label.setText(format_map.get(key, "{}").format(value)) 