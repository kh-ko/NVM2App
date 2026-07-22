from c_ui.b_control_packet.controls.my_value_label_hex import MyValueLabelHex
from c_ui.b_control_packet.controls_with_label.l_base_ro_widget import LBaseReadOnlyWidget

class LHexReadOnlyWidget(LBaseReadOnlyWidget):
    def __init__(self, label_text="", label_width=150, parent=None):
        super().__init__(label_text = label_text, label_width=label_width, parent=parent)

        self.value_widget = MyValueLabelHex()
        self.add_widget(self.value_widget)

    def set_value(self, value : int):
        self.value_widget.set_value(value)
        self.sig_value_changed.emit()

        

    
