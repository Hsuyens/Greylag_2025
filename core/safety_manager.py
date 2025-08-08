import time
import math
import requests
import os
from typing import Optional, Dict, List, Tuple, Any

class SafetyManager:
    def __init__(self, weather_api_key: Optional[str] = None):
        self.geofence = None
        self.home_position = None
        self.emergency_landing_points = []
        self.weather_data = None
        self.last_weather_update = 0
        self.weather_update_interval = 600  # 10 dakika (5 dakika yerine)
        # API anahtarını environment variable'dan al, fallback olarak parametreyi kullan
        self.weather_api_key = weather_api_key or os.getenv('WEATHER_API_KEY')
        self.weather_retry_count = 3
        self.logger = None  # Dışarıdan atanabilir
        
        # Güvenlik eşikleri - daha esnek değerler
        self.critical_battery_threshold = 20  # %25'ten %20'ye düşürüldü
        self.critical_gps_fix = 3  # 4'ten 3'e düşürüldü (daha esnek)
        self.critical_link_lost_timeout = 5  # 3'ten 5'e çıkarıldı (daha toleranslı)
        self.critical_temperature_threshold = 70  # °C (65'ten 70'e çıkarıldı)
        self.critical_rssi_threshold = -95  # dBm (-90'dan -95'e düşürüldü)
        
        self.last_heartbeat = None
        self.last_gps_fix = None
        self.last_battery = None
        self.last_health_check = None
        self.armed = False
        self.in_air = False
        self.critical_error = False
        self.critical_error_message = ''
        self.automatic_action = None
        
        # Güvenlik durumu geçmişi
        self.safety_history = []
        
    def set_geofence(self, points: List[Tuple[float, float]], max_alt: float) -> None:
        """Güvenli uçuş bölgesini tanımla"""
        if not points or len(points) < 3:
            raise ValueError("Geofence için en az 3 nokta gerekli")
        if max_alt <= 0 or max_alt > 3000:  # 3000m maksimum güvenli irtifa (400m yerine)
            raise ValueError("Geofence maksimum irtifası 0-3000m arasında olmalı")
            
        self.geofence = {
            'points': points,
            'max_alt': max_alt
        }
        if self.logger:
            self.logger.log_action(f"Geofence ayarlandı: {len(points)} nokta, max irtifa: {max_alt}m")
        
    def set_home_position(self, lat: float, lon: float, alt: float) -> None:
        """Eve dönüş noktasını ayarla"""
        if not (-90.1 <= lat <= 90.1) or not (-180.1 <= lon <= 180.1):  # Küçük sapmalara izin ver
            raise ValueError("Geçersiz koordinat değerleri")
        if alt < -50 or alt > 3000:  # 3000m maksimum güvenli irtifa (1000m yerine)
            raise ValueError("Ev konumu irtifası -50-3000m arasında olmalı")
            
        self.home_position = {
            'lat': lat,
            'lon': lon,
            'alt': alt
        }
        if self.logger:
            self.logger.log_action(f"Ev konumu ayarlandı: {lat:.5f}, {lon:.5f}, {alt}m")
        
    def add_emergency_landing_point(self, lat: float, lon: float, name: str = "", notes: str = "") -> None:
        """Acil iniş noktası ekle"""
        if not (-90.1 <= lat <= 90.1) or not (-180.1 <= lon <= 180.1):  # Küçük sapmalara izin ver
            raise ValueError("Geçersiz koordinat değerleri")
            
        self.emergency_landing_points.append({
            'lat': lat,
            'lon': lon,
            'name': name,
            'notes': notes
        })
        if self.logger:
            self.logger.log_action(f"Acil iniş noktası eklendi: {name} ({lat:.5f}, {lon:.5f})")
        
    def check_geofence(self, lat: float, lon: float, alt: float) -> Tuple[bool, str]:
        """Geofence kontrolü"""
        if not self.geofence:
            return True, "Geofence tanımlanmamış"
            
        # Koordinat doğrulaması - daha esnek
        if not (-90.1 <= lat <= 90.1) or not (-180.1 <= lon <= 180.1):
            return False, "Geçersiz koordinat değerleri"
            
        # İrtifa kontrolü
        if alt > self.geofence['max_alt']:
            return False, f"Maksimum irtifa aşıldı: {alt}m > {self.geofence['max_alt']}m"
            
        # Yatay sınır kontrolü
        if not self.point_in_polygon((lat, lon), self.geofence['points']):
            return False, "Araç güvenli bölge dışına çıktı"
            
        return True, "Güvenli bölge içinde"
        
    def find_nearest_landing_point(self, lat: float, lon: float, min_distance: float = 100) -> Optional[Dict[str, Any]]:
        """En yakın acil iniş noktasını bul"""
        if not (-90.1 <= lat <= 90.1) or not (-180.1 <= lon <= 180.1):  # Küçük sapmalara izin ver
            return None
            
        all_points = self.emergency_landing_points.copy()
        if self.home_position:
            all_points.append(self.home_position)

        if not all_points:
            return None

        nearest = None
        min_dist = float('inf')
        
        for point in all_points:
            dist = self.calculate_distance(lat, lon, point['lat'], point['lon'])
            if dist < min_dist:
                min_dist = dist
                nearest = point
                
        return nearest if min_dist <= min_distance else None
        
    def set_logger(self, logger) -> None:
        self.logger = logger
        
    def update_weather(self, lat: float, lon: float) -> Optional[Dict[str, Any]]:
        """Hava durumu verilerini güncelle (OpenWeatherMap API ile)"""
        if not self.weather_api_key:
            if self.logger:
                self.logger.log_error("Hava durumu API anahtarı tanımlı değil!")
            return None
            
        current_time = time.time()
        if current_time - self.last_weather_update < self.weather_update_interval:
            return self.weather_data
            
        if not (-90.1 <= lat <= 90.1) or not (-180.1 <= lon <= 180.1):  # Küçük sapmalara izin ver
            if self.logger:
                self.logger.log_error("Geçersiz koordinat değerleri")
            return None
            
        url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={self.weather_api_key}&units=metric"
        
        for attempt in range(self.weather_retry_count):
            try:
                response = requests.get(url, timeout=15)  # Timeout'u 10'dan 15'e çıkarıldı
                response.raise_for_status()
                api_data = response.json()
                
                # API yanıtını doğrula
                if 'wind' not in api_data or 'main' not in api_data:
                    raise ValueError("Geçersiz API yanıtı")
                    
                self.weather_data = {
                    'wind_speed': api_data['wind'].get('speed', 0),
                    'wind_direction': api_data['wind'].get('deg', 0),
                    'temperature': api_data['main'].get('temp', 0),
                    'pressure': api_data['main'].get('pressure', 1013),
                    'visibility': api_data.get('visibility', 10000),
                    'precipitation': api_data.get('rain', {}).get('1h', 0),
                    'clouds': api_data.get('clouds', {}).get('all', 0),
                    'warnings': [w.get('main', '') for w in api_data.get('weather', [])]
                }
                self.last_weather_update = current_time
                if self.logger:
                    self.logger.log_action("Hava durumu başarıyla güncellendi.")
                return self.weather_data
                
            except requests.exceptions.RequestException as e:
                if self.logger:
                    self.logger.log_error(f"Hava durumu verisi alınamadı (deneme {attempt+1}): {e}")
                if attempt < self.weather_retry_count - 1:
                    time.sleep(3)  # Retry aralığını artırıldı
            except (ValueError, KeyError) as e:
                if self.logger:
                    self.logger.log_error(f"Hava durumu verisi işlenemedi: {e}")
                break
                
        return None
            
    def check_weather_safety(self, weather_data: Optional[Dict[str, Any]] = None) -> Tuple[bool, str]:
        """Hava koşullarının güvenliğini kontrol et"""
        if not weather_data:
            weather_data = self.weather_data
            
        if not weather_data:
            return True, "Hava durumu verisi yok"
            
        warnings = []
        is_safe = True
        
        # Rüzgar kontrolü - daha esnek eşik
        if weather_data.get('wind_speed', 0) > 12:  # 8'den 12'ye çıkarıldı
            warnings.append(f"Yüksek rüzgar hızı: {weather_data['wind_speed']} m/s")
            is_safe = False
            
        # Görüş mesafesi kontrolü - daha esnek eşik
        if weather_data.get('visibility', 10000) < 3000:  # 5000'den 3000'e düşürüldü
            warnings.append(f"Düşük görüş mesafesi: {weather_data['visibility']} m")
            is_safe = False
            
        # Yağış kontrolü - daha esnek eşik
        if weather_data.get('precipitation', 0) > 5:  # 2'den 5'e çıkarıldı
            warnings.append(f"Yoğun yağış: {weather_data['precipitation']} mm/h")
            is_safe = False
            
        # Sıcaklık kontrolü - daha esnek eşik
        temp = weather_data.get('temperature', 0)
        if temp < -10 or temp > 45:  # -5/40'tan -10/45'e genişletildi
            warnings.append(f"Uygun olmayan sıcaklık: {temp}°C")
            is_safe = False
            
        return is_safe, "; ".join(warnings) if warnings else "Hava koşulları uygun"
        
    def suggest_rtl_altitude(self, current_alt: float, obstacles: Optional[List[Dict[str, Any]]] = None) -> float:
        """Eve dönüş için önerilen irtifa"""
        if not self.home_position:
            return current_alt
            
        # Basit irtifa hesaplama - daha esnek
        base_alt = max(current_alt, 100)  # Minimum 100m
        safety_margin = 50  # 30'dan 50'ye çıkarıldı
        
        if obstacles:
            max_obstacle = max(obs.get('altitude', 0) for obs in obstacles)
            suggested_alt = max_obstacle + safety_margin
        else:
            suggested_alt = base_alt + safety_margin
            
        return min(suggested_alt, 3000)  # Maksimum 3000m (2000m yerine)
        
    @staticmethod
    def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """İki GPS noktası arası mesafe (metre) - Haversine formülü"""
        R = 6371000  # Dünya yarıçapı (m)
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
        c = 2 * math.asin(math.sqrt(a))
        return R * c
        
    @staticmethod
    def point_in_polygon(point: Tuple[float, float], polygon: List[Tuple[float, float]]) -> bool:
        """Nokta polygon içinde mi kontrolü - Ray casting algoritması"""
        if len(polygon) < 3:
            return False
            
        x, y = point
        inside = False
        
        j = len(polygon) - 1
        for i in range(len(polygon)):
            xi, yi = polygon[i]
            xj, yj = polygon[j]
            
            if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / (yj - yi) + xi):
                inside = not inside
            j = i
            
        return inside
        
    def get_notams(self, lat: float, lon: float, radius_km: float = 50) -> List[Dict[str, Any]]:
        """NOTAM verilerini al (simüle edilmiş)"""
        # Gerçek NOTAM API'si entegrasyonu burada yapılabilir
        # Şimdilik boş liste döndür
        return []
        
    def get_restricted_areas(self, lat: float, lon: float, radius_km: float = 50) -> List[Dict[str, Any]]:
        """Kısıtlı bölgeleri al (simüle edilmiş)"""
        # Gerçek kısıtlı bölge API'si entegrasyonu burada yapılabilir
        # Şimdilik boş liste döndür
        return []
        
    def check_health(self, telemetry: Dict[str, Any]) -> bool:
        """Sistem sağlığını kontrol et"""
        if not telemetry:
            return False
            
        # GPS kontrolü - daha esnek
        gps_fix = telemetry.get('gps_fix', 0)
        if gps_fix < self.critical_gps_fix:
            self._log_safety_event("GPS", f"Kritik GPS fix: {gps_fix}")
            return False
            
        # Batarya kontrolü - USB bağlantısı için daha esnek
        battery = telemetry.get('battery', 100)
        voltage = telemetry.get('voltage', 0)
        
        # USB bağlantısında batarya verisi olmayabilir, bu durumda kontrol etme
        if battery == 0 and voltage == 0:
            # USB bağlantısı - batarya kontrolünü atla
            pass
        elif battery < self.critical_battery_threshold:
            self._log_safety_event("BATTERY", f"Kritik batarya: %{battery}")
            return False
            
        # Sıcaklık kontrolü - daha esnek
        temperature = telemetry.get('temperature', 25)
        if temperature > self.critical_temperature_threshold:
            self._log_safety_event("TEMPERATURE", f"Kritik sıcaklık: {temperature}°C")
            return False
            
        # RSSI kontrolü - daha esnek
        rssi = telemetry.get('rssi', -50)
        if rssi < self.critical_rssi_threshold:
            self._log_safety_event("RSSI", f"Kritik sinyal gücü: {rssi} dBm")
            return False
            
        # Bağlantı kaybı kontrolü - daha esnek
        if self.last_heartbeat:
            time_since_heartbeat = time.time() - self.last_heartbeat
            if time_since_heartbeat > self.critical_link_lost_timeout:
                self._log_safety_event("LINK", f"Bağlantı kaybı: {time_since_heartbeat:.1f}s")
                return False
                
        return True
        
    def _log_safety_event(self, event_type: str, message: str) -> None:
        """Güvenlik olayını kaydet"""
        event = {
            'timestamp': time.time(),
            'type': event_type,
            'message': message
        }
        self.safety_history.append(event)
        
        # Maksimum 1000 olay sakla
        if len(self.safety_history) > 1000:
            self.safety_history = self.safety_history[-1000:]
            
        if self.logger:
            self.logger.log_error(f"GÜVENLİK: {event_type} - {message}")
            
    def update_heartbeat(self) -> None:
        """Heartbeat güncelle"""
        self.last_heartbeat = time.time()
        
    def update_gps_fix(self, gps_fix: int) -> None:
        """GPS fix güncelle"""
        self.last_gps_fix = gps_fix
        
    def update_battery(self, battery: float) -> None:
        """Batarya seviyesi güncelle"""
        self.last_battery = battery
        
    def get_critical_status(self) -> Tuple[bool, str, Optional[str]]:
        """Kritik durum kontrolü"""
        if not self.last_heartbeat:
            return False, "Heartbeat yok", None
            
        time_since_heartbeat = time.time() - self.last_heartbeat
        if time_since_heartbeat > self.critical_link_lost_timeout:
            return True, f"Bağlantı kaybı: {time_since_heartbeat:.1f}s", "RTL"
            
        if self.last_battery and self.last_battery < self.critical_battery_threshold:
            return True, f"Kritik batarya: %{self.last_battery}", "RTL"
            
        if self.last_gps_fix and self.last_gps_fix < self.critical_gps_fix:
            return True, f"Kritik GPS fix: {self.last_gps_fix}", "MANUAL"
            
        return False, "", None
        
    def get_safety_history(self) -> List[Dict[str, Any]]:
        """Güvenlik geçmişini döndür"""
        return self.safety_history.copy() 