from PySide6.QtWidgets import QWidget, QHBoxLayout

from c_ui.b_control_packet.base import my_style
from c_ui.b_control_packet.controls.my_label import MyLabel

class LBaseWidget(QWidget):
    def __init__(self, label_text="", label_width=150, parent=None):
        super().__init__(parent)

        self.value_widget = None

        # 1. 레이아웃 구성
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(5)
        
        # 2. 메인 라벨 처리 로직
        self.lbl_label = MyLabel(label_text)
        self.lbl_label.setFixedWidth(label_width)
        self.layout.addWidget(self.lbl_label)
            
        # 3. Dirty 라벨 생성 (항상 생성하여 에러 방지)
        self.dirty_label = MyLabel("*")
        self.dirty_label.set_color(my_style.STYLE_ERR_COLOR)
        sp = self.dirty_label.sizePolicy()
        sp.setRetainSizeWhenHidden(True)
        self.dirty_label.setSizePolicy(sp)
        self.dirty_label.setVisible(False) # 초기에는 숨김
        self.layout.addWidget(self.dirty_label)     

    def add_widget(self, widget):
        self.layout.addWidget(widget, 1)   

    def set_error(self, value : bool):
        self.lbl_label.set_color(my_style.STYLE_ERR_COLOR if value else my_style.STYLE_LABEL_COLOR)

    def set_support(self, support : bool):
        if self.value_widget is not None:
            self.value_widget.set_support(support)
        
        
