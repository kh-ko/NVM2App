import sys
from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel, QFrame, QPushButton

class CustomPanel(QWidget):
    def __init__(self, title="", parent=None): # title의 기본값을 빈 문자열로 설정
        super().__init__(parent)
        self.setObjectName("Panel")

        # 1. 메인 레이아웃 설정
        self.card_layout = QVBoxLayout(self)
        self.card_layout.setContentsMargins(15, 15, 15, 15) # 카드 내부 여백
        self.card_layout.setSpacing(10) # 내부 위젯들 간의 기본 간격

        # 2. 타이틀 및 구분선 추가
        if title:
            lbl_title = QLabel(title)
            # 패널의 기본 스타일이 상속되어 테두리가 생길 수 있으므로 border: none 추가
            lbl_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #333; border: none;")
            self.card_layout.addWidget(lbl_title)

            line = QFrame()
            line.setFixedHeight(1) # 선의 두께를 명시적으로 1px로 지정
            # 스타일시트로 배경색 지정 및 위아래 여백 설정
            line.setStyleSheet("background-color: #e0e0e0; border: none; margin-top: 5px; margin-bottom: 5px;")
            self.card_layout.addWidget(line)

        # 3. 위젯들이 추가될 컨테이너의 기본 디자인 적용
        self.__color_design()

    def __color_design(self):
        # QWidget#Panel 에만 스타일이 적용되도록 제한 (#Panel)
        self.setStyleSheet("""
            QWidget#Panel {
                background-color: white;
                border-radius: 6px; /* 카드 느낌을 살리기 위해 살짝 둥글게 수정 (원치 않으시면 0px로 변경) */
                border: 1px solid #dcdcdc;
            }
        """)

    def add_widget(self, widget):
        """외부에서 위젯을 전달받아 패널 내부에 추가합니다."""
        self.card_layout.addWidget(widget)

    def add_stretch(self):
        """
        위젯을 다 추가한 후 마지막에 호출하면, 
        추가된 위젯들이 패널 상단으로 바짝 밀착되게(위로 정렬) 만들어줍니다.
        """
        self.card_layout.addStretch()

