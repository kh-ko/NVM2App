from PySide6.QtWidgets import QSizePolicy
from b_core.c_manager.local_setting_manager import LocalSettingManager
from c_ui.a_converter.float_converter_manager import FloatConverterManager
from c_ui.b_control_packet.base import my_style
from c_ui.b_control_packet.controls.my_labelcolorbox import MyLabelColorBox
from c_ui.b_control_packet.controls.my_label import MyLabel
from PySide6.QtWidgets import QHBoxLayout
from c_ui.b_control_packet.param.param_enum_ro_widget import ParamEnumReadOnlyWidget
from c_ui.b_control_packet.param.param_text_ro_widget import ParamTextReadOnlyWidget
from b_core.b_datatype.general_enum import ParamDisplayType
import re

from PySide6.QtWidgets import QVBoxLayout, QWidget
from b_core.c_manager.parameter_manager import ParamManager

from c_ui.b_control_packet.base.base_groupbox import BaseGroupBox
from c_ui.b_control_packet.base.base_label import BaseLabel
from c_ui.b_control_packet.base.base_table import BaseTableWidget
from c_ui.b_control_packet.param.param_checkdummy_rw_widget import ParamCheckDummyReadWriteWidget
from c_ui.b_control_packet.param_container.param_folder_widget import ParamFolderWidget

class ParamClusterMonitorItemWidget(QWidget):
    def __init__(self, addr, sub_params, parent=None):
        super().__init__(parent)

        self.converter = FloatConverterManager()
        self.local_setting = LocalSettingManager()
        self.lines = QVBoxLayout(self)
        self.err_components = []
        self.lines.setContentsMargins(0,0,0,5)
        self.lines.setSpacing(5)

        self.value_line = QHBoxLayout()
        self.value_line.setContentsMargins(0,0,0,0)
        self.value_line.setSpacing(0)
        
        self.addr = MyLabel(f"{addr}")
        self.addr.setWordWrap(False)
        self.addr.setMinimumWidth(0) 
        self.addr.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        self.act_posi = MyLabel("-")
        self.act_posi.setWordWrap(False)
        self.act_posi.setMinimumWidth(0) 
        self.act_posi.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        self.pos_offset = MyLabel("-")
        self.pos_offset.setWordWrap(False)
        self.pos_offset.setMinimumWidth(0) 
        self.pos_offset.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        self.pos_ctrl_speed = MyLabel("-")
        self.pos_ctrl_speed.setWordWrap(False)
        self.pos_ctrl_speed.setMinimumWidth(0) 
        self.pos_ctrl_speed.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        self.freeze = MyLabel("-")
        self.freeze.setWordWrap(False)
        self.freeze.setMinimumWidth(0) 
        self.freeze.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        self.access_mode = MyLabel("-")
        self.access_mode.setWordWrap(False)
        self.access_mode.setMinimumWidth(0) 
        self.access_mode.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        self.control_mode = MyLabel("-")
        self.control_mode.setWordWrap(False)
        self.control_mode.setMinimumWidth(0) 
        self.control_mode.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        self.compressed_air_value = MyLabel("-")
        self.compressed_air_value.setWordWrap(False)
        self.compressed_air_value.setMinimumWidth(0) 
        self.compressed_air_value.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)

        self.value_line.addWidget(self.addr, 5)
        self.value_line.addWidget(self.act_posi, 10)
        self.value_line.addWidget(self.pos_offset, 10)
        self.value_line.addWidget(self.pos_ctrl_speed, 10)
        self.value_line.addWidget(self.freeze, 10)
        self.value_line.addWidget(self.access_mode, 10)
        self.value_line.addWidget(self.control_mode, 10)
        self.value_line.addWidget(self.compressed_air_value, 10)

        self.lines.addLayout(self.value_line)

        self.error_line = QHBoxLayout()
        self.error_line.setContentsMargins(0,0,0,0)
        self.error_line.setSpacing(5)

        self.normal = MyLabelColorBox(text="Nor", type = my_style.STYLE_LABEL_DESCRIPTION)
        self.normal.set_color(label_color=my_style.STYLE_LABEL_COLOR, bg_color = my_style.STYLE_ACCENT_COLOR)
        self.service_request = MyLabelColorBox(text="Service", type = my_style.STYLE_LABEL_DESCRIPTION)
        self.service_request.set_color(label_color=my_style.STYLE_LABEL_COLOR, bg_color = my_style.STYLE_WARN_COLOR)
        self.err_components.append(self.service_request)
        self.pfo_not_fully_charged = MyLabelColorBox(text="PFO Charged", type = my_style.STYLE_LABEL_DESCRIPTION)
        self.pfo_not_fully_charged.set_color(label_color=my_style.STYLE_LABEL_COLOR, bg_color = my_style.STYLE_WARN_COLOR)
        self.err_components.append(self.pfo_not_fully_charged)
        self.sensor_factor_warning = MyLabelColorBox(text="Sensor Factor", type = my_style.STYLE_LABEL_DESCRIPTION)
        self.sensor_factor_warning.set_color(label_color=my_style.STYLE_LABEL_COLOR, bg_color = my_style.STYLE_WARN_COLOR)
        self.err_components.append(self.sensor_factor_warning)
        self.rom_error = MyLabelColorBox(text="ROM", type = my_style.STYLE_LABEL_DESCRIPTION)
        self.rom_error.set_color(label_color=my_style.STYLE_LABEL_COLOR, bg_color = my_style.STYLE_WARN_COLOR)
        self.err_components.append(self.rom_error)
        self.parameter_error = MyLabelColorBox(text="Param", type = my_style.STYLE_LABEL_DESCRIPTION)
        self.parameter_error.set_color(label_color=my_style.STYLE_LABEL_COLOR, bg_color = my_style.STYLE_ERR_COLOR)
        self.err_components.append(self.parameter_error)
        self.compressed_air_failure = MyLabelColorBox(text="Compressed Air", type = my_style.STYLE_LABEL_DESCRIPTION)
        self.compressed_air_failure.set_color(label_color=my_style.STYLE_LABEL_COLOR, bg_color = my_style.STYLE_ERR_COLOR)
        self.err_components.append(self.compressed_air_failure)
        self.offline_mode = MyLabelColorBox(text="Offline", type = my_style.STYLE_LABEL_DESCRIPTION)
        self.offline_mode.set_color(label_color=my_style.STYLE_LABEL_COLOR, bg_color = my_style.STYLE_ERR_COLOR)
        self.err_components.append(self.offline_mode)
        self.no_interface_found = MyLabelColorBox(text="Interface", type = my_style.STYLE_LABEL_DESCRIPTION)
        self.no_interface_found.set_color(label_color=my_style.STYLE_LABEL_COLOR, bg_color = my_style.STYLE_ERR_COLOR)
        self.err_components.append(self.no_interface_found)
        self.no_adc_signal = MyLabelColorBox(text="ADC", type = my_style.STYLE_LABEL_DESCRIPTION)
        self.no_adc_signal.set_color(label_color=my_style.STYLE_LABEL_COLOR, bg_color = my_style.STYLE_ERR_COLOR)
        self.err_components.append(self.no_adc_signal)
        self.no_adc_signal_on_logic = MyLabelColorBox(text="ADC on Logic", type = my_style.STYLE_LABEL_DESCRIPTION)
        self.no_adc_signal_on_logic.set_color(label_color=my_style.STYLE_LABEL_COLOR, bg_color = my_style.STYLE_ERR_COLOR)
        self.err_components.append(self.no_adc_signal_on_logic)

        self.error_line.addWidget(self.normal)
        self.error_line.addWidget(self.service_request)
        self.error_line.addWidget(self.pfo_not_fully_charged)
        self.error_line.addWidget(self.sensor_factor_warning)
        self.error_line.addWidget(self.rom_error)
        self.error_line.addWidget(self.parameter_error)
        self.error_line.addWidget(self.compressed_air_failure)
        self.error_line.addWidget(self.offline_mode)
        self.error_line.addWidget(self.no_interface_found)
        self.error_line.addWidget(self.no_adc_signal)
        self.error_line.addWidget(self.no_adc_signal_on_logic)
        self.error_line.addStretch()

        self.lines.addLayout(self.error_line)

        for offset, data_len, param in sub_params:
            if param.name == "Actual Position":
                param.sig_value_changed.connect(self.handle_actual_position_changed)
                self.act_posi_param = param
                self.handle_actual_position_changed()
            elif param.name == "Position Offset Used":
                param.sig_value_changed.connect(self.handle_position_offset_changed)
                self.pos_offset_param = param
                self.handle_position_offset_changed()
            elif param.name == "Position Control Speed Used (%)":
                param.sig_value_changed.connect(self.handle_position_control_speed_changed)
                self.pos_ctrl_speed_param = param
                self.handle_position_control_speed_changed()
            elif param.name == "Freeze":
                param.sig_value_changed.connect(self.handle_freeze_changed)
                self.freeze_param = param
                self.handle_freeze_changed()
            elif param.name == "Access Mode Used":
                param.sig_value_changed.connect(self.handle_access_mode_changed)
                self.access_mode_param = param
                self.handle_access_mode_changed()
            elif param.name == "Control Mode Used":
                param.sig_value_changed.connect(self.handle_control_mode_changed)
                self.control_mode_param = param
                self.handle_control_mode_changed()
            elif param.name == "Compressed Air Value(mbar)":
                param.sig_value_changed.connect(self.handle_compressed_air_value_changed)
                self.compressed_air_value_param = param
                self.handle_compressed_air_value_changed()
            elif param.name == "Service Request":
                param.sig_value_changed.connect(self.handle_service_request_changed)
                self.service_request_param = param
                self.handle_service_request_changed()
            elif param.name == "Parameter Error":
                param.sig_value_changed.connect(self.handle_parameter_error_changed)
                self.parameter_error_param = param
            elif param.name == "PFO Not Fully Charged":
                param.sig_value_changed.connect(self.handle_pfo_not_fully_charged_changed)
                self.pfo_not_fully_charged_param = param
            elif param.name == "Compressed Air Failure":
                param.sig_value_changed.connect(self.handle_compressed_air_failure_changed)
                self.compressed_air_failure_param = param
            elif param.name == "Sensor Factor Warning":
                param.sig_value_changed.connect(self.handle_sensor_factor_warning_changed)
                self.sensor_factor_warning_param = param
            elif param.name == "Offline Mode":
                param.sig_value_changed.connect(self.handle_offline_mode_changed)
                self.offline_mode_param = param
            elif param.name == "ROM Error":
                param.sig_value_changed.connect(self.handle_rom_error_changed)
                self.rom_error_param = param
            elif param.name == "No Interface Found":
                param.sig_value_changed.connect(self.handle_no_interface_found_changed)
                self.no_interface_found_param = param
            elif param.name == "No ADC Signal":
                param.sig_value_changed.connect(self.handle_no_adc_signal_changed)
                self.no_adc_signal_param = param
            elif param.name == "No ADC Siganl On Logic":
                param.sig_value_changed.connect(self.handle_no_adc_signal_on_logic_changed)
                self.no_adc_signal_on_logic_param = param

    def handle_actual_position_changed(self):
        if self.act_posi_param.value is None:
            self.act_posi.set_text("Unknown")
        else:
            value = self.act_posi_param.value / 1000
            value_str = self.converter.to_str_with_decimal_places(value, self.local_setting.posi_decimal_places)
            self.act_posi.set_text(value_str)

    def handle_position_offset_changed(self):
        if self.pos_offset_param.value is None:
            self.pos_offset.set_text("Unknown")
        else:
            value = self.pos_offset_param.value / 1000
            value_str = self.converter.to_str_with_decimal_places(value, self.local_setting.posi_decimal_places)
            self.pos_offset.set_text(value_str)

    def handle_position_control_speed_changed(self):
        if self.pos_ctrl_speed_param.value is None:
            self.pos_ctrl_speed.set_text("Unknown")
        else:
            value = self.pos_ctrl_speed_param.value / 10
            value_str = self.converter.to_str_with_decimal_places(value, 1)
            self.pos_ctrl_speed.set_text(f"{value_str} %")

    def handle_freeze_changed(self):
        value_str = self.freeze_param.ref_list.get_desc(self.freeze_param.value)
        self.freeze.set_text(value_str)    

    def handle_access_mode_changed(self):
        value_str = self.access_mode_param.ref_list.get_desc(self.access_mode_param.value)
        self.access_mode.set_text(value_str)   

    def handle_control_mode_changed(self):
        value_str = self.control_mode_param.ref_list.get_desc(self.control_mode_param.value)
        self.control_mode.set_text(value_str) 

    def handle_compressed_air_value_changed(self):
        if self.compressed_air_value_param.value is None:
            self.compressed_air_value.set_text("Unknown")
        else:
            value_str = self.converter.to_str(self.compressed_air_value_param.value)
            self.compressed_air_value.set_text(f"{value_str} mbar")

    def handle_service_request_changed(self):
        if self.service_request_param.value is None or self.service_request_param.value == 0:
            self.service_request.setVisible(False)
        else:
            self.service_request.setVisible(True)

        self.check_normal()
            
    def handle_parameter_error_changed(self):
        if self.parameter_error_param.value is None or self.parameter_error_param.value == 0:
            self.parameter_error.setVisible(False)
        else:
            self.parameter_error.setVisible(True)    

        self.check_normal()

    def handle_pfo_not_fully_charged_changed(self):
        if self.pfo_not_fully_charged_param.value is None or self.pfo_not_fully_charged_param.value == 0:
            self.pfo_not_fully_charged.setVisible(False)
        else:
            self.pfo_not_fully_charged.setVisible(True)

        self.check_normal()

    def handle_compressed_air_failure_changed(self):
        if self.compressed_air_failure_param.value is None or self.compressed_air_failure_param.value == 0:
            self.compressed_air_failure.setVisible(False)
        else:
            self.compressed_air_failure.setVisible(True)

        self.check_normal()

    def handle_sensor_factor_warning_changed(self):
        if self.sensor_factor_warning_param.value is None or self.sensor_factor_warning_param.value == 0:
            self.sensor_factor_warning.setVisible(False)
        else:
            self.sensor_factor_warning.setVisible(True)

        self.check_normal()

    def handle_offline_mode_changed(self):
        if self.offline_mode_param.value is None or self.offline_mode_param.value == 0:
            self.offline_mode.setVisible(False)
        else:
            self.offline_mode.setVisible(True)

        self.check_normal()

    def handle_rom_error_changed(self):
        if self.rom_error_param.value is None or self.rom_error_param.value == 0:
            self.rom_error.setVisible(False)
        else:
            self.rom_error.setVisible(True)

        self.check_normal()

    def handle_no_interface_found_changed(self):
        if self.no_interface_found_param.value is None or self.no_interface_found_param.value == 0:
            self.no_interface_found.setVisible(False)
        else:
            self.no_interface_found.setVisible(True)

        self.check_normal()

    def handle_no_adc_signal_changed(self):
        if self.no_adc_signal_param.value is None or self.no_adc_signal_param.value == 0:
            self.no_adc_signal.setVisible(False)
        else:
            self.no_adc_signal.setVisible(True)

        self.check_normal()

    def handle_no_adc_signal_on_logic_changed(self):
        if self.no_adc_signal_on_logic_param.value is None or self.no_adc_signal_on_logic_param.value == 0:
            self.no_adc_signal_on_logic.setVisible(False)
        else:
            self.no_adc_signal_on_logic.setVisible(True)

        self.check_normal()

    def check_normal(self):
        for component in self.err_components:
            if component.isVisible():
                self.normal.setVisible(False)
                return
        self.normal.setVisible(True)
        

class ParamFolderClusterMonitorWidget(ParamFolderWidget):
    def __init__(self, parent=None):
        super().__init__(folder_name="Cluster Monitor", param_path=None, label_width = 210, parent=parent)
        self.cluster_item_widgets = []

        self.value_line = QHBoxLayout()
        self.value_line.setContentsMargins(0,0,0,0)
        self.value_line.setSpacing(0)
        
        addr = MyLabelColorBox(text="Addr")
        addr.set_color(label_color=my_style.STYLE_LABEL_HOVER_COLOR, bg_color = my_style.STYLE_HOVER_COLOR)
        addr.setWordWrap(False)
        addr.setMinimumWidth(0) 
        addr.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)

        act_posi = MyLabelColorBox("Act Posi")
        act_posi.set_color(label_color=my_style.STYLE_LABEL_HOVER_COLOR, bg_color = my_style.STYLE_HOVER_COLOR)
        act_posi.setWordWrap(False)
        act_posi.setMinimumWidth(0) 
        act_posi.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        
        pos_offset = MyLabelColorBox("Posi Offset")
        pos_offset.set_color(label_color=my_style.STYLE_LABEL_HOVER_COLOR, bg_color = my_style.STYLE_HOVER_COLOR)
        pos_offset.setWordWrap(False)
        pos_offset.setMinimumWidth(0) 
        pos_offset.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        
        pos_ctrl_speed = MyLabelColorBox("Posi Speed")
        pos_ctrl_speed.set_color(label_color=my_style.STYLE_LABEL_HOVER_COLOR, bg_color = my_style.STYLE_HOVER_COLOR)
        pos_ctrl_speed.setWordWrap(False)
        pos_ctrl_speed.setMinimumWidth(0) 
        pos_ctrl_speed.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        
        freeze = MyLabelColorBox("Freeze")
        freeze.set_color(label_color=my_style.STYLE_LABEL_HOVER_COLOR, bg_color = my_style.STYLE_HOVER_COLOR)
        freeze.setWordWrap(False)
        freeze.setMinimumWidth(0) 
        freeze.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        
        access_mode = MyLabelColorBox("Acc Mode")
        access_mode.set_color(label_color=my_style.STYLE_LABEL_HOVER_COLOR, bg_color = my_style.STYLE_HOVER_COLOR)
        access_mode.setWordWrap(False)
        access_mode.setMinimumWidth(0) 
        access_mode.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        
        control_mode = MyLabelColorBox("Ctrl Mode")
        control_mode.set_color(label_color=my_style.STYLE_LABEL_HOVER_COLOR, bg_color = my_style.STYLE_HOVER_COLOR)
        control_mode.setWordWrap(False)
        control_mode.setMinimumWidth(0) 
        control_mode.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        
        compressed_air_value = MyLabelColorBox("Air (mbar)")
        compressed_air_value.set_color(label_color=my_style.STYLE_LABEL_HOVER_COLOR, bg_color = my_style.STYLE_HOVER_COLOR)
        compressed_air_value.setWordWrap(False)
        compressed_air_value.setMinimumWidth(0) 
        compressed_air_value.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)

        self.value_line.addWidget(addr, 5)
        self.value_line.addWidget(act_posi, 10)
        self.value_line.addWidget(pos_offset, 10)
        self.value_line.addWidget(pos_ctrl_speed, 10)
        self.value_line.addWidget(freeze, 10)
        self.value_line.addWidget(access_mode, 10)
        self.value_line.addWidget(control_mode, 10)
        self.value_line.addWidget(compressed_air_value, 10)

        self.content_layout.addLayout(self.value_line)
        
        for num in range(0, 2): 
            status_param = ParamManager().get_by_full_path(f"Cluster.Device {num}.Status")

            item_widget = ParamClusterMonitorItemWidget(num, status_param.sub_items)
            self.add_widget(item_widget)
            self.cluster_item_widgets.append(item_widget)

    def set_cluster_num(self, num):
        for item_widget in self.cluster_item_widgets:
            item_widget.setVisible(False)

        if num is None:
            return

        for num in range(0, num):
            self.cluster_item_widgets[num].setVisible(True)

        