from b_core.b_datatype.param_enum import SensUnitEnum
from b_core.c_manager.local_setting_manager import LocalSettingManager
from b_core.b_datatype.general_enum import ParamDisplayType
from c_ui.a_converter.pressure_converter_manager import PresConverterManager
from c_ui.a_converter.sens2_pres_converter_manager import Sens2PresConverterManager
from c_ui.a_converter.sens1_pres_converter_manager import Sens1PresConverterManager
from b_core.c_manager.parameter_manager import ParamManager

from c_ui.b_control_packet.controls_with_label.l_float_ro_widget import LFloatReadOnlyWidget

class ParamPresReadOnlyWidget(LFloatReadOnlyWidget):
    def __init__(self, param_full_path : str, label_width=150, parent = None):
        self.param = ParamManager().get_by_full_path(param_full_path)

        self.local_setting = LocalSettingManager()

        if self.param.display_type == ParamDisplayType.SENS1_PRES:
            self.converter = Sens1PresConverterManager()
        elif self.param.display_type == ParamDisplayType.SENS2_PRES:
            self.converter = Sens2PresConverterManager()
        else:
            self.converter = PresConverterManager()

        if self.param.display_type == ParamDisplayType.PRESS_SLOPE:
            label_text = f"{self.param.name} [{SensUnitEnum.get_desc(self.local_setting.pres_unit)}/sec]"
        else:
            label_text = f"{self.param.name} [{SensUnitEnum.get_desc(self.local_setting.pres_unit)}]"

        super().__init__(label_text=label_text, label_width=label_width, parent = parent)

        self.local_setting.sig_pres_unit_changed.connect(self.handle_pres_unit_changed)
        self.converter.sig_pres_range_changed.connect(self.handle_range_changed)
        self.param.sig_value_changed.connect(self.handle_value_changed)
        self.param.sig_is_err_changed.connect(self.handle_is_err_changed)
        self.param.sig_is_not_support_changed.connect(self.handle_is_not_support_changed)
        
        self.handle_range_changed()
        self.handle_is_err_changed()
        self.handle_is_not_support_changed() 

    def handle_pres_unit_changed(self):
        if self.param.display_type == ParamDisplayType.PRESS_SLOPE:
            label_text = f"{self.param.name} [{SensUnitEnum.get_desc(self.local_setting.pres_unit)}/sec]"
        else:
            label_text = f"{self.param.name} [{SensUnitEnum.get_desc(self.local_setting.pres_unit)}]"

        self.lbl_label.setText(label_text)
        
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

