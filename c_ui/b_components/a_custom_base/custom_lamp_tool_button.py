from PySide6.QtWidgets import QStyle
from PySide6.QtWidgets import QStyleOptionToolButton
from PySide6.QtWidgets import QToolButton
from PySide6.QtGui import QPainter, QColor
from PySide6.QtCore import Qt

class CustomLampToolButton(QToolButton):
    LAMP_ON_COLOR = QColor("#3fb950")   # 밝은 초록
    LAMP_OFF_COLOR = QColor("#484f58")  # 어두운 회색

    def __init__(self, parent=None):
        super().__init__(parent)
        
        self._is_accent_on = False
        
        self.setProperty("menuBtn", "true")
        self.setStyleSheet("padding-left: 22px; padding-right: 12px;")

    def set_accent(self, state: bool):
        if self._is_accent_on != state:
            self._is_accent_on = state
            self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        option = QStyleOptionToolButton()
        self.initStyleOption(option)
        self.style().drawComplexControl(QStyle.ComplexControl.CC_ToolButton, option, painter, self)

        lamp_color = self.LAMP_ON_COLOR if self._is_accent_on else self.LAMP_OFF_COLOR
        painter.setBrush(lamp_color)
        painter.setPen(Qt.NoPen)

        radius = 3
        margin_x = 8
        
        rect = self.rect()
        x = margin_x
        y = int((rect.height() / 2) - radius)

        # 원형 램프 그리기
        painter.drawEllipse(x, y, radius * 2, radius * 2)
        painter.end()