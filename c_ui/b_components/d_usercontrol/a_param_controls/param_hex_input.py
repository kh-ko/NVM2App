from PySide6.QtGui import QRegularExpressionValidator
from PySide6.QtCore import QRegularExpression

from b_core.c_manager.parameter_manager import ParamManager
from c_ui.b_components.c_custom_composit.line_edit_widget import LineEditWidget

class ParamHexInputWidget(LineEditWidget):
    def __init__(self, param_full_path, parent=None):
        self.param = ParamManager().get_by_full_path(param_full_path)       

        if self.param:
            super().__init__(label_text = self.param.name, parent = parent)

            self.param.sig_value_changed.connect(self.handle_value_changed)
            self.param.sig_is_err_changed.connect(self.handle_is_err_changed)
            self.param.sig_is_not_support_changed.connect(self.handle_is_not_support_changed)
            self.handle_value_changed()
            self.handle_is_err_changed()
            self.handle_is_not_support_changed()  
        else:
            super().__init__(label_text = "Not Define", parent = parent)

        regex = QRegularExpression("^[0-9A-Fa-f]*$")
        validator = QRegularExpressionValidator(regex, self.line_edit)
        self.line_edit.setValidator(validator)

    def handle_value_changed(self):
        if self.param.value is not None:
            self.setText(f"{self.param.value:X}")
        else:
            self.setText("-")

    def handle_is_err_changed(self):
        if self.param.is_err:
            self.label.setStyleSheet("background-color: transparent; color: red;")
        else:
            self.label.setStyleSheet("background-color: transparent; color: black;")

    def handle_is_not_support_changed(self):
        if self.param.is_not_support:
            self.setText("not support")
            self.setEnabled(False)
        else:
            self.setEnabled(True)

    def edit_value(self, value:str):
        if value:
            integer_value = int(value)
            hex_value = f"{integer_value:X}"
            super().edit_value(hex_value)
            
    def getParamWriteValue(self):
        hex_str = self.text()
        if hex_str == "-":
            return ""
        else:
            int_value = int(hex_str, 16)
            return str(int_value)

    def is_dirty(self):
        if self.dirty_label.isVisible():
            return True
        else:
            return False            