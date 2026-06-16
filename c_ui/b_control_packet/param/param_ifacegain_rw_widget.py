from b_core.c_manager.parameter_manager import ParamManager

from c_ui.a_converter.float_converter_manager import FloatConverterManager

from c_ui.b_control_packet.controls_with_label.l_float_rw_widget import LFloatReadWriteWidget


class ParamIfaceGainReadWriteWidget(LFloatReadWriteWidget):
    def __init__(self, param_full_path : str, label_text = None, label_width = 150, enable_wrap_border=False, is_only_enter_finished = False, parent = None):
        self.param = ParamManager().get_by_full_path(param_full_path)
        self.converter = FloatConverterManager()
        super().__init__(label_text=self.param.name, label_width=label_width, parent = parent)
        self.set_range(self.param.min_value, self.param.max_value)
        
        self.param.sig_value_changed.connect(self.handle_value_changed)
        self.param.sig_is_err_changed.connect(self.handle_is_err_changed)
        self.param.sig_is_not_support_changed.connect(self.handle_is_not_support_changed)
        
        self.handle_value_changed()
        self.handle_is_err_changed()
        self.handle_is_not_support_changed() 

    def handle_value_changed(self):
        if self.param.value is None:
            super().set_value(self.param.value)
        else:
            super().set_value(self.param.value * 10000)

        super().commit()
            
    def handle_is_err_changed(self):
        self.set_error(self.param.is_err)

    def handle_is_not_support_changed(self):
        self.set_support(not self.param.is_not_support)

    def get_param_write_value(self) -> str:
        input_value = self.get_value()
        return self.converter.to_str(input_value / 10000)

    def get_backup_value(self) -> str:
        input_value = self.get_value()
        return f"{input_value}"     

    def set_backup_value(self, value):       
        try:
            int_value = float(value)    
            self.set_value(int_value)
        except (ValueError, TypeError):
            self.set_value(None)   

