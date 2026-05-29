from PySide6.QtCore import QEvent
from PySide6.QtGui import QEnterEvent
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QWidget
from PySide6.QtWidgets import QGroupBox
from PySide6.QtWidgets import QHBoxLayout

from c_ui.b_control_packet.base import my_style
from c_ui.b_control_packet.controls.my_label import MyLabel

class BaseGroupBox(QGroupBox):    
    def __init__(self, text="", enable_border = True, parent=None):
        super().__init__(f"{text}", parent)
        self.setProperty("isHovered", False)

        self.title_widget = QWidget(self)

        self.title_layout = QHBoxLayout(self.title_widget)
        self.title_layout.setContentsMargins(0, 0, 0, 0)
        self.title_layout.setSpacing(0)

        self.lbl_label = MyLabel(text)

        self.title_layout.addWidget(self.lbl_label)

        if enable_border:
            self.set_color(my_style.STYLE_BORDER_COLOR, my_style.STYLE_HOVER_COLOR)
        else:
            self.set_color("transparent", "transparent")

    def set_color(self, border_color: str, hover_border_color: str):
        #base_label_color = QColor(label_color)
        #r = base_label_color.red()
        #g = base_label_color.green()
        #b = base_label_color.blue()
        #alpha = base_label_color.alpha()
        #label_disabled_color = f"rgba({r}, {g}, {b}, {alpha * 0.5})"

        base_border_color = QColor(border_color)
        r = base_border_color.red()
        g = base_border_color.green()
        b = base_border_color.blue()
        alpha = base_border_color.alpha()
        border_disabled_color = f"rgba({r}, {g}, {b}, {alpha * 0.5})"     

        #self.lbl_label.set_color(label_color)

        self.setStyleSheet(f"""
            BaseGroupBox {{
                background-color: transparent;
                font-size: 14px; 
                font-weight: normal;
                margin-top: 10px; 
                border: 1px solid {border_color};
                border-radius: 4px;
                color: transparent;
            }}
            BaseGroupBox:disabled {{
                border: 1px solid {border_disabled_color};
            }}
            BaseGroupBox[isHovered="true"] {{
                border: 1px solid {hover_border_color};
            }}
        """)

    def enterEvent(self, event: QEnterEvent):
        self.setProperty("isHovered", True)
        self.style().unpolish(self) # 스타일 강제 초기화
        self.style().polish(self)   # 스타일 재적용 (변경된 속성 반영)
        super().enterEvent(event)

    def leaveEvent(self, event: QEvent):
        self.setProperty("isHovered", False)
        self.style().unpolish(self)
        self.style().polish(self)
        super().leaveEvent(event)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        
        # 타이틀 위젯을 (x=10, y=0) 위치로 강제 이동 (테두리 선에 걸치는 느낌)
        self.title_widget.move(10, 0)
        
        # 내용물(글자) 길이에 맞춰서 위젯 크기를 자동으로 조절
        self.title_widget.resize(self.title_widget.sizeHint())
        

        
