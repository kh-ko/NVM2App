from PySide6.QtCore import Signal

from b_core.b_datatype.parameter import Parameter
from b_core.c_manager.parameter_manager import ParamManager

from c_ui.b_control_packet.controls_with_label.l_enum_wo_widget import LEnumWriteOnlyWidget


class ParamEnumWriteOnlyWidget(LEnumWriteOnlyWidget):
    sig_value_changed = Signal(Parameter, str)
    
    def __init__(self, param_full_path : str, label_width : int = 150, parent = None):
        self.param = ParamManager().get_by_full_path(param_full_path)

        super().__init__(enum_class=self.param.ref_list, label_text=self.param.name, label_width=label_width, parent = parent)

        self.btn_widget.clicked.connect(self._on_input_changed)
        self.param.sig_is_err_changed.connect(self.handle_is_err_changed)
        self.param.sig_is_not_support_changed.connect(self.handle_is_not_support_changed)
        
        self.handle_value_changed()
        self.handle_is_err_changed()
        self.handle_is_not_support_changed() 

    def _on_input_changed(self):
        self.sig_value_changed.emit(self.param, self.get_param_write_value())

    def handle_value_changed(self):
        super().set_value(self.param.value)
        super().commit()
            
    def handle_is_err_changed(self):
        self.set_error(self.param.is_err)

    def handle_is_not_support_changed(self):
        self.set_support(not self.param.is_not_support)

    def get_param_write_value(self) -> str:
        input_value = self.get_value()
        if input_value is not None:
            return f"{input_value}"
        else:
            return ""

    def get_backup_value(self) -> str:
        input_value = self.get_value()
        return f"{input_value}"

    def set_backup_value(self, value):
        try:
            backup_value = int(value)
            self.set_value(backup_value)
        except ValueError:
            self.set_value(None)
        


