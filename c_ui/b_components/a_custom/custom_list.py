from PySide6.QtWidgets import QListWidget

class CustomListWidget(QListWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.__color_design()

    def __color_design(self):
        # 전달해주신 스타일시트를 그대로 적용합니다.
        self.setStyleSheet("""
            QListWidget {
                border-radius: 0px;
                border: 1px solid #dcdcdc;
                background-color: white;
                padding: 0px;
            }
            QListWidget::item { padding: 5px; border-radius: 0px; }
            QListWidget::item:selected { background-color: #e3f2fd; color: #1976d2; font-weight: bold; }
        """)