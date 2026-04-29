from typing import List, Tuple

from b_core.c_manager.parameter_manager import ParamManager

from c_ui.b_components.a_custom.custom_panel import CustomPanel
from c_ui.b_components.a_custom.custom_icon_label_button import CustomIconLabelButton
from c_ui.b_components.b_usercontrol.user_enum_label import UserEnumLabel
from c_ui.b_components.b_usercontrol.user_float_label import UserFloatLabel

class MainStatus(CustomPanel):
    def __init__(self, title:str, control_mode_param:str, posi_ctrl_speed_param:str, controller_select_param:str, warn_bitmap_param:str, err_bitmap_param:str,parent=None): # title의 기본값을 빈 문자열로 설정
        super().__init__(title,parent)
        self.setObjectName("MainStatus")

        self.setStyleSheet("""
            QWidget#MainStatus {
                background-color: white;
                border: 1px solid #dcdcdc;
            }
        """)

        self.warn_list: List[Tuple[int, CustomIconLabelButton]] = []
        self.err_list: List[Tuple[int, CustomIconLabelButton]] = []

        control_mode_label = UserEnumLabel("Control Mode", control_mode_param, 180)
        self.add_widget(control_mode_label)

        posi_ctrl_speed_label = UserFloatLabel("Position Control Speed", posi_ctrl_speed_param, 180)
        self.add_widget(posi_ctrl_speed_label)
        
        controller_select_label = UserEnumLabel("Controller Selector", controller_select_param, 180)
        self.add_widget(controller_select_label)

        self.warn_param = ParamManager().get_by_full_path(warn_bitmap_param)
        if self.warn_param and self.warn_param.ref_list:  
            self.warn_param.sig_value_changed.connect(self.handle_warn_bitmap_changed)

            for member in self.warn_param.ref_list:
                bit_pos = member.value
                description = member.description

                button = CustomIconLabelButton(description, "\ue002")
                button.set_icon_colors("#FFA000")
                button.set_text_color("#F57C00")
                button.setVisible(False)
                button.clicked.connect(self.on_clicked_warn_err_button)

                self.add_widget(button)
                self.warn_list.append((bit_pos, button))

        self.err_param = ParamManager().get_by_full_path(err_bitmap_param)
        if self.err_param and self.err_param.ref_list:  
            self.err_param.sig_value_changed.connect(self.handle_err_bitmap_changed)

            for member in self.err_param.ref_list:
                bit_pos = member.value
                description = member.description

                button = CustomIconLabelButton(description, "\ue002")
                button.set_icon_colors("#FF0000")
                button.set_text_color("#F57C00")
                button.setVisible(False)
                button.clicked.connect(self.on_clicked_warn_err_button)

                self.add_widget(button)
                self.err_list.append((bit_pos, button))     

        self.add_stretch()           

    def on_clicked_warn_err_button(self):
        pass

    def handle_err_bitmap_changed(self):
        if not self.err_param.str_value:
            return

        for bit_pos, button in self.err_list:
            button.setVisible(bool(self.err_param.value & (1 << bit_pos)))

    def handle_warn_bitmap_changed(self):
        if not self.warn_param.str_value:
            return

        for bit_pos, button in self.warn_list:
            button.setVisible(bool(self.warn_param.value & (1 << bit_pos)))

        
