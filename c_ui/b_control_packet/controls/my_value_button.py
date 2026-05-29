from c_ui.b_control_packet.base.base_button import BaseButton

class MyValueButton(BaseButton):
    def __init__(self, text : str = "", parent=None):
        super().__init__(text = text, parent = parent)
        self.btn_label = text

    def set_support(self, support : bool):
        if not support:
            self.setText("Not Support")
            self.setEnabled(False)
        else:
            self.setText(self.btn_label)
            self.setEnabled(True)