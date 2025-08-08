#!/usr/bin/env python3
"""
Test script to verify log replay thread fixes
"""
import csv
import time
import tempfile
import os
from core.log_replay_thread import LogReplayThread

def create_test_log(num_rows=100):
    """Create a test CSV log file"""
    # Create temporary file
    fd, path = tempfile.mkstemp(suffix='.csv', text=True)
    
    try:
        with os.fdopen(fd, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            
            # Write header
            writer.writerow([
                'Timestamp', 'Latitude', 'Longitude', 'Altitude', 'Ground Speed',
                'Vertical Speed', 'Heading', 'Roll', 'Pitch', 'Yaw',
                'Battery Voltage', 'Battery Current', 'Battery Remaining',
                'RSSI', 'Ping', 'Data Loss', 'GPS Fix Type', 'GPS Satellites',
                'System Status', 'Flight Mode'
            ])
            
            # Write sample data
            for i in range(num_rows):
                writer.writerow([
                    i * 0.1,  # Timestamp (0.1 second intervals)
                    39.9334 + i * 0.0001,  # Latitude (moving slightly)
                    32.8597 + i * 0.0001,  # Longitude (moving slightly)
                    100 + i * 0.5,  # Altitude (climbing)
                    15.0,  # Ground Speed
                    0.5,   # Vertical Speed
                    45 + i % 360,  # Heading (rotating)
                    i % 10 - 5,    # Roll (-5 to 5)
                    i % 6 - 3,     # Pitch (-3 to 3)
                    45 + i % 360,  # Yaw
                    12.6,  # Battery Voltage
                    2.5,   # Battery Current
                    100 - i * 0.5,  # Battery Remaining (decreasing)
                    85,    # RSSI
                    10,    # Ping
                    0,     # Data Loss
                    3,     # GPS Fix Type
                    12,    # GPS Satellites
                    'ARMED' if i > 10 else 'DISARMED',  # System Status
                    'AUTO'  # Flight Mode
                ])
        
        return path
    except Exception as e:
        if os.path.exists(path):
            os.unlink(path)
        raise e

def test_empty_log():
    """Test with empty log file"""
    print("Testing empty log file...")
    fd, path = tempfile.mkstemp(suffix='.csv', text=True)
    
    try:
        # Write only header
        with os.fdopen(fd, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['Timestamp', 'Latitude', 'Longitude', 'Altitude'])
        
        thread = LogReplayThread(path)
        print(f"Empty log loaded: {len(thread._rows)} rows")
        return len(thread._rows) == 0
        
    finally:
        if os.path.exists(path):
            os.unlink(path)

def test_normal_log():
    """Test with normal log file"""
    print("Testing normal log file...")
    path = create_test_log(50)
    
    try:
        thread = LogReplayThread(path)
        print(f"Normal log loaded: {len(thread._rows)} rows")
        return len(thread._rows) == 50
        
    finally:
        if os.path.exists(path):
            os.unlink(path)

def test_thread_stopping():
    """Test thread stopping mechanism"""
    print("Testing thread stopping...")
    path = create_test_log(1000)  # Large log
    
    try:
        from PyQt6.QtCore import QCoreApplication
        import sys
        
        # Create minimal Qt application
        if not QCoreApplication.instance():
            app = QCoreApplication(sys.argv)
        
        thread = LogReplayThread(path)
        
        # Start thread
        thread.start()
        time.sleep(0.1)  # Let it start
        
        # Stop thread
        start_time = time.time()
        thread.stop()
        stopped = thread.wait(2000)  # 2 second timeout
        stop_time = time.time() - start_time
        
        print(f"Thread stopped: {stopped}, Time: {stop_time:.2f}s")
        return stopped and stop_time < 1.0  # Should stop quickly
        
    finally:
        if os.path.exists(path):
            os.unlink(path)

if __name__ == '__main__':
    print("Running log replay thread tests...")
    
    tests = [
        ("Empty log handling", test_empty_log),
        ("Normal log loading", test_normal_log),
        ("Thread stopping", test_thread_stopping),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            status = "PASSED" if result else "FAILED"
            print(f"{test_name}: {status}")
            if result:
                passed += 1
        except Exception as e:
            print(f"{test_name}: ERROR - {e}")
    
    print(f"\nResults: {passed}/{total} tests passed")
