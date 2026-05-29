from PySide6.QtGui import QColor
from PySide6.QtWidgets import QLineEdit

from c_ui.b_control_packet.base import my_style

class BaseLineEdit(QLineEdit):    
    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self.returnPressed.connect(self._on_enter_pressed)
        self.set_color(my_style.STYLE_LABEL_COLOR, my_style.STYLE_BORDER_COLOR)

    def _on_enter_pressed(self):
        self.clearFocus()

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
                BaseLineEdit {{
                    border: 1px solid {border_color};
                    border-radius: 4px;
                    padding-right: 5px;
                    background-color: transparent;
                    color: {label_color};
                }}
                BaseLineEdit:disabled {{
                    border: 1px solid {border_disabled_color};
                    border-radius: 4px;
                    padding-right: 5px;
                    background-color: transparent;
                    color: {label_disabled_color};
                }}
                BaseLineEdit:focus {{
                    border: 1px solid {my_style.STYLE_FOCUS_COLOR};
                }}
                BaseLineEdit:hover {{
                    background-color: transparent;
                    border: 1px solid {my_style.STYLE_HOVER_COLOR};
                }}
            """)

        
