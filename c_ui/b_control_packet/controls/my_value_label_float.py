from c_ui.a_converter.float_converter_manager import FloatConverterManager
from c_ui.b_control_packet.base.base_label import BaseLabel

class MyValueLabelFloat(BaseLabel):

    def __init__(self, parent=None):
        super().__init__(text="", parent = parent)

        self.decimal_places = -1
        self.ori_value = None
        self.converter = FloatConverterManager()
        self.set_value(None)    

    def set_decimal_places(self, decimals: int):
        self.decimal_places = decimals
        if self.ori_value is not None:
            self.set_value(self.ori_value)

    def set_value(self, value:float):
        self.ori_value = value

        if self.decimal_places < 0:
            str_value = self.converter.to_str(value)
        else:
            str_value = self.converter.to_str_with_decimal_places(value, self.decimal_places)

        if str_value:            
            self.set_text(str_value)
            self.setEnabled(True)
        else:
            self.set_text("Unknown (None)")
            self.setEnabled(False)

    def set_support(self, support : bool):
        if not support:
            self.set_text("Not Support")        
            self.setEnabled(False)
        else:
            self.set_value(self.ori_value)