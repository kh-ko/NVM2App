from typing import Type

from b_core.b_datatype.param_enum import DescriptionEnum

from c_ui.b_control_packet.base.base_label import BaseLabel

class MyValueLabelEnum(BaseLabel):

    def __init__(self, enum_class: Type[DescriptionEnum], parent=None):
        super().__init__(text="", parent = parent)

        self.ori_value = None
        self.enum_class = enum_class  
        self.set_value(None)      

    def set_value(self, value:int):
        self.ori_value = value

        try:
            enum_member = self.enum_class(value)  
            description = enum_member.description
            self.set_text(description)      
            self.setEnabled(True)
        except Exception:
            self.set_text(f"Unknown ({value})")   
            self.setEnabled(False)

    def set_support(self, support : bool):
        if not support:
            self.set_text("Not Support")        
            self.setEnabled(False)
        else:
            self.set_value(self.ori_value)