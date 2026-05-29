from c_ui.b_control_packet.base.base_label import BaseLabel

class MyLabel(BaseLabel):

    def __init__(self, text = "", parent=None):
        super().__init__(text=text, parent = parent)