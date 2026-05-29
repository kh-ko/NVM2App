from c_ui.b_control_packet.base import my_style
from c_ui.b_control_packet.base.base_label import BaseLabel

class MyIconCheck(BaseLabel):
    CHECK_ICON = "\ue5ca"
    UNCHECK_ICON = "\ue835"

    def __init__(self, parent=None):
        super().__init__(text = MyIconCheck.UNCHECK_ICON, type = my_style.STYLE_LABEL_ICON, parent = parent)
        self.set_check(False)

    def set_check(self, is_check: bool):
        self.is_checked = is_check

        if is_check:
            super().set_text(MyIconCheck.CHECK_ICON)
            super().set_color(my_style.STYLE_ACCENT_COLOR)
        else:
            super().set_text(MyIconCheck.UNCHECK_ICON)
            super().set_color(my_style.STYLE_BORDER_COLOR)