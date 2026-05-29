from c_ui.b_control_packet.controls_with_label.l_base_widget import LBaseWidget

class LBaseReadOnlyWidget(LBaseWidget):
    def __init__(self, label_text="", label_width=150, parent=None):
        super().__init__(label_text = label_text, label_width=label_width, parent=parent)

    
