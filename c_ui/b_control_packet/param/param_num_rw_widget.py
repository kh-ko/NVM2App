from b_core.c_manager.parameter_manager import ParamManager

from c_ui.b_control_packet.controls_with_label.l_number_rw_widget import LNumberReadWriteWidget


class ParamNumReadWriteWidget(LNumberReadWriteWidget):
    def __init__(self, param_full_path : str, label_width : int = 150, parent = None):
        self.param = ParamManager().get_by_full_path(param_full_path)

        super().__init__(label_text=self.param.name, label_width=label_width, parent = parent)
        super().set_range(self.param.min_value, self.param.max_value)

        self.param.sig_value_changed.connect(self.handle_value_changed)
        self.param.sig_is_err_changed.connect(self.handle_is_err_changed)
        self.param.sig_is_not_support_changed.connect(self.handle_is_not_support_changed)
        
        self.handle_value_changed()
        self.handle_is_err_changed()
        self.handle_is_not_support_changed() 

    def handle_value_changed(self):
        super().set_value(self.param.value)
        super().commit()
            
    def handle_is_err_changed(self):
        self.set_error(self.param.is_err)

    def handle_is_not_support_changed(self):
        self.set_support(not self.param.is_not_support)

    def get_param_write_value(self) -> str:
        input_value = self.get_value()
        return f"{input_value}"

    def get_backup_value(self) -> str:
        input_value = self.get_value()
        return f"{input_value}"     

    def set_backup_value(self, value):       
        try:
            int_value = int(value)    
            self.set_value(int_value)
        except (ValueError, TypeError):
            self.set_value(None)   

