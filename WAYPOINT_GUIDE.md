# Waypoint Kullanım Kılavuzu

Bu kılavuz, Lagger GCS arayüzünde waypoint oluşturma ve yönetme işlemlerini açıklar.

## 🎯 Waypoint Ekleme Yöntemleri

### 1. Harita Üzerinden Tıklama
1. **Waypoint Ekle** butonuna tıklayın
2. Buton yeşil olur ve "Waypoint Modu Aktif" yazar
3. Haritada istediğiniz konuma tıklayın
4. Waypoint otomatik olarak eklenir ve mod kapanır

### 2. Manuel Koordinat Girişi
1. **Manuel Koordinat Girişi** bölümünde:
   - Enlem (Latitude) girin
   - Boylam (Longitude) girin
2. **Manuel Waypoint Ekle** butonuna tıklayın

### 3. Test Waypoint Ekleme
1. **Test Tıklama** butonuna tıklayın
2. İstanbul merkezi koordinatlarına otomatik waypoint eklenir

## 🏗️ Görev Tipleri

### Waypoint Uçuşu
- Manuel olarak eklenen waypoint'ler arasında uçuş
- Her waypoint için irtifa ve hız ayarlanabilir

### Grid Tarama
1. **Poligon Çiz** butonuna tıklayın
2. Haritada poligon köşelerini tıklayarak çizin
3. **Görev Oluştur** butonuna tıklayın
4. Poligon içinde otomatik grid pattern oluşturulur

### Poligon Tarama
1. **Poligon Çiz** butonuna tıklayın
2. Haritada poligon köşelerini tıklayarak çizin
3. **Görev Oluştur** butonuna tıklayın
4. Poligon çevresinde waypoint'ler oluşturulur

### 8 Şekli Uçuş
1. **8 Şekli Çiz** butonuna tıklayın
2. Haritada iki nokta seçin (8'in merkezleri)
3. Yarıçap değerini ayarlayın
4. Otomatik olarak 8 şeklinde waypoint'ler oluşturulur

## ⚙️ Parametreler

### İrtifa (Altitude)
- **Aralık**: 5-500 metre
- **Varsayılan**: 50 metre
- **Birim**: metre

### Hız (Speed)
- **Aralık**: 1-50 m/s
- **Varsayılan**: 5 m/s
- **Birim**: metre/saniye

### 8 Şekli Yarıçapı
- **Aralık**: 5-100 metre
- **Varsayılan**: 20 metre
- **Birim**: metre

## 🔧 Görev Yönetimi

### Görev Oluşturma
1. Waypoint'leri ekleyin
2. Görev tipini seçin
3. Parametreleri ayarlayın
4. **Görev Oluştur** butonuna tıklayın

### Görev Yükleme
1. Görev oluşturulduktan sonra
2. **Araca Yükle** butonuna tıklayın
3. MAVLink protokolü ile araca gönderilir

### Görev Kontrolü
- **Görev Başlat**: Otomatik uçuşu başlatır
- **Görev Duraklat**: Uçuşu duraklatır
- **Görev İptal**: Uçuşu iptal eder ve eve döner

## 📊 Görev Bilgileri

### Waypoint Sayısı
- Eklenen waypoint'lerin toplam sayısı

### Tahmini Süre
- Hız parametresine göre hesaplanan uçuş süresi
- **Formül**: (Waypoint sayısı × 30 saniye) ÷ Hız

### Koordinat Bilgileri
- Her waypoint için enlem, boylam ve irtifa
- Haritada popup olarak görüntülenir

## 🗺️ Harita Özellikleri

### Waypoint İşaretleri
- **Turuncu bayrak**: Waypoint'ler
- **Mor işaret**: 8 şekli geçici noktaları
- **Kırmızı ok**: İHA konumu ve yönü
- **Yeşil ev**: Ev konumu

### Çizgiler
- **Mavi çizgi**: Uçuş yolu
- **Turuncu kesikli çizgi**: Waypoint rotası

## ⚠️ Hata Kontrolleri

### Koordinat Doğrulama
- Enlem: -90 ile 90 arası
- Boylam: -180 ile 180 arası
- İrtifa: 5 ile 500 metre arası

### Bağlantı Kontrolü
- MAVLink bağlantısı aktif olmalı
- Aracın sistem durumu kontrol edilir

### Görev Doğrulama
- En az 1 waypoint olmalı
- Tüm parametreler geçerli olmalı

## 🧪 Test Fonksiyonları

### Test Script'i Çalıştırma
```bash
cd lagger_gcs3
python test_waypoints.py
```

Bu script:
- Manuel waypoint ekleme
- 8 şekli oluşturma
- Poligon oluşturma
- Grid tarama
- Koordinat doğrulama
- Görev süresi hesaplama

testlerini yapar.

## 🔄 Güncellemeler

### Son Değişiklikler
- Harita tıklama olayları iyileştirildi
- Waypoint popup'larına koordinat bilgileri eklendi
- MAVLink görev yükleme protokolü güçlendirildi
- Hata mesajları detaylandırıldı
- Test fonksiyonları eklendi

### Bilinen Sorunlar
- JavaScript console mesajları bazen çalışmayabilir
- MAVLink bağlantısı olmadan görev yükleme simüle edilir

## 📞 Destek

Sorun yaşarsanız:
1. Test script'ini çalıştırın
2. Hata mesajlarını kontrol edin
3. Bağlantı durumunu doğrulayın
4. Koordinat değerlerini kontrol edin 