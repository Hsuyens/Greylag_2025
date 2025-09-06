import math
import time
import threading
from typing import Optional, Dict, Any, List
from pymavlink import mavutil
from PyQt6.QtCore import QThread, pyqtSignal
import serial  # Hall effect sensörü için

class MAVLinkThread(QThread):
    telemetry_received = pyqtSignal(dict)
    attitude_received = pyqtSignal(dict)
    position_received = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)
    emergency_triggered = pyqtSignal(dict)
    payload_status_changed = pyqtSignal(dict)
    mission_completed = pyqtSignal()  # Görev tamamlama sinyali
    
    def __init__(self):
        super().__init__()
        self.running = True
        self.connection = None
        self._connection_lock = threading.Lock()  # Thread güvenliği için
        
        # Spam önleme için önceki hataları takip et
        self.previous_errors = {}  # {error_message: last_time}
        self.error_cooldown = 30  # 30 saniye bekleme süresi
        
        # Güvenlik eşikleri - daha esnek değerler
        self.emergency_thresholds = {
            'battery_percent': 20,    # 25'ten 20'ye düşürüldü
            'temperature': 70,        # 65'ten 70'e çıkarıldı
            'altitude_error': 5,      # 3'ten 5'e çıkarıldı (daha toleranslı)
            'gps_fix': 3,            # 4'ten 3'e düşürüldü (daha esnek)
            'rssi': -95              # -90'dan -95'e düşürüldü
        }
        
        self.payload_release_pin = 0  # GPIO pin for payload release
        self.home_position = None
        # Elektromıknatıslar için relay indexleri (AUX OUT 1 -> 0, AUX OUT 2 -> 1 varsayılan)
        self.magnet1_relay_index = 0
        self.magnet2_relay_index = 1

        # Hall effect sensörü için
        self.hall_serial_port = None  # serial.Serial nesnesi
        self.hall_port_name = None    # Port adı (ör: 'COM6')
        self.hall_baudrate = 9600
        self._hall_lock = threading.Lock()  # Hall sensör için thread güvenliği
        self.hall_effect_value = 0
        self.magnetic_field_value = 0
        
        # Son konum (otomatik irtifa için)
        self.last_lat = None
        self.last_lon = None
        
        # Bağlantı durumu
        self.is_connected = False
        self.last_heartbeat = None
        self.connection_timeout = 10  # saniye (5'ten 10'a çıkarıldı)
        self.armed = False  # <-- ARM durumu
        self.last_mode = None  # <-- MODU KAYDET
        
    def set_magnet_relay_indices(self, magnet1_index: int, magnet2_index: int) -> None:
        """Elektromıknatısların bağlı olduğu AUX relay indexlerini ayarla."""
        try:
            self.magnet1_relay_index = int(magnet1_index)
            self.magnet2_relay_index = int(magnet2_index)
        except Exception:
            # Geçersiz girişte varsayılanlara dön
            self.magnet1_relay_index = 0
            self.magnet2_relay_index = 1
        
    def _emit_error(self, error_message: str) -> None:
        """Spam önleme ile hata gönder"""
        current_time = time.time()
        if error_message in self.previous_errors:
            last_time = self.previous_errors[error_message]
            if current_time - last_time < self.error_cooldown:
                return  # Aynı hatayı tekrar verme
        
        # Yeni hatayı kaydet
        self.previous_errors[error_message] = current_time
        self.error_occurred.emit(error_message)
        
    def connect(self, port='COM3', baud=57600) -> bool:
        """MAVLink bağlantısını kur"""
        try:
            with self._connection_lock:
                if self.connection:
                    try:
                        self.connection.close()
                    except:
                        pass  # Bağlantı zaten kapalı olabilir
                    
                self.connection = mavutil.mavlink_connection(port, baud=baud)
                self.is_connected = True
                self.last_heartbeat = time.time()
                
                # Bağlantıyı test et
                if not self._test_connection():
                    self.is_connected = False
                    self.connection = None
                    self._emit_error("Bağlantı testi başarısız")
                    return False
                return True
                
        except Exception as e:
            self.is_connected = False
            self.connection = None
            self._emit_error(f"Bağlantı hatası: {e}")
            return False
            
    def _test_connection(self) -> bool:
        """Bağlantıyı test et"""
        try:
            if not self.connection:
                return False
                
            # Heartbeat mesajını bekle
            start_time = time.time()
            while time.time() - start_time < 5:  # 5 saniye timeout (3'ten 5'e çıkarıldı)
                msg = self.connection.recv_match(type='HEARTBEAT', timeout=1)
                if msg:
                    return True
            return False
            
        except Exception:
            return False
            
    def set_home_position(self, lat: float, lon: float, alt: float) -> None:
        """Ev konumunu ayarla"""
        if not (-90.1 <= lat <= 90.1) or not (-180.1 <= lon <= 180.1):  # Küçük sapmalara izin ver
            raise ValueError("Geçersiz koordinat değerleri")
        if alt < -50 or alt > 3000:  # 3000m maksimum (1000m yerine)
            raise ValueError("Ev konumu irtifası -50-3000m arasında olmalı")
            
        self.home_position = {
            'lat': lat,
            'lon': lon,
            'alt': alt
        }
        
    def check_emergency_conditions(self, telemetry: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Acil durum koşullarını kontrol et"""
        emergency_conditions = []
        
        # Battery check - USB bağlantısı için daha esnek
        battery_percent = telemetry.get('battery', 0)
        voltage = telemetry.get('voltage', 0)
        
        # USB bağlantısında batarya verisi olmayabilir, bu durumda kontrol etme
        if not (battery_percent == 0 and voltage == 0):
            if battery_percent < self.emergency_thresholds['battery_percent']:
                emergency_conditions.append({
                    'type': 'battery_percent',
                    'severity': 'warning',
                    'message': f'Düşük batarya seviyesi: %{battery_percent}'
                })
            
        # Temperature check - daha esnek
        temperature = telemetry.get('temperature', 0)
        if temperature > self.emergency_thresholds['temperature']:
            emergency_conditions.append({
                'type': 'temperature',
                'severity': 'warning',
                'message': f'Yüksek sıcaklık: {temperature}°C'
            })
            
        # GPS check - daha esnek
        gps_fix = telemetry.get('gps_fix', 0)
        if gps_fix < self.emergency_thresholds['gps_fix']:
            emergency_conditions.append({
                'type': 'gps',
                'severity': 'critical',
                'message': f'GPS sinyali zayıf: {gps_fix}'
            })
            
        # RSSI check - daha esnek
        rssi = telemetry.get('rssi', 0)
        if rssi < self.emergency_thresholds['rssi']:
            emergency_conditions.append({
                'type': 'rssi',
                'severity': 'warning',
                'message': f'Zayıf haberleşme sinyali: {rssi}dBm'
            })
            
        return emergency_conditions
        
    def release_payload(self) -> bool:
        """Yük bırakma komutu gönder (relay off)."""
        with self._connection_lock:
            if not self.connection or not self.is_connected:
                self._emit_error("Yük bırakma hatası: Bağlantı aktif değil.")
                return False
                
        try:
            # Varsayılan olarak Magnet1'i kapat
            return self.deactivate_magnet1()
        except Exception as e:
            self._emit_error(f"Yük bırakma hatası: {e}")
            return False
    
    def activate_magnet1(self) -> bool:
        """Elektromıknatıs 1'i aktifleştir (Main Out 1)"""
        with self._connection_lock:
            if not self.connection or not self.is_connected:
                self._emit_error("Elektromıknatıs 1 hatası: Bağlantı aktif değil.")
                return False
                
        try:
            if hasattr(self.connection, 'mav'):
                self.connection.mav.command_long_send(
                    self.connection.target_system,
                    self.connection.target_component,
                    mavutil.mavlink.MAV_CMD_DO_SET_RELAY,
                    0,  # Confirmation
                    self.magnet1_relay_index,  # Relay number (Main Out 1)
                    1,  # State (1 = on)
                    0, 0, 0, 0, 0, 0  # Unused parameters
                )
            return True
        except Exception as e:
            self._emit_error(f"Elektromıknatıs 1 aktifleştirme hatası: {e}")
            return False
    
    def deactivate_magnet1(self) -> bool:
        """Elektromıknatıs 1'i deaktifleştir (Main Out 1)"""
        with self._connection_lock:
            if not self.connection or not self.is_connected:
                self._emit_error("Elektromıknatıs 1 hatası: Bağlantı aktif değil.")
                return False
                
        try:
            if hasattr(self.connection, 'mav'):
                self.connection.mav.command_long_send(
                    self.connection.target_system,
                    self.connection.target_component,
                    mavutil.mavlink.MAV_CMD_DO_SET_RELAY,
                    0,  # Confirmation
                    self.magnet1_relay_index,  # Relay number (Main Out 1)
                    0,  # State (0 = off)
                    0, 0, 0, 0, 0, 0  # Unused parameters
                )
            return True
        except Exception as e:
            self._emit_error(f"Elektromıknatıs 1 deaktifleştirme hatası: {e}")
            return False
    
    def activate_magnet2(self) -> bool:
        """Elektromıknatıs 2'yi aktifleştir (Main Out 2)"""
        with self._connection_lock:
            if not self.connection or not self.is_connected:
                self._emit_error("Elektromıknatıs 2 hatası: Bağlantı aktif değil.")
                return False
                
        try:
            if hasattr(self.connection, 'mav'):
                self.connection.mav.command_long_send(
                    self.connection.target_system,
                    self.connection.target_component,
                    mavutil.mavlink.MAV_CMD_DO_SET_RELAY,
                    0,  # Confirmation
                    self.magnet2_relay_index,  # Relay number (Main Out 2)
                    1,  # State (1 = on)
                    0, 0, 0, 0, 0, 0  # Unused parameters
                )
            return True
        except Exception as e:
            self._emit_error(f"Elektromıknatıs 2 aktifleştirme hatası: {e}")
            return False
    
    def deactivate_magnet2(self) -> bool:
        """Elektromıknatıs 2'yi deaktifleştir (Main Out 2)"""
        with self._connection_lock:
            if not self.connection or not self.is_connected:
                self._emit_error("Elektromıknatıs 2 hatası: Bağlantı aktif değil.")
                return False
                
        try:
            if hasattr(self.connection, 'mav'):
                self.connection.mav.command_long_send(
                    self.connection.target_system,
                    self.connection.target_component,
                    mavutil.mavlink.MAV_CMD_DO_SET_RELAY,
                    0,  # Confirmation
                    self.magnet2_relay_index,  # Relay number (Main Out 2)
                    0,  # State (0 = off)
                    0, 0, 0, 0, 0, 0  # Unused parameters
                )
            return True
        except Exception as e:
            self._emit_error(f"Elektromıknatıs 2 deaktifleştirme hatası: {e}")
            return False
            
    def return_to_home(self) -> bool:
        """Eve dönüş komutu gönder"""
        with self._connection_lock:
            if not self.connection or not self.is_connected:
                self._emit_error("Eve dönüş komutu hatası: Bağlantı aktif değil.")
                return False
                
        if not self.home_position:
            self._emit_error("Ev konumu ayarlanmamış")
            return False
            
        try:
            # Send RTL command
            if hasattr(self.connection, 'mav'):
                self.connection.mav.command_long_send(
                    self.connection.target_system,
                    self.connection.target_component,
                    mavutil.mavlink.MAV_CMD_NAV_RETURN_TO_LAUNCH,
                    0,  # Confirmation
                    0, 0, 0, 0, 0, 0, 0  # Unused parameters
                )
            return True
        except Exception as e:
            self._emit_error(f"Eve dönüş komutu hatası: {e}")
            return False

    def set_mode(self, mode_name: str) -> bool:
        """Uçuş modunu ayarla (ArduPlane custom mode)."""
        with self._connection_lock:
            if not self.connection or not self.is_connected:
                self._emit_error("Mod değiştirme hatası: Bağlantı aktif değil.")
                return False

        # ArduPlane için custom_mode eşlemesi
        mode_map = {
            'MANUAL': 0,
            'CIRCLE': 1,
            'STABILIZE': 2,
            'TRAINING': 3,
            'ACRO': 4,
            'FLY_BY_WIRE_A': 5,
            'FLY_BY_WIRE_B': 6,
            'CRUISE': 7,
            'AUTOTUNE': 8,
            'AUTO': 10,
            'RTL': 11,
            'LOITER': 12,
            'TAKEOFF': 14,
            'GUIDED': 16,
        }

        mode_name = (mode_name or '').upper()
        if mode_name not in mode_map:
            self._emit_error(f"Bilinmeyen mod: {mode_name}")
            return False

        try:
            if hasattr(self.connection, 'mav'):
                # set_mode_send(base_mode, custom_mode) için target_system gerekir
                self.connection.mav.set_mode_send(
                    self.connection.target_system,
                    1,  # MAV_MODE_FLAG_CUSTOM_MODE yerine 1 kullan
                    mode_map[mode_name]
                )
            return True
        except Exception as e:
            self._emit_error(f"Mod değiştirme hatası: {e}")
            return False
            
    def switch_to_manual(self) -> bool:
        """Manuel moda geçiş komutu gönder"""
        with self._connection_lock:
            if not self.connection or not self.is_connected:
                self._emit_error("Manuel moda geçiş hatası: Bağlantı aktif değil.")
                return False
                
        try:
            # Send manual mode command
            if hasattr(self.connection, 'mav'):
                self.connection.mav.command_long_send(
                    self.connection.target_system,
                    self.connection.target_component,
                    mavutil.mavlink.MAV_CMD_DO_SET_MODE,
                    0,  # Confirmation
                    mavutil.mavlink.MAV_MODE_FLAG_SAFETY_ARMED,  # Mode
                    0, 0, 0, 0, 0, 0  # Unused parameters
                )
            return True
        except Exception as e:
            self._emit_error(f"Manuel moda geçiş hatası: {e}")
            return False
            
    def land(self) -> bool:
        """Acil iniş komutu gönder"""
        with self._connection_lock:
            if not self.connection or not self.is_connected:
                self._emit_error("Acil iniş hatası: Bağlantı aktif değil.")
                return False
                
        return self._send_land_command(self.connection)
        
    def _send_land_command(self, conn) -> bool:
        """İniş komutu gönder"""
        try:
            if hasattr(conn, 'mav'):
                conn.mav.command_long_send(
                    conn.target_system,
                    conn.target_component,
                    mavutil.mavlink.MAV_CMD_NAV_LAND,
                    0,  # Confirmation
                    0, 0, 0, 0, 0, 0, 0  # Unused parameters
                )
            return True
        except Exception as e:
            self._emit_error(f"İniş komutu hatası: {e}")
            return False
            
    def cut_motors(self) -> bool:
        """Motor kesme komutu gönder"""
        with self._connection_lock:
            if not self.connection or not self.is_connected:
                self._emit_error("Motor kesme hatası: Bağlantı aktif değil.")
                return False
                
        return self._send_cut_motors_command(self.connection)
        
    def _send_cut_motors_command(self, conn) -> bool:
        """Motor kesme komutu gönder"""
        try:
            # Disarm command
            if hasattr(conn, 'mav'):
                conn.mav.command_long_send(
                    conn.target_system,
                    conn.target_component,
                    mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM,
                    0,  # Confirmation
                    0,  # Disarm
                    0, 0, 0, 0, 0, 0  # Unused parameters
                )
            return True
        except Exception as e:
            self._emit_error(f"Motor kesme komutu hatası: {e}")
            return False
            
    def connect_hall_sensor(self, port_name: str, baudrate: int = 9600) -> bool:
        """Hall Effect sensörü için seri port bağlantısını kur"""
        try:
            with self._hall_lock:
                if self.hall_serial_port:
                    try:
                        self.hall_serial_port.close()
                    except:
                        pass
                
                self.hall_serial_port = serial.Serial(port_name, baudrate, timeout=1)
                self.hall_port_name = port_name
                self.hall_baudrate = baudrate
                print(f"[HALL] Sensör bağlandı: {port_name}")
                return True
                
        except Exception as e:
            self._emit_error(f"Hall Effect sensör bağlantı hatası: {e}")
            return False
    
    def read_hall_sensor_data(self) -> Dict[str, Any]:
        """Hall Effect sensör verilerini oku"""
        try:
            with self._hall_lock:
                if not self.hall_serial_port or not self.hall_serial_port.is_open:
                    return {'hall_effect': 0, 'magnetic_field': 0}
                
                # Sensörden veri oku
                if self.hall_serial_port.in_waiting > 0:
                    line = self.hall_serial_port.readline().decode('utf-8').strip()
                    if line:
                        # Sensör verisi formatı: "HALL:123,MAG:456" gibi
                        try:
                            parts = line.split(',')
                            for part in parts:
                                if part.startswith('HALL:'):
                                    self.hall_effect_value = int(part.split(':')[1])
                                elif part.startswith('MAG:'):
                                    self.magnetic_field_value = int(part.split(':')[1])
                        except:
                            pass
                
                return {
                    'hall_effect': self.hall_effect_value,
                    'magnetic_field': self.magnetic_field_value
                }
                
        except Exception as e:
            self._emit_error(f"Hall Effect sensör okuma hatası: {e}")
            return {'hall_effect': 0, 'magnetic_field': 0}
    
    def disconnect_hall_sensor(self) -> None:
        """Hall Effect sensör bağlantısını kes"""
        with self._hall_lock:
            if self.hall_serial_port:
                try:
                    self.hall_serial_port.close()
                except:
                    pass
                self.hall_serial_port = None
                self.hall_port_name = None
            
    def goto_altitude(self, target_alt: float) -> bool:
        """Belirli irtifaya git komutu"""
        with self._connection_lock:
            if not self.connection or not self.is_connected:
                self._emit_error("İrtifa komutu hatası: Bağlantı aktif değil.")
                return False
                
        if not self.last_lat or not self.last_lon:
            self._emit_error("Son konum bilgisi yok")
            return False
            
        try:
            # Waypoint oluştur ve gönder
            if hasattr(self.connection, 'mav'):
                self.connection.mav.mission_item_send(
                    self.connection.target_system,
                    self.connection.target_component,
                    0,  # Sequence
                    mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT,
                    mavutil.mavlink.MAV_CMD_NAV_WAYPOINT,
                    0, 0,  # Current, autocontinue
                    0, 0, 0, 0,  # Param 1-4
                    target_alt,  # Altitude
                    0, 0,  # X, Y
                    self.last_lat, self.last_lon  # Lat, Lon
                )
            return True
        except Exception as e:
            self._emit_error(f"İrtifa komutu hatası: {e}")
            return False
            
    def upload_mission(self, waypoints: List[Dict[str, Any]]) -> bool:
        """Görev yükle"""
        with self._connection_lock:
            if not self.connection or not self.is_connected:
                self._emit_error("Görev yükleme hatası: Bağlantı aktif değil.")
                return False
                
        try:
            # Mission clear
            if hasattr(self.connection, 'mav'):
                self.connection.mav.mission_clear_all_send(
                    self.connection.target_system,
                    self.connection.target_component
                )
                
                # Waypoint'leri yükle
                for i, wp in enumerate(waypoints):
                    lat = wp.get('lat', 0)
                    lon = wp.get('lon', 0)
                    alt = wp.get('alt', 0)
                    command = wp.get('command', 16)  # MAV_CMD_NAV_WAYPOINT varsayılan
                    param1 = wp.get('param1', 0)
                    param2 = wp.get('param2', 0)
                    param3 = wp.get('param3', 0)
                    param4 = wp.get('param4', 0)
                    
                    # DO_SET_RELAY komutları için koordinat kontrolü yapma
                    if command == 181:  # MAV_CMD_DO_SET_RELAY
                        # MAVLink mission item gönder
                        self.connection.mav.mission_item_send(
                            self.connection.target_system,
                            self.connection.target_component,
                            int(i),  # Sequence - integer olarak cast et
                            mavutil.mavlink.MAV_FRAME_MISSION,
                            command,  # MAV_CMD_DO_SET_RELAY
                            0, 0,  # Current, autocontinue
                            param1, param2, param3, param4,  # Param 1-4
                            0,  # Altitude (relay için kullanılmaz)
                            0, 0,  # X, Y (relay için kullanılmaz)
                            0, 0  # Lat, Lon (relay için kullanılmaz)
                        )
                    else:
                        # Normal waypoint komutları için koordinat doğrulaması
                        if not (-90.1 <= lat <= 90.1) or not (-180.1 <= lon <= 180.1):
                            self._emit_error(f"Geçersiz waypoint koordinatları: {i}")
                            return False
                            
                        # İrtifa doğrulaması - daha esnek
                        if alt < -50 or alt > 3000:  # 3000m maksimum
                            self._emit_error(f"Geçersiz waypoint irtifası: {i}")
                            return False
                            
                        # MAVLink mission item gönder
                        self.connection.mav.mission_item_send(
                            self.connection.target_system,
                            self.connection.target_component,
                            int(i),  # Sequence - integer olarak cast et
                            mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT,
                            command,  # Command
                            0, 0,  # Current, autocontinue
                            param1, param2, param3, param4,  # Param 1-4
                            alt,  # Altitude
                            0, 0,  # X, Y
                            lat, lon  # Lat, Lon
                        )
                    
                    # Her waypoint için ACK bekle
                    ack_received = False
                    start_time = time.time()
                    while time.time() - start_time < 2.0:  # 2 saniye timeout
                        try:
                            msg = self.connection.recv_match(type='MISSION_ACK', timeout=0.1)
                            if msg and msg.seq == i:
                                ack_received = True
                                break
                        except:
                            pass
                    
                    if not ack_received:
                        self._emit_error(f"Waypoint {i} ACK alınamadı")
                        return False
                    
                # Mission count gönder
                self.connection.mav.mission_count_send(
                    self.connection.target_system,
                    self.connection.target_component,
                    int(len(waypoints))  # Integer olarak cast et
                )
                
                # Mission count ACK bekle
                count_ack_received = False
                start_time = time.time()
                while time.time() - start_time < 3.0:  # 3 saniye timeout
                    try:
                        msg = self.connection.recv_match(type='MISSION_ACK', timeout=0.1)
                        if msg and msg.type == mavutil.mavlink.MAV_MISSION_ACCEPTED:
                            count_ack_received = True
                            break
                    except:
                        pass
                
                if not count_ack_received:
                    self._emit_error("Mission count ACK alınamadı")
                    return False
                
            return True
        except Exception as e:
            self._emit_error(f"Görev yükleme hatası: {e}")
            return False

    def upload_mission_raw(self, items: List[Dict[str, Any]]) -> bool:
        """
        QGC WPL formatından gelen ham mission item'ları aynen Pixhawk'a yaz.
        items: dict list with keys: seq,current,frame,command,param1..4,x,y,z,autocontinue
        """
        with self._connection_lock:
            if not self.connection or not self.is_connected:
                self._emit_error("Görev yükleme hatası: Bağlantı aktif değil.")
                return False

        try:
            if not hasattr(self.connection, 'mav'):
                self._emit_error("MAV nesnesi yok")
                return False

            # Mission clear
            self.connection.mav.mission_clear_all_send(
                self.connection.target_system,
                self.connection.target_component
            )

            # Mission count
            self.connection.mav.mission_count_send(
                self.connection.target_system,
                self.connection.target_component,
                int(len(items))
            )

            # Gönderim
            for it in items:
                seq = int(it.get('seq', 0))
                current = int(it.get('current', 0))
                frame = int(it.get('frame', mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT))
                command = int(it.get('command', 16))
                p1 = float(it.get('param1', 0))
                p2 = float(it.get('param2', 0))
                p3 = float(it.get('param3', 0))
                p4 = float(it.get('param4', 0))
                x = float(it.get('x', 0))
                y = float(it.get('y', 0))
                z = float(it.get('z', 0))
                autocont = int(it.get('autocontinue', 1))

                self.connection.mav.mission_item_send(
                    self.connection.target_system,
                    self.connection.target_component,
                    seq,
                    frame,
                    command,
                    current,
                    autocont,
                    p1, p2, p3, p4,
                    x, y, z
                )

            # Basit ACK bekleme
            start_time = time.time()
            while time.time() - start_time < 3.0:
                try:
                    msg = self.connection.recv_match(type='MISSION_ACK', timeout=0.1)
                    if msg and msg.type == mavutil.mavlink.MAV_MISSION_ACCEPTED:
                        return True
                except:
                    pass

            self._emit_error("Ham mission ACK alınamadı")
            return False
        except Exception as e:
            self._emit_error(f"Ham görev yükleme hatası: {e}")
            return False
            
    def start_mission(self) -> bool:
        """Görev başlat - önce AUTO moda geç, sonra MISSION_START gönder"""
        with self._connection_lock:
            if not self.connection or not self.is_connected:
                self._emit_error("Görev başlatma hatası: Bağlantı aktif değil.")
                return False
                
        try:
            # Önce AUTO moda geç
            if not self.set_mode('AUTO'):
                self._emit_error("UYARI: AUTO moda geçilemedi, yine de görevi başlatmayı deneyeceğim.")
                
            # MISSION_START komutu gönder
            if hasattr(self.connection, 'mav'):
                self.connection.mav.command_long_send(
                    self.connection.target_system,
                    self.connection.target_component,
                    mavutil.mavlink.MAV_CMD_MISSION_START,
                    0,  # Confirmation
                    0, 0, 0, 0, 0, 0, 0  # Unused parameters
                )
            return True
        except Exception as e:
            self._emit_error(f"Görev başlatma hatası: {e}")
            return False
            
    def pause_mission(self) -> bool:
        """Görev duraklat"""
        with self._connection_lock:
            if not self.connection or not self.is_connected:
                self._emit_error("Görev duraklatma hatası: Bağlantı aktif değil.")
                return False
                
        try:
            if hasattr(self.connection, 'mav'):
                self.connection.mav.command_long_send(
                    self.connection.target_system,
                    self.connection.target_component,
                    mavutil.mavlink.MAV_CMD_DO_PAUSE_CONTINUE,
                    0,  # Confirmation
                    1,  # Pause
                    0, 0, 0, 0, 0, 0  # Unused parameters
                )
            return True
        except Exception as e:
            self._emit_error(f"Görev duraklatma hatası: {e}")
            return False

    def resume_mission(self) -> bool:
        """Görevi devam ettir"""
        with self._connection_lock:
            if not self.connection or not self.is_connected:
                self._emit_error("Görev devam ettirme hatası: Bağlantı aktif değil.")
                return False
        try:
            if hasattr(self.connection, 'mav'):
                self.connection.mav.command_long_send(
                    self.connection.target_system,
                    self.connection.target_component,
                    mavutil.mavlink.MAV_CMD_DO_PAUSE_CONTINUE,
                    0,
                    0,  # Continue
                    0, 0, 0, 0, 0, 0
                )
            return True
        except Exception as e:
            self._emit_error(f"Görev devam ettirme hatası: {e}")
            return False
            
    def abort_mission(self) -> bool:
        """Görev iptal et"""
        with self._connection_lock:
            if not self.connection or not self.is_connected:
                self._emit_error("Görev iptal hatası: Bağlantı aktif değil.")
                return False
                
        try:
            # Mission clear
            if hasattr(self.connection, 'mav'):
                self.connection.mav.mission_clear_all_send(
                    self.connection.target_system,
                    self.connection.target_component
                )
                
            # RTL komutu gönder
            if self.home_position:
                return self.return_to_home()
            else:
                return self.land()
                
        except Exception as e:
            self._emit_error(f"Görev iptal hatası: {e}")
            return False
            
    def add_waypoint(self, lat: float, lon: float, alt: float) -> bool:
        """Waypoint ekle"""
        with self._connection_lock:
            if not self.connection or not self.is_connected:
                self._emit_error("Waypoint ekleme hatası: Bağlantı aktif değil.")
                return False
                
        # Koordinat doğrulaması - daha esnek
        if not (-90.1 <= lat <= 90.1) or not (-180.1 <= lon <= 180.1):
            self._emit_error("Geçersiz koordinat değerleri")
            return False
            
        # İrtifa doğrulaması - daha esnek
        if alt < -50 or alt > 3000:  # 3000m maksimum
            self._emit_error("Geçersiz irtifa değeri")
            return False
            
        try:
            # Waypoint ekle
            if hasattr(self.connection, 'mav'):
                self.connection.mav.mission_item_send(
                    self.connection.target_system,
                    self.connection.target_component,
                    0,  # Sequence (will be updated)
                    mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT,
                    mavutil.mavlink.MAV_CMD_NAV_WAYPOINT,
                    0, 0,  # Current, autocontinue
                    0, 0, 0, 0,  # Param 1-4
                    alt,  # Altitude
                    0, 0,  # X, Y
                    lat, lon  # Lat, Lon
                )
            return True
        except Exception as e:
            self._emit_error(f"Waypoint ekleme hatası: {e}")
            return False
            
    def remove_last_waypoint(self) -> bool:
        """Son waypoint'i kaldır"""
        # Bu fonksiyon MAVLink protokolünde doğrudan desteklenmez
        # Görev yeniden yüklenmeli
        return True
        
    def arm_and_takeoff(self, target_alt: float) -> bool:
        """Arm ve takeoff - sabit kanat için görev tabanlı"""
        with self._connection_lock:
            if not self.connection or not self.is_connected:
                self._emit_error("Arm/Takeoff hatası: Bağlantı aktif değil.")
                return False
                
        if not self.home_position:
            self._emit_error("Ev konumu ayarlanmamış")
            return False
            
        # İrtifa doğrulaması - daha esnek
        if target_alt < 0 or target_alt > 3000:  # 3000m maksimum
            self._emit_error("Geçersiz takeoff irtifası")
            return False
            
        try:
            # Arm command
            if hasattr(self.connection, 'mav'):
                self.connection.mav.command_long_send(
                    self.connection.target_system,
                    self.connection.target_component,
                    mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM,
                    0,  # Confirmation
                    1,  # Arm
                    0, 0, 0, 0, 0, 0  # Unused parameters
                )
                
                # Sabit kanat için TAKEOFF waypoint'i oluştur ve gönder
                # Bu waypoint görev listesine eklenir ve AUTO modda çalıştırılır
                self.connection.mav.mission_item_send(
                    self.connection.target_system,
                    self.connection.target_component,
                    0,  # Sequence
                    mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT,
                    mavutil.mavlink.MAV_CMD_NAV_TAKEOFF,
                    0, 0,  # Current, autocontinue
                    0, 0, 0, 0,  # Param 1-4
                    target_alt,  # Altitude
                    0, 0,  # X, Y
                    self.home_position['lat'], self.home_position['lon']  # Lat, Lon
                )
                
                # AUTO moda geç
                self.set_mode('AUTO')
                
            return True
        except Exception as e:
            self._emit_error(f"Arm/Takeoff hatası: {e}")
            return False
            
    def land(self) -> bool:
        """İniş komutu gönder"""
        with self._connection_lock:
            if not self.connection or not self.is_connected:
                self._emit_error("İniş hatası: Bağlantı aktif değil.")
                return False
                
        try:
            if hasattr(self.connection, 'mav'):
                self.connection.mav.command_long_send(
                    self.connection.target_system,
                    self.connection.target_component,
                    mavutil.mavlink.MAV_CMD_NAV_LAND,
                    0,  # Confirmation
                    0, 0, 0, 0, 0, 0, 0  # Unused parameters
                )
            return True
        except Exception as e:
            self._emit_error(f"İniş hatası: {e}")
            return False
            
    def handle_automatic_action(self, action: str) -> None:
        """Otomatik aksiyon işle"""
        if action == "RTL":
            self.return_to_home()
        elif action == "LAND":
            self.land()
        elif action == "MANUAL":
            self.switch_to_manual()
        else:
            self._emit_error(f"Bilinmeyen otomatik aksiyon: {action}")
            
    def run(self):
        """Ana thread döngüsü"""
        while self.running:
            try:
                # Koruma: kritik alanlar yoksa varsayılanları ayarla
                if not hasattr(self, 'connection_timeout'):
                    self.connection_timeout = 10
                if not hasattr(self, 'last_heartbeat'):
                    self.last_heartbeat = None
                if not hasattr(self, 'armed'):
                    self.armed = False
                with self._connection_lock:
                    if not self.connection or not self.is_connected:
                        time.sleep(1)
                        continue
                        
                # Mesajları oku
                try:
                    msg = self.connection.recv_match(blocking=False, timeout=0.1)
                except Exception as ser_e:
                    # Seri port hatalarını bastırıp bildir, döngüye devam et
                    self._emit_error(f"Seri okuma hatası: {ser_e}")
                    time.sleep(0.2)
                    continue
                if msg:
                    self._process_message(msg)
                    
                # Bağlantı timeout kontrolü
                if self.last_heartbeat and time.time() - self.last_heartbeat > self.connection_timeout:
                    self.is_connected = False
                    self._emit_error("Bağlantı timeout")
                    
            except Exception as e:
                self._emit_error(f"Thread hatası: {e}")
                time.sleep(1)
                
    def _process_message(self, msg) -> None:
        """MAVLink mesajını işle"""
        try:
            msg_type = msg.get_type()
            
            if msg_type == 'HEARTBEAT':
                self.last_heartbeat = time.time()
                # ARM durumu güncelle
                base_mode = getattr(msg, 'base_mode', 0)
                self.armed = bool(base_mode & mavutil.mavlink.MAV_MODE_FLAG_SAFETY_ARMED)
                # Uçuş modu çözümü
                custom_mode = getattr(msg, 'custom_mode', None)
                mode_str = None
                if custom_mode is not None:
                    # ArduPilot/ArduPlane modları
                    mode_map = {
                        0: 'MANUAL', 1: 'CIRCLE', 2: 'STABILIZE', 3: 'TRAINING', 4: 'ACRO', 5: 'FLY_BY_WIRE_A',
                        6: 'FLY_BY_WIRE_B', 7: 'CRUISE', 8: 'AUTOTUNE', 10: 'AUTO', 11: 'RTL', 12: 'LOITER',
                        14: 'TAKEOFF', 15: 'AVOID_ADSB', 16: 'GUIDED', 17: 'INITIALISING', 18: 'QSTABILIZE',
                        19: 'QHOVER', 20: 'QLOITER', 21: 'QLAND', 22: 'QRTL', 23: 'QAUTOTUNE', 24: 'QACRO'
                    }
                    mode_str = mode_map.get(custom_mode, f'CUSTOM({custom_mode})')
                else:
                    mode_str = 'UNKNOWN'
                self.last_mode = mode_str  # <-- MODU KAYDET
                # Telemetriye ilet
                self.telemetry_received.emit({'armed': self.armed, 'mode': mode_str})
                
            elif msg_type == 'GPS_RAW_INT':
                # GPS verisi
                lat = msg.lat / 1e7
                lon = msg.lon / 1e7
                alt = msg.alt / 1000.0
                
                position_data = {
                    'lat': lat,
                    'lon': lon,
                    'alt': alt,
                    'heading': getattr(msg, 'hdg', 0) / 100.0,
                    'groundspeed': getattr(msg, 'vel', 0) / 100.0,
                    'gps_fix': msg.fix_type,
                    'satellites': msg.satellites_visible
                }
                
                self.last_lat = lat
                self.last_lon = lon
                self.position_received.emit(position_data)
                
            elif msg_type == 'ATTITUDE':
                # Attitude verisi
                attitude_data = {
                    'roll': math.degrees(msg.roll),
                    'pitch': math.degrees(msg.pitch),
                    'yaw': math.degrees(msg.yaw),
                    'roll_rate': math.degrees(msg.rollspeed),
                    'pitch_rate': math.degrees(msg.pitchspeed),
                    'yaw_rate': math.degrees(msg.yawspeed)
                }
                self.attitude_received.emit(attitude_data)
                
            elif msg_type == 'VFR_HUD':
                # Telemetri verisi
                telemetry_data = {
                    'alt': msg.alt,
                    'speed': msg.airspeed,
                    'groundspeed': msg.groundspeed,
                    'heading': msg.heading,
                    'throttle': msg.throttle,
                    'climb': msg.climb,
                    'armed': self.armed,
                    'mode': getattr(self, 'last_mode', 'UNKNOWN')
                }
                # Acil durum kontrolü
                emergency_conditions = self.check_emergency_conditions(telemetry_data)
                if emergency_conditions:
                    self.emergency_triggered.emit({'conditions': emergency_conditions})
                self.telemetry_received.emit(telemetry_data)
                
            elif msg_type == 'SYS_STATUS':
                # Sistem durumu
                system_data = {
                    'voltage': msg.voltage_battery / 1000.0,
                    'current': msg.current_battery / 100.0,
                    'battery': msg.battery_remaining,
                    'temperature': getattr(msg, 'temperature', 25),
                    'mode': getattr(self, 'last_mode', 'UNKNOWN')
                }
                self.telemetry_received.emit(system_data)
            
            elif msg_type == 'MISSION_ITEM_REACHED':
                # Waypoint'e ulaşıldı
                waypoint_index = msg.seq
                self.telemetry_received.emit({'waypoint_reached': waypoint_index})
                
            elif msg_type == 'MISSION_ACK':
                # Görev tamamlandı
                if msg.type == mavutil.mavlink.MAV_MISSION_ACCEPTED:
                    self.mission_completed.emit()
                    self.telemetry_received.emit({'mission_completed': True})
                
            elif msg_type == 'RADIO_STATUS':
                # RSSI verisi
                rssi = getattr(msg, 'rssi', None)
                print(f"[MAVLINK] RADIO_STATUS geldi, rssi: {rssi}")
                if rssi is not None:
                    self.telemetry_received.emit({'rssi': rssi})
                
        except Exception as e:
            self._emit_error(f"Mesaj işleme hatası: {e}")
            
    def stop(self):
        """Thread'i durdur"""
        self.running = False
        
        # Bağlantıları kapat
        with self._connection_lock:
            if self.connection:
                try:
                    self.connection.close()
                except:
                    pass
                self.connection = None
                
        with self._hall_lock:
            if self.hall_serial_port:
                try:
                    self.hall_serial_port.close()
                except:
                    pass
                self.hall_serial_port = None
                
        self.is_connected = False 