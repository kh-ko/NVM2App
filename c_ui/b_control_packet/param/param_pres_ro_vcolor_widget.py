from c_ui.a_converter.pressure_converter_manager import PresConverterManager
from b_core.c_manager.parameter_manager import ParamManager

from c_ui.b_control_packet.controls_with_label.l_float_ro_vcolor_widget import LFloatReadOnlyVerticalColorWidget


class ParamPresReadOnlyVerticalColorWidget(LFloatReadOnlyVerticalColorWidget):
    def __init__(self, param_full_path : str, label_text = None, label_color="transparent",bg_color="transparent", parent = None):
        self.param = ParamManager().get_by_full_path(param_full_path)
        self.converter = PresConverterManager()

        if label_text:
            super().__init__(label_text=label_text, label_color=label_color, bg_color=bg_color, parent = parent)
        else:
            super().__init__(label_text=self.param.name, label_color=label_color, bg_color=bg_color, parent = parent)

        self.converter.sig_pres_range_changed.connect(self.handle_range_changed)
        self.param.sig_value_changed.connect(self.handle_value_changed)
        self.param.sig_is_err_changed.connect(self.handle_is_err_changed)
        self.param.sig_is_not_support_changed.connect(self.handle_is_not_support_changed)
        
        self.handle_range_changed()
        self.handle_is_err_changed()
        self.handle_is_not_support_changed() 

    def handle_range_changed(self):
        decimals = self.converter.pres_decimal_places
        self.set_decimal_places(decimals)
        self.handle_value_changed()

    def handle_value_changed(self):
        dp_value = self.converter.convert_iface_pres_to_dp_pres(self.param.value)
        super().set_value(dp_value)
            
    def handle_is_err_changed(self):
        self.set_error(self.param.is_err)

    def handle_is_not_support_changed(self):
        self.set_support(not self.param.is_not_support)

