from PySide6.QtCore import QEvent, Qt
from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel, QLineEdit, QGraphicsOpacityEffect

from c_ui.b_components.a_custom.custom_label import CustomLabel
class CustomLineEdit(QWidget):
    def __init__(self, label_text="", label_width=150, parent=None):
        """
        :param label_text: 라벨에 표시할 문구 (없거나 빈 문자열이면 라벨 생성 안 함)
        :param label_width: 라벨의 고정 폭
        :param parent: 부모 위젯
        """
        super().__init__(parent)
        
        self._original_text = ""

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
        
        self.dirty_label = QLabel("*")
        self.dirty_label.setStyleSheet("color: red; font-weight: bold; font-size: 14px;")
        sp = self.dirty_label.sizePolicy()
        sp.setRetainSizeWhenHidden(True)
        self.dirty_label.setSizePolicy(sp)
        self.dirty_label.setVisible(False) # 초기에는 숨김
        self.layout.addWidget(self.dirty_label)

        # 3. 라인 에디트 생성 및 추가
        self.line_edit = QLineEdit()
        self.line_edit.setStyleSheet("background-color: white; color: black;")
        self.layout.addWidget(self.line_edit, 1)

        self.line_edit.textEdited.connect(self._on_text_edited)

        # 시그널 래핑 (동일하게 유지)
        self.textChanged = self.line_edit.textChanged
        self.textEdited = self.line_edit.textEdited
        self.returnPressed = self.line_edit.returnPressed
        self.editingFinished = self.line_edit.editingFinished
        self.selectionChanged = self.line_edit.selectionChanged

    # 주요 메서드 래핑
    def text(self) -> str:
        return self.line_edit.text()

    def setText(self, text: str):
        self._original_text = text
        self.line_edit.setText(text)
        self.dirty_label.setVisible(False)

    def clear(self):
        self.line_edit.clear()

    def setPlaceholderText(self, text: str):
        self.line_edit.setPlaceholderText(text)

    def setReadOnly(self, read_only: bool):
        self.line_edit.setReadOnly(read_only)

    def setFocus(self, reason=Qt.OtherFocusReason):
        self.line_edit.setFocus(reason)

    # 라벨 관련 안전한 래핑 (라벨이 없을 수도 있으므로 체크 필요)
    def setLabelText(self, text: str):
        if self.label:
            self.label.setText(text)
        
    def labelText(self) -> str:
        return self.label.text() if self.label else ""

    def isDirty(self) -> bool:
        """현재 값이 원본과 달라졌는지 확인 (추가 권장)"""
        return self.line_edit.text() != self._original_text
        
    def commit(self):
        """현재 선택된 항목을 '새로운 원본'으로 확정 짓고 Dirty 표시를 지움 (저장 버튼 누른 직후 등 활용)"""
        self._original_text = self.line_edit.text()
        self.dirty_label.setVisible(False)   
        
    def _on_text_edited(self, current_text):
        """텍스트가 바뀔 때 원본과 다르면 Dirty 표시를 켭니다."""
        is_dirty = (current_text != self._original_text)
        self.dirty_label.setVisible(is_dirty)     

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