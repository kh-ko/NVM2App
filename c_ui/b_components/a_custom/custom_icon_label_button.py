from PySide6.QtWidgets import QPushButton, QHBoxLayout, QLabel
from PySide6.QtGui import QFont
from PySide6.QtCore import Qt

class CustomIconLabelButton(QPushButton):
    def __init__(self, text="", icon_char="●", parent=None):
        super().__init__(parent)
        self._icon_char = icon_char

        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0) 
        self.layout.setSpacing(5) 

        self.lbl_icon = QLabel(self._icon_char)
        self.lbl_icon.setAttribute(Qt.WA_TransparentForMouseEvents)

        icon_font = QFont("Material Icons")
        icon_font.setPixelSize(16)
        self.lbl_icon.setFont(icon_font)

        self.lbl_text = QLabel(text)
        self.lbl_text.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.lbl_text.setStyleSheet("color: black; text-align: left;")

        self.layout.addWidget(self.lbl_icon)
        self.layout.addWidget(self.lbl_text)
        self.layout.addStretch()
        
        self.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #e6e6e6;
            }
            QPushButton:pressed {
                background-color: #d4d4d4;
            }
        """)

    def set_icon_colors(self, color: str):
        self.lbl_icon.setStyleSheet(f"color: {color};")

    def set_text_color(self, color: str):
        self.lbl_text.setStyleSheet(f"color: {color}; text-align: left;")
