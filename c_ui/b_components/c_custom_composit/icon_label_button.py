from PySide6.QtWidgets import QSizePolicy, QWidget
from PySide6.QtWidgets import QPushButton, QHBoxLayout, QLabel
from PySide6.QtGui import QFont
from PySide6.QtCore import Qt

from c_ui.b_components.a_custom_base.custom_icon_label import CustomIconLabel
from c_ui.b_components.a_custom_base.custom_label import CustomLabel
from c_ui.b_components.a_custom_base.custom_button import CustomButton

class IconLabelButton(CustomButton):
    def __init__(self, text="", icon_char="", icon_color ="black", icon_size_scale = 1.0, parent=None):
        super().__init__(parent)

        self.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Minimum)
        
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0) 
        self.layout.setSpacing(5) 
        self.layout.setSizeConstraint(QHBoxLayout.SetMinimumSize)

        self.lbl_icon = CustomIconLabel(text=icon_char, color = icon_color, icon_size_scale = icon_size_scale)
        self.lbl_icon.setAttribute(Qt.WA_TransparentForMouseEvents)

        self.lbl_text = CustomLabel(text)
        self.lbl_text.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.lbl_text.setAlignment(Qt.AlignCenter)

        self.layout.addWidget(self.lbl_icon, 0)
        self.layout.addWidget(self.lbl_text, 1)

        super().set_color(CustomButton.LABEL_COLOR, "transparent")

    def set_icon(self, icon:str):
        self.lbl_icon.setText(icon)

    def set_icon_colors(self, color: str):
        self.lbl_icon.set_color(color)

    def set_text_color(self, color: str):
        self.lbl_text.set_color(color)
