from typing import List, Dict, Union, Type, Optional

from PySide6.QtCore import QEvent, Qt
from PySide6.QtWidgets import QGroupBox, QVBoxLayout, QLabel, QGraphicsOpacityEffect

from b_core.b_datatype.param_enum import DescriptionEnum
from b_core.c_manager.parameter_manager import ParamManager
from c_ui.b_components.c_custom_composit.enum_label_widget import EnumLabelWidget

class ParamDigiLabelWidget(QGroupBox):
    def __init__(self, param_full_path="", parent=None):
        super().__init__(parent)
        self.item_list = []
        self.param = ParamManager().get_by_full_path(param_full_path) 

        self.setTitle(self.param.name)    
        self.setStyleSheet("""
            QGroupBox { 
                background-color: transparent;
                font-size: 14px; 
                font-weight: normal; 
                color: black; 
                border: 1px solid #dcdcdc; 
                margin-top: 10px; 
            }
        """)

        # 1. 레이아웃 구성
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(10, 10, 10, 10)
        self.layout.setSpacing(5)
        
        index = 0
        if self.param:
            for enum_name, enum_class in self.param.ref_list:
                label = EnumLabelWidget(enum_name, enum_class)
                self.layout.addWidget(label)
                self.item_list.append((label, index))
                index += 1

            self.param.sig_value_changed.connect(self.handle_value_changed)
            self.param.sig_is_err_changed.connect(self.handle_is_err_changed)
            self.param.sig_is_not_support_changed.connect(self.handle_is_not_support_changed)
            self.handle_value_changed()
            self.handle_is_err_changed()
            self.handle_is_not_support_changed()  

    def handle_value_changed(self):
        #if self.param:
        #    self.param.ref_list : Optional[Type[DescriptionEnum]] 

        #    if not self.param.ref_list or not self.param.str_value:
        #        self.setText("Unknown Value")
        #        return

        #    self.setText(self.param.ref_list(self.param.value).description)
        pass
            
    def handle_is_err_changed(self):
        #if self.param.is_err:
        #    self.label.setStyleSheet("background-color: transparent; color: red;")
        #else:
        #    self.label.setStyleSheet("background-color: transparent; color: black;")
        pass

    def handle_is_not_support_changed(self):
        #if self.param.is_not_support:
        #    self.setText("not support")
        #    self.setEnabled(False)
        #else:
        #    self.setEnabled(True)
        pass