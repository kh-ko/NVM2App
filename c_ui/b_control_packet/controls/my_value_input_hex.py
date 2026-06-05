from PySide6.QtGui import QRegularExpressionValidator
from PySide6.QtCore import QRegularExpression

from c_ui.b_control_packet.base.base_lineedit import BaseLineEdit

class MyValueInputHex(BaseLineEdit):    
    def __init__(self, parent=None):
        super().__init__(parent)

        self.regex = QRegularExpression("^[0-9a-fA-F]{0,8}$")
        self.validator = QRegularExpressionValidator(self.regex, self)
        self.setValidator(self.validator)

        self.set_range(0, 0xFFFFFFFF)
        self.setPlaceholderText("Unknown (None)")

        self.set_value(None)

    def set_range(self, min_value: int, max_value: int):
        if min_value >= -128 and max_value <= 255:
            self.bit_width = 8      
        elif min_value >= -32768 and max_value <= 65535:
            self.bit_width = 16     
        else:
            self.bit_width = 32     

        max_len = self.bit_width // 4
        self.regex.setPattern(f"^[0-9a-fA-F]{{0,{max_len}}}$")
        self.validator.setRegularExpression(self.regex)

    def set_value(self, value:int):
        try:
            int_value = int(value)
            str_value = f"{int_value:X}"
            self.setText(str_value)
        except Exception:
            self.clear()

    def get_value(self) -> int | None:
        str_value = self.text()

        try:
            return int(str_value, 16)
        except Exception:
            return None

    def set_support(self, support : bool):
        if not support:
            self.setPlaceholderText("Not Support")
            self.set_value(None)
            self.setEnabled(False)
        else:
            self.setPlaceholderText("Unknown (None)")
            self.setEnabled(True)            