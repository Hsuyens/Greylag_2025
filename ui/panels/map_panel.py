from __future__ import annotations
import os
from typing import TYPE_CHECKING
from PyQt6.QtWidgets import QWidget, QVBoxLayout
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtCore import QTimer, pyqtSignal, pyqtSlot
from PyQt6.QtWebChannel import QWebChannel

if TYPE_CHECKING:
    from ...mission.mission_planner import MissionPlanner

LEAFLET_HTML = """
<!DOCTYPE html>
<html>
<head>
  <meta charset='utf-8'/>
  <title>Lagger GCS Map</title>
  <meta name='viewport' content='width=device-width, initial-scale=1.0'>
  <link rel='stylesheet' href='https://unpkg.com/leaflet@1.9.4/dist/leaflet.css'/>
  <script src='https://unpkg.com/leaflet@1.9.4/dist/leaflet.js'></script>
  <script src='qrc:///qtwebchannel/qwebchannel.js'></script>
  <style>
    html, body, #map { height: 100%; margin: 0; padding: 0; }
    .plane-icon {
      transform-origin: center center;
      transition: transform 0.3s ease;
    }
  </style>
</head>
<body>
  <div id='map'></div>
  <script>
    var map = L.map('map').setView([41.0082, 28.9784], 10);
    L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png', {
      maxZoom: 19,
      attribution: '© OpenStreetMap, © CartoDB',
      subdomains: 'abcd'
    }).addTo(map);

    // Marker ve çizgi katmanları
    var vehicleMarker = null;
    var flightTrail = null;
    var waypointMarkers = [];
    var waypointLine = null;
    var homeMarker = null;
    var polyMarkers = [];
    var polyLine = null;
    var tempInfinityMarkers = [];
    
    // Flight trail points
    var trailPoints = [];

    // QWebChannel ile Python bağlantısı
    new QWebChannel(qt.webChannelTransport, function(channel) {
      window.pyObj = channel.objects.pyObj;

      // Harita tıklama
      map.on('click', function(e) {
        window.pyObj.js_map_clicked(e.latlng.lat, e.latlng.lng);
      });

      // Harita hareketi
      map.on('moveend zoomend', function(e) {
        var c = map.getCenter();
        window.pyObj.js_map_moved(c.lat, c.lng, map.getZoom());
      });
    });

    // Python'dan veri geldiğinde çağrılacak fonksiyon
    window.updateMap = function(data) {
      // Araç (Plane)
      if (data.vehicle) {
        var lat = data.vehicle.lat;
        var lon = data.vehicle.lon;
        var heading = data.vehicle.heading || 0;
        
        // Create plane icon with rotation (add 90 degrees to correct orientation)
        var planeIcon = L.divIcon({
          html: '<div class="plane-icon" style="transform: rotate(' + (heading - 90) + 'deg); font-size: 24px; text-align: center; line-height: 32px;">✈️</div>',
          className: '',
          iconSize: [32, 32],
          iconAnchor: [16, 16]
        });
        
        if (!vehicleMarker) {
          vehicleMarker = L.marker([lat, lon], {icon: planeIcon}).addTo(map);
          // Center map on plane for initial position
          map.setView([lat, lon], map.getZoom());
        } else {
          vehicleMarker.setLatLng([lat, lon]);
          vehicleMarker.setIcon(planeIcon);
          // Center map on plane during replay
          if (data.centerOnVehicle === true) {
            map.setView([lat, lon], map.getZoom());
          }
        }
        
        // Update flight trail
        trailPoints.push([lat, lon]);
        
        // Limit trail length to prevent memory issues (keep last 500 points)
        if (trailPoints.length > 500) {
          trailPoints = trailPoints.slice(-500);
        }
        
        // Update trail polyline
        if (flightTrail) {
          map.removeLayer(flightTrail);
        }
        
        if (trailPoints.length > 1) {
          flightTrail = L.polyline(trailPoints, {
            color: '#ff4444',
            weight: 3,
            opacity: 0.7,
            smoothFactor: 1,
            lineCap: 'round',
            lineJoin: 'round'
          }).addTo(map);
        }
        
      } else if (vehicleMarker) {
        map.removeLayer(vehicleMarker); 
        vehicleMarker = null;
        if (flightTrail) {
          map.removeLayer(flightTrail);
          flightTrail = null;
        }
        trailPoints = [];
      }
      // Home
      if (data.home) {
        if (!homeMarker) {
          homeMarker = L.marker([data.home[0], data.home[1]], {icon: L.icon({iconUrl:'https://cdn-icons-png.flaticon.com/512/25/25694.png', iconSize:[24,24]})}).addTo(map);
        } else {
          homeMarker.setLatLng([data.home[0], data.home[1]]);
        }
      } else if (homeMarker) {
        map.removeLayer(homeMarker); homeMarker = null;
      }
      // Waypoints
      waypointMarkers.forEach(m=>map.removeLayer(m)); waypointMarkers = [];
      if (waypointLine) { map.removeLayer(waypointLine); waypointLine = null; }
      if (data.waypoints && data.waypoints.length > 0) {
        var latlngs = [];
        data.waypoints.forEach(function(wp, i) {
          var marker = L.marker([wp.lat, wp.lon], {icon: L.icon({iconUrl:'https://cdn-icons-png.flaticon.com/512/684/684908.png', iconSize:[24,24]})}).addTo(map);
          marker.bindPopup('WP ' + (i+1) + '<br>Alt: ' + wp.alt + 'm');
          waypointMarkers.push(marker);
          latlngs.push([wp.lat, wp.lon]);
        });
        waypointLine = L.polyline(latlngs, {color:'#ff9800', dashArray:'5,5', weight:4}).addTo(map);
      }
      // Poligonlar (isteğe bağlı)
      polyMarkers.forEach(m=>map.removeLayer(m)); polyMarkers = [];
      if (polyLine) { map.removeLayer(polyLine); polyLine = null; }
      if (data.polygons && data.polygons.length > 0) {
        var poly = data.polygons[0];
        var latlngs = [];
        poly.forEach(function(pt) {
          var marker = L.marker([pt[0], pt[1]], {icon: L.icon({iconUrl:'https://cdn-icons-png.flaticon.com/512/61/61112.png', iconSize:[18,18]})}).addTo(map);
          polyMarkers.push(marker);
          latlngs.push([pt[0], pt[1]]);
        });
        polyLine = L.polyline(latlngs, {color:'#b388ff', weight:3}).addTo(map);
      }
      // Geçici sonsuzluk noktaları (mavi marker)
      tempInfinityMarkers.forEach(m=>map.removeLayer(m)); tempInfinityMarkers = [];
      if (data.temp_infinity_points && data.temp_infinity_points.length > 0) {
        data.temp_infinity_points.forEach(function(pt) {
          var marker = L.marker([pt[0], pt[1]], {icon: L.icon({iconUrl:'https://cdn-icons-png.flaticon.com/512/64/64572.png', iconSize:[20,20]})}).addTo(map);
          marker.bindPopup('8 şekli noktası');
          tempInfinityMarkers.push(marker);
        });
      }
    }
    
    // Function to clear flight trail
    window.clearFlightTrail = function() {
      trailPoints = [];
      if (flightTrail) {
        map.removeLayer(flightTrail);
        flightTrail = null;
      }
    }
  </script>
</body>
</html>
"""

class MapPanel(QWidget):
    map_clicked = pyqtSignal(float, float)  # lat, lon sinyali
    def __init__(self):
        super().__init__()
        self.vehicle_position = None
        self.vehicle_heading = 0
        self.mission_planner: MissionPlanner | None = None
        self.home_position = None
        self.flight_path = []
        self.emergency_markers = []
        self.last_center = [41.0082, 28.9784]
        self.last_zoom = 10
        self.temp_infinity_points = []  # Geçici sonsuzluk noktaları
        self.is_replaying = False  # Flag to track if we're in replay mode
        self.initUI()
        self.map_update_timer = QTimer(self)
        self.map_update_timer.timeout.connect(self.update_map)
        self.map_update_timer.start(1000)
    def initUI(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        self.web_view = QWebEngineView()
        layout.addWidget(self.web_view)
        self.setLayout(layout)
        self.channel = QWebChannel()
        self.channel.registerObject('pyObj', self)
        self.web_view.page().setWebChannel(self.channel)
        self.web_view.setHtml(LEAFLET_HTML)
    @pyqtSlot(float, float)
    def js_map_clicked(self, lat, lon):
        self.map_clicked.emit(float(lat), float(lon))
    @pyqtSlot(float, float, int)
    def js_map_moved(self, lat, lon, zoom):
        self.last_center = [float(lat), float(lon)]
        self.last_zoom = int(zoom)
    def update_vehicle_position(self, lat, lon, heading):
        print(f"[MapPanel] update_vehicle_position called: lat={lat}, lon={lon}, heading={heading}")
        self.vehicle_position = [lat, lon]
        self.vehicle_heading = heading
        if len(self.flight_path) == 0 or self.flight_path[-1] != [lat, lon]:
            self.flight_path.append([lat, lon])
            print(f"[MapPanel] Added to flight path. Total points: {len(self.flight_path)}")
    
    def set_replay_mode(self, is_replaying):
        """Set whether we're in replay mode to enable map centering"""
        self.is_replaying = is_replaying
        print(f"[MapPanel] Replay mode set to: {is_replaying}")
    def set_home_position(self, lat, lon):
        print(f"[MapPanel] set_home_position called: lat={lat}, lon={lon}")
        self.home_position = [lat, lon]
    def add_emergency_marker(self, lat, lon, message):
        self.emergency_markers.append({'lat': lat, 'lon': lon, 'message': message})

    def clear_flight_trail(self):
        """Clear the flight path trail"""
        self.flight_path = []
        # Send command to clear trail in JavaScript
        if hasattr(self, 'web_view') and self.web_view.page():
            js = "window.clearFlightTrail();"
            self.web_view.page().runJavaScript(js)
    def update_map(self):
        import json
        data = {
            'vehicle': None,
            'waypoints': [],
            'home': self.home_position,
            'polygons': [],
            'temp_infinity_points': self.temp_infinity_points,
            'centerOnVehicle': self.is_replaying  # Center on vehicle during replay
        }
        if self.vehicle_position:
            data['vehicle'] = {
                'lat': self.vehicle_position[0], 
                'lon': self.vehicle_position[1],
                'heading': self.vehicle_heading
            }
            print(f"[MapPanel] Updating map with vehicle position: {self.vehicle_position}")
        if self.mission_planner and self.mission_planner.waypoints:
            data['waypoints'] = self.mission_planner.waypoints
        if self.mission_planner and self.mission_planner.polygons:
            data['polygons'] = self.mission_planner.polygons
        # QWebChannel üzerinden haritaya veri gönder
        if hasattr(self, 'web_view') and self.web_view.page() and hasattr(self.web_view.page(), 'runJavaScript'):
            js = f"window.updateMap({json.dumps(data)})"
            print(f"[MapPanel] Executing JavaScript: {js[:100]}...")
            self.web_view.page().runJavaScript(js)
    def closeEvent(self, event):
        self.map_update_timer.stop()
        event.accept()