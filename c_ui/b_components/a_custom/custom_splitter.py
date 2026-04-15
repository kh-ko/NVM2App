from PySide6.QtWidgets import QSplitter

class CustomSplitter(QSplitter):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.__color_design()

    def __color_design(self):
        # 전달해주신 스타일시트를 그대로 적용합니다.
        self.setStyleSheet("QSplitter::handle { background-color: transparent; }")