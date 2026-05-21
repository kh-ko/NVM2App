from typing import List, Dict, Union, Type, Optional

from PySide6.QtCore import QEvent, Qt
from PySide6.QtWidgets import QGroupBox,QWidget, QHBoxLayout, QVBoxLayout, QLabel, QGraphicsOpacityEffect

from b_core.b_datatype.param_enum import DescriptionEnum
from b_core.c_manager.parameter_manager import ParamManager
from c_ui.b_components.a_custom_base.custom_icon_check_label import CustomIconCheckLabel


class ParamBitmapLabelWidget(QGroupBox):
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
        
        if self.param:
            for enum_item in self.param.ref_list:
                label = CustomIconCheckLabel(enum_item.description)
                self.layout.addWidget(label)
                self.item_list.append((label, enum_item.value))

            self.param.sig_value_changed.connect(self.handle_value_changed)
            self.param.sig_is_err_changed.connect(self.handle_is_err_changed)
            self.param.sig_is_not_support_changed.connect(self.handle_is_not_support_changed)
            self.handle_value_changed()
            self.handle_is_err_changed()
            self.handle_is_not_support_changed()    

    def handle_value_changed(self):
        if self.param.value is None:
            return

        bitmap = self.param.value

        for label, value in self.item_list:
            is_set = (bitmap & (1 << value)) != 0
            label.set_check(is_set)
        #if self.param:
        #    self.param.ref_list : Optional[Type[DescriptionEnum]] 

        #    if not self.param.ref_list or not self.param.str_value:
        #        self.setText("Unknown Value")
        #        return

        #    self.setText(self.param.ref_list(self.param.value).description)
        pass
            
    def handle_is_err_changed(self):
        if self.param.is_err:
            self.setStyleSheet("""
            QGroupBox { 
                background-color: transparent;
                font-size: 14px; 
                font-weight: normal; 
                color: red; 
                border: 1px solid #dcdcdc; 
                margin-top: 10px; 
            }
        """)
        else:
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

    def handle_is_not_support_changed(self):
        #if self.param.is_not_support:
        #    self.setText("not support")
        #    self.setEnabled(False)
        #else:
        #    self.setEnabled(True)
        pass
    