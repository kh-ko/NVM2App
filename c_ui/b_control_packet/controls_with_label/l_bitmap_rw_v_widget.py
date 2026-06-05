from typing import Type

from PySide6.QtCore import Signal
from PySide6.QtCore import Qt

from b_core.b_datatype.param_enum import DescriptionEnum

from c_ui.b_control_packet.base import my_style
from c_ui.b_control_packet.controls.my_value_input_check import MyValueInputCheck
from c_ui.b_control_packet.controls_with_label.l_base_v_rw_widget import LBaseVerticalReadWriteWidget

class LBitmapReadWriteVerticalWidget(LBaseVerticalReadWriteWidget):    
    sig_value_changed = Signal()

    def __init__(self, enum_class : Type[DescriptionEnum], label_text="", parent=None):
        super().__init__(label_text=label_text, enable_wrap_border=True, parent=parent) 
        self.original_value = None
        self.set_color(my_style.STYLE_BORDER_COLOR, my_style.STYLE_BORDER_COLOR)
        self.layout.setContentsMargins(10, 10, 10, 10) 
        self.layout.setSpacing(5)

        self.item_list = []

        for enum_item in enum_class:
            check_box = MyValueInputCheck(enum_item.description)
            check_box.clicked.connect(self._on_input_changed)
            self.add_widget(check_box)
            self.item_list.append((check_box, enum_item.value))

    def _on_input_changed(self, value):
        self.dirty_label.setVisible(self.is_dirty()) 
        self.sig_value_changed.emit()
        
    def commit(self):
        self.original_value = self.get_value()
        self.dirty_label.setVisible(False)
    
    def set_value(self, value : int):
        if value is None:
            value = 0
            
        for check_box, item_value in self.item_list:
            is_set = (value & (1 << item_value)) != 0
            check_box.set_value(is_set)

    def get_value(self) -> int:
        value = 0
        for check_box, item_value in self.item_list:
            if check_box.get_value():
                value = value | (1 << item_value)

        return value

    def is_dirty(self) -> bool:
        return self.original_value != self.get_value()

    def set_support(self, support : bool):
        for check_box, item_value in self.item_list:
            check_box.set_support(support)

    def restore(self):
        self.set_value(self.original_value)
        self.commit()


        

    
