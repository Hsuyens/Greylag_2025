from PyQt6.QtGui import QColor, QPalette
from PyQt6.QtWidgets import QApplication

class ThemeColors:
    # Ana Renkler
    BACKGROUND = "#1e1e1e"
    SECONDARY_BG = "#252526"
    BORDER = "#333333"
    
    # Metin Renkleri
    TEXT_PRIMARY = "#ffffff"
    TEXT_SECONDARY = "#cccccc"
    
    # Vurgu Renkleri
    ACCENT = "#007acc"  # Mavi vurgu
    ACCENT_HOVER = "#1f8ad2"
    SUCCESS = "#47d147"  # Yeşil
    WARNING = "#ffaa00"  # Turuncu
    DANGER = "#ff3333"   # Kırmızı
    
    # Grafik Renkleri
    GRAPH_BG = "#2d2d2d"
    GRID_COLOR = "#404040"
    
    # Buton Stilleri
    BUTTON_NORMAL = """
        QPushButton {
            background-color: #2d2d2d;
            color: #ffffff;
            border: 1px solid #404040;
            border-radius: 4px;
            padding: 5px 15px;
            font-weight: bold;
        }
        QPushButton:hover {
            background-color: #3d3d3d;
            border: 1px solid #505050;
        }
        QPushButton:pressed {
            background-color: #505050;
        }
        QPushButton:disabled {
            background-color: #252526;
            color: #666666;
            border: 1px solid #333333;
        }
    """
    
    BUTTON_PRIMARY = """
        QPushButton {
            background-color: #007acc;
            color: white;
            border: none;
            border-radius: 4px;
            padding: 5px 15px;
            font-weight: bold;
        }
        QPushButton:hover {
            background-color: #1f8ad2;
        }
        QPushButton:pressed {
            background-color: #005c99;
        }
        QPushButton:disabled {
            background-color: #252526;
            color: #666666;
        }
    """
    
    BUTTON_SUCCESS = """
        QPushButton {
            background-color: #47d147;
            color: white;
            border: none;
            border-radius: 4px;
            padding: 5px 15px;
            font-weight: bold;
        }
        QPushButton:hover {
            background-color: #53db53;
        }
        QPushButton:pressed {
            background-color: #39ac39;
        }
    """
    
    BUTTON_WARNING = """
        QPushButton {
            background-color: #ffaa00;
            color: white;
            border: none;
            border-radius: 4px;
            padding: 5px 15px;
            font-weight: bold;
        }
        QPushButton:hover {
            background-color: #ffb31a;
        }
        QPushButton:pressed {
            background-color: #cc8800;
        }
    """
    
    BUTTON_DANGER = """
        QPushButton {
            background-color: #ff3333;
            color: white;
            border: none;
            border-radius: 4px;
            padding: 5px 15px;
            font-weight: bold;
        }
        QPushButton:hover {
            background-color: #ff4d4d;
        }
        QPushButton:pressed {
            background-color: #cc2929;
        }
    """
    
    # Panel Stilleri
    PANEL_STYLE = """
        QGroupBox {
            background-color: #252526;
            border: 1px solid #333333;
            border-radius: 6px;
            margin-top: 12px;
            font-weight: bold;
        }
        QGroupBox::title {
            color: #ffffff;
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 3px 0 3px;
        }
    """
    
    # Input Stilleri
    INPUT_STYLE = """
        QLineEdit, QTextEdit, QComboBox {
            background-color: #1e1e1e;
            color: #ffffff;
            border: 1px solid #404040;
            border-radius: 4px;
            padding: 4px;
        }
        QLineEdit:focus, QTextEdit:focus, QComboBox:focus {
            border: 1px solid #007acc;
        }
        QComboBox::drop-down {
            border: none;
            width: 20px;
        }
    """
    
    # Progress Bar Stili
    PROGRESS_STYLE = """
        QProgressBar {
            border: 1px solid #404040;
            border-radius: 4px;
            text-align: center;
            background-color: #1e1e1e;
            color: #ffffff;
        }
        QProgressBar::chunk {
            background-color: #007acc;
            border-radius: 3px;
        }
    """

def apply_theme(app: QApplication):
    app.setStyle("Fusion")
    
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor(ThemeColors.BACKGROUND))
    palette.setColor(QPalette.ColorRole.WindowText, QColor(ThemeColors.TEXT_PRIMARY))
    palette.setColor(QPalette.ColorRole.Base, QColor(ThemeColors.SECONDARY_BG))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor(ThemeColors.BACKGROUND))
    palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(ThemeColors.TEXT_PRIMARY))
    palette.setColor(QPalette.ColorRole.ToolTipText, QColor(ThemeColors.TEXT_PRIMARY))
    palette.setColor(QPalette.ColorRole.Text, QColor(ThemeColors.TEXT_PRIMARY))
    palette.setColor(QPalette.ColorRole.Button, QColor(ThemeColors.SECONDARY_BG))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor(ThemeColors.TEXT_PRIMARY))
    palette.setColor(QPalette.ColorRole.BrightText, QColor(ThemeColors.TEXT_PRIMARY))
    palette.setColor(QPalette.ColorRole.Link, QColor(ThemeColors.ACCENT))
    palette.setColor(QPalette.ColorRole.Highlight, QColor(ThemeColors.ACCENT))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor(ThemeColors.TEXT_PRIMARY))
    
    # Set disabled colors
    palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.ButtonText, QColor("#666666"))
    palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.WindowText, QColor("#666666"))
    palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text, QColor("#666666"))
    palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Base, QColor(ThemeColors.SECONDARY_BG))
    palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.AlternateBase, QColor(ThemeColors.BACKGROUND))

    app.setPalette(palette)
    
    app.setStyleSheet(f"""
        QToolTip {{
            color: {ThemeColors.TEXT_PRIMARY};
            background-color: {ThemeColors.SECONDARY_BG};
            border: 1px solid {ThemeColors.BORDER};
            border-radius: 4px;
        }}
    """) 