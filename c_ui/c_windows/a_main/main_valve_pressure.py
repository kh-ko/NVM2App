from b_core.b_datatype.param_enum import SensUnitEnum
from c_ui.b_control_packet.param.param_pres_ro_vcolor_widget import ParamPresReadOnlyVerticalColorWidget
from c_ui.b_control_packet.base.base_button import BaseButton
from xml.etree.ElementTree import TreeBuilder
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QDoubleSpinBox, QSizePolicy, QFrame, QVBoxLayout, QWidget, QHBoxLayout, QComboBox

from b_core.b_datatype.general_enum import PositionUnitEnum
from b_core.c_manager.local_setting_manager import LocalSettingManager

from c_ui.a_converter.pressure_converter_manager import PresConverterManager

from c_ui.b_control_packet.base import my_style
from c_ui.b_control_packet.layout.my_card_widget import MyCardWidget
from c_ui.b_control_packet.controls.my_buttonedit import MyButtonEdit
from c_ui.b_control_packet.param.param_pres_rw_vspin_widget import ParamPresReadWriteVerticalSpinWidget
from c_ui.b_control_packet.param.param_pres_ro_vcolor_widget import ParamPresReadOnlyVerticalColorWidget
from c_ui.b_control_packet.controls_with_label.l_enum_rw_v_widget import LEnumReadWriteVerticalWidget

class MainValvePressure(MyCardWidget):
    sig_btn_clicked = Signal(str)
    def __init__(self, parent=None): # title의 기본값을 빈 문자열로 설정
        super().__init__(title = "Pressure", is_big_title=True, parent=parent)

        self.converter = PresConverterManager()  
        self.local_manager = LocalSettingManager()

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
        
        self.pres_input = ParamPresReadWriteVerticalSpinWidget(label_text = "Target", param_full_path="Pressure Control.Basic.Target.Target Pressure", enable_wrap_border=True, is_only_enter_finished = True)        
        right_layout.addWidget(self.pres_input)

        self.btn_01 = BaseButton("")
        self.btn_01.setMinimumWidth(1)
        self.btn_01.clicked.connect(self.on_btn_01_clicked)
        right_layout.addWidget(self.btn_01)

        self.btn_02 = BaseButton("")
        self.btn_02.setMinimumWidth(1)
        self.btn_02.clicked.connect(self.on_btn_02_clicked)
        right_layout.addWidget(self.btn_02)

        self.btn_03 = BaseButton("")
        self.btn_03.setMinimumWidth(1)
        self.btn_03.clicked.connect(self.on_btn_03_clicked)
        right_layout.addWidget(self.btn_03)

        self.btn_04 = BaseButton("")
        self.btn_04.setMinimumWidth(1)
        self.btn_04.clicked.connect(self.on_btn_04_clicked)
        right_layout.addWidget(self.btn_04)

        self.btn_05 = BaseButton("")
        self.btn_05.setMinimumWidth(1)
        self.btn_05.clicked.connect(self.on_btn_05_clicked)
        right_layout.addWidget(self.btn_05)

        self.btn_06 = BaseButton("")
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
        
        self.status_actual = ParamPresReadOnlyVerticalColorWidget(label_text = "Actual", param_full_path = "Pressure Control.Basic.Actual Pressure", label_color=my_style.STYLE_PRES_BOX_LABEL_COLOR, bg_color=my_style.STYLE_PRES_BOX_BG_COLOR)
        self.status_target = ParamPresReadOnlyVerticalColorWidget(label_text = "Target Used", param_full_path = "Pressure Control.Basic.Target Pressure Used", label_color=my_style.STYLE_PRES_BOX_LABEL_COLOR, bg_color=my_style.STYLE_PRES_BOX_BG_COLOR)
        self.combo_unit = LEnumReadWriteVerticalWidget(label_text="Unit",enum_class =SensUnitEnum)
        self.combo_unit.set_value(self.local_manager.pres_unit)
        self.combo_unit.sig_value_changed.connect(self.on_pres_unit_changed)
        self.combo_unit.commit()
        
        left_layout.addWidget(self.status_actual)
        left_layout.addWidget(self.status_target)
        left_layout.addWidget(self.combo_unit)
        left_layout.addStretch()

        content_layout.addWidget(left_container, 8)  
        content_layout.addWidget(right_container, 10) 
        self.content_layout.addLayout(content_layout)         

        self.converter.sig_pres_range_changed.connect(self.handle_pres_range_changed)
        self.local_manager.sig_pres_setpoint01_changed.connect(self.handle_pres_setpoint01_changed)
        self.local_manager.sig_pres_setpoint02_changed.connect(self.handle_pres_setpoint02_changed)
        self.local_manager.sig_pres_setpoint03_changed.connect(self.handle_pres_setpoint03_changed)
        self.local_manager.sig_pres_setpoint04_changed.connect(self.handle_pres_setpoint04_changed)
        self.local_manager.sig_pres_setpoint05_changed.connect(self.handle_pres_setpoint05_changed)
        self.local_manager.sig_pres_setpoint06_changed.connect(self.handle_pres_setpoint06_changed)

        self.handle_pres_range_changed()
        self.handle_pres_setpoint01_changed()
        self.handle_pres_setpoint02_changed()
        self.handle_pres_setpoint03_changed()
        self.handle_pres_setpoint04_changed()
        self.handle_pres_setpoint05_changed()
        self.handle_pres_setpoint06_changed()
        
    def handle_pres_setpoint01_changed(self):
        display_value = self.converter.convert_sfs_to_dp_pres_str(self.local_manager.pres_setpoint01)
        if display_value:
            self.btn_01.setText(display_value)   
            self.btn_01.setEnabled(True)
        else:
            self.btn_01.setText("Unknown (None)")
            self.btn_01.setEnabled(False)

    def handle_pres_setpoint02_changed(self):
        display_value = self.converter.convert_sfs_to_dp_pres_str(self.local_manager.pres_setpoint02)
        if display_value:
            self.btn_02.setText(display_value)   
            self.btn_02.setEnabled(True)
        else:
            self.btn_02.setText("Unknown (None)")
            self.btn_02.setEnabled(False)  

    def handle_pres_setpoint03_changed(self):
        display_value = self.converter.convert_sfs_to_dp_pres_str(self.local_manager.pres_setpoint03)
        if display_value:
            self.btn_03.setText(display_value)   
            self.btn_03.setEnabled(True)
        else:
            self.btn_03.setText("Unknown (None)")
            self.btn_03.setEnabled(False)  

    def handle_pres_setpoint04_changed(self):
        display_value = self.converter.convert_sfs_to_dp_pres_str(self.local_manager.pres_setpoint04)
        if display_value:
            self.btn_04.setText(display_value)   
            self.btn_04.setEnabled(True)
        else:
            self.btn_04.setText("Unknown (None)")
            self.btn_04.setEnabled(False)  

    def handle_pres_setpoint05_changed(self):
        display_value = self.converter.convert_sfs_to_dp_pres_str(self.local_manager.pres_setpoint05)
        if display_value:
            self.btn_05.setText(display_value)   
            self.btn_05.setEnabled(True)
        else:
            self.btn_05.setText("Unknown (None)")
            self.btn_05.setEnabled(False)  

    def handle_pres_setpoint06_changed(self):
        display_value = self.converter.convert_sfs_to_dp_pres_str(self.local_manager.pres_setpoint06)
        if display_value:
            self.btn_06.setText(display_value)   
            self.btn_06.setEnabled(True)
        else:
            self.btn_06.setText("Unknown (None)")
            self.btn_06.setEnabled(False)  

    def handle_pres_range_changed(self):
        self.handle_pres_setpoint01_changed()
        self.handle_pres_setpoint02_changed()
        self.handle_pres_setpoint03_changed()
        self.handle_pres_setpoint04_changed()
        self.handle_pres_setpoint05_changed()
        self.handle_pres_setpoint06_changed()  

    def on_pres_unit_changed(self):
        selected_unit = self.combo_unit.get_value()
        self.combo_unit.commit()
        if selected_unit:
            LocalSettingManager().pres_unit = selected_unit

    def on_btn_01_clicked(self):
        btn_value = float(self.btn_01.text())
        pres_value = self.converter.convert_dp_pres_to_iface_pres_str(btn_value)
        self.sig_btn_clicked.emit(pres_value)       

    def on_btn_02_clicked(self):
        btn_value = float(self.btn_02.text())
        pres_value = self.converter.convert_dp_pres_to_iface_pres_str(btn_value)
        self.sig_btn_clicked.emit(pres_value) 

    def on_btn_03_clicked(self):
        btn_value = float(self.btn_03.text())
        pres_value = self.converter.convert_dp_pres_to_iface_pres_str(btn_value)
        self.sig_btn_clicked.emit(pres_value) 

    def on_btn_04_clicked(self):
        btn_value = float(self.btn_04.text())
        pres_value = self.converter.convert_dp_pres_to_iface_pres_str(btn_value)
        self.sig_btn_clicked.emit(pres_value) 

    def on_btn_05_clicked(self):
        btn_value = float(self.btn_05.text())
        pres_value = self.converter.convert_dp_pres_to_iface_pres_str(btn_value)
        self.sig_btn_clicked.emit(pres_value) 

    def on_btn_06_clicked(self):
        btn_value = float(self.btn_06.text())
        pres_value = self.converter.convert_dp_pres_to_iface_pres_str(btn_value)
        self.sig_btn_clicked.emit(pres_value) 
        

