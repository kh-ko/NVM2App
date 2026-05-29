from c_ui.b_control_packet.base.base_labelcolorbox import BaseLabelColorBox

class MyLabelColorBox(BaseLabelColorBox):

    def __init__(self, text = "", type = 0, parent=None):
        super().__init__(text=text, type=type, parent = parent)