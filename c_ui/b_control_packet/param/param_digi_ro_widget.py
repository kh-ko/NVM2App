from b_core.c_manager.parameter_manager import ParamManager

from c_ui.b_control_packet.controls_with_label.l_digi_ro_v_widget import LDigiReadOnlyVerticalWidget


class ParamDigiReadOnlyWidget(LDigiReadOnlyVerticalWidget):
    def __init__(self, param_full_path : str, label_width : int = 150, parent = None):
        self.param = ParamManager().get_by_full_path(param_full_path)

        super().__init__(label_text=self.param.name, enum_list=self.param.ref_list, label_width=label_width, parent = parent)

        self.param.sig_value_changed.connect(self.handle_value_changed)
        self.param.sig_is_err_changed.connect(self.handle_is_err_changed)
        self.param.sig_is_not_support_changed.connect(self.handle_is_not_support_changed)
        self.handle_value_changed()
        self.handle_is_err_changed()
        self.handle_is_not_support_changed() 

    def handle_value_changed(self):
        super().set_value(self.param.value)
            
    def handle_is_err_changed(self):
        self.set_error(self.param.is_err)

    def handle_is_not_support_changed(self):
        self.set_support(not self.param.is_not_support)

