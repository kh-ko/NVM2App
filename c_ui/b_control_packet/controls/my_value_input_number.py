from PySide6.QtGui import QIntValidator

from c_ui.b_control_packet.base.base_lineedit import BaseLineEdit

class MyValueInputNumber(BaseLineEdit):    
    def __init__(self, parent=None):
        super().__init__(parent)

        self.validator = QIntValidator(self)
        self.setValidator(self.validator)

        self.set_range(-2147483648, 2147483647)
        self.setPlaceholderText("Unknown (None)")

        self.set_value(None)

    def set_range(self, min_value: int, max_value: int):
        self.validator.setBottom(min_value)
        self.validator.setTop(max_value)

    def set_value(self, value:int):
        try:
            str_value = str(int(value))
            self.setText(str_value)
        except Exception:
            self.clear()

    def get_value(self) -> int | None:
        str_value = self.text()

        try:
            return int(str_value)
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