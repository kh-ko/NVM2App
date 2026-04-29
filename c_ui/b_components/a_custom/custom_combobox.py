from PySide6.QtCore import QEvent, Qt
from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel, QComboBox, QSizePolicy, QGraphicsOpacityEffect

from c_ui.b_components.a_custom.custom_label import CustomLabel

class CustomComboBox(QWidget):
    def __init__(self, label_text="", label_width=150, parent=None):
        """
        :param label_text: 라벨에 표시할 문구 (없거나 빈 문자열이면 라벨 생성 안 함)
        :param label_width: 라벨의 고정 폭
        :param parent: 부모 위젯
        """
        super().__init__(parent)
        
        # 콤보박스는 주로 '선택된 인덱스'로 변경 여부를 추적합니다.
        self._original_index = -1

        # 1. 레이아웃 구성
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(5)
        
        # 2. 메인 라벨 처리 로직
        if label_text:
            self.label = CustomLabel(label_text)
            self.label.setFixedWidth(label_width)
            self.layout.addWidget(self.label)
        else:
            self.label = None
        
        # 3. Dirty 라벨 생성 (항상 생성하여 에러 방지)
        self.dirty_label = QLabel("*")
        self.dirty_label.setStyleSheet("color: red; font-weight: bold; font-size: 14px;")
        sp = self.dirty_label.sizePolicy()
        sp.setRetainSizeWhenHidden(True)
        self.dirty_label.setSizePolicy(sp)
        self.dirty_label.setVisible(False) # 초기에는 숨김
        self.layout.addWidget(self.dirty_label)
        
        # 4. 콤보박스 생성 및 추가
        self.combo_box = QComboBox()
        self.layout.addWidget(self.combo_box, 1)

        # 인덱스가 변경될 때마다 Dirty 체크
        self.combo_box.activated.connect(self._on_index_changed)

        # 5. 주요 시그널 래핑
        self.currentIndexChanged = self.combo_box.currentIndexChanged
        self.currentTextChanged = self.combo_box.currentTextChanged
        self.activated = self.combo_box.activated
        self.highlighted = self.combo_box.highlighted

        self.__color_design()

    def __color_design(self):
        self.setStyleSheet("""
            /* 콤보박스 기본 디자인 */
            QComboBox {
                color: black;
                border: 1px solid #dcdcdc;
                border-radius: 4px;
                padding: 4px 8px;
                background-color: white;
                min-height: 24px;
            }
            
            /* 콤보박스에 마우스를 올렸을 때 */
            QComboBox:hover {
                border: 1px solid #1976d2;
            }
            
            /* 콤보박스 우측 화살표 영역 */
            QComboBox::drop-down {
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 20px;
                border-left: 1px solid #dcdcdc;
            }

            /* ★ 콤보박스 드롭다운 팝업 리스트 스타일 (테두리 추가) ★ */
            QComboBox QAbstractItemView {
                border: 1px solid #a0a0a0; /* 팝업창 테두리 추가 */
                border-radius: 4px;
                background-color: white;
                outline: 0px; /* 클릭 시 생기는 점선 테두리 제거 */
                selection-background-color: #e3f2fd; /* 선택 항목 배경색 */
                selection-color: #1976d2;            /* 선택 항목 글자색 */
            }
        """)
    # ==========================================
    # QComboBox 주요 메서드 래핑
    # ==========================================
    def addItem(self, text: str, userData=None):
        self.combo_box.addItem(text, userData)
        
    def addItems(self, texts: list):
        self.combo_box.addItems(texts)

    def clear(self):
        # 목록을 초기화하면 원본 인덱스도 초기화하고 Dirty 마커를 숨김
        self._original_index = -1
        self.combo_box.clear()
        self.dirty_label.setVisible(False)

    def currentText(self) -> str:
        return self.combo_box.currentText()

    def currentData(self, role=Qt.UserRole):
        return self.combo_box.currentData(role)

    def currentIndex(self) -> int:
        return self.combo_box.currentIndex()

    def setCurrentIndex(self, index: int):
        """API를 통해 강제로 인덱스를 바꿀 경우, 이를 '원본'으로 취급하여 Dirty 마커를 띄우지 않음"""
        self._original_index = index
        self.combo_box.setCurrentIndex(index)
        self.dirty_label.setVisible(False)
        
    def setCurrentText(self, text: str):
        self.combo_box.setCurrentText(text)

    def findData(self, data, role=Qt.UserRole, flags=Qt.MatchExactly) -> int:
        return self.combo_box.findData(data, role, flags)
        
    def findText(self, text: str, flags=Qt.MatchExactly) -> int:
        return self.combo_box.findText(text, flags)

    def setFocus(self, reason=Qt.OtherFocusReason):
        self.combo_box.setFocus(reason)

    # ==========================================
    # 라벨 관련 메서드 래핑
    # ==========================================
    def setLabelText(self, text: str):
        if self.label:
            self.label.setText(text)
        
    def labelText(self) -> str:
        return self.label.text() if self.label else ""

    # ==========================================
    # Dirty(변경 추적) 관련 기능
    # ==========================================
    def isDirty(self) -> bool:
        """현재 인덱스가 원본 인덱스와 다른지 확인"""
        return self.combo_box.currentIndex() != self._original_index
        
    def commit(self):
        """현재 선택된 항목을 '새로운 원본'으로 확정 짓고 Dirty 표시를 지움 (저장 버튼 누른 직후 등 활용)"""
        self._original_index = self.combo_box.currentIndex()
        self.dirty_label.setVisible(False)

    def _on_index_changed(self, index: int):
        """사용자가 콤보박스 값을 변경하면 원본과 비교하여 Dirty 표시를 켭니다."""
        # 아이템이 하나도 없을 때(-1)는 무시하도록 처리 가능
        is_dirty = (index != self._original_index)
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
