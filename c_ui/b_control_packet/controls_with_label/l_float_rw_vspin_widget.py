import math

from PySide6.QtCore import Signal

from c_ui.b_control_packet.controls_with_label.l_base_v_rw_widget import LBaseVerticalReadWriteWidget
from c_ui.b_control_packet.controls.my_value_input_float_spin import MyValueInputFloatSpin

class LFloatReadWriteVerticalSpinWidget(LBaseVerticalReadWriteWidget):    
    sig_value_changed = Signal()

    def __init__(self, label_text="", parent=None, enable_wrap_border=False, is_only_enter_finished = False):
        super().__init__(label_text=label_text, enable_wrap_border=enable_wrap_border, parent=parent) 
        
        self.original_value = None 

        self.value_widget = MyValueInputFloatSpin(enable_border = not enable_wrap_border)
        self.value_widget.valueChanged.connect(self._on_input_changed)
        if is_only_enter_finished == False:
            self.value_widget.editingFinished.connect(self._on_editing_finished)
        
        self.value_widget.enterFinished.connect(self._on_editing_finished)

        self.add_widget(self.value_widget)

    def _on_editing_finished(self):
        self.sig_value_changed.emit()

    def _on_input_changed(self):
        self.dirty_label.setVisible(self.isDirty()) 

    def commit(self):
        self.original_value = self.value_widget.get_value()
        self.dirty_label.setVisible(False)
    
    def set_range(self, min_value: float, max_value: float):
        self.value_widget.set_range(min_value, max_value)
        
    def set_decimal_places(self, decimal_places: int):
        self.value_widget.set_decimal_places(decimal_places)

    def set_value(self, value : float):
        self.value_widget.set_value(value)

    def get_value(self) -> float:
        return self.value_widget.get_value()

    def isDirty(self) -> bool:
        input_value = self.value_widget.get_value()

        if input_value is None:
            return False
        elif self.original_value is None:
            return True
        else:
            return not math.isclose(self.original_value, input_value)
    

        

    
