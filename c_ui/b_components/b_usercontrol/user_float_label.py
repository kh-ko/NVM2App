from PySide6.QtCore import QEvent, Qt
from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel, QGraphicsOpacityEffect

from b_core.b_datatype.param_enum import DescriptionEnum
from c_ui.b_components.a_custom.custom_label import CustomLabel
from b_core.c_manager.parameter_manager import ParamManager

class UserFloatLabel(QWidget):
    def __init__(self, label_text="", param_full_path="",label_width=150, parent=None):
        """
        :param label_text: 라벨에 표시할 문구 (없거나 빈 문자열이면 라벨 생성 안 함)
        :param label_width: 라벨의 고정 폭
        :param parent: 부모 위젯
        """
        super().__init__(parent)

        # 1. 레이아웃 구성
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(5)
        
        # 2. 라벨 처리 로직
        # label_text가 존재하고 빈 문자열이 아닐 경우에만 QLabel 추가
        if label_text:
            self.label = CustomLabel(label_text)
            self.label.setFixedWidth(label_width) # 입력받은 너비로 폭 고정
            self.layout.addWidget(self.label)
        else:
            self.label = None

        # 3. 라인 에디트 생성 및 추가
        self.label_value = CustomLabel("-")
        self.label_value.setStyleSheet("background-color: transparent; color: black;")
        self.layout.addWidget(self.label_value, 1)

        if param_full_path:
            self.param = ParamManager().get_by_full_path(param_full_path)
            if self.param:
                self.param.sig_value_changed.connect(self.handle_value_changed)
                self.param.sig_is_err_changed.connect(self.handle_is_err_changed)
                self.param.sig_is_not_support_changed.connect(self.handle_is_not_support_changed)
                #self.param.sig_dirty_changed.connect(self.handle_dirty_changed)
                self.handle_value_changed()
                self.handle_is_err_changed()
                self.handle_is_not_support_changed()        

    # 주요 메서드 래핑
    def text(self) -> str:
        return self.label_value.text()

    def setText(self, text: str):
        self.label_value.setText(text)

    def clear(self):
        self.label_value.setText("-")

    # 라벨 관련 안전한 래핑 (라벨이 없을 수도 있으므로 체크 필요)
    def setLabelText(self, text: str):
        if self.label:
            self.label.setText(text)
        
    def labelText(self) -> str:
        return self.label.text() if self.label else ""

    def handle_value_changed(self):
        if self.param:
            self.setText(self.param.str_value)
            
    def handle_is_err_changed(self):
        if self.param.is_err:
            self.label_value.setStyleSheet("background-color: transparent; color: red;")
        else:
            self.label_value.setStyleSheet("background-color: transparent; color: black;")

    def handle_is_not_support_changed(self):
        if self.param.is_not_support:
            self.setVisible(False)
        else:
            self.setVisible(True)

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