from PySide6.QtCore import Signal

from c_ui.b_control_packet.controls.my_value_input_text import MyValueInputText
from c_ui.b_control_packet.controls_with_label.l_base_rw_widget import LBaseReadWriteWidget

class LTextReadWriteWidget(LBaseReadWriteWidget):    
    def __init__(self, label_text="", label_width=150, parent=None):
        super().__init__(label_text = label_text, label_width=label_width, parent=parent)

        self.original_value = None

        self.value_widget = MyValueInputText()
        self.value_widget.textChanged.connect(self._on_input_changed)
        self.value_widget.editingFinished.connect(self._on_editing_finished)
        self.add_widget(self.value_widget)

    def _on_editing_finished(self):
        self.sig_value_changed.emit()

    def _on_input_changed(self):
        self.dirty_label.setVisible(self.is_dirty()) 

    def commit(self):
        self.original_value = self.value_widget.get_value()
        self.dirty_label.setVisible(False)
    
    def set_value(self, value : str):
        self.value_widget.set_value(value)

    def get_value(self) -> str:
        return self.value_widget.get_value()

    def is_dirty(self) -> bool:
        return self.original_value != self.value_widget.get_value()
    

        

    
