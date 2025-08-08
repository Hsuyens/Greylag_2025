#!/usr/bin/env python3
"""
Waypoint Test Script
Bu script waypoint fonksiyonlarını test etmek için kullanılır.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from mission.mission_planner import MissionPlanner

def test_waypoint_functions():
    """Waypoint fonksiyonlarını test et"""
    print("=== Waypoint Test Başlıyor ===")
    
    # Mission planner oluştur
    planner = MissionPlanner()
    
    # Test 1: Manuel waypoint ekleme
    print("\n1. Manuel waypoint ekleme testi:")
    wp1 = planner.add_waypoint(41.0082, 28.9784, 100)  # İstanbul merkezi
    wp2 = planner.add_waypoint(41.0182, 28.9884, 120)  # Biraz kuzeydoğu
    wp3 = planner.add_waypoint(41.0282, 28.9984, 150)  # Daha kuzeydoğu
    
    print(f"   {len(planner.waypoints)} waypoint eklendi")
    for i, wp in enumerate(planner.waypoints):
        print(f"   WP {i+1}: {wp['lat']:.6f}, {wp['lon']:.6f}, {wp['alt']}m")
    
    # Test 2: 8 şekli oluşturma
    print("\n2. 8 şekli oluşturma testi:")
    planner.clear_infinity_points()
    planner.add_infinity_point(41.0082, 28.9784)  # Merkez nokta 1
    planner.add_infinity_point(41.0182, 28.9884)  # Merkez nokta 2
    
    success = planner.generate_infinity_pattern(100, 50)  # 100m irtifa, 50m yarıçap
    print(f"   8 şekli oluşturma: {'Başarılı' if success else 'Başarısız'}")
    if success:
        print(f"   {len(planner.waypoints)} waypoint oluşturuldu")
    
    # Test 3: Poligon oluşturma
    print("\n3. Poligon oluşturma testi:")
    planner.polygons = []  # Poligonları temizle
    planner.add_polygon_point(41.0082, 28.9784)  # Köşe 1
    planner.add_polygon_point(41.0182, 28.9784)  # Köşe 2
    planner.add_polygon_point(41.0182, 28.9884)  # Köşe 3
    planner.add_polygon_point(41.0082, 28.9884)  # Köşe 4
    
    print(f"   {len(planner.polygons[0])} poligon noktası eklendi")
    
    # Test 4: Grid tarama oluşturma
    print("\n4. Grid tarama oluşturma testi:")
    success = planner.generate_grid_mission(100, 20, 10)  # 100m irtifa, 20m aralık, 10m/s hız
    print(f"   Grid tarama: {'Başarılı' if success else 'Başarısız'}")
    if success:
        print(f"   {len(planner.waypoints)} grid waypoint oluşturuldu")
    
    # Test 5: Görev süresi hesaplama
    print("\n5. Görev süresi hesaplama testi:")
    if planner.waypoints:
        duration = planner.estimate_mission_time(10.0)  # 10 m/s hız
        print(f"   Tahmini görev süresi: {duration/60:.1f} dakika")
    
    # Test 6: Koordinat doğrulama
    print("\n6. Koordinat doğrulama testi:")
    test_coords = [
        (41.0082, 28.9784),  # Geçerli
        (90.1, 180.1),       # Geçersiz (çok büyük)
        (-90.1, -180.1),     # Geçersiz (çok küçük)
        (0, 0),              # Geçerli
    ]
    
    for lat, lon in test_coords:
        is_valid = (-90 <= lat <= 90) and (-180 <= lon <= 180)
        print(f"   ({lat}, {lon}): {'Geçerli' if is_valid else 'Geçersiz'}")
    
    print("\n=== Waypoint Test Tamamlandı ===")

def test_mission_types():
    """Görev tiplerini test et"""
    print("\n=== Görev Tipleri Testi ===")
    
    planner = MissionPlanner()
    print("Mevcut görev tipleri:")
    for key, value in planner.mission_types.items():
        print(f"   {key}: {value}")

if __name__ == "__main__":
    test_waypoint_functions()
    test_mission_types() 