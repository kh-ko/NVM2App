from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel, QFrame, QPushButton, QScrollArea

from b_core.b_datatype import param_enum as p_enum

from c_ui.b_components.a_custom.custom_title import CustomTitle
from c_ui.b_components.a_custom.custom_icon_button import CustomIconButton

class MainControl(QWidget):
    def __init__(self, parent=None): # title의 기본값을 빈 문자열로 설정
        super().__init__(parent)
        self.setObjectName("MainControl")

        self.setAttribute(Qt.WA_StyledBackground, True)

        self.setStyleSheet("""
            QWidget#MainControl {
                background-color: white;
                border: 1px solid #dcdcdc;
            }
        """)

         # 1. 메인 레이아웃 설정
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(10, 10, 10, 10) # 카드 내부 여백
        self.main_layout.setSpacing(5) # 내부 위젯들 간의 기본 간격

        lbl_title = CustomTitle("Status")
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

        self.open_btn = CustomIconButton("Open", "\uf88a")
        self.open_btn.clicked.connect(self.on_clicked_open_btn)
        self.add_widget(self.open_btn)

        self.close_btn = CustomIconButton("Close", "\uf88a")
        self.close_btn.clicked.connect(self.on_clicked_close_btn)
        self.add_widget(self.close_btn)

        self.hold_btn = CustomIconButton("Hold", "\uf88a")
        self.hold_btn.clicked.connect(self.on_clicked_hold_btn)
        self.add_widget(self.hold_btn)

        self.learn_btn = CustomIconButton("Learn", "\uf88a")
        self.learn_btn.clicked.connect(self.on_clicked_learn_btn)
        self.add_widget(self.learn_btn)
        self.add_stretch()

    def add_widget(self, widget):
        """외부에서 위젯을 전달받아 패널 내부에 추가합니다."""
        self.scroll_layout.addWidget(widget)

    def add_stretch(self):
        """
        위젯을 다 추가한 후 마지막에 호출하면, 
        추가된 위젯들이 패널 상단으로 바짝 밀착되게(위로 정렬) 만들어줍니다.
        """
        self.scroll_layout.addStretch()             

    def on_clicked_open_btn(self):
        pass

    def on_clicked_close_btn(self):
        pass

    def on_clicked_hold_btn(self):
        pass

    def on_clicked_learn_btn(self):
        pass

    def set_ctrl_mode_value(self, int_value: int):

        if int_value == p_enum.ControlModeEnum.CLOSE.value or int_value == p_enum.ControlModeEnum.INTERLOCK_CLOSE.value:
            self.open_btn.set_icon_colors("#30000000")
            self.open_btn.set_icon("\ue835")
            self.close_btn.set_icon_colors("#3fb950")
            self.close_btn.set_icon("\ue5ca")
            self.hold_btn.set_icon_colors("#30000000")
            self.hold_btn.set_icon("\ue835")
            self.learn_btn.set_icon_colors("#30000000")
            self.learn_btn.set_icon("\ue835")
        elif int_value == p_enum.ControlModeEnum.OPEN.value or int_value == p_enum.ControlModeEnum.INTERLOCK_OPEN.value:
            self.open_btn.set_icon_colors("#3fb950")
            self.open_btn.set_icon("\ue5ca")
            self.close_btn.set_icon_colors("#30000000")
            self.close_btn.set_icon("\ue835")
            self.hold_btn.set_icon_colors("#30000000")
            self.hold_btn.set_icon("\ue835")
            self.learn_btn.set_icon_colors("#30000000")
            self.learn_btn.set_icon("\ue835")
        elif int_value == p_enum.ControlModeEnum.HOLD.value:
            self.open_btn.set_icon_colors("#30000000")
            self.open_btn.set_icon("\ue835")
            self.close_btn.set_icon_colors("#30000000")
            self.close_btn.set_icon("\ue835")
            self.hold_btn.set_icon_colors("#3fb950")
            self.hold_btn.set_icon("\ue5ca")
            self.learn_btn.set_icon_colors("#30000000")
            self.learn_btn.set_icon("\ue835")
        elif int_value == p_enum.ControlModeEnum.LEARN.value:
            self.open_btn.set_icon_colors("#30000000")
            self.open_btn.set_icon("\ue835")
            self.close_btn.set_icon_colors("#30000000")
            self.close_btn.set_icon("\ue835")
            self.hold_btn.set_icon_colors("#30000000")
            self.hold_btn.set_icon("\ue835")
            self.learn_btn.set_icon_colors("#3fb950")
            self.learn_btn.set_icon("\ue5ca")
        else:
            self.open_btn.set_icon_colors("#30000000")
            self.open_btn.set_icon("\ue835")
            self.close_btn.set_icon_colors("#30000000")
            self.close_btn.set_icon("\ue835")
            self.hold_btn.set_icon_colors("#30000000")
            self.hold_btn.set_icon("\ue835")
            self.learn_btn.set_icon_colors("#30000000")
            self.learn_btn.set_icon("\ue835")

        
