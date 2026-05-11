from typing import List, Tuple

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel, QFrame, QPushButton, QScrollArea

from b_core.c_manager.parameter_manager import ParamManager

from c_ui.b_components.a_custom.custom_title import CustomTitle
from c_ui.b_components.a_custom.custom_icon_label_button import CustomIconLabelButton
from c_ui.b_components.b_usercontrol.a_param_controls.param_enum_label_widget import ParamEnumLabelWidget
from c_ui.b_components.b_usercontrol.a_param_controls.param_float_label_widget import ParamFloatLabelWidget

class MainStatus(QWidget):
    def __init__(self, control_mode_param:str, posi_ctrl_speed_param:str, controller_select_param:str, warn_bitmap_param:str, err_bitmap_param:str,parent=None): # title의 기본값을 빈 문자열로 설정
        super().__init__(parent)
        self.setObjectName("MainStatus")

        self.setAttribute(Qt.WA_StyledBackground, True)

        self.setStyleSheet("""
            QWidget#MainStatus {
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

        self.warn_list: List[Tuple[int, CustomIconLabelButton]] = []
        self.err_list: List[Tuple[int, CustomIconLabelButton]] = []

        control_mode_label = ParamEnumLabelWidget(control_mode_param, 180)
        self.add_widget(control_mode_label)

        posi_ctrl_speed_label = ParamFloatLabelWidget(posi_ctrl_speed_param, 180)
        self.add_widget(posi_ctrl_speed_label)
        
        controller_select_label = ParamEnumLabelWidget(controller_select_param, 180)
        self.add_widget(controller_select_label)

        self.warn_param = ParamManager().get_by_full_path(warn_bitmap_param)
        if self.warn_param and self.warn_param.ref_list:  
            self.warn_param.sig_value_changed.connect(self.handle_warn_bitmap_changed)

            for member in self.warn_param.ref_list:
                bit_pos = member.value
                description = member.description

                button = CustomIconLabelButton(description, "\ue002")
                button.set_icon_colors("#FFA000")
                button.set_text_color("#F57C00")
                button.setVisible(False)
                button.clicked.connect(self.on_clicked_warn_err_button)

                self.add_widget(button)
                self.warn_list.append((bit_pos, button))

        self.err_param = ParamManager().get_by_full_path(err_bitmap_param)
        if self.err_param and self.err_param.ref_list:  
            self.err_param.sig_value_changed.connect(self.handle_err_bitmap_changed)

            for member in self.err_param.ref_list:
                bit_pos = member.value
                description = member.description

                button = CustomIconLabelButton(description, "\ue002")
                button.set_icon_colors("#FF0000")
                button.set_text_color("#F57C00")
                button.setVisible(False)
                button.clicked.connect(self.on_clicked_warn_err_button)

                self.add_widget(button)
                self.err_list.append((bit_pos, button))     

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

    def on_clicked_warn_err_button(self):
        pass

    def handle_err_bitmap_changed(self):
        if not self.err_param.str_value:
            return

        for bit_pos, button in self.err_list:
            button.setVisible(bool(self.err_param.value & (1 << bit_pos)))

    def handle_warn_bitmap_changed(self):
        if not self.warn_param.str_value:
            return

        for bit_pos, button in self.warn_list:
            button.setVisible(bool(self.warn_param.value & (1 << bit_pos)))

        
