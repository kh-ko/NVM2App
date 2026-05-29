from c_ui.b_control_packet.base import my_style
from c_ui.b_control_packet.base.base_label import BaseLabel

class MyIconWarn(BaseLabel):
    ICON = "\ue002"

    def __init__(self, parent=None):
        super().__init__(text = MyIconWarn.ICON, type = my_style.STYLE_LABEL_ICON, parent = parent)
        super().set_color(my_style.STYLE_WARN_COLOR)