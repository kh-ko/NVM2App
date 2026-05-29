from PySide6.QtCore import Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QDoubleSpinBox

from c_ui.b_control_packet.base import my_style

class BaseDoubleSpinBox(QDoubleSpinBox):
    enterFinished = Signal()
    
    def __init__(self, enable_border = True, parent=None):
        super().__init__(parent)
        self.lineEdit().returnPressed.connect(self._on_enter_pressed)
        self.enable_border = enable_border

        self.set_color(my_style.STYLE_LABEL_COLOR, my_style.STYLE_BORDER_COLOR)        

    def _on_enter_pressed(self):
        self.clearFocus()
        self.enterFinished.emit()

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

        border_hover_color = my_style.STYLE_HOVER_COLOR
        border_focus_color = my_style.STYLE_FOCUS_COLOR

        if self.enable_border is False:
            border_color = "transparent"
            border_disabled_color = "transparent"
            border_hover_color = "transparent"
            border_focus_color = "transparent"

        self.setStyleSheet(f"""
                BaseDoubleSpinBox {{
                    border: 1px solid {border_color};
                    border-radius: 4px;
                    padding-right: 5px;
                    background-color: transparent;
                    color: {label_color};
                }}
                BaseDoubleSpinBox:disabled {{
                    border: 1px solid {border_disabled_color};
                    border-radius: 4px;
                    padding-right: 5px;
                    background-color: transparent;
                    color: {label_disabled_color};
                }}
                BaseDoubleSpinBox:focus {{
                    border: 1px solid {border_focus_color};
                }}
                BaseDoubleSpinBox:hover {{
                background-color: transparent;
                border: 1px solid {border_hover_color};
            }}
            """)

        
