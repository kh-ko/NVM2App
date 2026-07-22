from PySide6.QtCore import Signal
from PySide6.QtCore import Qt

from c_ui.b_control_packet.base import my_style
from c_ui.b_control_packet.controls_with_label.l_base_v_ro_widget import LBaseVerticalReadOnlyWidget
from c_ui.b_control_packet.controls.my_value_label_float_color import MyValueLabelFloatColor

class LFloatReadOnlyVerticalColorWidget(LBaseVerticalReadOnlyWidget):    
    sig_value_changed = Signal()

    def __init__(self, label_text="", label_color=my_style.STYLE_LABEL_COLOR, bg_color=my_style.STYLE_BORDER_COLOR, parent=None):
        super().__init__(label_text=label_text, enable_wrap_border=False, parent=parent) 

        self.value_widget = MyValueLabelFloatColor()
        self.value_widget.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.value_widget.set_color(label_color, my_style.STYLE_BORDER_COLOR, bg_color)

        self.add_widget(self.value_widget)
        
    def set_decimal_places(self, decimal_places: int):
        self.value_widget.set_decimal_places(decimal_places)

    def set_value(self, value : float):
        self.value_widget.set_value(value)
        self.sig_value_changed.emit()

        

    
