#!/usr/bin/env python3
"""
Hall Effect Sensör Test Scripti
HW 477 Hall Effect Sensör Modülü için test kodu
"""

import serial
import time
import threading

class HallSensorTest:
    def __init__(self, port='COM6', baudrate=9600):
        self.port = port
        self.baudrate = baudrate
        self.serial_port = None
        self.running = False
        
    def connect(self):
        """Sensöre bağlan"""
        try:
            self.serial_port = serial.Serial(self.port, self.baudrate, timeout=1)
            print(f"[TEST] Hall Effect sensör bağlandı: {self.port}")
            return True
        except Exception as e:
            print(f"[TEST] Bağlantı hatası: {e}")
            return False
    
    def disconnect(self):
        """Bağlantıyı kes"""
        if self.serial_port:
            try:
                self.serial_port.close()
                print("[TEST] Bağlantı kesildi")
            except:
                pass
            self.serial_port = None
    
    def read_data(self):
        """Sensör verilerini oku"""
        try:
            if not self.serial_port or not self.serial_port.is_open:
                return None
            
            # Sensörden veri oku
            if self.serial_port.in_waiting > 0:
                line = self.serial_port.readline().decode('utf-8').strip()
                if line:
                    print(f"[TEST] Ham veri: {line}")
                    return line
            return None
            
        except Exception as e:
            print(f"[TEST] Okuma hatası: {e}")
            return None
    
    def simulate_data(self):
        """Test için simüle edilmiş veri gönder"""
        try:
            if self.serial_port and self.serial_port.is_open:
                # Simüle edilmiş Hall Effect verisi
                test_data = f"HALL:{int(time.time() % 1000)},MAG:{int(time.time() % 500)}\n"
                self.serial_port.write(test_data.encode('utf-8'))
                print(f"[TEST] Simüle veri gönderildi: {test_data.strip()}")
        except Exception as e:
            print(f"[TEST] Simüle veri gönderme hatası: {e}")
    
    def run_test(self, duration=30):
        """Test çalıştır"""
        if not self.connect():
            return
        
        self.running = True
        start_time = time.time()
        
        print(f"[TEST] Test başladı, {duration} saniye çalışacak...")
        print("[TEST] Ctrl+C ile durdurabilirsiniz")
        
        try:
            while self.running and (time.time() - start_time) < duration:
                # Her 2 saniyede bir simüle veri gönder
                if int(time.time()) % 2 == 0:
                    self.simulate_data()
                
                # Sensör verilerini oku
                data = self.read_data()
                if data:
                    print(f"[TEST] Okunan veri: {data}")
                
                time.sleep(0.5)
                
        except KeyboardInterrupt:
            print("\n[TEST] Test kullanıcı tarafından durduruldu")
        except Exception as e:
            print(f"[TEST] Test hatası: {e}")
        finally:
            self.running = False
            self.disconnect()
            print("[TEST] Test tamamlandı")

if __name__ == "__main__":
    # Test başlat
    test = HallSensorTest(port='COM6', baudrate=9600)
    test.run_test(duration=30)
