from PyQt6.QtWidgets import QDialog, QVBoxLayout, QFormLayout, QLineEdit, QPushButton, QHBoxLayout, QLabel

class LoiterDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Loiter (Daire Çiz) Ayarları")
        self.radius_input = QLineEdit("50")
        self.altitude_input = QLineEdit("10")
        self.altitude_input.setPlaceholderText("İrtifa (m)")
        self.radius_input.setPlaceholderText("Yarıçap (m)")

        form = QFormLayout()
        form.addRow("Yarıçap (m):", self.radius_input)
        form.addRow("İrtifa (m):", self.altitude_input)

        self.ok_btn = QPushButton("Tamamla")
        self.ok_btn.clicked.connect(self.accept)
        self.cancel_btn = QPushButton("İptal")
        self.cancel_btn.clicked.connect(self.reject)

        btn_layout = QHBoxLayout()
        btn_layout.addWidget(self.ok_btn)
        btn_layout.addWidget(self.cancel_btn)

        layout = QVBoxLayout()
        layout.addLayout(form)
        layout.addLayout(btn_layout)
        self.setLayout(layout)

    def get_values(self):
        try:
            radius = float(self.radius_input.text())
            altitude = float(self.altitude_input.text())
            return radius, altitude
        except ValueError:
            return None, None 