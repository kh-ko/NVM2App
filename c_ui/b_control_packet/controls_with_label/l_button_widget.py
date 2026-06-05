from b_core.b_datatype.parameter import Parameter

from c_ui.b_control_packet.controls.my_value_button import MyValueButton
from c_ui.b_control_packet.controls_with_label.l_base_widget import LBaseWidget

class LButtonWidget(LBaseWidget):
    def __init__(self, label_text="", btn_text = "", label_width=150, parent=None):
        super().__init__(label_text = label_text, label_width=label_width, parent=parent)
        
        self.value_widget = MyValueButton(btn_text)
        self.add_widget(self.value_widget)

    def is_dirty(self):
        return False