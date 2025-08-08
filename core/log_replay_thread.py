import csv
import time
from PyQt6.QtCore import QThread, pyqtSignal

class LogReplayThread(QThread):
    telemetry_updated = pyqtSignal(dict)
    position_updated = pyqtSignal(float, float, float)  # lat, lon, heading
    seek_updated = pyqtSignal(int)
    finished = pyqtSignal()

    def __init__(self, log_path, speed=1.0, parent=None):
        super().__init__(parent)
        self.log_path = log_path
        self.speed = speed
        self._running = False
        self._paused = False
        self._seek_index = 0
        self._requested_seek = None
        self._requested_speed = None
        self._rows = []
        self._load_log()

    def _load_log(self):
        try:
            with open(self.log_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                self._rows = list(reader)
            print(f"[LogReplayThread] Loaded {len(self._rows)} log entries from {self.log_path}")
        except UnicodeDecodeError:
            try:
                with open(self.log_path, 'r', encoding='latin1') as f:
                    reader = csv.DictReader(f)
                    self._rows = list(reader)
                print(f"[LogReplayThread] Loaded {len(self._rows)} log entries from {self.log_path} (latin1 encoding)")
            except Exception as e:
                print(f'[LogReplayThread] Log dosyası okunamıyor: {e}')
                self._rows = []
        except Exception as e:
            print(f'[LogReplayThread] Log dosyası okunamıyor: {e}')
            self._rows = []
        
        # Check if log file is empty or has no data rows
        if len(self._rows) == 0:
            print(f"[LogReplayThread] WARNING: Log file is empty or has no data rows: {self.log_path}")
        elif len(self._rows) < 5:
            print(f"[LogReplayThread] WARNING: Log file has very few data rows ({len(self._rows)}): {self.log_path}")

    def run(self):
        print(f"[LogReplayThread] Starting replay with {len(self._rows)} rows")
        
        # Don't start if no data
        if len(self._rows) == 0:
            print("[LogReplayThread] No data to replay, finishing immediately")
            self.finished.emit()
            return
            
        self._running = True
        idx = self._seek_index
        last_emit_time = 0
        
        while self._running and idx < len(self._rows):
            if self._paused:
                time.sleep(0.05)
                continue
                
            # Handle seek requests immediately
            if self._requested_seek is not None:
                idx = max(0, min(self._requested_seek, len(self._rows) - 1))
                self._requested_seek = None
                print(f"[LogReplayThread] Seeked to index {idx}")
                
            if self._requested_speed is not None:
                self.speed = max(0.1, self._requested_speed)  # Minimum speed limit
                self._requested_speed = None
                print(f"[LogReplayThread] Speed changed to {self.speed}")
                
            # Check if we should stop (important check after seek)
            if not self._running:
                break
                
            try:
                row = self._rows[idx]
                
                # Safely convert values with defaults
                def safe_float(value, default=0.0):
                    try:
                        return float(value) if value and str(value).strip() else default
                    except (ValueError, TypeError):
                        return default
                
                def safe_str(value, default=''):
                    return str(value) if value else default
                
                # Telemetri ve konum verisi çıkar
                telemetry = {
                    'lat': safe_float(row.get('Latitude')),
                    'lon': safe_float(row.get('Longitude')),
                    'alt': safe_float(row.get('Altitude')),
                    'speed': safe_float(row.get('Ground Speed')),
                    'roll': safe_float(row.get('Roll')),
                    'pitch': safe_float(row.get('Pitch')),
                    'yaw': safe_float(row.get('Yaw')),
                    'battery': safe_float(row.get('Battery Remaining')),
                    'voltage': safe_float(row.get('Battery Voltage')),
                    'current': safe_float(row.get('Battery Current')),
                    'rssi': safe_float(row.get('RSSI')),
                    'mode': safe_str(row.get('Flight Mode')),
                    'armed': safe_str(row.get('System Status')).lower() == 'armed',
                }
                
                # Emit signals (check if we're still running before each emit)
                if self._running:
                    self.telemetry_updated.emit(telemetry)
                if self._running:
                    # Only emit position updates if we have valid coordinates
                    if telemetry['lat'] != 0.0 or telemetry['lon'] != 0.0:
                        print(f"[LogReplayThread] Emitting position: lat={telemetry['lat']}, lon={telemetry['lon']}, yaw={telemetry['yaw']}")
                        self.position_updated.emit(telemetry['lat'], telemetry['lon'], telemetry['yaw'])
                    else:
                        print(f"[LogReplayThread] Skipping zero coordinates: lat={telemetry['lat']}, lon={telemetry['lon']}")
                if self._running:
                    self.seek_updated.emit(idx)
                
                # Calculate sleep time for next iteration
                sleep_time = 0.01  # Default fallback
                if idx + 1 < len(self._rows):
                    try:
                        t0 = safe_float(row.get('Timestamp'))
                        t1 = safe_float(self._rows[idx + 1].get('Timestamp'))
                        if t1 > t0 and self.speed > 0:
                            dt = (t1 - t0) / self.speed
                            # Limit sleep time to prevent excessive delays
                            sleep_time = max(0.001, min(dt, 1.0))  # Between 1ms and 1s
                    except Exception as e:
                        print(f"[LogReplayThread] Timing calculation error: {e}")
                
                # Sleep in small chunks to be more responsive to stop requests
                total_sleep = 0
                while total_sleep < sleep_time and self._running:
                    chunk_sleep = min(0.05, sleep_time - total_sleep)  # 50ms chunks max
                    time.sleep(chunk_sleep)
                    total_sleep += chunk_sleep
                        
            except Exception as e:
                print(f"[LogReplayThread] Error processing row {idx}: {e}")
                if self._running:
                    time.sleep(0.01)  # Continue with small delay
                
            idx += 1
            
        print(f"[LogReplayThread] Replay finished at index {idx}, running={self._running}")
        self.finished.emit()

    def pause(self):
        print("[LogReplayThread] Pausing replay")
        self._paused = True
        
    def resume(self):
        print("[LogReplayThread] Resuming replay")
        self._paused = False
        
    def stop(self):
        print("[LogReplayThread] Stopping replay")
        self._running = False
        self._paused = False  # Ensure thread isn't stuck in pause loop
        
    def seek(self, idx):
        self._requested_seek = max(0, min(idx, len(self._rows) - 1))
        print(f"[LogReplayThread] Seeking to index {self._requested_seek}")
        
    def set_speed(self, speed):
        self._requested_speed = max(0.1, speed)  # Minimum speed limit
        print(f"[LogReplayThread] Setting speed to {self._requested_speed}") 