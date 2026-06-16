
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QWidget

from c_ui.b_control_packet.base import my_style
from c_ui.b_control_packet.controls.my_labeltitle import MyLabelTitle
from c_ui.b_control_packet.controls.my_labeldescription import MyLabelDescription

class MyCardWidget(QWidget):

    def __init__(self, title, is_big_title = False, parent=None):
        super().__init__(parent)

        self.setAttribute(Qt.WA_StyledBackground, True)
        
        self.setStyleSheet(f"""
            MyCardWidget {{
                background-color: white;
                border: 1px solid {my_style.STYLE_BORDER_COLOR};
            }}
        """)
        
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(10, 10, 10, 10)
        self.main_layout.setSpacing(5)
        
        self.title_layout = QHBoxLayout()
        self.title_layout.setContentsMargins(0, 0, 0, 0)
        
        # 1. 상단 타이틀
        if is_big_title:
            lbl_title = MyLabelTitle(title)
        else:
            lbl_title = MyLabelDescription(title)

        lbl_title.setWordWrap(False)
        self.title_layout.addWidget(lbl_title)
        self.title_layout.addStretch()
        self.main_layout.addLayout(self.title_layout)

        line = QFrame()
        line.setFixedHeight(1) # 선의 두께를 명시적으로 1px로 지정
        # 스타일시트로 배경색 지정 및 위아래 여백 설정
        line.setStyleSheet(f"background-color: {my_style.STYLE_BORDER_COLOR}; border: none; margin-top: 5px; margin-bottom: 5px;")
        self.main_layout.addWidget(line)
        
        # 3. 하단 컨텐츠를 담을 빈 위젯 & 레이아웃
        self.content_widget = QWidget()
        self.content_widget.setStyleSheet("border: none; background: transparent;")
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(5)
        self.main_layout.addWidget(self.content_widget)
        self.main_layout.addStretch()

    def add_widget(self, widget):
        self.content_layout.addWidget(widget)