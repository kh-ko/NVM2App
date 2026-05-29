from PySide6.QtGui import QColor
from PySide6.QtWidgets import QPushButton

from c_ui.b_control_packet.base import my_style

class BaseButton(QPushButton):
    def __init__(self, text="", parent=None):
        super().__init__(text, parent)

        self.set_color(my_style.STYLE_LABEL_COLOR,my_style.STYLE_BORDER_COLOR)

    def set_color(self, label_color: str, border_color: str):
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

        self.setStyleSheet(f"""
            BaseButton {{
                background-color: transparent;
                border: 1px solid {border_color};
                border-radius: 4px;
                color: {label_color};
            }}
            BaseButton:disabled {{
                background-color: transparent;
                border: 1px solid {border_disabled_color};
                border-radius: 4px;
                color: {label_disabled_color};
            }}
            BaseButton:hover {{
                background-color: transparent;
                border: 1px solid {my_style.STYLE_HOVER_COLOR};
            }}
            BaseButton:pressed {{
                background-color: {my_style.STYLE_PRESSED_COLOR};
            }}
        """)

        
