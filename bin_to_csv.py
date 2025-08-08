import sys
import os
from pymavlink import mavutil
import csv

def bin_to_csv(bin_path, csv_path=None):
    if not os.path.isfile(bin_path):
        print(f'Bin dosyası bulunamadı: {bin_path}')
        return
    if csv_path is None:
        csv_path = os.path.splitext(bin_path)[0] + '.csv'
    
    print(f'Bin dosyası okunuyor: {bin_path}')
    print(f'CSV olarak kaydedilecek: {csv_path}')
    
    mlog = mavutil.mavlink_connection(bin_path)
    
    # Define standard telemetry fields we want to extract
    telemetry_fields = [
        'Timestamp', 'Latitude', 'Longitude', 'Altitude', 'Ground Speed',
        'Vertical Speed', 'Heading', 'Roll', 'Pitch', 'Yaw',
        'Battery Voltage', 'Battery Current', 'Battery Remaining',
        'RSSI', 'Ping', 'Data Loss', 'GPS Fix Type', 'GPS Satellites',
        'System Status', 'Flight Mode'
    ]
    
    telemetry_data = []
    last_values = {}  # Keep track of last known values
    
    # Initialize with defaults
    for field in telemetry_fields:
        if field in ['Battery Voltage', 'Battery Current', 'Ground Speed', 'Vertical Speed', 'Altitude', 'Roll', 'Pitch', 'Yaw', 'Latitude', 'Longitude', 'Heading', 'RSSI', 'Battery Remaining', 'GPS Fix Type', 'GPS Satellites']:
            last_values[field] = 0.0
        else:
            last_values[field] = ''
    
    msg_count = 0
    start_time = None
    last_record_time = 0
    
    while True:
        msg = mlog.recv_match(blocking=False)
        if msg is None:
            break
            
        msg_count += 1
        if msg_count % 1000 == 0:
            print(f'Processed {msg_count} messages...')
        
        msg_type = msg.get_type()
        timestamp = getattr(msg, '_timestamp', 0)
        
        if start_time is None:
            start_time = timestamp
        
        current_time = timestamp - start_time
        
        # Extract relevant data based on message type (ArduPilot DataFlash format)
        data_updated = False
        
        if msg_type == 'POS':
            # Position data (GPS)
            if hasattr(msg, 'Lat') and msg.Lat != 0:
                last_values['Latitude'] = msg.Lat
                data_updated = True
            if hasattr(msg, 'Lng') and msg.Lng != 0:
                last_values['Longitude'] = msg.Lng
                data_updated = True
            if hasattr(msg, 'Alt'):
                last_values['Altitude'] = msg.Alt
                data_updated = True
            
        elif msg_type == 'GPS':
            # GPS data
            if hasattr(msg, 'Lat') and msg.Lat != 0:
                last_values['Latitude'] = msg.Lat
                data_updated = True
            if hasattr(msg, 'Lng') and msg.Lng != 0:
                last_values['Longitude'] = msg.Lng
                data_updated = True
            if hasattr(msg, 'Alt'):
                last_values['Altitude'] = msg.Alt
                data_updated = True
            if hasattr(msg, 'Spd'):
                last_values['Ground Speed'] = msg.Spd
                data_updated = True
            if hasattr(msg, 'GCrs'):
                last_values['Heading'] = msg.GCrs
                data_updated = True
            if hasattr(msg, 'VZ'):
                last_values['Vertical Speed'] = msg.VZ
                data_updated = True
            if hasattr(msg, 'NSats'):
                last_values['GPS Satellites'] = msg.NSats
                data_updated = True
            
        elif msg_type == 'ATT':
            # Attitude data
            if hasattr(msg, 'Roll'):
                last_values['Roll'] = msg.Roll
                data_updated = True
            if hasattr(msg, 'Pitch'):
                last_values['Pitch'] = msg.Pitch
                data_updated = True
            if hasattr(msg, 'Yaw'):
                last_values['Yaw'] = msg.Yaw
                if last_values['Yaw'] < 0:
                    last_values['Yaw'] += 360  # Normalize to 0-360
                data_updated = True
                
        elif msg_type == 'BARO':
            # Barometer data for altitude
            if hasattr(msg, 'Alt'):
                last_values['Altitude'] = msg.Alt
                data_updated = True
            
        elif msg_type == 'CURR':
            # Current/Battery data
            if hasattr(msg, 'Volt') and msg.Volt > 0:
                last_values['Battery Voltage'] = msg.Volt
                data_updated = True
            if hasattr(msg, 'Curr'):
                last_values['Battery Current'] = msg.Curr
                data_updated = True
            if hasattr(msg, 'CurrTot'):
                # Calculate remaining battery percentage (rough estimate)
                # This would need calibration for real use
                total_capacity = 5000  # mAh - adjust based on your battery
                used_capacity = msg.CurrTot
                remaining = max(0, 100 * (1 - used_capacity / total_capacity))
                last_values['Battery Remaining'] = remaining
                data_updated = True
                
        elif msg_type == 'POWR':
            # Power data (alternative to CURR)
            if hasattr(msg, 'Vcc') and msg.Vcc > 0:
                last_values['Battery Voltage'] = msg.Vcc / 1000.0  # Convert mV to V
                data_updated = True
            
        elif msg_type == 'STAT':
            # Status data
            if hasattr(msg, 'Armed'):
                last_values['System Status'] = 'ARMED' if msg.Armed else 'DISARMED'
                data_updated = True
                
        elif msg_type == 'MODE':
            # Flight mode
            if hasattr(msg, 'Mode'):
                mode_names = {
                    0: 'MANUAL', 1: 'CIRCLE', 2: 'STABILIZE', 3: 'TRAINING', 4: 'ACRO',
                    5: 'FLY_BY_WIRE_A', 6: 'FLY_BY_WIRE_B', 7: 'CRUISE', 8: 'AUTOTUNE',
                    10: 'AUTO', 11: 'RTL', 12: 'LOITER', 14: 'TAKEOFF', 15: 'AVOID_ADSB',
                    16: 'GUIDED', 17: 'INITIALISING'
                }
                last_values['Flight Mode'] = mode_names.get(msg.Mode, f'MODE_{msg.Mode}')
                data_updated = True
                
        elif msg_type == 'RCIN':
            # RC input - could derive RSSI
            if hasattr(msg, 'C8') and msg.C8 > 0:  # Many systems use channel 8 for RSSI
                last_values['RSSI'] = min(100, max(0, (msg.C8 - 1000) / 10))  # Convert PWM to percentage
                data_updated = True
                
        elif msg_type == 'IMU':
            # IMU data - backup for attitude if ATT not available
            if not last_values.get('Roll') and hasattr(msg, 'GyrX'):
                # This would need integration over time for proper attitude
                # For now, just indicate we have IMU data
                data_updated = True
        
        # Update timestamp for any meaningful message
        if data_updated:
            last_values['Timestamp'] = current_time
        
        # Create telemetry record at regular intervals (every 0.1 seconds) or when important data changes
        should_record = (
            data_updated and (current_time - last_record_time >= 0.1 or  # Every 100ms
            len(telemetry_data) == 0 or  # First record
            msg_type in ['POS', 'GPS', 'ATT', 'BARO'])  # Important position/attitude updates
        )
        
        if should_record:
            # Only record if we have some meaningful data (not all zeros)
            has_meaningful_data = (
                last_values['Latitude'] != 0.0 or last_values['Longitude'] != 0.0 or
                last_values['Altitude'] != 0.0 or last_values['Battery Voltage'] != 0.0 or
                last_values['System Status'] or last_values['Flight Mode'] or
                abs(last_values['Roll']) > 0.1 or abs(last_values['Pitch']) > 0.1 or  # Small attitude changes
                abs(last_values['Yaw']) > 0.1
            )
            
            if has_meaningful_data:
                # Create a copy of current values
                record = dict(last_values)
                telemetry_data.append(record)
                last_record_time = current_time
    
    print(f'Processed {msg_count} messages, created {len(telemetry_data)} telemetry records')
    
    # Write to CSV
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=telemetry_fields)
        writer.writeheader()
        writer.writerows(telemetry_data)
    
    print(f'Dönüştürme tamamlandı. {len(telemetry_data)} kayıt yazıldı.')

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Kullanım: python bin_to_csv.py logdosyasi.bin')
        sys.exit(1)
    bin_path = sys.argv[1]
    bin_to_csv(bin_path) 