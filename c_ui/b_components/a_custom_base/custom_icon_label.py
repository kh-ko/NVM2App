from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import QLabel

class CustomIconLabel(QLabel):

    def __init__(self, text="", color = "black", icon_size_scale = 1.0, parent=None):
        super().__init__(text, parent)

        font = QFont("Material Icons")
        base_font = QApplication.font()
        base_pixel_size = base_font.pixelSize()
        font.setPixelSize(base_pixel_size * icon_size_scale)
        self.setFont(font)

        self.set_color(color)

    def set_color(self, color: str):
        base_label_color = QColor(color)
        r = base_label_color.red()
        g = base_label_color.green()
        b = base_label_color.blue()

        label_color = base_label_color.name()
        label_disabled_color = f"rgba({r}, {g}, {b}, 0.5)"

        self.setStyleSheet(f"""
            CustomIconLabel {{
                color: {label_color};
                background-color: transparent;
            }}
            CustomIconLabel:disabled {{
                color: {label_disabled_color};
            }}
        """)

    def set_text(self, text: str):
        super().setText(text)