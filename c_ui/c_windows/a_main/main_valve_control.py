
from b_core.b_datatype import param_enum as p_enum

from c_ui.b_control_packet.layout.my_card_widget import MyCardWidget
from c_ui.b_control_packet.controls.my_buttoncheck import MyButtonCheck

class MainValveControl(MyCardWidget):
    def __init__(self, parent=None): # title의 기본값을 빈 문자열로 설정
        super().__init__(title = "Control", is_big_title=True, parent=parent)

        self.open_btn = MyButtonCheck(text="Open")
        self.open_btn.clicked.connect(self.on_clicked_open_btn)
        self.add_widget(self.open_btn)

        self.close_btn = MyButtonCheck(text="Close")
        self.close_btn.clicked.connect(self.on_clicked_close_btn)
        self.add_widget(self.close_btn)

        self.hold_btn = MyButtonCheck(text="Hold")
        self.hold_btn.clicked.connect(self.on_clicked_hold_btn)
        self.add_widget(self.hold_btn)

        self.learn_btn = MyButtonCheck(text="Learn")
        self.learn_btn.clicked.connect(self.on_clicked_learn_btn)
        self.add_widget(self.learn_btn)

    def on_clicked_open_btn(self):
        pass

    def on_clicked_close_btn(self):
        pass

    def on_clicked_hold_btn(self):
        pass

    def on_clicked_learn_btn(self):
        pass

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

        
