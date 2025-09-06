# DO_SET_RELAY Komutları Kullanım Kılavuzu

## Genel Bakış

Bu güncelleme ile arayüz artık DO_SET_RELAY komutlarını desteklemektedir. Bu komutlar elektromıknatısları kontrol etmek için kullanılır ve waypoint dosyalarına eklenebilir.

## Elektromıknatıs Bağlantıları

- **Elektromıknatıs 1**: Pixhawk Main Out 1 (Relay 0)
- **Elektromıknatıs 2**: Pixhawk Main Out 2 (Relay 1)

## Arayüzde Kullanım

### 1. Mission Panel'de DO_SET_RELAY Komutları

Mission Panel'de "Elektromıknatıs Kontrolü" bölümünde şu butonlar bulunur:

- **Mıknatıs 1 Aç**: Elektromıknatıs 1'i aktifleştirir
- **Mıknatıs 1 Kapat**: Elektromıknatıs 1'i deaktifleştirir
- **Mıknatıs 2 Aç**: Elektromıknatıs 2'yi aktifleştirir
- **Mıknatıs 2 Kapat**: Elektromıknatıs 2'yi deaktifleştirir
- **Yük Bırak**: Her iki mıknatısı da kapatır (yük bırakma sekansı)

### 2. Teknofest Panel'de Manuel Kontrol

Teknofest Panel'de "Elektromıknatıs Kontrolü" bölümünde manuel kontrol butonları bulunur.

## Waypoint Dosyası Formatı

DO_SET_RELAY komutları waypoint dosyalarına şu formatta eklenir:

```
INDEX CURRENT AUTOFRAME COMMAND PARAM1 PARAM2 PARAM3 PARAM4 LAT LON ALT LABEL
```

### DO_SET_RELAY Komut Parametreleri

- **COMMAND**: 181 (MAV_CMD_DO_SET_RELAY)
- **PARAM1**: Relay numarası (0 = Main Out 1, 1 = Main Out 2)
- **PARAM2**: Durum (0 = OFF, 1 = ON)
- **PARAM3**: Gecikme süresi (saniye)
- **PARAM4**: Kullanılmaz
- **LAT/LON/ALT**: 0 (relay komutları için kullanılmaz)

### Örnek Waypoint Dosyası

```
QGC WPL 110
0	1	3	16	0	0	0	0	41.26430	28.70097	50	WP1
1	0	3	16	0	0	0	0	41.26450	28.70120	50	WP2
2	0	3	181	0	1	0	0	0	0	0	RELAY1_ON
3	0	3	16	0	0	0	0	41.26470	28.70150	50	WP3
4	0	3	181	1	1	0	0	0	0	0	RELAY2_ON
5	0	3	16	0	0	0	0	41.26490	28.70180	50	WP4
6	0	3	181	0	0	0	0	0	0	0	RELAY1_OFF
7	0	3	181	1	0	0	0	0	0	0	RELAY2_OFF
8	0	3	16	0	0	0	0	41.26510	28.70210	50	WP5
```

## Görev Akışı

1. **Görev Oluşturma**: Mission Panel'de waypoint'ler ve DO_SET_RELAY komutları ekleyin
2. **Görev Yükleme**: "Araca Yükle" butonuna basın
3. **Görev Başlatma**: "Görev Başlat" butonuna basın
4. **Otomatik Çalışma**: Uçak waypoint'leri takip ederken DO_SET_RELAY komutları otomatik olarak çalışır

## Manuel Kontrol

Teknofest Panel'deki butonlar ile elektromıknatısları manuel olarak kontrol edebilirsiniz:

- Görev çalışırken manuel kontrol mümkündür
- Manuel komutlar anında uygulanır
- Görev devam ederken manuel komutlar görev akışını etkilemez

## Güvenlik Notları

- Elektromıknatıslar güçlü manyetik alanlar üretir
- Yük bırakma işlemi geri alınamaz
- Test uçuşlarında düşük irtifada çalışın
- Acil durum butonları her zaman kullanılabilir

## Hata Ayıklama

### Yaygın Sorunlar

1. **Hall Effect Sensör Hatası**: `_hall_lock` attribute'u eksik
   - **Çözüm**: MAVLink thread yeniden başlatılmalı

2. **Mod Değiştirme Hatası**: `MAV_MODE_FLAG_CUSTOM_MODE` attribute'u eksik
   - **Çözüm**: Güncellenmiş kod kullanın

3. **Görev Yükleme Hatası**: `required argument is not an integer`
   - **Çözüm**: Sequence numaraları integer olarak cast edildi

### Log Mesajları

Sistem mesajlarında şu bilgileri görebilirsiniz:

- `Relay komutu X: Relay Y = Z`: DO_SET_RELAY komutu tanımlandı
- `Mıknatıs X aktifleştirildi/deaktifleştirildi`: Manuel kontrol başarılı
- `Yük bırakma sekansı eklendi`: Otomatik yük bırakma komutu eklendi

## Teknik Detaylar

### MAVLink Komutları

- **MAV_CMD_DO_SET_RELAY**: 181
- **MAV_FRAME_MISSION**: Relay komutları için
- **MAV_FRAME_GLOBAL_RELATIVE_ALT**: Waypoint komutları için

### Relay Mapping

- Relay 0 → Main Out 1 → Elektromıknatıs 1
- Relay 1 → Main Out 2 → Elektromıknatıs 2

### Gecikme Parametresi

PARAM3 ile relay komutlarının ne kadar gecikme ile çalışacağını ayarlayabilirsiniz:

- 0: Anında çalış
- 1: 1 saniye gecikme
- 2: 2 saniye gecikme
- vb.

## Örnek Senaryolar

### Senaryo 1: Basit Yük Bırakma
1. Waypoint 1'e git
2. Elektromıknatıs 1'i kapat
3. Elektromıknatıs 2'yi kapat
4. Waypoint 2'ye git

### Senaryo 2: Kademeli Yük Bırakma
1. Waypoint 1'e git
2. Elektromıknatıs 1'i kapat
3. Waypoint 2'ye git
4. Elektromıknatıs 2'yi kapat
5. Waypoint 3'e git

### Senaryo 3: Test Uçuşu
1. Elektromıknatıs 1'i aç
2. Elektromıknatıs 2'yi aç
3. Test waypoint'lerini takip et
4. Elektromıknatıs 1'i kapat
5. Elektromıknatıs 2'yi kapat
