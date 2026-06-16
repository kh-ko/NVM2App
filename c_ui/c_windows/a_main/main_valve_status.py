from typing import List, Tuple

from b_core.c_manager.parameter_manager import ParamManager

from c_ui.b_control_packet.controls.my_buttonwarn import MyButtonWarn
from c_ui.b_control_packet.layout.my_panel_widget import MyPanelWidget
from c_ui.b_control_packet.param.param_enum_ro_widget import ParamEnumReadOnlyWidget
from c_ui.b_control_packet.param.param_scale_ro_widget import ParamScaleReadOnlyWidget

class MainValveStatus(MyPanelWidget):
    def __init__(self, control_mode_param:str, posi_ctrl_speed_param:str, controller_select_param:str, warn_bitmap_param:str, err_bitmap_param:str,parent=None): # title의 기본값을 빈 문자열로 설정
        super().__init__(title="Status", parent = parent)

        self.warn_list: List[Tuple[int, MyButtonWarn]] = []
        self.err_list: List[Tuple[int, MyButtonWarn]] = []

        control_mode_label = ParamEnumReadOnlyWidget(control_mode_param, 217)
        self.add_widget(control_mode_label)

        posi_ctrl_speed_label = ParamScaleReadOnlyWidget(posi_ctrl_speed_param, 217)
        self.add_widget(posi_ctrl_speed_label)
        
        controller_select_label = ParamEnumReadOnlyWidget(controller_select_param, 217)
        self.add_widget(controller_select_label)

        self.warn_param = ParamManager().get_by_full_path(warn_bitmap_param)
        if self.warn_param and self.warn_param.ref_list:  
            self.warn_param.sig_value_changed.connect(self.handle_warn_bitmap_changed)

            for member in self.warn_param.ref_list:
                bit_pos = member.value
                description = member.description

                button = MyButtonWarn(text = description)
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

                button = MyButtonWarn(text = description)
                button.setVisible(False)
                button.clicked.connect(self.on_clicked_warn_err_button)

                self.add_widget(button)
                self.err_list.append((bit_pos, button))     

        self.add_stretch()         

    def add_widget(self, widget):
        """외부에서 위젯을 전달받아 패널 내부에 추가합니다."""
        self.scroll_layout.addWidget(widget)

    def add_stretch(self):
        """
        위젯을 다 추가한 후 마지막에 호출하면, 
        추가된 위젯들이 패널 상단으로 바짝 밀착되게(위로 정렬) 만들어줍니다.
        """
        self.scroll_layout.addStretch()          

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

        
