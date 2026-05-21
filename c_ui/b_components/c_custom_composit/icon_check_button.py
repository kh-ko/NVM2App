from PySide6.QtWidgets import QSizePolicy
from PySide6.QtWidgets import QPushButton, QHBoxLayout, QLabel
from PySide6.QtGui import QFont
from PySide6.QtCore import Qt

from c_ui.b_components.a_custom_base.custom_icon_check_label import CustomIconCheckLabel
from c_ui.b_components.a_custom_base.custom_icon_label import CustomIconLabel
from c_ui.b_components.a_custom_base.custom_label import CustomLabel
from c_ui.b_components.a_custom_base.custom_button import CustomButton

class IconCheckButton(CustomButton):
    def __init__(self, text="", parent=None):
        super().__init__(parent)

        self.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Minimum)
        
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(10, 10, 10, 10) 
        self.layout.setSpacing(5) 
        self.layout.setSizeConstraint(QHBoxLayout.SetMinimumSize)

        self.lbl_icon = CustomIconCheckLabel()
        self.lbl_icon.setAttribute(Qt.WA_TransparentForMouseEvents)

        self.lbl_text = CustomLabel(text)
        self.lbl_text.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.lbl_text.setAlignment(Qt.AlignCenter)

        self.layout.addWidget(self.lbl_icon, 0)
        self.layout.addWidget(self.lbl_text, 1)

    def set_check(self, value:bool):
        self.lbl_icon.set_check(value)

