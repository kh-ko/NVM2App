from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QLabel

class CustomTitle(QLabel):
    LABEL_COLOR = "black"
    
    def __init__(self, text="", parent=None):
        super().__init__(text, parent)

        base_font = QApplication.font()
        base_pixel_size = base_font.pixelSize()
        font = self.font()
        font.setPixelSize(base_pixel_size * 1.2)
        self.setFont(font)

        self.set_color(CustomTitle.LABEL_COLOR)

    def set_color(self, color: str):
        base_label_color = QColor(color)
        r = base_label_color.red()
        g = base_label_color.green()
        b = base_label_color.blue()

        label_color = base_label_color.name()
        label_disabled_color = f"rgba({r}, {g}, {b}, 0.5)"

        self.setStyleSheet(f"""
            CustomTitle {{
                color: {label_color};
                background-color: transparent;
            }}
            CustomTitle:disabled {{
                color: {label_disabled_color};
            }}
        """)

    def set_text(self, text: str):
        super().setText(text)
    