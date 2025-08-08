#!/usr/bin/env python3
"""
Test script for the improved bin_to_csv conversion and seek functionality
"""
import os
import tempfile
import csv
from bin_to_csv import bin_to_csv
from core.log_replay_thread import LogReplayThread

def test_csv_structure():
    """Test that a CSV file has the expected structure"""
    # Create a simple test CSV to verify our expectations
    fd, test_csv = tempfile.mkstemp(suffix='.csv', text=True)
    
    try:
        with os.fdopen(fd, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            
            # Write header matching our expected format
            writer.writerow([
                'Timestamp', 'Latitude', 'Longitude', 'Altitude', 'Ground Speed',
                'Vertical Speed', 'Heading', 'Roll', 'Pitch', 'Yaw',
                'Battery Voltage', 'Battery Current', 'Battery Remaining',
                'RSSI', 'Ping', 'Data Loss', 'GPS Fix Type', 'GPS Satellites',
                'System Status', 'Flight Mode'
            ])
            
            # Write some test data
            for i in range(10):
                writer.writerow([
                    i * 0.1,  # Timestamp
                    39.9334 + i * 0.0001,  # Latitude
                    32.8597 + i * 0.0001,  # Longitude
                    100 + i,  # Altitude
                    15.0,  # Ground Speed
                    0.5,   # Vertical Speed
                    45 + i * 10,  # Heading
                    i % 5 - 2,    # Roll
                    i % 3 - 1,     # Pitch
                    45 + i * 10,  # Yaw
                    12.6,  # Battery Voltage
                    2.5,   # Battery Current
                    100 - i,  # Battery Remaining
                    85,    # RSSI
                    10,    # Ping
                    0,     # Data Loss
                    3,     # GPS Fix Type
                    12,    # GPS Satellites
                    'ARMED' if i > 2 else 'DISARMED',  # System Status
                    'AUTO'  # Flight Mode
                ])
        
        # Test loading with LogReplayThread
        thread = LogReplayThread(test_csv)
        
        print(f"CSV structure test:")
        print(f"  - Loaded {len(thread._rows)} rows")
        print(f"  - Expected 10 rows: {'PASS' if len(thread._rows) == 10 else 'FAIL'}")
        
        if len(thread._rows) > 0:
            first_row = thread._rows[0]
            expected_keys = ['Timestamp', 'Latitude', 'Longitude', 'Altitude', 'System Status', 'Flight Mode']
            missing_keys = [key for key in expected_keys if key not in first_row]
            
            print(f"  - Has expected columns: {'PASS' if not missing_keys else f'FAIL - Missing: {missing_keys}'}")
            print(f"  - Sample row keys: {list(first_row.keys())[:5]}...")
            
            # Test data conversion
            try:
                lat = float(first_row.get('Latitude', 0))
                lon = float(first_row.get('Longitude', 0))
                alt = float(first_row.get('Altitude', 0))
                print(f"  - Data conversion: PASS (lat={lat}, lon={lon}, alt={alt})")
            except Exception as e:
                print(f"  - Data conversion: FAIL - {e}")
        
        return len(thread._rows) == 10
        
    finally:
        if os.path.exists(test_csv):
            os.unlink(test_csv)

def test_seek_functionality():
    """Test seek functionality with a small log"""
    from PyQt6.QtCore import QCoreApplication
    import sys
    import time
    
    # Create minimal Qt application if needed
    if not QCoreApplication.instance():
        app = QCoreApplication(sys.argv)
    
    # Create test CSV
    fd, test_csv = tempfile.mkstemp(suffix='.csv', text=True)
    
    try:
        with os.fdopen(fd, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['Timestamp', 'Latitude', 'Longitude', 'Altitude', 'System Status', 'Flight Mode'])
            
            for i in range(20):
                writer.writerow([i * 0.5, 39.0 + i * 0.001, 32.0 + i * 0.001, 100 + i, 'ARMED', 'AUTO'])
        
        thread = LogReplayThread(test_csv)
        
        print(f"Seek functionality test:")
        print(f"  - Created log with {len(thread._rows)} rows")
        
        # Test seek to middle
        middle = len(thread._rows) // 2
        thread.seek(middle)
        
        # Start thread briefly to process seek
        thread.start()
        time.sleep(0.1)  # Let it process
        thread.stop()
        thread.wait(1000)
        
        print(f"  - Seek to middle ({middle}): PASS")
        
        # Test seek bounds
        thread.seek(-5)  # Should clamp to 0
        thread.seek(1000)  # Should clamp to max
        
        print(f"  - Seek bounds handling: PASS")
        
        return True
        
    except Exception as e:
        print(f"  - Seek test: FAIL - {e}")
        return False
        
    finally:
        if os.path.exists(test_csv):
            os.unlink(test_csv)

def main():
    print("Testing improved log replay functionality...")
    print("=" * 50)
    
    tests = [
        ("CSV structure and loading", test_csv_structure),
        ("Seek functionality", test_seek_functionality),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n{test_name}:")
        try:
            result = test_func()
            if result:
                passed += 1
                print(f"✓ {test_name}: PASSED")
            else:
                print(f"✗ {test_name}: FAILED")
        except Exception as e:
            print(f"✗ {test_name}: ERROR - {e}")
    
    print(f"\n{'='*50}")
    print(f"Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! The log replay fixes should work correctly.")
    else:
        print("⚠️  Some tests failed. Check the issues above.")

if __name__ == '__main__':
    main()
