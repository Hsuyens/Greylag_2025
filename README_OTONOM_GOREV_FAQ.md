# Otonom Görev (Waypoint) Yükleme ve Başlatma – SSS (FAQ)

Bu doküman, .waypoints dosyasını araca yazdıktan sonra otonom görevi güvenle başlatmak için tüm pratik adımları ve sık sorulan soruları içerir.

## 1) .waypoints Köprüsü Nasıl Çalışır?

- Arayüz, Mission Planner’ın ürettiği `QGC WPL` formatındaki dosyayı olduğu gibi Pixhawk’a yazar.
- Yükleme sırasında arayüz içerik değiştirmez (ham mission item’ları aynen gönderir).
- Yükleme akışı: Dosyayı yükle → Araca Yükle → Başarı/başarısızlık loglarını izle.

## 2) Adım Adım Otonom Başlatma

1. Bağlan: Doğru COM ve baud ile MAVLink’e bağlanın; bağlantı durumunu kontrol edin.
2. Görevi Yükle: “Yükle (.waypoints)” ile dosyayı seçin; “Araca Yükle” ile yazdırın.
3. Arm: Gerekli arming koşullarını sağlayıp aracı arm edin (gerekirse Manual/Stabilize modunda arm edilir).
4. AUTO Moda Geçiş: Sabit kanat/çok rotorlu için AUTO moduna geçin.
5. Görevi Başlat: “Görev Başlat” komutunu gönderin (MAV_CMD_MISSION_START). Araç AUTO modda ise ilk (current) görev maddesine başlar.

Notlar:
- Bazı araçlarda AUTO moduna geçince görev otomatik başlar; bazılarında ayrıca MISSION_START gerekir.
- Kalkış irtifası/komutları görev içinde olmalıdır (örn. TAKEOFF komutu – ArduPlane/ArduCopter farklarını göz önünde bulundurun).

## 3) Gerekli Ön Koşullar (Pre-Flight Checklist)

- GPS: En az 3D Fix (fix_type ≥ 3) ve yeterli uydu sayısı.
- EKF: “EKF OK” (sensör hizalaması/kalibrasyonlar tamam).
- Compass/IMU: Compass, IMU kalibrasyonları güncel; ciddi manyetik sapma yok.
- RC Güvenliği: Gerekliyse failsafe değerleri, RTL ayarları doğrulanmış.
- Batarya: Yeterli enerji; voltaj/akım limitleri doğru.
- Home/Ev: Ev konumu alınmış; RTL yüksekliği/parametreleri uygun.
- Uçuş Alanı: GEO çitleri (fence), irtifa limitleri ve mod kısıtları parametreleri kontrol edildi.

## 4) Arayüzde Temel Butonlar ve Anlamları

- Yükle (.waypoints): Dosyadan görevi içe aktarır (ham item’lar ayrıca saklanır).
- Araca Yükle: Saklanan görevi/farklıysa ham item’ları aynen Pixhawk’a yazar.
- Görev Başlat: AUTO mod ve MISSION_START kombinasyonu ile görevi başlatır.
- Görev Duraklat (Loiter): Belirtilen yarıçap/irtifada loiter komutu gönderir.
- Görev İptal (Abort/RTL): Görevi sonlandırır; RTL/Loiter gibi güvenli moda geçiş yapar.

## 5) ArduPilot Mod/Komut Notları (Özet)

- Waypoint: `MAV_CMD_NAV_WAYPOINT (16)`
- Takeoff: ArduCopter: `MAV_CMD_NAV_TAKEOFF (22)`, ArduPlane: genelde AUTO içinde kalkış profili/komutları.
- RTL: `MAV_CMD_NAV_RETURN_TO_LAUNCH (20)`
- LAND: (Araç tipine göre değişir; Plane için görev sonu/RTL sonu iniş profili ayrı olabilir.)
- Görev Başlat: `MAV_CMD_MISSION_START`

## 6) DO_SET_RELAY (Elektromıknatıs vb.)

- `MAV_CMD_DO_SET_RELAY (181)` ile röle açık/kapalı yönetilir.
- .waypoints içine bu komutları ekleyebilirsiniz; köprü modu aynen yazar.
- Not: Orta paneldeki “Elektromıknatıs Kontrolü” görseli kaldırıldı; Teknofest sekmesi fonksiyonel kalır.

## 7) Güvenli Kapatma / Çalıştırma

- Windows PowerShell’de çalıştırma:
  - `cd C:\Users\husey\Downloads\Greylag_2025-main`
  - `python .\main.py`
- Kapatırken arayüz kaynakları otomatik kapatır; takılma varsa log’u kontrol edin.

## 8) Hall Effect Sensörü

- Hata “PermissionError: Erişim engellendi” ise COM port başka uygulama tarafından kilitlidir.
- Mission Planner/diğer port dinleyicilerini kapatın, kabloyu çıkar-tak yapın (COM değişebilir), doğru COM’u seçin.
- İsterseniz Hall sensörü otomatik bağlama devre dışı bırakılabilir veya manuel COM seçimi eklenebilir.

## 9) Telemetri Ekranı Stabilizasyonları

- Mod: Geçici “0” yerine son geçerli mod metni korunur.
- Yön (Heading): Anlık 0 sapmaları filtrelenir; son geçerli değer tutulur.

## 10) Sık Karşılaşılan Sorunlar

1. Görev Yüklenmiyor (ACK gelmiyor)
   - Bağlantı kararlı mı? Hız/port doğru mu?
   - Görev çok uzun olabilir; parça parça deneyin.
   - Arayüz log’larında “Mission ACK alınamadı” varsa tekrar deneyin; gerekirse yeniden bağlanın.

2. AUTO moduna geçemiyor
   - Arming check’ler (EKF, GPS, batarya) tamamlanmadan AUTO engellenebilir.
   - Önce Stabilize/Manual arm edin, sonra AUTO’ya geçin.

3. Yön/Mod “0” görünüyor
   - GPS/EKF geçici olarak gecikmiş olabilir; arayüz son geçerli değeri tutar. GPS yoksa yön 0’a düşebilir.

4. Hall Effect okumuyor
   - COM port kilitli; başka uygulamalar kapatılmalı. Doğru COM’u seçin ve tekrar deneyin.

5. Görev başladı ama hareket yok
   - İlk waypoint çok uzakta/geride olabilir; “current” işaretli maddeyi ve aracı başlatma konumunu kontrol edin.
   - RTL yüksekliği/görev irtifaları gerçek sahayla uyumlu mu?

## 11) En İyi Uygulamalar

- İlk denemelerde kısa, basit bir görev ile başlayın (3–5 WP).
- Kalkış irtifasını bölgeye uygun seçin; rüzgâr/engel analizini yapın.
- RTL yüksekliği her arazide güvenli olacak şekilde yeterli olsun.
- Görev öncesi kumandadan mod değişimlerini test edin (failsafe senaryoları).

## 12) Günlük (Log) ve Destek

- Arayüz logları: Sağ panel log alanında gerçek zamanlı görünür.
- Hataları tespit için logları export edebilir ve bizimle paylaşabilirsiniz.

---
Bu doküman, .waypoints köprüsü ile sade ve güvenli bir otonom görev akışı sağlamanız için hazırlandı. İhtiyaç halinde araç türünüze özel (Plane/Copter) ek yönergeler eklenebilir.


