from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel, QFrame, QPushButton, QScrollArea

from c_ui.b_components.a_custom.custom_title import CustomTitle

class CustomPanel(QWidget):
    def __init__(self, title="", parent=None): # title의 기본값을 빈 문자열로 설정
        super().__init__(parent)
        self.setObjectName("Panel")

        # 1. 메인 레이아웃 설정
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(10, 10, 10, 10) # 카드 내부 여백
        self.main_layout.setSpacing(5) # 내부 위젯들 간의 기본 간격

        # 2. 타이틀 및 구분선 추가
        if title:
            lbl_title = CustomTitle(title)
            # 패널의 기본 스타일이 상속되어 테두리가 생길 수 있으므로 border: none 추가
            self.main_layout.addWidget(lbl_title)

            line = QFrame()
            line.setFixedHeight(1) # 선의 두께를 명시적으로 1px로 지정
            # 스타일시트로 배경색 지정 및 위아래 여백 설정
            line.setStyleSheet("background-color: #dcdcdc; border: none; margin-top: 5px; margin-bottom: 5px;")
            self.main_layout.addWidget(line)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.NoFrame)
        self.scroll_area.setStyleSheet("background-color: transparent;")
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.scroll_content = QWidget()
        self.scroll_content.setObjectName("ScrollContent")
        self.scroll_content.setStyleSheet("background-color: transparent; border: none;")

        self.scroll_layout = QVBoxLayout(self.scroll_content)
        self.scroll_layout.setContentsMargins(0, 0, 0, 0) # 스크롤 내부 여백
        self.scroll_layout.setSpacing(5)

        self.scroll_area.setWidget(self.scroll_content)

        self.main_layout.addWidget(self.scroll_area)

        # 3. 위젯들이 추가될 컨테이너의 기본 디자인 적용
        self.__color_design()

    def __color_design(self):
        self.setAttribute(Qt.WA_StyledBackground, True)
        
        # QWidget#Panel 에만 스타일이 적용되도록 제한 (#Panel)
        self.setStyleSheet("""
            QWidget#Panel {
                background-color: white;
                border: 1px solid #dcdcdc;
            }
        """)

    def add_widget(self, widget):
        """외부에서 위젯을 전달받아 패널 내부에 추가합니다."""
        self.scroll_layout.addWidget(widget)

    def add_stretch(self):
        """
        위젯을 다 추가한 후 마지막에 호출하면, 
        추가된 위젯들이 패널 상단으로 바짝 밀착되게(위로 정렬) 만들어줍니다.
        """
        self.scroll_layout.addStretch()

