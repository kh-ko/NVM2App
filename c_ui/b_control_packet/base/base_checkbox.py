from PySide6.QtGui import QColor
from PySide6.QtWidgets import QCheckBox

from c_ui.b_control_packet.base import my_style

class BaseCheckBox(QCheckBox):
    def __init__(self, text="", parent=None):
        super().__init__(text, parent)

        self.set_color(my_style.STYLE_LABEL_COLOR)

    def set_color(self, label_color: str):
        base_label_color = QColor(label_color)
        r = base_label_color.red()
        g = base_label_color.green()
        b = base_label_color.blue()
        alpha = base_label_color.alpha()
        label_disabled_color = f"rgba({r}, {g}, {b}, {alpha * 0.5})"   

        self.setStyleSheet(f"""
            BaseCheckBox {{
                color: {label_color};
            }}
            BaseCheckBox:disabled {{
                color: {label_disabled_color};
            }}
        """)

        
