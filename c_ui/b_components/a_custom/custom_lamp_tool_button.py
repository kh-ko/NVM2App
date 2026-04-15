from PySide6.QtWidgets import QToolButton
from PySide6.QtGui import QPainter, QColor
from PySide6.QtCore import Qt

class CustomLampToolButton(QToolButton):
    """
    배경 서비스 상태 등에 따라 램프(LED) 켜짐/꺼짐을 시각적으로 표시할 수 있는 커스텀 툴버튼입니다.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # 기본적으로 램프는 꺼진 상태로 시작
        self._is_accent_on = False
        
        # 기존 툴바의 스타일시트(hover 효과 등)가 그대로 적용되도록 속성 부여
        self.setProperty("menuBtn", "true")
        self.setStyleSheet("padding-left: 22px; padding-right: 12px;")

    def set_accent(self, state: bool):
        """
        [API] 램프의 상태를 설정합니다. (True: 켜짐, False: 꺼짐)
        백그라운드 서비스에서 상태 변경 시 이 메서드를 호출합니다.
        """
        if self._is_accent_on != state:
            self._is_accent_on = state
            self.update()  # 상태가 변경되면 버튼을 다시 그리도록(paintEvent 호출) 트리거

    def paintEvent(self, event):
        """
        버튼이 화면에 그려질 때 호출됩니다. 
        기본 버튼을 먼저 그리고, 그 위에 램프를 덧그립니다.
        """
        # 1. 원래 QToolButton의 디자인(배경, 텍스트, 호버 등)을 먼저 그립니다.
        super().paintEvent(event)

        # 2. QPainter를 이용해 램프(LED)를 그립니다.
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing) # 테두리를 부드럽게 처리

        # 램프 색상 결정
        if self._is_accent_on:
            lamp_color = QColor("#3fb950") # 켜짐 상태 (밝은 초록색 - GitHub 스타일)
            # 다른 색상을 원하시면 "#58a6ff" (파란색) 등으로 변경 가능합니다.
        else:
            lamp_color = QColor("#484f58") # 꺼짐 상태 (어두운 회색)

        painter.setBrush(lamp_color)
        painter.setPen(Qt.NoPen) # 테두리 선 없음

        # 램프 크기 및 위치 계산 (버튼 우측 상단에 배치)
        radius = 3       # 램프 반지름 크기 (총 지름 6px)
        margin_x = 8     # 우측 여백
        
        rect = self.rect()
        x = margin_x
        y = int((rect.height() / 2) - radius)

        # 원형 램프 그리기
        painter.drawEllipse(x, y, radius * 2, radius * 2)
        painter.end()