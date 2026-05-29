from c_ui.a_converter.position_converter_manager import PosiConverterManager
from b_core.c_manager.parameter_manager import ParamManager

from c_ui.b_control_packet.controls_with_label.l_float_rw_vspin_widget import LFloatReadWriteVerticalSpinWidget


class ParamFloatReadWriteVerticalSpinWidget(LFloatReadWriteVerticalSpinWidget):
    def __init__(self, param_full_path : str, label_text = None, enable_wrap_border=False, is_only_enter_finished = False, parent = None):
        self.param = ParamManager().get_by_full_path(param_full_path)
        self.converter = PosiConverterManager()

        if label_text:
            super().__init__(label_text=label_text, enable_wrap_border=enable_wrap_border, is_only_enter_finished = is_only_enter_finished, parent = parent)
        else:
            super().__init__(label_text=self.param.name, enable_wrap_border=enable_wrap_border, is_only_enter_finished = is_only_enter_finished, parent = parent)

        self.converter.sig_posi_range_changed.connect(self.handle_range_changed)
        self.param.sig_value_changed.connect(self.handle_value_changed)
        self.param.sig_is_err_changed.connect(self.handle_is_err_changed)
        self.param.sig_is_not_support_changed.connect(self.handle_is_not_support_changed)
        
        self.handle_range_changed()
        self.handle_is_err_changed()
        self.handle_is_not_support_changed() 

    def handle_range_changed(self):
        decimals = self.converter.posi_decimal_places
        self.set_decimal_places(decimals)
        self.handle_value_changed()

    def handle_value_changed(self):
        dp_value = self.converter.convert_posi_to_display_value(self.param.value)

        if dp_value is None:
            super().set_value(0)
        else:
            super().set_value(dp_value)
        super().commit()
            
    def handle_is_err_changed(self):
        self.set_error(self.param.is_err)

    def handle_is_not_support_changed(self):
        self.set_support(not self.param.is_not_support)

    def get_param_write_value(self) -> str:
        input_value = self.get_value()
        return self.converter.convert_display_to_posi_value_str(input_value)

