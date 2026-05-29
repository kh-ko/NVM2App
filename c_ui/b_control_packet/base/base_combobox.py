from PySide6.QtGui import QColor
from PySide6.QtWidgets import QComboBox

from c_ui.b_control_packet.base import my_style

class BaseComboBox(QComboBox):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.set_color(my_style.STYLE_LABEL_COLOR, my_style.STYLE_BORDER_COLOR)

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
            BaseComboBox {{
                color: {label_color};
                border: 1px solid {border_color};
                border-radius: 4px;
                padding: 4px 8px;
                background-color: transparent;
                min-height: 24px;
            }}
            BaseComboBox:disabled {{
                color: {label_disabled_color};
                border: 1px solid {border_disabled_color};
                border-radius: 4px;
                padding: 4px 8px;
                background-color: transparent;
                min-height: 24px;
            }}
            
            BaseComboBox:hover {{
                background-color: transparent;
                border: 1px solid {my_style.STYLE_HOVER_COLOR};
            }}
            
            BaseComboBox::drop-down {{
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 20px;
                border-left: 1px solid {border_color};
            }}

            BaseComboBox QAbstractItemView {{
                font-size: 14px;
                border: 1px solid {border_color};
                border-radius: 4px;
                background-color: white;
                outline: 0px;
                selection-background-color: {my_style.STYLE_ITEM_SEL_BG_COLOR};
                selection-color: {my_style.STYLE_ITEM_SEL_COLOR};
            }}
        """)

        
