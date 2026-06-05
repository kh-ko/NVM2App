from c_ui.b_control_packet.base import my_style

from c_ui.b_control_packet.controls.my_value_input_check import MyValueInputCheck
from c_ui.b_control_packet.controls_with_label.l_base_rw_widget import LBaseReadWriteWidget

class LCheckReadWriteWidget(LBaseReadWriteWidget):
    def __init__(self, label_text="", parent=None):
        super().__init__(label_text = "", label_width=0, parent=parent)

        self.original_value = None

        self.value_widget = MyValueInputCheck(label_text)
        self.value_widget.stateChanged.connect(self._on_input_changed)
        self.add_widget(self.value_widget)

    def _on_input_changed(self, value):
        self.dirty_label.setVisible(self.is_dirty()) 
        self.sig_value_changed.emit()

    def commit(self):
        self.original_value = self.value_widget.get_value()
        self.dirty_label.setVisible(False)
    
    def set_value(self, value : bool):
        self.value_widget.set_value(value)

    def get_value(self) -> bool:
        return self.value_widget.get_value()

    def is_dirty(self) -> bool:
        if self.value_widget.get_value() is None:
            return False

        return self.original_value != self.value_widget.get_value()

    def set_error(self, value : bool):
        self.value_widget.set_color(my_style.STYLE_ERR_COLOR if value else my_style.STYLE_LABEL_COLOR)
    

        

    
