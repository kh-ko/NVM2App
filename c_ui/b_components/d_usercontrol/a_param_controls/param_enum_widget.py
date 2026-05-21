from typing import List, Dict, Union, Type, Optional

from b_core.b_datatype.param_enum import DescriptionEnum
from b_core.c_manager.parameter_manager import ParamManager
from c_ui.b_components.c_custom_composit.combo_input_widget import ComboInputWidget


class ParamEnumWidget(ComboInputWidget):
    def __init__(self, param_full_path, parent=None):
        self.param = ParamManager().get_by_full_path(param_full_path)       

        if self.param:
            super().__init__(label_text = self.param.name, parent = parent)

            if self.param.ref_list:
                for item in self.param.ref_list:
                    self.addItem(item.description, item.value)

            self.param.sig_value_changed.connect(self.handle_value_changed)
            self.param.sig_is_err_changed.connect(self.handle_is_err_changed)
            self.param.sig_is_not_support_changed.connect(self.handle_is_not_support_changed)
            self.handle_value_changed()
            self.handle_is_err_changed()
            self.handle_is_not_support_changed()  
        else:
            super().__init__(label_text = "Not Define", parent = parent)

    def handle_value_changed(self):
        if self.param.value is not None:
            self.setCurrentIndex(self.findData(self.param.value))
        else:
            self.setCurrentIndex(-1)
            
    def handle_is_err_changed(self):
        if self.param.is_err:
            self.label.setStyleSheet("background-color: transparent; color: red;")
        else:
            self.label.setStyleSheet("background-color: transparent; color: black;")

    def handle_is_not_support_changed(self):
        if self.param.is_not_support:
            self.setCurrentText("not support")
            self.setEnabled(False)
        else:
            self.setEnabled(True)

    def edit_value(self, value:str):
        if value:
            integer_value = int(value)
            super().edit_value(self.findData(integer_value))

    def getParamWriteValue(self):
        current_data = self.currentData()
        return str(current_data)

    def is_dirty(self):
        if self.dirty_label.isVisible():
            return True
        else:
            return False


