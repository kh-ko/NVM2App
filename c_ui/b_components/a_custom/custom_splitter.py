from PySide6.QtWidgets import QSplitter

class CustomSplitter(QSplitter):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setHandleWidth(1)

        self.__color_design()

    def __color_design(self):
        # 전달해주신 스타일시트를 그대로 적용합니다.
        self.setStyleSheet("""
            QSplitter::handle { 
                background-color: transparent; 
                margin: 0px;
                padding: 0px;
            }
            /* 가로 스플리터일 경우 폭 1px 고정 */
            QSplitter::handle:horizontal {
                width: 1px;
            }
            /* 세로 스플리터일 경우 높이 1px 고정 */
            QSplitter::handle:vertical {
                height: 1px;
            }
        """)