from PySide6.QtWidgets import QListWidget

class CustomListWidget(QListWidget):
    BORDER_COLOR = "#dcdcdc"
    SELECT_COLOR = "#e3f2fd"
    SELECT_FONT_COLOR = "#1976d2"
    BACKGROUND_COLOR = "white"

    def __init__(self, parent=None):
        super().__init__(parent)
        self.__set_style()

    def __set_style(self):
        self.setStyleSheet(f"""
            CustomListWidget {{
                border-radius: 0px;
                border: 1px solid {CustomListWidget.BORDER_COLOR};
                background-color: {CustomListWidget.BACKGROUND_COLOR};
                padding: 0px;
            }}
            CustomListWidget::item {{ padding: 5px; border-radius: 0px; }}
            CustomListWidget::item:selected {{ background-color: {CustomListWidget.SELECT_COLOR}; color: {CustomListWidget.SELECT_FONT_COLOR}; font-weight: bold; }}
        """)