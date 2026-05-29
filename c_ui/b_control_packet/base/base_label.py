from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QLabel

from c_ui.b_control_packet.base import my_style

class BaseLabel(QLabel):    
    def __init__(self, text="", type = my_style.STYLE_LABEL_BASE, parent=None):
        super().__init__(text, parent)

        if type != my_style.STYLE_LABEL_BASE:
            base_font = QApplication.font()
            base_pixel_size = base_font.pixelSize()

            if type == my_style.STYLE_LABEL_ICON:
                font = QFont("Material Icons")
                font.setPixelSize(base_pixel_size)
                self.setFont(font)
            elif type == my_style.STYLE_LABEL_DESCRIPTION:
                font = self.font()
                font.setPixelSize(base_pixel_size * 0.8)
                self.setFont(font)
            else:
                font = self.font()
                font.setPixelSize(base_pixel_size * 1.2)
                self.setFont(font)

        self.set_color(my_style.STYLE_LABEL_COLOR)

    def set_color(self, label_color: str, border_color="transparent", bg_color="transparent"):
        base_label_color = QColor(label_color)
        r = base_label_color.red()
        g = base_label_color.green()
        b = base_label_color.blue()
        alpha = base_label_color.alpha()
        label_disabled_color = f"rgba({r}, {g}, {b}, {alpha * 0.5})"

        base_border_color = QColor(border_color)
        r = base_border_color.red()
        g = base_border_color.green()
        b = base_border_color.blue()
        alpha = base_border_color.alpha()
        border_disabled_color = f"rgba({r}, {g}, {b}, {alpha * 0.5})"

        base_bg_color = QColor(bg_color)
        r = base_bg_color.red()
        g = base_bg_color.green()
        b = base_bg_color.blue()
        alpha = base_bg_color.alpha()
        bg_disabled_color = f"rgba({r}, {g}, {b}, {alpha * 0.5})"


        self.setStyleSheet(f"""
            * {{
                color: {label_color};
                background-color: {bg_color};
                border-color: {border_color};
            }}
            *:disabled {{
                color: {label_disabled_color};
                background-color: {bg_disabled_color};
                border-color: {border_disabled_color};
            }}
        """)

    def set_text(self, text: str):
        super().setText(text)
    