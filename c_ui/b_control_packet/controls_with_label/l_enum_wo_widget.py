from typing import Type

from b_core.b_datatype.param_enum import DescriptionEnum
from c_ui.b_control_packet.controls.my_value_input_enum import MyValueInputEnum
from c_ui.b_control_packet.controls_with_label.l_base_rw_widget import LBaseReadWriteWidget
from c_ui.b_control_packet.controls.my_value_button import MyValueButton

class LEnumWriteOnlyWidget(LBaseReadWriteWidget):
    def __init__(self, enum_class : Type[DescriptionEnum],label_text="", label_width=150, parent=None):
        super().__init__(label_text = label_text, label_width=label_width, parent=parent)

        self.original_value = None

        self.value_widget = MyValueInputEnum(enum_class = enum_class)
        #self.value_widget.set_value(enum_class.default_value())
        #self.value_widget.currentIndexChanged.connect(self._on_input_changed)
        self.add_widget(self.value_widget)

        self.btn_widget = MyValueButton("Run")
        self.add_widget(self.btn_widget)

    def _on_input_changed(self, value):
        #self.dirty_label.setVisible(self.is_dirty()) 
        #self.sig_value_changed.emit()
        pass

    def commit(self):
        self.original_value = self.value_widget.get_value()
        self.dirty_label.setVisible(False)
    
    def set_value(self, value : int):
        self.value_widget.set_value(value)

    def get_value(self) -> int:
        return self.value_widget.get_value()

    def is_dirty(self) -> bool:
        #if self.value_widget.get_value() is None:
        #    return False
        #return self.original_value != self.value_widget.get_value()
        return False

    def set_support(self, support : bool):
        if self.value_widget is not None:
            self.value_widget.set_support(support)

        if self.btn_widget is not None:
            self.btn_widget.setEnabled(support)
            
    

        

    
