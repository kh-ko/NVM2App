from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QVBoxLayout, QWidget

from c_ui.b_components.a_custom_base.custom_description import CustomDescription

class CustomCardWidget(QWidget):
    BORDER_COLOR = "#dcdcdc"

    def __init__(self, title, parent=None):
        super().__init__(parent)
        self.setObjectName("Card")

        self.setAttribute(Qt.WA_StyledBackground, True)
        
        # QWidget#Panel 에만 스타일이 적용되도록 제한 (#Panel)
        self.setStyleSheet(f"""
            QWidget#Card {{
                background-color: transparent;
                border: 1px solid {CustomCardWidget.BORDER_COLOR};
            }}
        """)
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(5)
        
        # 1. 상단 타이틀
        lbl_title = CustomDescription(title)
        main_layout.addWidget(lbl_title)

        line = QFrame()
        line.setFixedHeight(1) # 선의 두께를 명시적으로 1px로 지정
        # 스타일시트로 배경색 지정 및 위아래 여백 설정
        line.setStyleSheet(f"background-color: {CustomCardWidget.BORDER_COLOR}; border: none; margin-top: 5px; margin-bottom: 5px;")
        main_layout.addWidget(line)
        
        # 3. 하단 컨텐츠를 담을 빈 위젯 & 레이아웃
        self.content_widget = QWidget()
        self.content_widget.setStyleSheet("border: none; background: transparent;")
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(5)
        main_layout.addWidget(self.content_widget)
        main_layout.addStretch()

    def add_widget(self, widget):
        """컨텐츠 영역에 위젯을 추가하는 편의 메서드"""
        self.content_layout.addWidget(widget)