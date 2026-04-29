from PySide6.QtWidgets import QSizePolicy
from PySide6.QtWidgets import QPushButton, QHBoxLayout, QLabel
from PySide6.QtGui import QFont
from PySide6.QtCore import Qt

class CustomIconButton(QPushButton):
    def __init__(self, text="", icon_char="●", parent=None):
        super().__init__(parent)
        self._icon_char = icon_char

        self.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Minimum)
        
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(10, 10, 10, 10) 
        self.layout.setSpacing(5) 
        self.layout.setSizeConstraint(QHBoxLayout.SetMinimumSize)

        self.lbl_icon = QLabel(self._icon_char)
        self.lbl_icon.setAttribute(Qt.WA_TransparentForMouseEvents)

        icon_font = QFont("Material Icons")
        icon_font.setPixelSize(16)
        self.lbl_icon.setFont(icon_font)

        self.lbl_text = QLabel(text)
        self.lbl_text.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.lbl_text.setStyleSheet("color: black;")
        self.lbl_text.setAlignment(Qt.AlignCenter)

        self.layout.addWidget(self.lbl_icon, 0)
        self.layout.addWidget(self.lbl_text, 1)
        
        self.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: 1px solid #dcdcdc;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #e6e6e6;
            }
            QPushButton:pressed {
                background-color: #d4d4d4;
            }
        """)

    def set_icon(self, icon:str):
        self.lbl_icon.setText(icon)

    def set_icon_colors(self, color: str):
        self.lbl_icon.setStyleSheet(f"color: {color};")

    def set_text_color(self, color: str):
        self.lbl_text.setStyleSheet(f"color: {color};")
