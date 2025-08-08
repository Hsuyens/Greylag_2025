import win32gui
import win32con
import win32process
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QListWidget, QListWidgetItem, QLabel, QMessageBox)
from PyQt6.QtCore import Qt, pyqtSignal

class WindowSelectorDialog(QDialog):
    window_selected = pyqtSignal(str, int)  # window_title, window_handle
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Harici Pencere Seç")
        self.setModal(True)
        self.setFixedSize(500, 400)
        self.windows = []
        self.initUI()
        self.refresh_windows()
        
    def initUI(self):
        layout = QVBoxLayout()
        
        # Başlık
        title_label = QLabel("Açık pencereleri seçin:")
        title_label.setStyleSheet("font-weight: bold; font-size: 14px; margin: 10px;")
        layout.addWidget(title_label)
        
        # Pencere listesi
        self.window_list = QListWidget()
        self.window_list.setStyleSheet("""
            QListWidget {
                border: 2px solid #3498db;
                border-radius: 5px;
                background-color: #2c3e50;
                color: white;
                font-size: 12px;
            }
            QListWidget::item {
                padding: 8px;
                border-bottom: 1px solid #34495e;
            }
            QListWidget::item:selected {
                background-color: #3498db;
            }
            QListWidget::item:hover {
                background-color: #34495e;
            }
        """)
        layout.addWidget(self.window_list)
        
        # Butonlar
        button_layout = QHBoxLayout()
        
        self.refresh_btn = QPushButton("Yenile")
        self.refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2ecc71;
            }
        """)
        self.refresh_btn.clicked.connect(self.refresh_windows)
        
        self.select_btn = QPushButton("Seç")
        self.select_btn.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
        """)
        self.select_btn.clicked.connect(self.select_window)
        
        self.cancel_btn = QPushButton("İptal")
        self.cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #c0392b;
            }
        """)
        self.cancel_btn.clicked.connect(self.reject)
        
        button_layout.addWidget(self.refresh_btn)
        button_layout.addStretch()
        button_layout.addWidget(self.select_btn)
        button_layout.addWidget(self.cancel_btn)
        
        layout.addLayout(button_layout)
        self.setLayout(layout)
        
    def enum_windows_callback(self, hwnd, windows):
        """Pencere listesini oluşturmak için callback fonksiyonu"""
        if win32gui.IsWindowVisible(hwnd):
            window_text = win32gui.GetWindowText(hwnd)
            if window_text and len(window_text) > 0:
                # Sistem pencerelerini filtrele
                if not self.is_system_window(hwnd, window_text):
                    windows.append((window_text, hwnd))
        return True
    
    def is_system_window(self, hwnd, title):
        """Sistem pencerelerini filtrele"""
        system_titles = [
            "Program Manager", "Task Manager", "Settings", "Control Panel",
            "Desktop", "Start", "Search", "Cortana", "Action Center",
            "Notification Area", "System Tray", "Clock", "Volume",
            "Network", "Battery", "Power", "Windows Security",
            "Windows Update", "Device Manager", "File Explorer",
            "Lagger GCS"  # Kendi uygulamamızı filtrele
        ]
        
        # Sistem pencerelerini filtrele
        if any(sys_title.lower() in title.lower() for sys_title in system_titles):
            print(f"[WindowSelector] Filtrelenen pencere: {title}")
            return True
            
        # Boş başlıkları filtrele
        if not title.strip():
            return True
            
        # Çok kısa başlıkları filtrele
        if len(title.strip()) < 3:
            return True
            
        print(f"[WindowSelector] Kabul edilen pencere: {title}")
        return False
    
    def refresh_windows(self):
        """Açık pencereleri yenile"""
        self.window_list.clear()
        self.windows.clear()
        
        try:
            win32gui.EnumWindows(self.enum_windows_callback, self.windows)
            
            # Pencereleri başlık sırasına göre sırala
            self.windows.sort(key=lambda x: x[0].lower())
            
            for title, hwnd in self.windows:
                item = QListWidgetItem(f"{title}")
                item.setData(Qt.ItemDataRole.UserRole, hwnd)
                self.window_list.addItem(item)
                
        except Exception as e:
            QMessageBox.warning(self, "Hata", f"Pencere listesi alınamadı: {str(e)}")
    
    def select_window(self):
        """Seçilen pencereyi onayla"""
        current_item = self.window_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "Uyarı", "Lütfen bir pencere seçin!")
            return
            
        hwnd = current_item.data(Qt.ItemDataRole.UserRole)
        title = current_item.text()
        
        print(f"[WindowSelector] Seçilen pencere: '{title}' (HWND: {hwnd})")
        
        # Pencere hala var mı kontrol et
        if not win32gui.IsWindow(hwnd):
            QMessageBox.warning(self, "Hata", "Seçilen pencere artık mevcut değil!")
            self.refresh_windows()
            return
            
        # Pencere bilgilerini göster
        try:
            left, top, right, bottom = win32gui.GetWindowRect(hwnd)
            print(f"[WindowSelector] Pencere koordinatları: ({left}, {top}, {right}, {bottom})")
            print(f"[WindowSelector] Pencere boyutu: {right-left}x{bottom-top}")
        except Exception as e:
            print(f"[WindowSelector] Pencere bilgisi alınamadı: {e}")
            
        self.window_selected.emit(title, hwnd)
        self.accept() 