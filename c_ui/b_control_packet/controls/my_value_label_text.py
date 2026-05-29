from typing import Type

from c_ui.b_control_packet.base.base_label import BaseLabel

class MyValueLabelText(BaseLabel):

    def __init__(self, parent=None):
        super().__init__(text="", parent = parent)
        self.ori_value = None
        self.set_value(None)      

    def set_value(self, value:str):
        self.ori_value = value
    
        if value is not None:
            self.set_text(value)
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