from c_ui.a_converter.float_converter_manager import FloatConverterManager
from c_ui.b_control_packet.controls.my_value_label_float import MyValueLabelFloat
from c_ui.b_control_packet.controls_with_label.l_base_ro_widget import LBaseReadOnlyWidget

class LFloatReadOnlyWidget(LBaseReadOnlyWidget):
    def __init__(self, label_text="", label_width=150, parent=None):
        super().__init__(label_text = label_text, label_width=label_width, parent=parent)

        self.value_widget = MyValueLabelFloat()
        self.add_widget(self.value_widget)

    def set_decimal_places(self, decimal_places: int):
        self.value_widget.set_decimal_places(decimal_places)

    def set_value(self, value : float):
        self.value_widget.set_value(value)
        self.sig_value_changed.emit()

        

    
