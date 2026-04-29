from b_core.b_datatype import param_enum as p_enum

from c_ui.b_components.a_custom.custom_panel import CustomPanel
from c_ui.b_components.a_custom.custom_icon_button import CustomIconButton

class MainControl(CustomPanel):
    def __init__(self, title="", parent=None): # title의 기본값을 빈 문자열로 설정
        super().__init__(title, parent)
        self.setObjectName("MainControl")

        self.setStyleSheet("""
            QWidget#MainControl {
                background-color: white;
                border: 1px solid #dcdcdc;
            }
        """)

        self.open_btn = CustomIconButton("Open", "\uf88a")
        self.open_btn.clicked.connect(self.on_clicked_open_btn)
        self.add_widget(self.open_btn)

        self.close_btn = CustomIconButton("Close", "\uf88a")
        self.close_btn.clicked.connect(self.on_clicked_close_btn)
        self.add_widget(self.close_btn)

        self.hold_btn = CustomIconButton("Hold", "\uf88a")
        self.hold_btn.clicked.connect(self.on_clicked_hold_btn)
        self.add_widget(self.hold_btn)

        self.learn_btn = CustomIconButton("Learn", "\uf88a")
        self.learn_btn.clicked.connect(self.on_clicked_learn_btn)
        self.add_widget(self.learn_btn)
        self.add_stretch()

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
            self.open_btn.set_icon_colors("#30000000")
            self.open_btn.set_icon("\ue835")
            self.close_btn.set_icon_colors("#3fb950")
            self.close_btn.set_icon("\ue5ca")
            self.hold_btn.set_icon_colors("#30000000")
            self.hold_btn.set_icon("\ue835")
            self.learn_btn.set_icon_colors("#30000000")
            self.learn_btn.set_icon("\ue835")
        elif int_value == p_enum.ControlModeEnum.OPEN.value or int_value == p_enum.ControlModeEnum.INTERLOCK_OPEN.value:
            self.open_btn.set_icon_colors("#3fb950")
            self.open_btn.set_icon("\ue5ca")
            self.close_btn.set_icon_colors("#30000000")
            self.close_btn.set_icon("\ue835")
            self.hold_btn.set_icon_colors("#30000000")
            self.hold_btn.set_icon("\ue835")
            self.learn_btn.set_icon_colors("#30000000")
            self.learn_btn.set_icon("\ue835")
        elif int_value == p_enum.ControlModeEnum.HOLD.value:
            self.open_btn.set_icon_colors("#30000000")
            self.open_btn.set_icon("\ue835")
            self.close_btn.set_icon_colors("#30000000")
            self.close_btn.set_icon("\ue835")
            self.hold_btn.set_icon_colors("#3fb950")
            self.hold_btn.set_icon("\ue5ca")
            self.learn_btn.set_icon_colors("#30000000")
            self.learn_btn.set_icon("\ue835")
        elif int_value == p_enum.ControlModeEnum.LEARN.value:
            self.open_btn.set_icon_colors("#30000000")
            self.open_btn.set_icon("\ue835")
            self.close_btn.set_icon_colors("#30000000")
            self.close_btn.set_icon("\ue835")
            self.hold_btn.set_icon_colors("#30000000")
            self.hold_btn.set_icon("\ue835")
            self.learn_btn.set_icon_colors("#3fb950")
            self.learn_btn.set_icon("\ue5ca")
        else:
            self.open_btn.set_icon_colors("#30000000")
            self.open_btn.set_icon("\ue835")
            self.close_btn.set_icon_colors("#30000000")
            self.close_btn.set_icon("\ue835")
            self.hold_btn.set_icon_colors("#30000000")
            self.hold_btn.set_icon("\ue835")
            self.learn_btn.set_icon_colors("#30000000")
            self.learn_btn.set_icon("\ue835")

        
