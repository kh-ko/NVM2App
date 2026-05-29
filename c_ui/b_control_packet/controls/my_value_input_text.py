from typing import Type

from PySide6.QtCore import Qt

from b_core.b_datatype.param_enum import DescriptionEnum
from c_ui.b_control_packet.base.base_lineedit import BaseLineEdit

class MyValueInputText(BaseLineEdit):    
    def __init__(self, parent=None):
        super().__init__(parent)

        self.clear()
        self.setPlaceholderText("Unknown (None)")

        self.set_value(None)

    def set_value(self, value:str):
        self.setText(value)

    def get_value(self) -> str:
        value = self.text()
        return value