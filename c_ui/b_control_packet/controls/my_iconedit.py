from c_ui.b_control_packet.base import my_style
from c_ui.b_control_packet.base.base_label import BaseLabel

class MyIconEdit(BaseLabel):
    ICON = "\ue8b8"

    def __init__(self, parent=None):
        super().__init__(text = MyIconEdit.ICON, type = my_style.STYLE_LABEL_ICON, parent = parent)
        super().set_color(my_style.STYLE_LABEL_COLOR)