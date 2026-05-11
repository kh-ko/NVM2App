from c_ui.b_components.a_custom.custom_icon_label_button import CustomIconLabelButton
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QDoubleSpinBox, QSizePolicy, QFrame, QVBoxLayout, QWidget, QHBoxLayout, QComboBox

from b_core.c_manager.local_setting_manager import LocalSettingManager

from c_ui.a_converter.position_converter_manager import PosiConverterManager

from c_ui.b_components.a_custom.custom_label import CustomLabel
from c_ui.b_components.a_custom.custom_button import CustomButton
from c_ui.b_components.a_custom.custom_title import CustomTitle

from c_ui.b_components.b_usercontrol.b_main_win_controls.posi_label_in_main import PosiLabelInMain
from c_ui.b_components.b_usercontrol.b_main_win_controls.posi_input_in_main import PosiInputInMain

class MainPosition(QWidget):
    sig_btn_clicked = Signal(str)
    
    def __init__(self, parent=None): # title의 기본값을 빈 문자열로 설정
        super().__init__(parent)
        self.setObjectName("MainPosition")

        self.setAttribute(Qt.WA_StyledBackground, True)

        self.setStyleSheet("""
            QWidget#MainPosition {
                background-color: white;
                border: 1px solid #dcdcdc;
            }
        """)

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(10, 10, 10, 10) # 카드 내부 여백
        self.main_layout.setSpacing(5) # 내부 위젯들 간의 기본 간격

        self.title_layout = QHBoxLayout()
        self.title_layout.setContentsMargins(0, 0, 0, 0)
        
        lbl_title = CustomTitle("Position")
        # 패널의 기본 스타일이 상속되어 테두리가 생길 수 있으므로 border: none 추가
        self.title_layout.addWidget(lbl_title)

        self.title_layout.addStretch()

        self.btn_edit = CustomIconLabelButton("Edit", "\ue8b8")
        self.btn_edit.setMinimumWidth(50)
        self.btn_edit.setMaximumHeight(18)
        self.title_layout.addWidget(self.btn_edit)

        self.main_layout.addLayout(self.title_layout)

        line = QFrame()
        line.setFixedHeight(1) # 선의 두께를 명시적으로 1px로 지정
        # 스타일시트로 배경색 지정 및 위아래 여백 설정
        line.setStyleSheet("background-color: #dcdcdc; border: none; margin-top: 5px; margin-bottom: 5px;")
        self.main_layout.addWidget(line)

        content_layout = QHBoxLayout()
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(15)
        
        # ✨ 레이아웃 대신 컨테이너 위젯을 생성합니다.
        right_container = QWidget()
        right_container.setStyleSheet("background-color: transparent;")
        right_container.setMinimumWidth(1) # 핵심 1: 최소 폭을 1로 만들어버림
        
        right_layout = QVBoxLayout(right_container)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(5)
        
        self.posi_input = PosiInputInMain("Target", param_full_path="Position Control.Basic.Target Position")
        self.posi_input.setDecimals(2)
        self.posi_input.setRange(-100.0, 100.0)
        self.posi_input.setAlignment(Qt.AlignRight)
        self.posi_input.setMinimumWidth(1) 
        self.posi_input.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.Fixed)        
        
        right_layout.addWidget(self.posi_input)

        self.btn_01 = CustomButton("100")
        self.btn_01.setMinimumWidth(1)
        self.btn_01.clicked.connect(self.on_btn_01_clicked)
        right_layout.addWidget(self.btn_01)

        self.btn_02 = CustomButton("100")
        self.btn_02.setMinimumWidth(1)
        self.btn_02.clicked.connect(self.on_btn_02_clicked)
        right_layout.addWidget(self.btn_02)

        self.btn_03 = CustomButton("100")
        self.btn_03.setMinimumWidth(1)
        self.btn_03.clicked.connect(self.on_btn_03_clicked)
        right_layout.addWidget(self.btn_03)

        self.btn_04 = CustomButton("100")
        self.btn_04.setMinimumWidth(1)
        self.btn_04.clicked.connect(self.on_btn_04_clicked)
        right_layout.addWidget(self.btn_04)

        self.btn_05 = CustomButton("100")
        self.btn_05.setMinimumWidth(1)
        self.btn_05.clicked.connect(self.on_btn_05_clicked)
        right_layout.addWidget(self.btn_05)

        self.btn_06 = CustomButton("100")
        self.btn_06.setMinimumWidth(1)
        self.btn_06.clicked.connect(self.on_btn_06_clicked)
        right_layout.addWidget(self.btn_06)
            
        right_layout.addStretch()
        
        left_container = QWidget()
        left_container.setStyleSheet("background-color: transparent;")
        left_container.setMinimumWidth(1) # 핵심 3: 최소 폭을 1로 강제
        
        left_layout = QVBoxLayout(left_container)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(10)
        
        self.status_actual = PosiLabelInMain("Actual", "Position Control.Basic.Actual Position")
        self.status_target = PosiLabelInMain("Target Used", "Position Control.Basic.Target Position Used")
        #self.status_max = UserPosiLabelInMain("Max", "Position Control.Basic.Position Max")
        
        left_layout.addWidget(self.status_actual)
        left_layout.addWidget(self.status_target)
        #left_layout.addWidget(self.status_max)
        
        unit_layout = QVBoxLayout()
        unit_layout.setSpacing(0)
        
        lbl_unit = CustomLabel("Unit")
        
        self.combo_unit = QComboBox()
        self.combo_unit.setEnabled(False)
        self.combo_unit.addItems([
            "Percent(%)"
        ])

        self.converter = PosiConverterManager()   
        
        LocalSettingManager().sig_posi_setpoint01_changed.connect(self.handle_posi_setpoint01_changed)
        LocalSettingManager().sig_posi_setpoint02_changed.connect(self.handle_posi_setpoint02_changed)
        LocalSettingManager().sig_posi_setpoint03_changed.connect(self.handle_posi_setpoint03_changed)
        LocalSettingManager().sig_posi_setpoint04_changed.connect(self.handle_posi_setpoint04_changed)
        LocalSettingManager().sig_posi_setpoint05_changed.connect(self.handle_posi_setpoint05_changed)
        LocalSettingManager().sig_posi_setpoint06_changed.connect(self.handle_posi_setpoint06_changed)

        self.handle_posi_setpoint01_changed()
        self.handle_posi_setpoint02_changed()
        self.handle_posi_setpoint03_changed()
        self.handle_posi_setpoint04_changed()
        self.handle_posi_setpoint05_changed()
        self.handle_posi_setpoint06_changed()

        self.converter.sig_posi_range_changed.connect(self.handle_posi_range_changed)   
        
        # 기존 스핀박스/라벨과 디자인 톤을 맞추기 위한 스타일 적용
        self.combo_unit.setStyleSheet("""
            /* 콤보박스 기본 디자인 */
            QComboBox {
                color: black;
                border: 1px solid #dcdcdc;
                border-radius: 4px;
                padding: 4px 8px;
                background-color: white;
                min-height: 24px;
            }
            
            /* 콤보박스에 마우스를 올렸을 때 */
            QComboBox:hover {
                border: 1px solid #1976d2;
            }

            QComboBox:disabled {
                /* rgba(R, G, B, Alpha) 형태로 작성하며, Alpha 값 127이 약 50% 투명도입니다. */
                color: rgba(0, 0, 0, 127);                 /* 검은색 글자 투명도 50% */
                border: 1px solid rgba(220, 220, 220, 127);/* #dcdcdc 테두리 투명도 50% */
                background-color: rgba(255, 255, 255, 127);/* 하얀색 배경 투명도 50% */
            }
            
            /* 콤보박스 우측 화살표 영역 */
            QComboBox::drop-down {
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 20px;
                border-left: 1px solid #dcdcdc;
            }

            /* ★ 콤보박스 드롭다운 팝업 리스트 스타일 (테두리 추가) ★ */
            QComboBox QAbstractItemView {
                border: 1px solid #a0a0a0; /* 팝업창 테두리 추가 */
                border-radius: 4px;
                background-color: white;
                outline: 0px; /* 클릭 시 생기는 점선 테두리 제거 */
                selection-background-color: #e3f2fd; /* 선택 항목 배경색 */
                selection-color: #1976d2;            /* 선택 항목 글자색 */
            }
        """)

        unit_layout.addWidget(lbl_unit)
        unit_layout.addWidget(self.combo_unit)
        
        left_layout.addLayout(unit_layout)

        left_layout.addStretch()
        
        content_layout.addWidget(left_container, 8)  
        content_layout.addWidget(right_container, 10) 
        self.main_layout.addLayout(content_layout)
        self.main_layout.addStretch()

    def handle_posi_setpoint01_changed(self):
        setpoint_ratio = LocalSettingManager().posi_setpoint01
        display_value = setpoint_ratio * 100
        self.btn_01.setText(f"{display_value:.2f}")   

    def handle_posi_setpoint02_changed(self):
        setpoint_ratio = LocalSettingManager().posi_setpoint02
        display_value = setpoint_ratio * 100
        self.btn_02.setText(f"{display_value:.2f}")  

    def handle_posi_setpoint03_changed(self):
        setpoint_ratio = LocalSettingManager().posi_setpoint03
        display_value = setpoint_ratio * 100
        self.btn_03.setText(f"{display_value:.2f}")

    def handle_posi_setpoint04_changed(self):
        setpoint_ratio = LocalSettingManager().posi_setpoint04
        display_value = setpoint_ratio * 100
        self.btn_04.setText(f"{display_value:.2f}")

    def handle_posi_setpoint05_changed(self):
        setpoint_ratio = LocalSettingManager().posi_setpoint05
        display_value = setpoint_ratio * 100
        self.btn_05.setText(f"{display_value:.2f}")

    def handle_posi_setpoint06_changed(self):
        setpoint_ratio = LocalSettingManager().posi_setpoint06
        display_value = setpoint_ratio * 100
        self.btn_06.setText(f"{display_value:.2f}") 

    def handle_posi_range_changed(self):
        self.handle_posi_setpoint01_changed()
        self.handle_posi_setpoint02_changed()
        self.handle_posi_setpoint03_changed()
        self.handle_posi_setpoint04_changed()
        self.handle_posi_setpoint05_changed()
        self.handle_posi_setpoint06_changed()  

    def on_btn_01_clicked(self):
        setpoint_ratio = LocalSettingManager().posi_setpoint01
        display_value = 100 * setpoint_ratio
        posi_value = self.converter.convert_display_to_posi_value_str(display_value)
        self.sig_btn_clicked.emit(posi_value)       

    def on_btn_02_clicked(self):
        setpoint_ratio = LocalSettingManager().posi_setpoint02
        display_value = 100 * setpoint_ratio
        posi_value = self.converter.convert_display_to_posi_value_str(display_value)
        self.sig_btn_clicked.emit(posi_value) 

    def on_btn_03_clicked(self):
        setpoint_ratio = LocalSettingManager().posi_setpoint03
        display_value = 100 * setpoint_ratio
        posi_value = self.converter.convert_display_to_posi_value_str(display_value)
        self.sig_btn_clicked.emit(posi_value) 

    def on_btn_04_clicked(self):
        setpoint_ratio = LocalSettingManager().posi_setpoint04
        display_value = 100 * setpoint_ratio
        posi_value = self.converter.convert_display_to_posi_value_str(display_value)
        self.sig_btn_clicked.emit(posi_value) 

    def on_btn_05_clicked(self):
        setpoint_ratio = LocalSettingManager().posi_setpoint05
        display_value = 100 * setpoint_ratio
        posi_value = self.converter.convert_display_to_posi_value_str(display_value)
        self.sig_btn_clicked.emit(posi_value) 

    def on_btn_06_clicked(self):
        setpoint_ratio = LocalSettingManager().posi_setpoint06
        display_value = 100 * setpoint_ratio
        posi_value = self.converter.convert_display_to_posi_value_str(display_value)
        self.sig_btn_clicked.emit(posi_value) 
        

