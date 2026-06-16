from PySide6.QtGui import QDoubleValidator

from c_ui.a_converter.float_converter_manager import FloatConverterManager
from c_ui.b_control_packet.base.base_lineedit import BaseLineEdit

class MyValueInputFloat(BaseLineEdit):    
    def __init__(self, parent=None):
        super().__init__(parent)

        self.converter = FloatConverterManager()

        self.min = -3.4028235e38
        self.max = 3.4028235e38
        self.validator = QDoubleValidator(self)
        self.validator.setNotation(QDoubleValidator.Notation.StandardNotation)
        self.setValidator(self.validator)

        self.setPlaceholderText("Unknown (None)")

        self.set_value(None)
        self.editingFinished.connect(self.check_value)

    def check_value(self):
        val = self.get_value()
        if val is not None:
            if val < self.min or val > self.max:
                clamped_val = max(self.min, min(val, self.max))
                self.set_value(clamped_val)
        else:
            self.clear()        

    def set_range(self, min_value: float, max_value: float):
        #self.validator.setBottom(min_value)
        #self.validator.setTop(max_value)
        self.min = min_value
        self.max = max_value

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