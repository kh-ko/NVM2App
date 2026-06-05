from PySide6.QtCore import Signal

from c_ui.b_control_packet.base import my_style

from c_ui.b_control_packet.controls_with_label.l_base_v_widget import LBaseVerticalWidget

class LBaseVerticalReadOnlyWidget(LBaseVerticalWidget):
    sig_value_changed = Signal()
    
    def __init__(self, label_text="", enable_wrap_border = False, parent=None):
        super().__init__(label_text = label_text, enable_wrap_border = enable_wrap_border, parent=parent)

    
