from b_core.b_datatype.general_enum import LogType
from PySide6.QtGui import QColor
from PySide6.QtCore import QAbstractListModel
from PySide6.QtWidgets import QListView
from PySide6.QtCore import Qt
        
class BaseConsoleList(QListView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.viewport().setStyleSheet("background-color: #000000;")
        
        self.setStyleSheet("""
            QListView {
                border: 1px solid #dcdcdc;
            }
            QListView::item:selected {
                background-color: #333333;
                color: #ffffff;
            }
        """)


    

        
