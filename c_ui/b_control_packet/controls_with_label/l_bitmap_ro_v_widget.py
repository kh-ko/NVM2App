from typing import Type

from PySide6.QtCore import Signal
from PySide6.QtCore import Qt

from b_core.b_datatype.param_enum import DescriptionEnum

from c_ui.b_control_packet.base import my_style
from c_ui.b_control_packet.controls_with_label.l_base_v_ro_widget import LBaseVerticalReadOnlyWidget
from c_ui.b_control_packet.controls.my_value_label_check import MyValueLabelCheck

class LBitmapReadOnlyVerticalWidget(LBaseVerticalReadOnlyWidget):    
    def __init__(self, enum_class : Type[DescriptionEnum], label_text="", parent=None):
        super().__init__(label_text=label_text, enable_wrap_border=True, parent=parent) 
        self.set_color(my_style.STYLE_BORDER_COLOR, my_style.STYLE_BORDER_COLOR)
        self.layout.setContentsMargins(10, 10, 10, 10) 
        self.layout.setSpacing(5)

        self.item_list = []

        for enum_item in enum_class:
            check_label = MyValueLabelCheck(enum_item.description)
            self.add_widget(check_label)
            self.item_list.append((check_label, enum_item.value))

    def set_value(self, value : int):
        if value is None:
            bitmap = 0
        else:
            bitmap = value

        for label, item_value in self.item_list:
            is_set = (bitmap & (1 << item_value)) != 0
            label.set_value(is_set)

        self.sig_value_changed.emit()

    def set_support(self, support : bool):
        for label, item_value in self.item_list:
            label.set_support(support)


        

    
