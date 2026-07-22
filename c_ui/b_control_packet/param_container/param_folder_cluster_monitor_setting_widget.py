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

class ParamFolderClusterMonitorSettingWidget(ParamFolderWidget):
    sig_apply_clicked = Signal()
    
    def __init__(self, parent=None):
        super().__init__(folder_name="Option Settings [N/A]", param_path=None, label_width = 210, parent=parent)

        self.converter = PosiConverterManager()
        self.posi_speed_param = None
        self.posi_offset_param = None
        self.homing_end_posi_param = None
        self.homing_start_cond_param = None
        self.homing_mode_param = None
        self.stroke_limitation_param = None
        self.power_failure_option_param = None
        self.network_failure_option_param = None

        self.homing_end_posi = LEnumReadWriteWidget([], "Homing End Position", 180)
        self.add_widget(self.homing_end_posi)

        self.homing_start_cond = LEnumReadWriteWidget([], "Homing Start Condition", 180)
        self.add_widget(self.homing_start_cond)

        self.homing_mode = LEnumReadWriteWidget([], "Homing Mode", 180)
        self.add_widget(self.homing_mode)

        self.stroke_limitation = LEnumReadWriteWidget([], "Control Stroke Limitation", 180)
        self.add_widget(self.stroke_limitation)

        self.power_failure_option = LEnumReadWriteWidget([], "Power Failure Option", 180)
        self.add_widget(self.power_failure_option)

        self.network_failure_option = LEnumReadWriteWidget([], "Network Failure Option", 180)
        self.add_widget(self.network_failure_option)

        self.posi_speed = LFloatReadWriteWidget("Position Control Speed (%)", 180)
        self.posi_speed.set_range(1, 100)
        self.add_widget(self.posi_speed)

        self.posi_offset = LFloatReadWriteWidget("Position Offset", 180)
        self.posi_offset.set_range(-130.0, 130.0)
        self.add_widget(self.posi_offset)

        self.btn_apply = MyValueButton("Apply")
        self.btn_apply.clicked.connect(self.on_apply_clicked)
        self.add_widget(self.btn_apply)

        self.setEnabled(False)

        self.converter.sig_posi_range_changed.connect(self.handle_range_changed)
        self.handle_range_changed()

    def _clear_signal_connections(self):
        if self.posi_speed_param is not None:
            self.posi_speed_param.sig_value_changed.disconnect(self.handle_changed_posi_speed)

        if self.posi_offset_param is not None:
            self.posi_offset_param.sig_value_changed.disconnect(self.handle_changed_posi_offset)

        if self.homing_end_posi_param is not None:
            self.homing_end_posi_param.sig_value_changed.disconnect(self.handle_changed_homing_end_posi)

        if self.homing_start_cond_param is not None:
            self.homing_start_cond_param.sig_value_changed.disconnect(self.handle_changed_homing_start_cond)

        if self.homing_mode_param is not None:
            self.homing_mode_param.sig_value_changed.disconnect(self.handle_changed_homing_mode)

        if self.stroke_limitation_param is not None:
            self.stroke_limitation_param.sig_value_changed.disconnect(self.handle_changed_stroke_limitation)

        if self.power_failure_option_param is not None:
            self.power_failure_option_param.sig_value_changed.disconnect(self.handle_changed_power_failure_option)

        if self.network_failure_option_param is not None:
            self.network_failure_option_param.sig_value_changed.disconnect(self.handle_changed_network_failure_option)

    def set_addr(self, addr):
        self._clear_signal_connections()
        
        if addr is None:
            self.lbl_title.setText("Option Settings [N/A]")
            self.setEnabled(False)
            self.btn_apply.setEnabled(False)
            self.homing_end_posi.set_value(None)
            self.homing_start_cond.set_value(None)
            self.homing_mode.set_value(None)
            self.stroke_limitation.set_value(None)
            self.power_failure_option.set_value(None)
            self.network_failure_option.set_value(None)
            self.posi_speed.set_value(None)
            self.posi_offset.set_value(None)
        else:
            self.lbl_title.setText(f"Option Settings [{addr}]")
            self.setEnabled(True)
            self.btn_apply.setEnabled(True)
            self.set_param(addr)

    def set_param(self, addr):
        self.posi_speed_param = ParamManager().get_by_full_path(f"Cluster.Device {addr}.Setting.Position Control Speed (%)")
        self.posi_speed_param.sig_value_changed.connect(self.handle_changed_posi_speed)
        self.handle_changed_posi_speed()

        self.posi_offset_param = ParamManager().get_by_full_path(f"Cluster.Device {addr}.Setting.Position Offset")
        self.posi_offset_param.sig_value_changed.connect(self.handle_changed_posi_offset)
        self.handle_changed_posi_offset()

        self.opt_param = ParamManager().get_by_full_path(f"Cluster.Device {addr}.Setting.Option")
        self.opt_param.sub_items

        for offset, data_len, param in self.opt_param.sub_items:
            if param.name == "End Position":
                self.homing_end_posi_param = param
                self.homing_end_posi.set_enum_class(self.homing_end_posi_param.ref_list)
                param.sig_value_changed.connect(self.handle_changed_homing_end_posi)
                self.handle_changed_homing_end_posi()
            elif param.name == "Start Condition":
                self.homing_start_cond_param = param
                self.homing_start_cond.set_enum_class(self.homing_start_cond_param.ref_list)
                param.sig_value_changed.connect(self.handle_changed_homing_start_cond)
                self.handle_changed_homing_start_cond()
            elif param.name == "Mode":
                self.homing_mode_param = param
                self.homing_mode.set_enum_class(self.homing_mode_param.ref_list)
                param.sig_value_changed.connect(self.handle_changed_homing_mode)
                self.handle_changed_homing_mode()
            elif param.name == "Position Control Stroke Limitation":
                self.stroke_limitation_param = param
                self.stroke_limitation.set_enum_class(self.stroke_limitation_param.ref_list)
                param.sig_value_changed.connect(self.handle_changed_stroke_limitation)
                self.handle_changed_stroke_limitation()
            elif param.name == "Power Failure Option":
                self.power_failure_option_param = param
                self.power_failure_option.set_enum_class(self.power_failure_option_param.ref_list)
                param.sig_value_changed.connect(self.handle_changed_power_failure_option)
                self.handle_changed_power_failure_option()
            elif param.name == "Network Failure Option":
                self.network_failure_option_param = param
                self.network_failure_option.set_enum_class(self.network_failure_option_param.ref_list)
                param.sig_value_changed.connect(self.handle_changed_network_failure_option)
                self.handle_changed_network_failure_option()

    def handle_range_changed(self):
        decimals = self.converter.posi_decimal_places
        self.posi_offset.set_decimal_places(decimals)
        self.handle_changed_posi_offset()

    def handle_changed_posi_speed(self):
        if self.posi_speed_param.value is None:
            self.posi_speed.set_value(None)
        else:
            self.posi_speed.set_value(self.posi_speed_param.value * 100)

        self.posi_speed.commit()

    def handle_changed_posi_offset(self):
        if self.posi_offset_param is None:
            pass
        elif self.posi_offset_param.value is None:
            self.posi_offset.set_value(None)
        else:
            dp_value = self.converter.convert_posi_to_display_value(self.posi_offset_param.value)
            self.posi_offset.set_value(dp_value)

        self.posi_offset.commit()

    def handle_changed_homing_end_posi(self):
        self.homing_end_posi.set_value(self.homing_end_posi_param.value)
        self.homing_end_posi.commit()

    def handle_changed_homing_start_cond(self):
        self.homing_start_cond.set_value(self.homing_start_cond_param.value)
        self.homing_start_cond.commit()

    def handle_changed_homing_mode(self):
        self.homing_mode.set_value(self.homing_mode_param.value)
        self.homing_mode.commit()

    def handle_changed_stroke_limitation(self):
        self.stroke_limitation.set_value(self.stroke_limitation_param.value)
        self.stroke_limitation.commit()

    def handle_changed_power_failure_option(self):
        self.power_failure_option.set_value(self.power_failure_option_param.value)
        self.power_failure_option.commit()

    def handle_changed_network_failure_option(self):
        self.network_failure_option.set_value(self.network_failure_option_param.value)
        self.network_failure_option.commit()

    def on_apply_clicked(self):
        self.sig_apply_clicked.emit()

    def get_posi_speed_write_value(self):
        value = self.posi_speed.get_value()
        if value is None:
            return ""
        else:
            return FloatConverterManager().to_str(value / 100)
             
    def get_posi_offset_write_value(self):
        value = self.posi_offset.get_value()
        if value is None:
            return ""
        else:
            return self.converter.convert_display_to_posi_value_str(value)