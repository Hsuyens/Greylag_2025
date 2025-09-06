from __future__ import annotations
from typing import TYPE_CHECKING
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QGroupBox, QHBoxLayout, 
                             QComboBox, QLabel, QPushButton, QGridLayout, 
                             QTextEdit, QLineEdit, QFormLayout, QFileDialog)
from PyQt6.QtCore import pyqtSignal

from ui.theme import ThemeColors
from mission.mission_planner import MissionPlanner

if TYPE_CHECKING:
    from .map_panel import MapPanel

class MissionPlannerPanel(QWidget):
    mission_upload_requested = pyqtSignal(list)  # waypoints listesi
    
    def __init__(self, mission_planner: MissionPlanner):
        super().__init__()
        self.mission_planner = mission_planner
        self.map_panel: MapPanel | None = None # Will be set by main window
        self.initUI()
        
    def initUI(self):
        layout = QVBoxLayout()
        layout.setSpacing(10)
        
        # Mission Type Selection
        mission_group = QGroupBox("Görev Tipi")
        mission_layout = QFormLayout()
        
        self.mission_type_combo = QComboBox()
        self.mission_type_combo.addItems(["Waypoint Uçuşu", "Grid Tarama", "Poligon Tarama"])
        mission_layout.addRow("Görev Tipi:", self.mission_type_combo)
        
        self.altitude_input = QLineEdit("50")
        mission_layout.addRow("İrtifa (m):", self.altitude_input)
        
        self.speed_input = QLineEdit("5")
        mission_layout.addRow("Hız (m/s):", self.speed_input)
        
        mission_group.setLayout(mission_layout)
        layout.addWidget(mission_group)
        
        # Sonsuzluk İşareti Ayarları
        infinity_group = QGroupBox("Sonsuzluk İşareti (8)")
        infinity_layout = QFormLayout()
        
        self.radius_input = QLineEdit("20")
        infinity_layout.addRow("Yarıçap (m):", self.radius_input)
        
        infinity_group.setLayout(infinity_layout)
        layout.addWidget(infinity_group)
        
        # Manuel Koordinat Girişi
        manual_group = QGroupBox("Manuel Koordinat Girişi")
        manual_layout = QFormLayout()
        
        self.lat_input = QLineEdit("41.0082")
        manual_layout.addRow("Enlem:", self.lat_input)
        
        self.lon_input = QLineEdit("28.9784")
        manual_layout.addRow("Boylam:", self.lon_input)
        
        self.add_manual_btn = QPushButton("Manuel Waypoint Ekle")
        self.add_manual_btn.setStyleSheet(ThemeColors.BUTTON_PRIMARY)
        self.add_manual_btn.clicked.connect(self.add_manual_waypoint)
        manual_layout.addRow(self.add_manual_btn)
        
        manual_group.setLayout(manual_layout)
        layout.addWidget(manual_group)
        
        # Actions
        actions_group = QGroupBox("İşlemler")
        actions_layout = QHBoxLayout()
        
        self.add_wp_btn = QPushButton("Waypoint Ekle")
        self.add_wp_btn.setStyleSheet(ThemeColors.BUTTON_PRIMARY)
        self.add_wp_btn.clicked.connect(self.enable_waypoint_mode)
        
        self.draw_poly_btn = QPushButton("Poligon Çiz")
        self.draw_poly_btn.setStyleSheet(ThemeColors.BUTTON_PRIMARY)
        self.draw_poly_btn.clicked.connect(self.enable_polygon_mode)
        
        self.infinity_btn = QPushButton("8 Şekli Çiz")
        self.infinity_btn.setStyleSheet(ThemeColors.BUTTON_PRIMARY)
        self.infinity_btn.clicked.connect(self.enable_infinity_mode)
        
        self.clear_btn = QPushButton("Temizle")
        self.clear_btn.setStyleSheet(ThemeColors.BUTTON_DANGER)
        self.clear_btn.clicked.connect(self.clear_mission)
        
        self.generate_btn = QPushButton("Görev Oluştur")
        self.generate_btn.setStyleSheet(ThemeColors.BUTTON_SUCCESS)
        self.generate_btn.clicked.connect(self.generate_mission)
        
        self.upload_btn = QPushButton("Araca Yükle")
        self.upload_btn.setStyleSheet(ThemeColors.BUTTON_SUCCESS)
        self.upload_btn.clicked.connect(self.upload_mission)
        
        # Mission Planner .waypoints yükleme
        self.load_btn = QPushButton("Yükle (.waypoints)")
        self.load_btn.setStyleSheet(ThemeColors.BUTTON_PRIMARY)
        self.load_btn.clicked.connect(self.load_waypoints_file)
        
        self.export_btn = QPushButton("Kaydet (.waypoints)")
        self.export_btn.setStyleSheet(ThemeColors.BUTTON_PRIMARY)
        self.export_btn.clicked.connect(self.export_waypoints_file)
        
        actions_layout.addWidget(self.add_wp_btn)
        actions_layout.addWidget(self.draw_poly_btn)
        actions_layout.addWidget(self.infinity_btn)
        actions_layout.addWidget(self.clear_btn)
        actions_layout.addWidget(self.generate_btn)
        actions_layout.addWidget(self.upload_btn)
        actions_layout.addWidget(self.load_btn)
        actions_layout.addWidget(self.export_btn)
        
        actions_group.setLayout(actions_layout)
        layout.addWidget(actions_group)
        
        # Elektromıknatıs Kontrolü bölümü isteğe göre kaldırıldı
        
        # Mission Info
        info_group = QGroupBox("Görev Bilgisi")
        info_layout = QVBoxLayout()
        
        self.mission_info = QTextEdit()
        self.mission_info.setMaximumHeight(100)
        self.mission_info.setReadOnly(True)
        info_layout.addWidget(self.mission_info)
        
        info_group.setLayout(info_layout)
        layout.addWidget(info_group)
        
        self.setLayout(layout)
        
        # Çizim modları
        self.waypoint_mode = False
        self.polygon_mode = False
        self.infinity_mode = False
        
        self.update_mission_info()

    def enable_waypoint_mode(self):
        """Waypoint ekleme modunu aktif et"""
        self.waypoint_mode = True
        self.polygon_mode = False
        self.infinity_mode = False
        self.add_wp_btn.setText("Waypoint Modu Aktif")
        self.add_wp_btn.setStyleSheet(ThemeColors.BUTTON_SUCCESS)
        self.draw_poly_btn.setText("Poligon Çiz")
        self.draw_poly_btn.setStyleSheet(ThemeColors.BUTTON_PRIMARY)
        self.infinity_btn.setText("8 Şekli Çiz")
        self.infinity_btn.setStyleSheet(ThemeColors.BUTTON_PRIMARY)

    def enable_polygon_mode(self):
        """Poligon çizim modunu aktif et"""
        self.polygon_mode = True
        self.waypoint_mode = False
        self.infinity_mode = False
        self.draw_poly_btn.setText("Poligon Modu Aktif")
        self.draw_poly_btn.setStyleSheet(ThemeColors.BUTTON_SUCCESS)
        self.add_wp_btn.setText("Waypoint Ekle")
        self.add_wp_btn.setStyleSheet(ThemeColors.BUTTON_PRIMARY)
        self.infinity_btn.setText("8 Şekli Çiz")
        self.infinity_btn.setStyleSheet(ThemeColors.BUTTON_PRIMARY)

    def enable_infinity_mode(self):
        """Sonsuzluk işareti çizim modunu aktif et"""
        self.infinity_mode = True
        self.waypoint_mode = False
        self.polygon_mode = False
        self.infinity_btn.setText("8 Modu Aktif")
        self.infinity_btn.setStyleSheet(ThemeColors.BUTTON_SUCCESS)
        self.add_wp_btn.setText("Waypoint Ekle")
        self.add_wp_btn.setStyleSheet(ThemeColors.BUTTON_PRIMARY)
        self.draw_poly_btn.setText("Poligon Çiz")
        self.draw_poly_btn.setStyleSheet(ThemeColors.BUTTON_PRIMARY)
        # Geçici noktaları temizle
        self.mission_planner.clear_infinity_points()
        self.update_mission_info()

    def on_map_click(self, lat, lon):
        """Haritaya tıklandığında çağrılır"""
        if self.waypoint_mode:
            # Waypoint ekle
            try:
                alt = float(self.altitude_input.text())
                self.mission_planner.add_waypoint(lat, lon, alt)
                self.waypoint_mode = False
                self.add_wp_btn.setText("Waypoint Ekle")
                self.add_wp_btn.setStyleSheet(ThemeColors.BUTTON_PRIMARY)
                self.mission_info.setText(f"Waypoint eklendi: {lat:.6f}, {lon:.6f}, {alt}m")
                if self.map_panel:
                    self.map_panel.update_map()
            except ValueError:
                self.mission_info.setText("Hata: İrtifa sayısal olmalı!")
            self.update_mission_info()
        elif self.polygon_mode:
            self.mission_planner.add_polygon_point(lat, lon)
            self.mission_info.setText(f"Poligon noktası eklendi: {lat:.6f}, {lon:.6f}")
            if self.map_panel:
                self.map_panel.update_map()
            self.update_mission_info()
        elif self.infinity_mode:
            self.mission_planner.add_infinity_point(lat, lon)
            infinity_count = len(self.mission_planner.infinity_points)
            if self.map_panel:
                self.map_panel.temp_infinity_points = list(self.mission_planner.infinity_points)
                self.map_panel.update_map()
            if infinity_count == 1:
                self.mission_info.setText(f"8 şekli: İlk nokta eklendi ({lat:.6f}, {lon:.6f}). İkinci noktayı seçin.")
            elif infinity_count == 2:
                p1, p2 = self.mission_planner.infinity_points
                if p1 == p2:
                    self.mission_info.setText("Hata: İki farklı nokta seçmelisiniz!")
                    self.mission_planner.infinity_points.pop()
                    return
                try:
                    radius = float(self.radius_input.text())
                    altitude = float(self.altitude_input.text())
                    if self.mission_planner.generate_infinity_pattern(altitude, radius):
                        self.infinity_mode = False
                        self.infinity_btn.setText("8 Şekli Çiz")
                        self.infinity_btn.setStyleSheet(ThemeColors.BUTTON_PRIMARY)
                        self.mission_info.setText("8 şekli başarıyla oluşturuldu!")
                        if self.map_panel:
                            self.map_panel.temp_infinity_points = []
                            self.map_panel.update_map()
                    else:
                        self.mission_info.setText("Hata: 8 şekli oluşturulamadı!")
                except ValueError:
                    self.mission_info.setText("Hata: Yarıçap ve irtifa sayısal olmalı!")
            self.update_mission_info()

    def clear_mission(self):
        """Görevi temizle"""
        self.mission_planner.waypoints = []
        self.mission_planner.polygons = []
        self.mission_planner.clear_infinity_points()
        self.mission_info.setText("Görev temizlendi.")
        if self.map_panel:
            self.map_panel.update_map()
        self.update_mission_info()
        
    def generate_mission(self):
        """Görev oluştur"""
        mission_type_text = self.mission_type_combo.currentText()
        
        # Mission type mapping
        mission_type_mapping = {
            "Waypoint Uçuşu": "waypoint",
            "Grid Tarama": "grid", 
            "Poligon Tarama": "polygon"
        }
        
        mission_type_key = mission_type_mapping.get(mission_type_text, "waypoint")
        
        # Parametre doğrulama
        try:
            altitude = float(self.altitude_input.text())
            speed = float(self.speed_input.text())
        except ValueError:
            self.mission_info.setText("Hata: Tüm parametreler sayısal olmalı!")
            return
        if not (5 <= altitude <= 500):
            self.mission_info.setText("Hata: İrtifa 5-500 metre arasında olmalı!")
            return
        if not (1 <= speed <= 50):
            self.mission_info.setText("Hata: Hız 1-50 m/s arasında olmalı!")
            return
        
        # Generate mission based on type
        success = False
        if mission_type_key == "waypoint":
            if self.mission_planner.waypoints:
                success = self.mission_planner.generate_waypoint_mission(altitude, speed)
            else:
                self.mission_info.setText("Hata: Önce waypoint ekleyin!")
                return
        elif mission_type_key == "grid":
            if self.mission_planner.polygons and self.mission_planner.polygons[0]:
                spacing = 20
                success = self.mission_planner.generate_grid_mission(altitude, spacing, speed)
            else:
                self.mission_info.setText("Hata: Önce poligon çizin!")
                return
        elif mission_type_key == "polygon":
            if self.mission_planner.polygons and self.mission_planner.polygons[0]:
                success = self.mission_planner.generate_polygon_mission(altitude, speed)
            else:
                self.mission_info.setText("Hata: Önce poligon çizin!")
                return
        
        if success:
            # Update info
            wp_count = len(self.mission_planner.waypoints)
            try:
                estimated_time = wp_count * 30 / speed  # 30 saniye per waypoint
                info = f"Görev oluşturuldu!\nWaypoint sayısı: {wp_count}\nTahmini süre: {estimated_time:.1f} dakika"
            except:
                info = f"Görev oluşturuldu!\nWaypoint sayısı: {wp_count}"
            
            self.mission_info.setText(info)
            
            # Haritayı güncelle
            if self.map_panel:
                self.map_panel.update_map()
        else:
            self.mission_info.setText("Hata: Görev oluşturulamadı!")

    def update_mission_info(self):
        wp_count = len(self.mission_planner.waypoints)
        poly_count = len(self.mission_planner.polygons)
        poly_points = len(self.mission_planner.polygons[0]) if poly_count > 0 else 0
        info = f"Waypoint Sayısı: {wp_count}\n"
        if poly_count > 0:
            info += f"Poligon Noktaları: {poly_points}\n"
        SABIT_HIZ = 19.44  # 70 km/s
        try:
            duration_min = self.mission_planner.estimate_mission_time(SABIT_HIZ) / 60
            info += f"Tahmini Süre (70 km/s): {duration_min:.1f} dk\n"
        except (ValueError, ZeroDivisionError):
            pass
        self.mission_info.setText(info)

    def upload_mission(self):
        """
        Görevi araca yükler.
        """
        if not self.mission_planner.waypoints:
            self.mission_info.setText("Hata: Yüklenecek görev yok! Önce görev oluşturun.")
            return
        
        # Ana pencereye görev yükleme sinyali gönder
        if hasattr(self, 'mission_upload_requested'):
            self.mission_upload_requested.emit(self.mission_planner.waypoints)
        else:
            self.mission_info.setText("Hata: Görev yükleme sinyali bağlı değil.")

    def load_waypoints_file(self):
        """Mission Planner .waypoints dosyasını içe aktarır ve mevcut göreve yükler."""
        file_path, _ = QFileDialog.getOpenFileName(self, "Waypoints Dosyası Seç", "", "Waypoints Files (*.waypoints *.txt);;All Files (*)")
        if not file_path:
            return
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = [ln.strip() for ln in f.readlines() if ln.strip()]
            if not lines:
                self.mission_info.setText("Hata: Dosya boş.")
                return
            if not lines[0].startswith("QGC WPL"):
                self.mission_info.setText("Hata: Geçersiz .waypoints formatı (başlık yok).")
                return
            waypoints = []
            raw_items = []  # ham mission item listesi
            for ln in lines[1:]:
                parts = ln.split('\t') if '\t' in ln else ln.split(',') if ',' in ln else ln.split()
                # Beklenen: seq, current, frame, command, p1..p4, x(lat), y(lon), z(alt), autocontinue
                if len(parts) < 12:
                    # Eski formatlar için minimum alan kontrolü
                    if len(parts) < 11:
                        continue
                try:
                    seq = int(parts[0])
                    command = int(parts[3])
                    p1 = float(parts[4]); p2 = float(parts[5]); p3 = float(parts[6]); p4 = float(parts[7])
                    lat = float(parts[8]); lon = float(parts[9]); alt = float(parts[10])
                except Exception:
                    continue
                # Ham mission item satırını sakla (seq/current/frame/command/p1..p4/x/y/z/autocontinue)
                try:
                    current = int(parts[1])
                    frame = int(parts[2])
                    autocontinue = int(parts[11]) if len(parts) > 11 else 1
                except Exception:
                    current, frame, autocontinue = 0, 3, 1
                raw_items.append({
                    'seq': seq, 'current': current, 'frame': frame, 'command': command,
                    'param1': p1, 'param2': p2, 'param3': p3, 'param4': p4,
                    'x': lat, 'y': lon, 'z': alt, 'autocontinue': autocontinue
                })
                action = 'NAV_WAYPOINT'
                if command == 16:  # MAV_CMD_NAV_WAYPOINT
                    action = 'NAV_WAYPOINT'
                elif command == 22:  # MAV_CMD_NAV_TAKEOFF
                    action = 'NAV_TAKEOFF'
                elif command in (21, 20):  # RTL/HOME -> waypoint listesinde hedef değil, atla
                    action = 'NAV_WAYPOINT'
                elif command in (21,):
                    action = 'NAV_RTL'
                elif command in (20,):
                    action = 'NAV_RTH'
                elif command in (21, 20):
                    action = 'NAV_WAYPOINT'
                elif command in (21,):
                    action = 'NAV_WAYPOINT'
                elif command in (21,):
                    action = 'NAV_WAYPOINT'
                elif command == 21:  # MAV_CMD_NAV_LAND (ArduPlane: 21 is RTL; LAND is 21 for Copter; Plane LAND is 21? In MP export LAND is 21 or 20?)
                    action = 'NAV_LAND'
                elif command == 21 or command == 20:
                    action = 'NAV_WAYPOINT'
                elif command == 21:  # fallback
                    action = 'NAV_WAYPOINT'
                elif command == 21:
                    action = 'NAV_WAYPOINT'
                elif command == 21:
                    action = 'NAV_WAYPOINT'
                # Basit eşleme: TAKEOFF/LAND dışındakileri waypoint yap
                wp = {'lat': lat, 'lon': lon, 'alt': alt, 'action': action}
                waypoints.append(wp)
            if not waypoints:
                self.mission_info.setText("Hata: Geçerli waypoint bulunamadı.")
                return
            # MissonPlanner'a yükle ve haritayı güncelle
            if hasattr(self.mission_planner, 'set_waypoints'):
                self.mission_planner.set_waypoints(waypoints)
                # Ham item'ları da sakla: köprü modu için
                if hasattr(self.mission_planner, 'raw_mission_items'):
                    self.mission_planner.raw_mission_items = raw_items
                if self.map_panel:
                    self.map_panel.update_map()
                self.update_mission_info()
                self.mission_info.setText(f"Yüklendi: {len(waypoints)} waypoint ({file_path})")
        except Exception as e:
            self.mission_info.setText(f"Hata: Dosya okunamadı ({e})")

    def add_manual_waypoint(self):
        """Manuel koordinat girişi ile waypoint ekler"""
        try:
            lat = float(self.lat_input.text())
            lon = float(self.lon_input.text())
            alt = float(self.altitude_input.text()) if self.altitude_input.text() else 50
            
            # Koordinat doğrulama
            if not (-90 <= lat <= 90):
                self.mission_info.setText("Hata: Enlem -90 ile 90 arasında olmalı!")
                return
            if not (-180 <= lon <= 180):
                self.mission_info.setText("Hata: Boylam -180 ile 180 arasında olmalı!")
                return
            
            self.mission_planner.add_waypoint(lat, lon, alt)
            self.mission_info.setText(f"Manuel waypoint eklendi: {lat:.6f}, {lon:.6f}, {alt}m")
            if self.map_panel:
                self.map_panel.update_map()
            self.update_mission_info()
            
        except ValueError:
            self.mission_info.setText("Hata: Koordinatlar ve irtifa sayısal olmalı!")
            

            
    def export_waypoints_file(self):
        """Waypoint'leri .waypoints dosyası olarak dışa aktar"""
        try:
            file_path, _ = QFileDialog.getSaveFileName(self, "Waypoints Dosyasını Kaydet", "", "Waypoints Files (*.waypoints);;All Files (*)")
            if not file_path:
                return
                
            if not file_path.endswith('.waypoints'):
                file_path += '.waypoints'
                
            success = self.mission_planner.export_waypoints_file(file_path)
            if success:
                self.mission_info.setText(f"Waypoint dosyası kaydedildi: {file_path}")
            else:
                self.mission_info.setText("Hata: Waypoint dosyası kaydedilemedi")
        except Exception as e:
            self.mission_info.setText(f"Hata: Dosya kaydetme hatası ({e})") 