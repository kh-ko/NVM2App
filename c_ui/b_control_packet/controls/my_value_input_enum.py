from typing import Type

from PySide6.QtCore import Qt

from b_core.b_datatype.param_enum import DescriptionEnum
from c_ui.b_control_packet.base.base_combobox import BaseComboBox

class MyValueInputEnum(BaseComboBox):    
    def __init__(self, enum_class : Type[DescriptionEnum], parent=None):
        super().__init__(parent)

        self.clear()
        self.setPlaceholderText("Unknown (None)")

        for item in enum_class:
            self.addItem(item.description, item.value)

        self.set_value(None)

    def set_value(self, value:int):
        try:
            self.setCurrentIndex(self.findData(value, role = Qt.UserRole, flags = Qt.MatchExactly))
        except Exception:
            self.setCurrentIndex(-1)

    def get_value(self) -> int:
        value = self.currentData(role = Qt.UserRole)
        return value

    def set_support(self, support : bool):
        if not support:
            self.setPlaceholderText("Not Support")
            self.set_value(-1)
            self.setEnabled(False)
        else:
            self.setPlaceholderText("Unknown (None)")
            self.setEnabled(True)