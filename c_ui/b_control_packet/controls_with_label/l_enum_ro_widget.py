from typing import Type

from b_core.b_datatype.param_enum import DescriptionEnum
from c_ui.b_control_packet.controls.my_value_label_enum import MyValueLabelEnum
from c_ui.b_control_packet.controls_with_label.l_base_ro_widget import LBaseReadOnlyWidget

class LEnumReadOnlyWidget(LBaseReadOnlyWidget):
    def __init__(self, enum_class : Type[DescriptionEnum],label_text="", label_width=150, parent=None):
        super().__init__(label_text = label_text, label_width=label_width, parent=parent)

        self.value_widget = MyValueLabelEnum(enum_class = enum_class)
        self.add_widget(self.value_widget)

    def set_value(self, value : int):
        self.value_widget.set_value(value)

        

    
