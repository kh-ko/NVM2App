from c_ui.b_control_packet.base.base_doublespinbox import BaseDoubleSpinBox

class MyValueInputFloatSpin(BaseDoubleSpinBox):    
    def __init__(self, enable_border = True, parent=None):
        super().__init__(enable_border=enable_border, parent=parent)

        self.set_range(-3.4028235e38, 3.4028235e38)

    def set_range(self, min_value: float, max_value: float):
        self.setRange(min_value, max_value)

    def set_decimal_places(self, decimals: int):
        self.setDecimals(decimals)

    def set_value(self, value:float):
        if value is None:
            self.clear()
        else:
            self.setValue(value)

    def get_value(self) -> float | None:
        return self.value()

    def set_support(self, support : bool):
        if not support:
            self.set_value(None)
            self.setEnabled(False)
        else:
            self.setEnabled(True)