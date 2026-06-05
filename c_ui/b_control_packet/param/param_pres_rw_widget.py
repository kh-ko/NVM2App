from b_core.c_manager.local_setting_manager import LocalSettingManager
from b_core.c_manager.parameter_manager import ParamManager

from c_ui.a_converter.pressure_converter_manager import PresConverterManager

from c_ui.b_control_packet.controls_with_label.l_float_rw_widget import LFloatReadWriteWidget


class ParamPresReadWriteWidget(LFloatReadWriteWidget):
    def __init__(self, param_full_path : str, label_width=150, parent = None):
        self.param = ParamManager().get_by_full_path(param_full_path)
        self.converter = PresConverterManager()

        super().__init__(label_text=self.param.name, label_width=label_width, parent = parent)

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
        super().commit()
            
    def handle_is_err_changed(self):
        self.set_error(self.param.is_err)

    def handle_is_not_support_changed(self):
        self.set_support(not self.param.is_not_support)

    def get_param_write_value(self) -> str:
        input_value = self.get_value()
        return self.converter.convert_dp_pres_to_iface_pres_str(input_value)

    def get_backup_value(self) -> dict:
        input_value = self.get_value()
        value = f"{input_value}"
        unit = f"{LocalSettingManager().pres_unit}"

        return {
            "Unit": unit,
            "Value": value
        }

    def set_backup_value(self, value):       
        if not isinstance(value, dict):
            self.set_value(None)
            return

        unit_str = value.get("Unit")
        val_str = value.get("Value")

        try:
            unit = int(unit_str)
            val = float(val_str)

            converted_value = self.converter._convert_pressure(val, unit, LocalSettingManager().pres_unit)
            self.set_value(converted_value)
        except Exception:
            self.set_value(None)
            return

        

