
from PySide6.QtCore import Qt
from c_ui.b_control_packet.base.base_checkbox import BaseCheckBox


class MyValueInputCheck(BaseCheckBox):    
    def __init__(self, text="", parent=None):
        super().__init__(text, parent)

        self.label = text
        self.set_value(None)

    def set_value(self, value:bool):
        try:
            is_check = bool(value)
            self.setChecked(is_check)
        except Exception:
            self.setChecked(False)

    def get_value(self) -> bool:
        return self.checkState() == Qt.CheckState.Checked

    def set_support(self, support : bool):
        if not support:
            self.setText("Not Support")
            self.set_value(False)
            self.setEnabled(False)
        else:
            self.setText(self.label)
            self.setEnabled(True)