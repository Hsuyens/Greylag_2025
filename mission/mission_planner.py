import math
import json

class MissionPlanner:
    def __init__(self):
        self.waypoints = []
        self.polygons = []
        self.raw_mission_items = []  # Yüklü .waypoints dosyasındaki ham mission item listesi
        self.mission_types = {
            'waypoint': 'Waypoint Uçuşu',
            'grid': 'Grid Tarama', 
            'polygon': 'Poligon Tarama',
            'spiral': 'Spiral Tarama',
            'infinity': '8 Şekli Uçuş'
        }
        # Sonsuzluk işareti için geçici noktalar
        self.infinity_points = []
        self.map_panel = None  # Harita paneli referansı (isteğe bağlı)
        
    def add_waypoint(self, lat, lon, alt, command=16):  # MAV_CMD_NAV_WAYPOINT = 16
        waypoint = {
            'lat': lat,
            'lon': lon,
            'alt': alt,
            'command': command,
            'param1': 0,  # Hold time (seconds)
            'param2': 2,  # Acceptance radius (meters)
            'param3': 0,  # Pass by waypoint (0 = False)
            'param4': 0,  # Desired yaw angle
            'seq': len(self.waypoints)
        }
        self.waypoints.append(waypoint)
        return len(self.waypoints) - 1
        
    def remove_waypoint(self, index):
        if 0 <= index < len(self.waypoints):
            self.waypoints.pop(index)
            # Yeniden sıralama
            for i in range(index, len(self.waypoints)):
                self.waypoints[i]['seq'] = i
                
    def move_waypoint(self, index, new_lat, new_lon):
        if 0 <= index < len(self.waypoints):
            self.waypoints[index]['lat'] = new_lat
            self.waypoints[index]['lon'] = new_lon
            
    def add_polygon(self, points):
        """Points: [(lat1, lon1), (lat2, lon2), ...]"""
        self.polygons.append(points)
        return len(self.polygons) - 1
        
    def add_polygon_point(self, lat, lon):
        if not self.polygons:
            self.polygons.append([])
        self.polygons[0].append((lat, lon))

    def add_infinity_point(self, lat, lon):
        """Sonsuzluk işareti için nokta ekler"""
        self.infinity_points.append((lat, lon))
        if len(self.infinity_points) > 2:
            self.infinity_points.pop(0)  # En fazla 2 nokta tut

    def generate_infinity_pattern(self, altitude, radius_meters):
        """İki nokta arasında sonsuzluk işareti (8) şeklinde waypoint'ler oluşturur"""
        if len(self.infinity_points) != 2:
            return False
            
        point1, point2 = self.infinity_points
        
        # İki nokta arasındaki mesafeyi hesapla
        distance = self.calculate_distance(point1[0], point1[1], point2[0], point2[1])
        
        # Yarıçap kontrolü
        if radius_meters > distance / 2:
            radius_meters = distance / 2 - 5  # Güvenlik payı
        
        # İki nokta arasındaki orta nokta
        center_lat = (point1[0] + point2[0]) / 2
        center_lon = (point1[1] + point2[1]) / 2
        
        # İki nokta arasındaki açıyı hesapla
        angle_rad = math.atan2(point2[0] - point1[0], point2[1] - point1[1])
        
        # 8 şeklini oluşturmak için gerekli noktalar
        waypoints = []
        
        # Sol döngü merkezi
        left_center_lat = center_lat - (radius_meters / 111111.0) * math.cos(angle_rad)
        left_center_lon = center_lon - (radius_meters / (111111.0 * math.cos(math.radians(center_lat)))) * math.sin(angle_rad)
        
        # Sağ döngü merkezi
        right_center_lat = center_lat + (radius_meters / 111111.0) * math.cos(angle_rad)
        right_center_lon = center_lon + (radius_meters / (111111.0 * math.cos(math.radians(center_lat)))) * math.sin(angle_rad)
        
        # Sol döngü waypoint'leri (saat yönünde)
        for i in range(0, 361, 30):  # 30 derece aralıklarla
            angle = math.radians(i)
            wp_lat = left_center_lat + (radius_meters / 111111.0) * math.cos(angle)
            wp_lon = left_center_lon + (radius_meters / (111111.0 * math.cos(math.radians(left_center_lat)))) * math.sin(angle)
            waypoints.append({'lat': wp_lat, 'lon': wp_lon, 'alt': altitude})
        
        # Sağ döngü waypoint'leri (saat yönünün tersine)
        for i in range(360, -1, -30):  # 30 derece aralıklarla
            angle = math.radians(i)
            wp_lat = right_center_lat + (radius_meters / 111111.0) * math.cos(angle)
            wp_lon = right_center_lon + (radius_meters / (111111.0 * math.cos(math.radians(right_center_lat)))) * math.sin(angle)
            waypoints.append({'lat': wp_lat, 'lon': wp_lon, 'alt': altitude})
        
        # Waypoint'leri mevcut listeye ekle
        for wp in waypoints:
            self.add_waypoint(wp['lat'], wp['lon'], wp['alt'])
        
        # Geçici noktaları temizle
        self.infinity_points = []
        
        return True

    def clear_infinity_points(self):
        """Sonsuzluk işareti için geçici noktaları temizle"""
        self.infinity_points = []

    def generate_waypoint_mission(self, altitude, speed):
        """Waypoint görevi oluşturur"""
        # Mevcut waypoint'ler zaten var, sadece parametreleri güncelle
        for wp in self.waypoints:
            wp['alt'] = altitude
        return True

    def generate_grid_mission(self, altitude, spacing, speed):
        """Grid tarama görevi oluşturur"""
        if not self.polygons or not self.polygons[0]:
            return False
        self.generate_grid_scan(self.polygons[0], altitude, spacing)
        return True

    def generate_polygon_mission(self, altitude, speed):
        """Poligon tarama görevi oluşturur"""
        if not self.polygons or not self.polygons[0]:
            return False
        # Poligon çevresinde waypoint'ler oluştur
        polygon = self.polygons[0]
        self.waypoints = []
        for point in polygon:
            self.add_waypoint(point[0], point[1], altitude)
        return True

    def generate_grid_scan(self, polygon, altitude, spacing):
        """Verilen poligon içinde grid tarama görevi oluşturur"""
        if len(polygon) < 3: return
        # Poligonun sınırlarını bul
        lats = [p[0] for p in polygon]
        lons = [p[1] for p in polygon]
        min_lat, max_lat = min(lats), max(lats)
        min_lon, max_lon = min(lons), max(lons)
        
        # Grid noktalarını oluştur
        new_waypoints = []
        lat_step = spacing / 111111.0
        lon_step = spacing / (111111.0 * abs(math.cos(math.radians(min_lat))))

        current_lat = min_lat
        direction = 1
        
        while current_lat <= max_lat:
            if direction == 1:
                current_lon = min_lon
                while current_lon <= max_lon:
                    if self.point_in_polygon((current_lat, current_lon), polygon):
                        new_waypoints.append({'lat': current_lat, 'lon': current_lon, 'alt': altitude})
                    current_lon += lon_step
            else:
                current_lon = max_lon
                while current_lon >= min_lon:
                    if self.point_in_polygon((current_lat, current_lon), polygon):
                        new_waypoints.append({'lat': current_lat, 'lon': current_lon, 'alt': altitude})
                    current_lon -= lon_step
            current_lat += lat_step
            direction *= -1
            
        self.waypoints = new_waypoints
            
    def generate_spiral_scan(self, center_lat, center_lon, radius, altitude, spacing):
        """Merkez noktası etrafında spiral tarama görevi oluşturur"""
        new_waypoints = []
        angle = 0
        current_radius = 0
        
        while current_radius <= radius:
            lat = center_lat + (current_radius * math.cos(angle) / 111111)
            lon = center_lon + (current_radius * math.sin(angle) / (111111 * math.cos(math.radians(center_lat))))
            new_waypoints.append({'lat': lat, 'lon': lon, 'alt': altitude})
            
            if current_radius > 0:
                angle_step = 2 * math.asin(spacing / (2 * current_radius))
                angle += angle_step
            
            current_radius += (spacing * angle_step) / (2 * math.pi) if 'angle_step' in locals() else spacing

        self.waypoints = new_waypoints
            
    def estimate_mission_time(self, ground_speed: float = 10.0):
        """Görev süresini tahmin eder (saniye)"""
        if len(self.waypoints) < 2 or ground_speed <= 0:
            return 0
            
        total_distance = 0
        for i in range(len(self.waypoints) - 1):
            wp1 = self.waypoints[i]
            wp2 = self.waypoints[i + 1]
            total_distance += self.calculate_distance(
                wp1['lat'], wp1['lon'],
                wp2['lat'], wp2['lon']
            )
            
        return total_distance / ground_speed
        
    @staticmethod
    def calculate_distance(lat1, lon1, lat2, lon2):
        """İki nokta arası mesafeyi hesaplar (metre)"""
        R = 6371000  # Dünya yarıçapı (metre)
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        delta_phi = math.radians(lat2 - lat1)
        delta_lambda = math.radians(lon2 - lon1)
        
        a = (math.sin(delta_phi/2) * math.sin(delta_phi/2) +
             math.cos(phi1) * math.cos(phi2) *
             math.sin(delta_lambda/2) * math.sin(delta_lambda/2))
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        
        return R * c
        
    @staticmethod
    def point_in_polygon(point, polygon):
        """Noktanın poligon içinde olup olmadığını kontrol eder"""
        x, y = point[0], point[1]
        n = len(polygon)
        inside = False
        
        p1x, p1y = polygon[0]
        for i in range(n + 1):
            p2x, p2y = polygon[i % n]
            if y > min(p1y, p2y):
                if y <= max(p1y, p2y):
                    if x <= max(p1x, p2x):
                        if p1y != p2y:
                            xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                        if p1x == p2x or x <= xinters:
                            inside = not inside
            p1x, p1y = p2x, p2y
            
        return inside 

    def set_waypoints(self, waypoints):
        """Waypoint listesini doğrudan ayarla ve haritayı güncelle"""
        self.waypoints = waypoints
        if self.map_panel:
            self.map_panel.update_map()
            
    def clear_infinity_points(self):
        """Sonsuzluk işareti için geçici noktaları temizle"""
        self.infinity_points = []

    def add_relay_command(self, relay_number, state, delay_seconds=0):
        """DO_SET_RELAY komutu ekler (MAV_CMD_DO_SET_RELAY = 181)"""
        relay_command = {
            'lat': 0,  # Relay komutları için koordinat gerekmez
            'lon': 0,
            'alt': 0,
            'command': 181,  # MAV_CMD_DO_SET_RELAY
            'param1': relay_number,  # Relay number (0-15)
            'param2': state,  # 0=off, 1=on
            'param3': delay_seconds,  # Delay before execution
            'param4': 0,  # Unused
            'seq': len(self.waypoints)
        }
        self.waypoints.append(relay_command)
        return len(self.waypoints) - 1
        
    def add_magnet1_activate(self, delay_seconds=0):
        """Elektromıknatıs 1'i aktifleştir (Main Out 1)"""
        return self.add_relay_command(0, 1, delay_seconds)  # Relay 0 = Main Out 1
        
    def add_magnet1_deactivate(self, delay_seconds=0):
        """Elektromıknatıs 1'i deaktifleştir (Main Out 1)"""
        return self.add_relay_command(0, 0, delay_seconds)  # Relay 0 = Main Out 1
        
    def add_magnet2_activate(self, delay_seconds=0):
        """Elektromıknatıs 2'yi aktifleştir (Main Out 2)"""
        return self.add_relay_command(1, 1, delay_seconds)  # Relay 1 = Main Out 2
        
    def add_magnet2_deactivate(self, delay_seconds=0):
        """Elektromıknatıs 2'yi deaktifleştir (Main Out 2)"""
        return self.add_relay_command(1, 0, delay_seconds)  # Relay 1 = Main Out 2
        
    def add_payload_release_sequence(self, delay_before_release=2):
        """Yük bırakma sekansı ekler (her iki mıknatısı da kapatır)"""
        # Önce mıknatıs 1'i kapat
        self.add_magnet1_deactivate(0)
        # Sonra mıknatıs 2'yi kapat
        self.add_magnet2_deactivate(delay_before_release)
        
    def export_waypoints_file(self, filename):
        """Waypoint'leri .waypoints dosyası formatında dışa aktar"""
        try:
            with open(filename, 'w') as f:
                f.write("QGC WPL 110\n")  # QGroundControl waypoint format header
                
                for i, wp in enumerate(self.waypoints):
                    # QGC waypoint format: INDEX CURRENT AUTOFRAME COMMAND PARAM1 PARAM2 PARAM3 PARAM4 LAT LON ALT LABEL
                    current = 1 if i == 0 else 0  # İlk waypoint current
                    autoframe = 3  # MAV_FRAME_GLOBAL_RELATIVE_ALT
                    command = wp.get('command', 16)  # MAV_CMD_NAV_WAYPOINT
                    param1 = wp.get('param1', 0)
                    param2 = wp.get('param2', 0)
                    param3 = wp.get('param3', 0)
                    param4 = wp.get('param4', 0)
                    lat = wp.get('lat', 0)
                    lon = wp.get('lon', 0)
                    alt = wp.get('alt', 0)
                    label = f"WP{i+1}"
                    
                    f.write(f"{i}\t{current}\t{autoframe}\t{command}\t{param1}\t{param2}\t{param3}\t{param4}\t{lat:.7f}\t{lon:.7f}\t{alt}\t{label}\n")
                    
            return True
        except Exception as e:
            print(f"Waypoint dosyası yazma hatası: {e}")
            return False
            
    def import_waypoints_file(self, filename):
        """QGroundControl .waypoints dosyasından waypoint'leri içe aktar"""
        try:
            self.waypoints = []
            with open(filename, 'r') as f:
                lines = f.readlines()
                
                # Header'ı atla
                if lines and lines[0].startswith("QGC WPL"):
                    lines = lines[1:]
                    
                for line in lines:
                    if line.strip():
                        parts = line.strip().split('\t')
                        if len(parts) >= 11:
                            wp = {
                                'seq': int(parts[0]),
                                'command': int(parts[3]),
                                'param1': float(parts[4]),
                                'param2': float(parts[5]),
                                'param3': float(parts[6]),
                                'param4': float(parts[7]),
                                'lat': float(parts[8]),
                                'lon': float(parts[9]),
                                'alt': float(parts[10])
                            }
                            self.waypoints.append(wp)
                            
            return True
        except Exception as e:
            print(f"Waypoint dosyası okuma hatası: {e}")
            return False 