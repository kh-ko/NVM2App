from c_ui.b_control_packet.controls_with_label.l_float_rw_vspin_widget import LFloatReadWriteVerticalSpinWidget
from b_core.b_datatype.param_enum import AccModeEnum
from b_core.b_datatype.param_enum import ClusterUnfreezeFreezeEnum
from c_ui.b_control_packet.controls.my_buttoncheck import MyButtonCheck
from PySide6.QtWidgets import QHBoxLayout
from c_ui.b_control_packet.base.base_groupbox import BaseGroupBox
from c_ui.b_control_packet.controls_with_label.l_base_v_widget import LBaseVerticalWidget
from c_ui.b_control_packet.controls_with_label.l_enum_ro_widget import LEnumReadOnlyWidget
from c_ui.a_converter.float_converter_manager import FloatConverterManager
from PySide6.QtCore import Signal
from c_ui.a_converter.position_converter_manager import PosiConverterManager
from c_ui.b_control_packet.controls_with_label.l_float_rw_widget import LFloatReadWriteWidget
from c_ui.b_control_packet.controls.my_value_button import MyValueButton
from c_ui.b_control_packet.controls_with_label.l_button_widget import LButtonWidget
from c_ui.b_control_packet.controls_with_label.l_float_ro_widget import LFloatReadOnlyWidget
from c_ui.b_control_packet.controls_with_label.l_enum_rw_widget import LEnumReadWriteWidget
from b_core.c_manager.parameter_manager import ParamManager
from c_ui.b_control_packet.param_container.param_folder_widget import ParamFolderWidget

class ParamFolderClusterMonitorControlWidget(ParamFolderWidget):
    sig_unfreeze_clicked = Signal()
    sig_freeze_clicked = Signal()
    sig_target_posi_edit_finished = Signal()
    sig_open_clicked = Signal()
    sig_close_clicked = Signal()
    sig_restart_clicked = Signal()
    
    def __init__(self, parent=None):
        super().__init__(folder_name="Control [N/A]", param_path=None, label_width = 210, parent=parent)
        self.converter = PosiConverterManager()
        self.opt_param = None
        self.freeze_param = None
        self.ctrl_setpoint_param = None
        self.target_posi_param = None
        self.restart_param = None


        # Freeze Box
        group_box = BaseGroupBox(text="Freeze Mode", enable_border = False)
        layout = QHBoxLayout(group_box)
        layout.setContentsMargins(0, 5, 0, 0) 
        layout.setSpacing(5)

        self.btn_no_freeze = MyButtonCheck("No Freeze")
        layout.addWidget(self.btn_no_freeze)
        self.btn_no_freeze.clicked.connect(self.on_unfreeze_clicked)
        self.btn_freeze = MyButtonCheck("Freeze")
        layout.addWidget(self.btn_freeze)
        self.btn_freeze.clicked.connect(self.on_freeze_clicked)
        
        self.add_widget(group_box)

        self.target_posi = LFloatReadWriteVerticalSpinWidget(label_text="Target Position", parent = None, enable_wrap_border = False, is_only_enter_finished = True)
        self.target_posi.set_range(-130.0, 130.0)
        self.add_widget(self.target_posi)
        self.target_posi.sig_value_changed.connect(self.on_target_posi_edit_finished)

        self.btn_open = MyValueButton("Open")
        self.add_widget(self.btn_open)
        self.btn_open.clicked.connect(self.on_open_clicked)
        self.btn_close = MyValueButton("Close")
        self.add_widget(self.btn_close)
        self.btn_close.clicked.connect(self.on_close_clicked)
        self.btn_restart = MyValueButton("Restart Controller")
        self.add_widget(self.btn_restart)
        self.btn_restart.clicked.connect(self.on_restart_clicked)

        self.setEnabled(False)

        self.converter.sig_posi_range_changed.connect(self.handle_range_changed)
        self.handle_range_changed()

    def _clear_signal_connections(self):
        if self.freeze_param is not None:
            self.freeze_param.sig_value_changed.disconnect(self.handle_changed_freeze)

    def set_addr(self, addr):
        self._clear_signal_connections()
        
        if addr is None:
            self.lbl_title.setText("Control [N/A]")
            self.setEnabled(False)
            self.btn_no_freeze.set_check(False)
            self.btn_freeze.set_check(False)
            self.target_posi.set_value(0)
            self.target_posi.commit()
        else:
            self.lbl_title.setText(f"Control [{addr}]")
            self.setEnabled(True)
            self.set_param(addr)

    def set_param(self, addr):
        self.freeze_param = ParamManager().get_by_full_path(f"Cluster.Device {addr}.Control.Freeze")     
        self.target_posi_param = ParamManager().get_by_full_path(f"Cluster.Device {addr}.Control.Target Position")
        self.ctrl_setpoint_param = ParamManager().get_by_full_path(f"Cluster.Device {addr}.Control.Control Mode Setpoint")                   
        self.restart_param = ParamManager().get_by_full_path(f"Cluster.Device {addr}.Control.Restart Controller")

        self.freeze_param.sig_value_changed.connect(self.handle_changed_freeze)

        self.handle_changed_freeze()

    def handle_range_changed(self):
        decimals = self.converter.posi_decimal_places
        self.target_posi.set_decimal_places(decimals)

    def handle_changed_freeze(self):
        if self.freeze_param.value is not None and self.freeze_param.value == ClusterUnfreezeFreezeEnum.FREEZE.value:
            self.btn_no_freeze.set_check(False)
            self.btn_freeze.set_check(True)
        else:
            self.btn_no_freeze.set_check(True)
            self.btn_freeze.set_check(False)

    def on_unfreeze_clicked(self):
        self.sig_unfreeze_clicked.emit()

    def on_freeze_clicked(self):
        self.sig_freeze_clicked.emit()

    def on_target_posi_edit_finished(self):
        self.sig_target_posi_edit_finished.emit()

    def on_open_clicked(self):
        self.sig_open_clicked.emit()

    def on_close_clicked(self):
        self.sig_close_clicked.emit()

    def on_restart_clicked(self):
        self.sig_restart_clicked.emit()

    def get_target_posi_write_value(self):
        value = self.target_posi.get_value()
        if value is None:
            return ""
        else:
            value = int(value * 1000)
            return f"{self.target_posi_param.nv1_write_req}{value:0{self.target_posi_param.len}d}"