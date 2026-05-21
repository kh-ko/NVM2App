from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QColor, QFont

from c_ui.b_components.a_custom_base.custom_icon_label import CustomIconLabel

class CustomIconCheckLabel(CustomIconLabel):
    CHECK_ICON = "\ue5ca"
    UNCHECK_ICON = "\ue835"
    CHECK_COLOR = "#3fb950" 
    UNCHECK_COLOR = "#484f58"

    def __init__(self, parent=None):
        super().__init__(text = CustomIconCheckLabel.UNCHECK_ICON, color = CustomIconCheckLabel.UNCHECK_COLOR, icon_size_scale = 1.2, parent = parent)
        self.set_check(False)

    def set_check(self, is_check: bool):
        self.is_checked = is_check

        if is_check:
            super().set_text(CustomIconCheckLabel.CHECK_ICON)
            super().set_color(CustomIconCheckLabel.CHECK_COLOR)
        else:
            super().set_text(CustomIconCheckLabel.UNCHECK_ICON)
            super().set_color(CustomIconCheckLabel.UNCHECK_COLOR)