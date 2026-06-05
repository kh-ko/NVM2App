from c_ui.b_control_packet.controls_with_label.l_enum_ro_widget import LEnumReadOnlyWidget
from typing import List, Tuple, Type

from PySide6.QtCore import Signal
from PySide6.QtCore import Qt

from b_core.b_datatype.param_enum import DescriptionEnum

from c_ui.b_control_packet.base import my_style
from c_ui.b_control_packet.controls_with_label.l_base_v_ro_widget import LBaseVerticalReadOnlyWidget

class LDigiReadOnlyVerticalWidget(LBaseVerticalReadOnlyWidget):    
    sig_value_changed = Signal()

    def __init__(self, enum_list : List[Tuple[str, Type[DescriptionEnum]]], label_text="", label_width = 150, parent=None):
        super().__init__(label_text=label_text, enable_wrap_border=True, parent=parent) 
        self.set_color(my_style.STYLE_BORDER_COLOR, my_style.STYLE_BORDER_COLOR)
        self.layout.setContentsMargins(10, 10, 10, 10) 
        self.layout.setSpacing(5)

        self.item_list = []
        self.base_value = 10 ** (len(enum_list) - 1) if enum_list else 0

        for enum_name, enum_class in enum_list:
            digi_label = LEnumReadOnlyWidget(enum_class = enum_class, label_text = enum_name, label_width=label_width)
            self.add_widget(digi_label)
            self.item_list.append(digi_label)

    def set_value(self, value : int):
        temp_base_value = self.base_value
        if value is None:
            for label in self.item_list:
                label.set_value(None)
        elif value < self.base_value:
            for label in self.item_list:
                label.setVisible(False)
        else:
            for label in self.item_list:
                label.setVisible(True)
                digit = (value // temp_base_value) % 10
                label.set_value(digit)
                temp_base_value = int(temp_base_value / 10)

    def set_support(self, support : bool):
        for label in self.item_list:
            label.set_support(support)


        

    
