from PySide6.QtGui import QDoubleValidator

from c_ui.a_converter.float_converter_manager import FloatConverterManager
from c_ui.b_control_packet.base.base_lineedit import BaseLineEdit

class MyValueInputFloat(BaseLineEdit):    
    def __init__(self, parent=None):
        super().__init__(parent)

        self.converter = FloatConverterManager()

        self.validator = QDoubleValidator(self)
        self.validator.setNotation(QDoubleValidator.Notation.StandardNotation)
        self.setValidator(self.validator)

        self.set_range(-3.4028235e38, 3.4028235e38)
        self.setPlaceholderText("Unknown (None)")

        self.set_value(None)

    def set_range(self, min_value: float, max_value: float):
        self.validator.setBottom(min_value)
        self.validator.setTop(max_value)

    def set_decimal_places(self, decimals: int):
        self.validator.setDecimals(decimals)
        
        current_value = self.get_value()
        if current_value is not None:
            self.set_value(current_value)

    def set_value(self, value:float):
        decimals = self.validator.decimals()

        if decimals < 0:
            str_value = self.converter.to_str(value)
        else:
            str_value = self.converter.to_str_with_decimal_places(value, decimals)

        if str_value:
            self.setText(str_value)
        else:
            self.clear()

    def get_value(self) -> float | None:
        str_value = self.text()

        try:
            return float(str_value)
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