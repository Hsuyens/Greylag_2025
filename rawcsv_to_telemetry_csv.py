import sys
import csv

def convert_raw_csv_to_telemetry_csv(raw_csv_path, out_csv_path):
    # Hedef başlıklar
    headers = [
        'Timestamp', 'Latitude', 'Longitude', 'Altitude', 'Ground Speed',
        'Vertical Speed', 'Heading', 'Roll', 'Pitch', 'Yaw',
        'Battery Voltage', 'Battery Current', 'Battery Remaining', 'RSSI',
        'Ping', 'Data Loss', 'GPS Fix Type', 'GPS Satellites',
        'System Status', 'Flight Mode'
    ]
    with open(raw_csv_path, 'r', encoding='utf-8', errors='ignore') as infile, \
         open(out_csv_path, 'w', encoding='utf-8', newline='') as outfile:
        writer = csv.writer(outfile)
        writer.writerow(headers)
        for row in csv.reader(infile):
            if not row or row[0] == 'mavpackettype':
                continue
            if row[0] == 'GPS':
                # GPS satırından temel verileri çek
                # Örnek: GPS,TimeMS,Status,GMS,Time,Week,NSats,HDop,Lat,Lng,Alt,Spd,GCrs,VZ,U
                # Sıralama Mission Planner'ın CSV'sine göre değişebilir
                try:
                    # Sütun indeksleri Mission Planner'ın GPS mesajına göre ayarlanmalı
                    # Burada örnek olarak: [0]mavpackettype, [1]TimeMS, [8]Lat, [9]Lng, [10]Alt, [11]Spd, [12]GCrs
                    Timestamp = row[1]
                    Latitude = float(row[8]) / 1e7
                    Longitude = float(row[9]) / 1e7
                    Altitude = float(row[10]) / 100.0
                    GroundSpeed = float(row[11]) / 100.0
                    Heading = float(row[12]) / 100.0
                    # Diğer alanlar için boş veya 0 yaz
                    out_row = [Timestamp, Latitude, Longitude, Altitude, GroundSpeed, '', Heading, '', '', '', '', '', '', '', '', '', '', '', '', '']
                    writer.writerow(out_row)
                except Exception as e:
                    continue
    print(f'Yeni CSV dosyası oluşturuldu: {out_csv_path}')

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print('Kullanım: python rawcsv_to_telemetry_csv.py ham_log.csv cikti_telemetri.csv')
        sys.exit(1)
    convert_raw_csv_to_telemetry_csv(sys.argv[1], sys.argv[2]) 