from PySide6.QtCore import Signal
from c_ui.b_control_packet.controls_with_label.l_base_widget import LBaseWidget

class LBaseReadWriteWidget(LBaseWidget):
    sig_value_changed = Signal()
    
    def __init__(self, label_text="", label_width=150, parent=None):
        super().__init__(label_text = label_text, label_width=label_width, parent=parent)

    def restore(self):
        if self.value_widget is not None and self.original_value is not None:
            self.value_widget.set_value(self.original_value)
            self.commit()
