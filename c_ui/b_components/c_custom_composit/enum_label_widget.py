from typing import Type
from PySide6.QtWidgets import QWidget, QHBoxLayout

from b_core.b_datatype.param_enum import DescriptionEnum

from c_ui.b_components.a_custom_base.custom_label import CustomLabel

class EnumLabelWidget(QWidget):
    def __init__(self, name: str, enum_class: Type[DescriptionEnum], parent=None):
        super().__init__(parent)

        self.enum_class = enum_class

        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0) 
        self.layout.setSpacing(0) 

        self.lbl_label = CustomLabel(name)

        self.lbl_value = CustomLabel("-")

        self.layout.addWidget(self.lbl_label)
        self.layout.addWidget(self.lbl_value)
        self.layout.addStretch()

    def set_value(self, value:int):
        pass            
