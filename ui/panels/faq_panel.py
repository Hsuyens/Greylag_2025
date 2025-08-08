from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QTextEdit, QScrollArea
from PyQt6.QtCore import Qt

class FAQPanel(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()
        
    def initUI(self):
        layout = QVBoxLayout()
        
        # Başlık
        title = QLabel("Sıkça Sorulan Sorular (FAQ)")
        title.setStyleSheet("font-weight: bold; font-size: 18px; margin-bottom: 10px;")
        layout.addWidget(title)
        
        # Scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        # FAQ içeriği
        faq_widget = QWidget()
        faq_layout = QVBoxLayout()
        
        faq_text = QTextEdit()
        faq_text.setReadOnly(True)
        faq_text.setPlainText(
            "🚁 İHA KONTROL SİSTEMİ FAQ\n"
            "========================\n\n"
            
            "1. Bağlantı Kurma\n"
            "Q: Pixhawk ile bağlantı kurulamıyor, ne yapmalıyım?\n"
            "A: - USB kablosunu kontrol edin\n"
            "   - Doğru port ve baudrate seçin (genellikle 115200)\n"
            "   - Pixhawk'ın açık olduğundan emin olun\n"
            "   - Sürücülerin yüklü olduğunu kontrol edin\n\n"
            
            "2. Telemetri Verisi\n"
            "Q: Telemetri verisi gelmiyor, neden?\n"
            "A: - Bağlantının sağlıklı olduğundan emin olun\n"
            "   - Aracın açık ve çalışır durumda olduğunu kontrol edin\n"
            "   - GPS sinyalinin alındığını doğrulayın\n\n"
            
            "3. FPV Görüntüsü\n"
            "Q: FPV görüntüsü gelmiyor, neden?\n"
            "A: - Kamera bağlantısını kontrol edin\n"
            "   - Video sürücülerinin yüklü olduğunu doğrulayın\n"
            "   - Doğru video kaynağını seçin\n"
            "   - Harici pencere yakalama özelliğini kullanabilirsiniz\n\n"
            
            "3.1. Harici Pencere Yakalama\n"
            "Q: Harici uygulamalardan gelen video akışını nasıl gösteririm?\n"
            "A: - Uçuş panelindeki 'Harici Pencere Seç' butonuna tıklayın\n"
            "   - Açık pencereler listesinden istediğiniz pencereyi seçin\n"
            "   - Seçilen pencere HUD'un arkasında görüntülenir\n"
            "   - 'Harici Pencereyi Durdur' ile yakalamayı durdurabilirsiniz\n\n"
            
            "4. Waypoint Görevleri\n"
            "Q: Waypoint nasıl çizerim?\n"
            "A: - 'Waypoint Ekle' butonuna basın\n"
            "   - Harita üzerinde istediğiniz noktalara tıklayın\n"
            "   - 'Görev Oluştur' ile görevi oluşturun\n"
            "   - 'Araca Yükle' ile Pixhawk'a gönderin\n"
            "   - 'Görevi Başlat' ile otonom uçuşa geçin\n\n"
            
            "5. Güvenlik\n"
            "Q: Acil durumda ne yapmalıyım?\n"
            "A: - 'Acil İniş' butonunu kullanın\n"
            "   - 'Eve Dönüş' ile güvenli bölgeye çekin\n"
            "   - 'Motor Kes' ile acil durdurma yapın\n\n"
            
            "6. Hava Durumu\n"
            "Q: Hava durumu verisi nereden geliyor?\n"
            "A: OpenWeatherMap API kullanılarak gerçek zamanlı hava durumu verisi alınır.\n\n"
            
            "7. Veri Loglama\n"
            "Q: Uçuş verileri nerede saklanıyor?\n"
            "A: Tüm telemetri verileri 'data/' klasöründe CSV formatında otomatik olarak kaydedilir.\n\n"
            
            "8. Sistem Gereksinimleri\n"
            "Q: Hangi sistem gereksinimleri var?\n"
            "A: - Python 3.8+\n"
            "   - PyQt6\n"
            "   - pymavlink\n"
            "   - Windows 10/11 (önerilen)\n\n"
            
            "9. Sorun Giderme\n"
            "Q: Program kapanıyor, ne yapmalıyım?\n"
            "A: - Terminal çıktısını kontrol edin\n"
            "   - uncaught_exceptions.log dosyasını inceleyin\n"
            "   - Bağlantı ayarlarını kontrol edin\n\n"
            
            "10. İletişim\n"
            "Q: Teknik destek için nereye başvurabilirim?\n"
            "A: Geliştirici ekibi ile iletişime geçin.\n"
        )
        
        faq_layout.addWidget(faq_text)
        faq_widget.setLayout(faq_layout)
        scroll.setWidget(faq_widget)
        
        layout.addWidget(scroll)
        self.setLayout(layout)