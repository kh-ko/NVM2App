from PySide6.QtCore import Signal
from typing import Type

from b_core.b_datatype.param_enum import DescriptionEnum
from c_ui.b_control_packet.controls.my_value_input_enum import MyValueInputEnum
from c_ui.b_control_packet.controls_with_label.l_base_rw_widget import LBaseReadWriteWidget

class LEnumReadWriteWidget(LBaseReadWriteWidget):
    sig_ui_changed = Signal()
    
    def __init__(self, enum_class : Type[DescriptionEnum],label_text="", label_width=150, parent=None):
        super().__init__(label_text = label_text, label_width=label_width, parent=parent)

        self.original_value = None

        self.value_widget = MyValueInputEnum(enum_class = enum_class)
        self.value_widget.currentIndexChanged.connect(self._on_input_changed)
        self.value_widget.activated.connect(self._on_user_activated)
        self.add_widget(self.value_widget)

    def _on_input_changed(self, value):
        self.dirty_label.setVisible(self.is_dirty()) 
        self.sig_value_changed.emit()

    def _on_user_activated(self, index):
        self.sig_ui_changed.emit()

    def commit(self):
        self.original_value = self.value_widget.get_value()
        self.dirty_label.setVisible(False)

    def set_enum_class(self, enum_class : Type[DescriptionEnum]):
        self.value_widget.set_enum_class(enum_class)
    
    def set_value(self, value : int):
        self.value_widget.set_value(value)

    def get_value(self) -> int:
        return self.value_widget.get_value()

    def is_dirty(self) -> bool:
        if self.value_widget.get_value() is None:
            return False

        return self.original_value != self.value_widget.get_value()
    

        

    
