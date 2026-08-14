from typing import List, Tuple
from PySide6.QtCore import Signal

from c_ui.b_control_ver2.b_base import icons
from c_ui.b_control_ver2.a_theme.tokens import tokens
from c_ui.b_control_ver2.b_base.buttons import BaseButton
from c_ui.b_control_ver2.b_base.containers import ScrolledPanelWidget
from c_ui.b_control_ver2.d_param.param_values import ParamReadOnlyEnumValueWidget
from c_ui.b_control_ver2.d_param.param_values import ParamReadOnlyScaleValueWidget

class MainStatusPanel(ScrolledPanelWidget):
    sig_warn_err_clicked = Signal()
    def __init__(self, parent=None): 
        super().__init__(title="Status", is_big_title=True, parent = parent)
        self._ctrl_mode_param = None
        self._posi_ctrl_speed_param = None
        self._pres_controller_selector_param = None
        self._warn_bitmap_param = None
        self._err_bitmap_param = None
        self._warn_list: List[Tuple[int, BaseButton]] = []
        self._err_list: List[Tuple[int, BaseButton]] = []

    def set_ctrl_mode_param(self, param):
        self._ctrl_mode_param = param
        widget = ParamReadOnlyEnumValueWidget(param_full_path = f"{param.path}.{param.name}", force_label_text = "Control Mode", label_width = 180)
        self.add_widget(widget)

    def set_posi_ctrl_speed_param(self, param):
        self._posi_ctrl_speed_param = param
        widget = ParamReadOnlyScaleValueWidget(param_full_path = f"{param.path}.{param.name}", force_label_text = "Pos. Control Speed (%)", label_width = 180)
        self.add_widget(widget)

    def set_pres_controller_selector_param(self, param):
        self._pres_controller_selector_param = param
        widget = ParamReadOnlyEnumValueWidget(param_full_path = f"{param.path}.{param.name}", force_label_text = "Controller Selector Used", label_width = 180)
        self.add_widget(widget)

    def set_warn_bitmap_param(self, param):
        self._warn_bitmap_param = param

        if param is not None and param.ref_list:  
            self._warn_bitmap_param.sig_value_changed.connect(self.handle_warn_bitmap_changed)

            for member in param.ref_list:
                bit_pos = member.value
                description = member.description

                button = BaseButton(glyph = icons.GLYPH_WARN, glyph_color = tokens().warning, text = description)
                button.setVisible(False)
                button.clicked.connect(self.on_clicked_warn_err_button)

                self.add_widget(button)
                self._warn_list.append((bit_pos, button))

    def set_err_bitmap_param(self, param):
        self._err_bitmap_param = param

        if param is not None and param.ref_list:  
            self._err_bitmap_param.sig_value_changed.connect(self.handle_err_bitmap_changed)

            for member in param.ref_list:
                bit_pos = member.value
                description = member.description

                button = BaseButton(glyph = icons.GLYPH_WARN, glyph_color = tokens().warning, text = description)
                button.setVisible(False)
                button.clicked.connect(self.on_clicked_warn_err_button)

                self.add_widget(button)
                self._err_list.append((bit_pos, button))    

    def on_clicked_warn_err_button(self):
        self.sig_warn_err_clicked.emit()

    def handle_warn_bitmap_changed(self):
        if self._warn_bitmap_param.value is None:
            return

        for bit_pos, button in self._warn_list:
            button.setVisible(bool(self._warn_bitmap_param.value & (1 << bit_pos)))

    def handle_err_bitmap_changed(self):
        if self._err_bitmap_param.value is None:
            return
            
        for bit_pos, button in self._err_list:
            button.setVisible(bool(self._err_bitmap_param.value & (1 << bit_pos)))