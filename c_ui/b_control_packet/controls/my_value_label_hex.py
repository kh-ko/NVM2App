from c_ui.a_converter.float_converter_manager import FloatConverterManager
from c_ui.b_control_packet.base.base_label import BaseLabel

class MyValueLabelHex(BaseLabel):

    def __init__(self, parent=None):
        super().__init__(text="", parent = parent)

        self.ori_value = None
        self.set_value(None)    

    def set_value(self, value:int):
        self.ori_value = value

        try:
            int_value = int(value)
            str_value = f"{int_value:X}"
            self.set_text(str_value)
            self.setEnabled(True)
        except:
            self.set_text("Unknown (None)")
            self.setEnabled(False)

    def set_support(self, support : bool):
        if not support:
            self.set_text("Not Support")        
            self.setEnabled(False)
        else:
            self.set_value(self.ori_value)