from PySide6.QtCore import QEvent
from PySide6.QtWidgets import QLabel, QGraphicsOpacityEffect

class CustomLabel(QLabel):
    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self.__color_design("transparent")

    def __color_design(self, bg_color: str):
        # f-string을 사용하여 텍스트 색상은 유지하고 배경색만 변수로 받습니다.
        self.setStyleSheet(f"""
            QLabel {{
                color: black;
                background-color: {bg_color};
            }}
        """)

    def set_bg_color(self, color_code: str):
        self.__color_design(color_code)

    def changeEvent(self, event: QEvent):
        """위젯의 상태 변화(Enabled 등)를 감시하고 처리합니다."""
        super().changeEvent(event) # 기본 이벤트 처리 유지
        
        # 상태 변화 이벤트 중 '활성화/비활성화(EnabledChange)' 이벤트인 경우에만 작동
        if event.type() == QEvent.Type.EnabledChange:
            
            # 1. 그래픽스 효과 객체가 없으면 새로 생성해서 달아줌
            effect = self.graphicsEffect()
            if not isinstance(effect, QGraphicsOpacityEffect):
                effect = QGraphicsOpacityEffect(self)
                self.setGraphicsEffect(effect)
            
            # 2. 현재 위젯이 진짜 활성화 상태인지 확인 (부모 때문에 꺼졌는지도 모두 포함됨)
            if self.isEnabled():
                effect.setOpacity(1.0) # 원래 상태
            else:
                effect.setOpacity(0.5) # 반투명 상태        