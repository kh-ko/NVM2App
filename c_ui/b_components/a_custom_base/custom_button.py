from PySide6.QtGui import QColor
from PySide6.QtWidgets import QPushButton

class CustomButton(QPushButton):
    LABEL_COLOR = "black"
    BORDER_COLOR = "#dcdcdc"
    HOVER_COLOR = "#1a73e8"
    PRESSED_COLOR = "#d4d4d4"
    
    def __init__(self, text="", parent=None):
        super().__init__(text, parent)

        self.set_color(CustomButton.LABEL_COLOR, CustomButton.BORDER_COLOR)

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
            CustomButton {{
                background-color: transparent;
                border: 1px solid {border_color};
                border-radius: 4px;
                color: {label_color};
            }}
            CustomButton:disabled {{
                background-color: transparent;
                border: 1px solid {border_disabled_color};
                border-radius: 4px;
                color: {label_disabled_color};
            }}
            CustomButton:hover {{
                background-color: transparent;
                border: 1px solid {CustomButton.HOVER_COLOR};
            }}
            CustomButton:pressed {{
                background-color: {CustomButton.PRESSED_COLOR};
            }}
        """)

        
