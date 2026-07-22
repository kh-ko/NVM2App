from b_core.c_manager.parameter_manager import ParamManager
from c_ui.b_control_packet.controls.my_value_label_check import MyValueLabelCheck
from c_ui.b_control_packet.param_container.param_folder_widget import ParamFolderWidget

class ParamFolderClusterMonitorStatusWidget(ParamFolderWidget):
    def __init__(self, parent=None):
        super().__init__(folder_name="Error/Warning [N/A]", param_path=None, label_width = 210, parent=parent)

        self.service_request = MyValueLabelCheck("Service Request")
        self.add_widget(self.service_request)

        self.parameter_error = MyValueLabelCheck("Parameter Error")
        self.add_widget(self.parameter_error)

        self.pfo_not_fully_charged = MyValueLabelCheck("PFO Not Fully Charged")
        self.add_widget(self.pfo_not_fully_charged)
        
        self.compressed_air_failure = MyValueLabelCheck("Compressed Air Failure")
        self.add_widget(self.compressed_air_failure)
        
        self.sensor_factor_warning = MyValueLabelCheck("Sensor Factor Warning")
        self.add_widget(self.sensor_factor_warning)
        
        self.offline_mode = MyValueLabelCheck("Offline Mode")
        self.add_widget(self.offline_mode)
        
        self.rom_error = MyValueLabelCheck("ROM Error")
        self.add_widget(self.rom_error)
        
        self.no_interface_found = MyValueLabelCheck("No Interface Found")
        self.add_widget(self.no_interface_found)
        
        self.no_adc_signal = MyValueLabelCheck("No ADC Signal")
        self.add_widget(self.no_adc_signal)
        
        self.no_adc_signal_on_logic = MyValueLabelCheck("No ADC Siganl On Logic")
        self.add_widget(self.no_adc_signal_on_logic)

        self.setEnabled(False)

    def _clear_signal_connections(self):
        if self.service_request_param is not None:
            self.service_request_param.sig_value_changed.disconnect(self.handle_changed_service_request)
        if self.parameter_error_param is not None:
            self.parameter_error_param.sig_value_changed.disconnect(self.handle_changed_parameter_error)
        if self.pfo_not_fully_charged_param is not None:
            self.pfo_not_fully_charged_param.sig_value_changed.disconnect(self.handle_changed_pfo_not_fully_charged)
        if self.compressed_air_failure_param is not None:
            self.compressed_air_failure_param.sig_value_changed.disconnect(self.handle_changed_compressed_air_failure)
        if self.sensor_factor_warning_param is not None:
            self.sensor_factor_warning_param.sig_value_changed.disconnect(self.handle_changed_sensor_factor_warning)
        if self.offline_mode_param is not None:
            self.offline_mode_param.sig_value_changed.disconnect(self.handle_changed_offline_mode)
        if self.rom_error_param is not None:
            self.rom_error_param.sig_value_changed.disconnect(self.handle_changed_rom_error)
        if self.no_interface_found_param is not None:
            self.no_interface_found_param.sig_value_changed.disconnect(self.handle_changed_no_interface_found)
        if self.no_adc_signal_param is not None:
            self.no_adc_signal_param.sig_value_changed.disconnect(self.handle_changed_no_adc_signal)
        if self.no_adc_signal_on_logic_param is not None:
            self.no_adc_signal_on_logic_param.sig_value_changed.disconnect(self.handle_changed_no_adc_signal_on_logic)

    def set_addr(self, addr):
        self._clear_signal_connections()

        if addr is None:
            self.lbl_title.setText("Error/Warning [N/A]")
            self.setEnabled(False)
            self.service_request.set_value(False)
            self.parameter_error.set_value(False)
            self.pfo_not_fully_charged.set_value(False)
            self.compressed_air_failure.set_value(False)
            self.sensor_factor_warning.set_value(False)
            self.offline_mode.set_value(False)
            self.rom_error.set_value(False)
            self.no_interface_found.set_value(False)
            self.no_adc_signal.set_value(False)
            self.no_adc_signal_on_logic.set_value(False)
        else:
            self.lbl_title.setText(f"Error/Warning [{addr}]")
            self.setEnabled(True)
            self.set_param(addr)
            
    def set_param(self, addr):
        self.param = ParamManager().get_by_full_path(f"Cluster.Device {addr}.Status")
        self.param.sub_items

        for offset, data_len, param in self.param.sub_items:
            if param.name == "Service Request":
                self.service_request_param = param
                param.sig_value_changed.connect(self.handle_changed_service_request)
                self.handle_changed_service_request()
            elif param.name == "Parameter Error":
                self.parameter_error_param = param
                param.sig_value_changed.connect(self.handle_changed_parameter_error)
                self.handle_changed_parameter_error()
            elif param.name == "PFO Not Fully Charged":
                self.pfo_not_fully_charged_param = param
                param.sig_value_changed.connect(self.handle_changed_pfo_not_fully_charged)
                self.handle_changed_pfo_not_fully_charged()
            elif param.name == "Compressed Air Failure":
                self.compressed_air_failure_param = param
                param.sig_value_changed.connect(self.handle_changed_compressed_air_failure)
                self.handle_changed_compressed_air_failure()
            elif param.name == "Sensor Factor Warning":
                self.sensor_factor_warning_param = param
                param.sig_value_changed.connect(self.handle_changed_sensor_factor_warning)
                self.handle_changed_sensor_factor_warning()
            elif param.name == "Offline Mode":
                self.offline_mode_param = param
                param.sig_value_changed.connect(self.handle_changed_offline_mode)
                self.handle_changed_offline_mode()
            elif param.name == "ROM Error":
                self.rom_error_param = param
                param.sig_value_changed.connect(self.handle_changed_rom_error)
                self.handle_changed_rom_error()
            elif param.name == "No Interface Found":
                self.no_interface_found_param = param
                param.sig_value_changed.connect(self.handle_changed_no_interface_found)
                self.handle_changed_no_interface_found()
            elif param.name == "No ADC Signal":
                self.no_adc_signal_param = param
                param.sig_value_changed.connect(self.handle_changed_no_adc_signal)
                self.handle_changed_no_adc_signal()
            elif param.name == "No ADC Siganl On Logic":
                self.no_adc_signal_on_logic_param = param
                param.sig_value_changed.connect(self.handle_changed_no_adc_signal_on_logic)
                self.handle_changed_no_adc_signal_on_logic()

    def handle_changed_service_request(self):
        self.service_request.set_value(self.service_request_param.value)

    def handle_changed_parameter_error(self):
        self.parameter_error.set_value(self.parameter_error_param.value)

    def handle_changed_pfo_not_fully_charged(self):
        self.pfo_not_fully_charged.set_value(self.pfo_not_fully_charged_param.value)

    def handle_changed_compressed_air_failure(self):
        self.compressed_air_failure.set_value(self.compressed_air_failure_param.value)

    def handle_changed_sensor_factor_warning(self):
        self.sensor_factor_warning.set_value(self.sensor_factor_warning_param.value)

    def handle_changed_offline_mode(self):
        self.offline_mode.set_value(self.offline_mode_param.value)

    def handle_changed_rom_error(self):
        self.rom_error.set_value(self.rom_error_param.value)

    def handle_changed_no_interface_found(self):
        self.no_interface_found.set_value(self.no_interface_found_param.value)

    def handle_changed_no_adc_signal(self):
        self.no_adc_signal.set_value(self.no_adc_signal_param.value)

    def handle_changed_no_adc_signal_on_logic(self):
        self.no_adc_signal_on_logic.set_value(self.no_adc_signal_on_logic_param.value)
