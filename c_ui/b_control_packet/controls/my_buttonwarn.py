
from PySide6.QtWidgets import QHBoxLayout
from PySide6.QtWidgets import QSizePolicy
from PySide6.QtCore import Qt

from c_ui.b_control_packet.base.base_button import BaseButton
from c_ui.b_control_packet.base.base_label import BaseLabel
from c_ui.b_control_packet.controls.my_iconwarn import MyIconWarn

class MyButtonWarn(BaseButton):
    def __init__(self, text : str = "", parent=None):
        super().__init__(text = "", parent = parent)

        self.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Minimum)
        
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(10, 10, 10, 10) 
        self.layout.setSpacing(5) 
        self.layout.setSizeConstraint(QHBoxLayout.SetMinimumSize)

        self.lbl_icon = MyIconWarn()
        self.lbl_icon.setAttribute(Qt.WA_TransparentForMouseEvents)

        self.lbl_text = BaseLabel(text)
        self.lbl_text.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.lbl_text.setAlignment(Qt.AlignCenter)

        self.layout.addWidget(self.lbl_icon, 0)
        self.layout.addWidget(self.lbl_text, 1)