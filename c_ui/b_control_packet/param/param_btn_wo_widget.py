from PySide6.QtCore import Signal

from b_core.b_datatype.parameter import Parameter

from b_core.c_manager.parameter_manager import ParamManager

from c_ui.b_control_packet.controls_with_label.l_button_widget import LButtonWidget


class ParamBtnWriteOnlyWidget(LButtonWidget):
    sig_value_changed = Signal(Parameter)

    def __init__(self, param_full_path : str, label_width : int = 150, parent = None):
        self.param = ParamManager().get_by_full_path(param_full_path)

        super().__init__(label_text=self.param.name, btn_text="Run", label_width=label_width, parent = parent)

        self.value_widget.clicked.connect(self._on_input_changed)
        self.param.sig_is_err_changed.connect(self.handle_is_err_changed)
        self.param.sig_is_not_support_changed.connect(self.handle_is_not_support_changed)
        self.handle_is_err_changed()
        self.handle_is_not_support_changed() 

    def _on_input_changed(self):
        self.sig_value_changed.emit(self.param)
            
    def handle_is_err_changed(self):
        self.set_error(self.param.is_err)

    def handle_is_not_support_changed(self):
        self.set_support(not self.param.is_not_support)

