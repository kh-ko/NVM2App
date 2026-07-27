from PySide6.QtWidgets import QVBoxLayout

from c_ui.b_control_packet.base import my_style
from c_ui.b_control_packet.controls.my_label import MyLabel
from c_ui.b_control_packet.base.base_groupbox import BaseGroupBox

class LBaseVerticalWidget(BaseGroupBox):   
    def __init__(self, label_text="", enable_wrap_border = True, parent=None):
        super().__init__(text=label_text, enable_border=enable_wrap_border, parent=parent)
        
        self.enable_wrap_border = enable_wrap_border
        self.value_widget = None
       
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 5, 0, 0) 
        self.layout.setSpacing(5)

        self.dirty_label = MyLabel("*")
        self.dirty_label.set_color(my_style.STYLE_ERR_COLOR)
        sp = self.dirty_label.sizePolicy()
        sp.setRetainSizeWhenHidden(True)
        self.dirty_label.setSizePolicy(sp)
        self.dirty_label.setVisible(False)
        self.title_layout.addWidget(self.dirty_label,1)   
        self.title_layout.addStretch()

        self.enable_conditions = []

    def add_widget(self, widget):
        self.layout.addWidget(widget)

    def set_error(self, value : bool):
        self.lbl_label.set_color(my_style.STYLE_ERR_COLOR if value else my_style.STYLE_LABEL_COLOR)

    def set_support(self, support : bool):
        if self.value_widget is not None:
            self.value_widget.set_support(support)

    def reg_enable_condition(self, ref_widget, conditions):
        self.enable_conditions.append((ref_widget, conditions))
        ref_widget.sig_value_changed.connect(self.on_enable_condition_changed)
        self.on_enable_condition_changed()

    def on_enable_condition_changed(self):
        for ref_widget, conditions in self.enable_conditions:
            if ref_widget.get_value() not in conditions:
                self.setEnabled(False)
                self.restore()
                return
        self.setEnabled(True)

    
