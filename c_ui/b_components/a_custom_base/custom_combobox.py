from PySide6.QtGui import QColor
from PySide6.QtWidgets import QComboBox

class CustomComboBox(QComboBox):
    LABEL_COLOR = "black"
    BORDER_COLOR = "#dcdcdc"
    HOVER_COLOR = "#1a73e8"
    SELECT_COLOR = "#1976d2"
    SELECT_BG_COLOR = "#e3f2fd"
    
    def __init__(self, parent=None):
        super().__init__(parent)

        self.set_color(CustomComboBox.LABEL_COLOR, CustomComboBox.BORDER_COLOR)

    def set_color(self, label_color: str, border_color: str):
        base_label_color = QColor(label_color)
        r = base_label_color.red()
        g = base_label_color.green()
        b = base_label_color.blue()
        label_disabled_color = f"rgba({r}, {g}, {b}, 0.5)"

        base_border_color = QColor(border_color)
        r = base_border_color.red()
        g = base_border_color.green()
        b = base_border_color.blue()
        border_disabled_color = f"rgba({r}, {g}, {b}, 0.5)"        

        self.setStyleSheet(f"""
            CustomComboBox {{
                color: {label_color};
                border: 1px solid {border_color};
                border-radius: 4px;
                padding: 4px 8px;
                background-color: transparent;
                min-height: 24px;
            }}
            CustomComboBox:disabled {{
                color: {label_disabled_color};
                border: 1px solid {border_disabled_color};
                border-radius: 4px;
                padding: 4px 8px;
                background-color: transparent;
                min-height: 24px;
            }}
            
            CustomComboBox:hover {{
                background-color: transparent;
                border: 1px solid {CustomComboBox.HOVER_COLOR};
            }}
            
            CustomComboBox::drop-down {{
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 20px;
                border-left: 1px solid {border_color};
            }}

            CustomComboBox QAbstractItemView {{
                font-size: 14px;
                border: 1px solid {border_color};
                border-radius: 4px;
                background-color: white;
                outline: 0px;
                selection-background-color: {CustomComboBox.SELECT_BG_COLOR};
                selection-color: {CustomComboBox.SELECT_COLOR};
            }}
        """)

        
