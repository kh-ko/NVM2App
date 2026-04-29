from PySide6.QtWidgets import QPushButton
from PySide6.QtCore import Qt

class CustomButton(QPushButton):
    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        
        self.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: 1px solid #dcdcdc;
                border-radius: 4px;
                color: black;
            }
            QPushButton:hover {
                background-color: #e6e6e6;
            }
            QPushButton:pressed {
                background-color: #d4d4d4;
            }
        """)
