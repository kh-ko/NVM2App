from c_ui.b_control_packet.base import my_style
from c_ui.b_control_packet.base.base_label import BaseLabel

class MyLabelTitle(BaseLabel):
    def __init__(self, text = "", parent=None):
        super().__init__(text=text, type = my_style.STYLE_LABEL_TITLE, parent = parent)