from PySide6.QtWidgets import QListWidget

from c_ui.b_control_packet.base import my_style

class MyListWidget(QListWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.__set_style()

    def __set_style(self):
        self.setStyleSheet(f"""
            MyListWidget {{
                border-radius: 0px;
                border: 1px solid {my_style.STYLE_BORDER_COLOR};
                background-color: "white";
                padding: 0px;
            }}
            MyListWidget::item {{ padding: 5px; border-radius: 0px; }}
            MyListWidget::item:selected {{ background-color: {my_style.STYLE_LIST_SEL_COLOR}; color: {my_style.STYLE_LIST_SEL_FONT_COLOR}; font-weight: bold; }}
        """)