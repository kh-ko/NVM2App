from PySide6.QtCore import Signal

from b_core.b_datatype import param_enum as p_enum
from c_ui.b_control_ver2.b_base.containers import PanelWidget
from c_ui.b_control_ver2.b_base.buttons import CheckButton

class MainControlPanel(PanelWidget):
    def __init__(self, parent=None): 
        super().__init__(title="Control", is_big_title=True, parent = parent)

        self.open_btn = CheckButton(text="Open")
        self.add_widget(self.open_btn)

        self.close_btn = CheckButton(text="Close")
        self.add_widget(self.close_btn)

        self.hold_btn = CheckButton(text="Hold")
        self.add_widget(self.hold_btn)

        self.learn_btn = CheckButton(text="Learn")
        self.add_widget(self.learn_btn)

    def set_ctrl_mode_value(self, int_value: int):
        if int_value == p_enum.ControlModeEnum.CLOSE.value or int_value == p_enum.ControlModeEnum.INTERLOCK_CLOSE.value:
            self.open_btn.set_check(False)
            self.close_btn.set_check(True)
            self.hold_btn.set_check(False)
            self.learn_btn.set_check(False)
        elif int_value == p_enum.ControlModeEnum.OPEN.value or int_value == p_enum.ControlModeEnum.INTERLOCK_OPEN.value:
            self.open_btn.set_check(True)
            self.close_btn.set_check(False)
            self.hold_btn.set_check(False)
            self.learn_btn.set_check(False)
        elif int_value == p_enum.ControlModeEnum.HOLD.value:
            self.open_btn.set_check(False)
            self.close_btn.set_check(False)
            self.hold_btn.set_check(True)
            self.learn_btn.set_check(False)
        elif int_value == p_enum.ControlModeEnum.LEARN.value:
            self.open_btn.set_check(False)
            self.close_btn.set_check(False)
            self.hold_btn.set_check(False)
            self.learn_btn.set_check(True)
        else:
            self.open_btn.set_check(False)
            self.close_btn.set_check(False)
            self.hold_btn.set_check(False)
            self.learn_btn.set_check(False)