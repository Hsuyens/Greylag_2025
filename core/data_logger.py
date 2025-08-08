from datetime import datetime
import csv
import os

class DataLogger:
    def __init__(self):
        self.log_file = None
        self.start_time = None
        self.system_log_file = None
        self.system_log_filename = None
        
    def start_logging(self):
        if not self.log_file:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"flight_log_{timestamp}.csv"
            self.log_file = open(filename, "w", newline='')
            self.start_time = datetime.now()
            # System log file
            self.system_log_filename = f"flight_log_{timestamp}.log"
            self.system_log_file = open(self.system_log_filename, "a", encoding="utf-8")
            # Write CSV header
            headers = [
                "Timestamp", "Latitude", "Longitude", "Altitude", "Ground Speed",
                "Vertical Speed", "Heading", "Roll", "Pitch", "Yaw",
                "Battery Voltage", "Battery Current", "Battery Remaining", "RSSI",
                "Ping", "Data Loss", "GPS Fix Type", "GPS Satellites",
                "System Status", "Flight Mode"
            ]
            writer = csv.writer(self.log_file)
            writer.writerow(headers)
            return True
        return False
        
    def log_data(self, telemetry_data):
        if self.log_file and self.start_time is not None:
            timestamp = (datetime.now() - self.start_time).total_seconds()
            
            # Prepare data row
            data = [
                f"{timestamp:.3f}",
                telemetry_data.get("lat", ""),
                telemetry_data.get("lon", ""),
                telemetry_data.get("alt", ""),
                telemetry_data.get("groundspeed", ""),
                telemetry_data.get("verticalspeed", ""),
                telemetry_data.get("heading", ""),
                telemetry_data.get("roll", ""),
                telemetry_data.get("pitch", ""),
                telemetry_data.get("yaw", ""),
                telemetry_data.get("voltage", ""),
                telemetry_data.get("current", ""),
                telemetry_data.get("battery", ""),
                telemetry_data.get("rssi", ""),
                telemetry_data.get("ping", ""),
                telemetry_data.get("data_loss", ""),
                telemetry_data.get("gps_fix", ""),
                telemetry_data.get("satellites", ""),
                telemetry_data.get("system_status", ""),
                telemetry_data.get("flight_mode", "")
            ]
            
            writer = csv.writer(self.log_file)
            writer.writerow(data)
            
    def log_system(self, message):
        self._write_system_log("SYSTEM", message)
    def log_error(self, message):
        self._write_system_log("ERROR", message)
    def log_action(self, message):
        self._write_system_log("ACTION", message)
    def _write_system_log(self, level, message):
        if self.system_log_file:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.system_log_file.write(f"[{timestamp}] [{level}] {message}\n")
            self.system_log_file.flush()
    
    def stop_logging(self):
        if self.log_file:
            self.log_file.close()
            self.log_file = None
        if self.system_log_file:
            self.system_log_file.close()
            self.system_log_file = None
            self.system_log_filename = None
        self.start_time = None
        return True
        return False 