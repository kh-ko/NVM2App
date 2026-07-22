from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout
from PySide6.QtWidgets import QSizePolicy
from PySide6.QtWidgets import QWidget

from c_ui.b_control_packet.base.base_label import BaseLabel
from c_ui.b_control_packet.controls.my_iconcheck import MyIconCheck

class MyValueLabelCheck(QWidget):

    def __init__(self, label_text="", parent=None):
        super().__init__(parent = parent)
        self.ori_value = None

        self.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Minimum)
        
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0) 
        self.layout.setSpacing(5) 
        self.layout.setSizeConstraint(QHBoxLayout.SetMinimumSize)

        self.lbl_icon = MyIconCheck()
        self.lbl_icon.setAttribute(Qt.WA_TransparentForMouseEvents)

        self.lbl_text = BaseLabel(label_text)
        self.lbl_text.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.lbl_text.setAlignment(Qt.AlignLeft)

        self.layout.addWidget(self.lbl_icon, 0)
        self.layout.addWidget(self.lbl_text, 1)

    def set_text(self, text :str):
        self.lbl_text.set_text(text)

    def set_value(self, value:bool):
        self.ori_value = value

        try:
            check_value = bool(value)
            self.lbl_icon.set_check(check_value)    
            self.setEnabled(True)
        except Exception:
            self.set_text(f"Unknown ({value})")   
            self.setEnabled(False)

    def set_support(self, support : bool):
        if not support:
            self.set_text("Not Support")        
            self.setEnabled(False)
        else:
            self.set_value(self.ori_value)