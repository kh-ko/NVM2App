from xml.etree.ElementTree import TreeBuilder
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QDoubleSpinBox, QSizePolicy, QFrame, QVBoxLayout, QWidget, QHBoxLayout, QComboBox

from b_core.b_datatype.general_enum import PositionUnitEnum
from b_core.c_manager.local_setting_manager import LocalSettingManager

from c_ui.a_converter.position_converter_manager import PosiConverterManager

from c_ui.b_control_packet.base import my_style
from c_ui.b_control_packet.layout.my_card_widget import MyCardWidget
from c_ui.b_control_packet.controls.my_buttonedit import MyButtonEdit
from c_ui.b_control_packet.param.param_posi_rw_vspin_widget import ParamFloatReadWriteVerticalSpinWidget
from c_ui.b_control_packet.param.param_posi_ro_vcolor_widget import ParamPosiReadOnlyVerticalColorWidget
from c_ui.b_control_packet.controls_with_label.l_enum_rw_v_widget import LEnumReadWriteVerticalWidget

class MainValvePosition(MyCardWidget):
    sig_btn_clicked = Signal(str)
    def __init__(self, parent=None): # title의 기본값을 빈 문자열로 설정
        super().__init__(title = "Control", is_big_title=True, parent=parent)

        self.btn_edit = MyButtonEdit(text="Edit", is_without_bolder=True)
        self.btn_edit.setMinimumWidth(50)
        self.btn_edit.setMaximumWidth(50)
        self.btn_edit.setMaximumHeight(18)
        self.title_layout.addWidget(self.btn_edit)

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
        
        self.posi_input = ParamFloatReadWriteVerticalSpinWidget(label_text = "Target", param_full_path="Position Control.Basic.Target Position", enable_wrap_border=True, is_only_enter_finished = True)
        #self.posi_input.setRange(-100.0, 100.0)
        #self.posi_input.setAlignment(Qt.AlignRight)
        #self.posi_input.setMinimumWidth(1) 
        #self.posi_input.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.Fixed)        
        
        right_layout.addWidget(self.posi_input)

        #self.btn_01 = CustomButton("100")
        #self.btn_01.setMinimumWidth(1)
        #self.btn_01.clicked.connect(self.on_btn_01_clicked)
        #right_layout.addWidget(self.btn_01)

        #self.btn_02 = CustomButton("100")
        #self.btn_02.setMinimumWidth(1)
        #self.btn_02.clicked.connect(self.on_btn_02_clicked)
        #right_layout.addWidget(self.btn_02)

        #self.btn_03 = CustomButton("100")
        #self.btn_03.setMinimumWidth(1)
        #self.btn_03.clicked.connect(self.on_btn_03_clicked)
        #right_layout.addWidget(self.btn_03)

        #self.btn_04 = CustomButton("100")
        #self.btn_04.setMinimumWidth(1)
        #self.btn_04.clicked.connect(self.on_btn_04_clicked)
        #right_layout.addWidget(self.btn_04)

        #self.btn_05 = CustomButton("100")
        #self.btn_05.setMinimumWidth(1)
        #self.btn_05.clicked.connect(self.on_btn_05_clicked)
        #right_layout.addWidget(self.btn_05)

        #self.btn_06 = CustomButton("100")
        #self.btn_06.setMinimumWidth(1)
        #self.btn_06.clicked.connect(self.on_btn_06_clicked)
        #right_layout.addWidget(self.btn_06)
            
        #right_layout.addStretch()
        
        left_container = QWidget()
        left_container.setStyleSheet("background-color: transparent;")
        left_container.setMinimumWidth(1) # 핵심 3: 최소 폭을 1로 강제
        
        left_layout = QVBoxLayout(left_container)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(10)
        
        self.status_actual = ParamPosiReadOnlyVerticalColorWidget(label_text = "Actual", param_full_path = "Position Control.Basic.Actual Position", label_color=my_style.STYLE_POSI_BOX_LABEL_COLOR, bg_color=my_style.STYLE_POSI_BOX_BG_COLOR)
        self.status_target = ParamPosiReadOnlyVerticalColorWidget(label_text = "Target Used", param_full_path = "Position Control.Basic.Target Position Used", label_color=my_style.STYLE_POSI_BOX_LABEL_COLOR, bg_color=my_style.STYLE_POSI_BOX_BG_COLOR)
        self.combo_unit = LEnumReadWriteVerticalWidget(label_text="Unit",enum_class =PositionUnitEnum)
        self.combo_unit.set_value(PositionUnitEnum.POSI_UNIT_PERCENT.value)
        self.combo_unit.commit()
        self.combo_unit.setEnabled(False)
        
        left_layout.addWidget(self.status_actual)
        left_layout.addWidget(self.status_target)
        left_layout.addWidget(self.combo_unit)
        left_layout.addStretch()

        #unit_layout = QVBoxLayout()
        #unit_layout.setSpacing(0)
        
        #lbl_unit = CustomLabel("Unit")
        
        #self.combo_unit = QComboBox()
        #self.combo_unit.setEnabled(False)
        #self.combo_unit.addItems([
        #    "Percent(%)"
        #])

        #unit_layout.addWidget(lbl_unit)
        #unit_layout.addWidget(self.combo_unit)
        
        #left_layout.addLayout(unit_layout)

        #left_layout.addStretch()

        content_layout.addWidget(left_container, 8)  
        content_layout.addWidget(right_container, 10) 
        self.content_layout.addLayout(content_layout)
        #self.main_layout.addLayout(content_layout)
        #self.main_layout.addStretch()


        self.converter = PosiConverterManager()   

        self.converter.sig_posi_range_changed.connect(self.handle_posi_range_changed)
        LocalSettingManager().sig_posi_setpoint01_changed.connect(self.handle_posi_setpoint01_changed)
        LocalSettingManager().sig_posi_setpoint02_changed.connect(self.handle_posi_setpoint02_changed)
        LocalSettingManager().sig_posi_setpoint03_changed.connect(self.handle_posi_setpoint03_changed)
        LocalSettingManager().sig_posi_setpoint04_changed.connect(self.handle_posi_setpoint04_changed)
        LocalSettingManager().sig_posi_setpoint05_changed.connect(self.handle_posi_setpoint05_changed)
        LocalSettingManager().sig_posi_setpoint06_changed.connect(self.handle_posi_setpoint06_changed)

        self.handle_posi_range_changed()
        self.handle_posi_setpoint01_changed()
        self.handle_posi_setpoint02_changed()
        self.handle_posi_setpoint03_changed()
        self.handle_posi_setpoint04_changed()
        self.handle_posi_setpoint05_changed()
        self.handle_posi_setpoint06_changed()
        
    def handle_posi_setpoint01_changed(self):
        display_value = self.converter.convert_pfs_to_dp_posi_str(LocalSettingManager().posi_setpoint01)
        #self.btn_01.setText(display_value)   

    def handle_posi_setpoint02_changed(self):
        display_value = self.converter.convert_pfs_to_dp_posi_str(LocalSettingManager().posi_setpoint02)
        #self.btn_02.setText(display_value)  

    def handle_posi_setpoint03_changed(self):
        display_value = self.converter.convert_pfs_to_dp_posi_str(LocalSettingManager().posi_setpoint03)
        #self.btn_03.setText(display_value)

    def handle_posi_setpoint04_changed(self):
        display_value = self.converter.convert_pfs_to_dp_posi_str(LocalSettingManager().posi_setpoint04)
        #self.btn_04.setText(display_value)

    def handle_posi_setpoint05_changed(self):
        display_value = self.converter.convert_pfs_to_dp_posi_str(LocalSettingManager().posi_setpoint05)
        #self.btn_05.setText(display_value)

    def handle_posi_setpoint06_changed(self):
        display_value = self.converter.convert_pfs_to_dp_posi_str(LocalSettingManager().posi_setpoint06)
        #self.btn_06.setText(display_value) 

    def handle_posi_range_changed(self):
        self.handle_posi_setpoint01_changed()
        self.handle_posi_setpoint02_changed()
        self.handle_posi_setpoint03_changed()
        self.handle_posi_setpoint04_changed()
        self.handle_posi_setpoint05_changed()
        self.handle_posi_setpoint06_changed()  

    def on_btn_01_clicked(self):
        posi_value = self.converter.convert_display_to_posi_value_str(LocalSettingManager().posi_setpoint01 * 100)
        self.sig_btn_clicked.emit(posi_value)       

    def on_btn_02_clicked(self):
        posi_value = self.converter.convert_display_to_posi_value_str(LocalSettingManager().posi_setpoint02 * 100)
        self.sig_btn_clicked.emit(posi_value) 

    def on_btn_03_clicked(self):
        posi_value = self.converter.convert_display_to_posi_value_str(LocalSettingManager().posi_setpoint03 * 100)
        self.sig_btn_clicked.emit(posi_value) 

    def on_btn_04_clicked(self):
        posi_value = self.converter.convert_display_to_posi_value_str(LocalSettingManager().posi_setpoint04 * 100)
        self.sig_btn_clicked.emit(posi_value) 

    def on_btn_05_clicked(self):
        posi_value = self.converter.convert_display_to_posi_value_str(LocalSettingManager().posi_setpoint05 * 100)
        self.sig_btn_clicked.emit(posi_value) 

    def on_btn_06_clicked(self):
        posi_value = self.converter.convert_display_to_posi_value_str(LocalSettingManager().posi_setpoint06 * 100)
        self.sig_btn_clicked.emit(posi_value) 
        

