from PySide6.QtCore import QEvent, Qt, Signal
from PySide6.QtWidgets import QGroupBox, QHBoxLayout, QDoubleSpinBox, QGraphicsOpacityEffect

from b_core.c_manager.parameter_manager import ParamManager

from c_ui.a_converter.pressure_converter_manager import PresConverterManager

class PresInputInMain(QGroupBox):
    editingFinished = Signal()

    def __init__(self, title_text="", param_full_path = "", parent=None):
        """
        :param title_text: 그룹박스 타이틀에 표시할 문구
        :param parent: 부모 위젯
        """
        super().__init__(parent)
        
        self.converter = PresConverterManager()  

        # 💡 원본 타이틀 텍스트를 기억하기 위한 변수 추가
        self._base_title = title_text
        self.setTitle(self._base_title)

        self.setStyleSheet("""
            QGroupBox { 
                font-size: 14px; 
                font-weight: normal; 
                color: black; 
                border: 1px solid #dcdcdc; 
                margin-top: 10px; 
            }
        """)

        
        self._original_value = 0.0
        self._is_enter_pressed = False

        # 1. 레이아웃 구성 (그룹박스 내부)
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(0, 5, 0, 0) 
        self.layout.setSpacing(5)
        
        # 기존의 self.dirty_label 관련 코드는 모두 삭제되었습니다.

        # 2. 라인 에디트(스핀박스) 생성 및 추가
        self.line_edit = QDoubleSpinBox()
        self.line_edit.setStyleSheet("background-color: white; color: black; border: none;")
        self.line_edit.setRange(-3.4028235e38, 3.4028235e38)
        self.layout.addWidget(self.line_edit, 1)

        self.line_edit.valueChanged.connect(self._on_text_edited)

        # 시그널 래핑
        self.valueChanged = self.line_edit.valueChanged
        self.textChanged = self.line_edit.textChanged
        # self.editingFinished = self.line_edit.editingFinished (삭제 및 클래스 Signal로 대체됨)

        self.line_edit.installEventFilter(self)

        self.param = ParamManager().get_by_full_path(param_full_path)

        if self.param:
            self.param.sig_value_changed.connect(self.handle_value_changed)
            self.param.sig_is_err_changed.connect(self.handle_is_err_changed)
            self.param.sig_is_not_support_changed.connect(self.handle_is_not_support_changed)
            self.handle_value_changed()
            self.handle_is_err_changed()
            self.handle_is_not_support_changed()   
        else:
            print(f"PosiInputInMain: {param_full_path} parameter is not found")

    def eventFilter(self, obj, event):
        if obj == self.line_edit:
            if event.type() == QEvent.Type.KeyPress:
                if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                    self._is_enter_pressed = True
                    self.line_edit.clearFocus() # 포커스 해제 (이로 인해 FocusOut 이벤트가 즉시 발생함)
                    return True # 엔터키 이벤트 소비
            
            elif event.type() == QEvent.Type.FocusOut:
                if self._is_enter_pressed:
                    # Enter 키에 의한 포커스 아웃인 경우
                    self._is_enter_pressed = False
                    self.editingFinished.emit() # 값은 유지하고 시그널만 발생
                else:
                    # 마우스 클릭 등 단순 포커스 아웃인 경우
                    self.line_edit.blockSignals(True)
                    self.line_edit.setValue(self._original_value)
                    self.line_edit.blockSignals(False)
                    self._update_title_display()
                return False # 기본 포커스 아웃 이벤트는 처리되도록 둠
        return super().eventFilter(obj, event)

    # --- 내부 타이틀 업데이트 헬퍼 메서드 ---
    def _update_title_display(self):
        """현재 Dirty 상태에 따라 그룹박스 타이틀을 업데이트합니다."""
        if self.isDirty():
            # 값이 바뀌었다면 타이틀 끝에 * 표시를 붙임
            self.setTitle(f"{self._base_title} *")
        else:
            # 원본 값과 같다면 기본 타이틀로 복구
            self.setTitle(self._base_title)

    # --- 주요 메서드 래핑 ---
    def value(self) -> float:
        return self.line_edit.value()

    def setValue(self, val: float):
        self._original_value = val
        
        self.line_edit.blockSignals(True)
        self.line_edit.setValue(val)
        self.line_edit.blockSignals(False) 
        
        self._update_title_display() # 타이틀 업데이트

    def setDecimals(self, decimals: int):
        self.line_edit.setDecimals(decimals)

    def setRange(self, minimum: float, maximum: float):
        self.line_edit.setRange(minimum, maximum)

    def setAlignment(self, alignment: Qt.AlignmentFlag):
        self.line_edit.setAlignment(alignment)

    def setSuffix(self, suffix: str):
        self.line_edit.setSuffix(suffix)

    def setPrefix(self, prefix: str):
        self.line_edit.setPrefix(prefix)

    def clear(self):
        self.line_edit.clear()

    def setReadOnly(self, read_only: bool):
        self.line_edit.setReadOnly(read_only)

    def setFocus(self, reason=Qt.OtherFocusReason):
        self.line_edit.setFocus(reason)

    # 💡 라벨(타이틀) 텍스트를 외부에서 바꿀 때의 처리
    def setLabelText(self, text: str):
        self._base_title = text # 기본 타이틀 변경
        self._update_title_display() # 현재 Dirty 상태를 반영하여 타이틀 다시 설정
        
    def labelText(self) -> str:
        return self._base_title # *가 붙지 않은 순수 원본 타이틀만 반환

    def isDirty(self) -> bool:
        """현재 값이 원본과 달라졌는지 확인"""
        return self.line_edit.value() != self._original_value
        
    def commit(self):
        """현재 선택된 항목을 '새로운 원본'으로 확정 짓고 Dirty 표시를 지움"""
        self._original_value = self.line_edit.value()
        self._update_title_display() # 타이틀 복구
        
    def _on_text_edited(self, current_value: float):
        """텍스트가 바뀔 때마다 타이틀 업데이트 함수를 호출합니다."""
        self._update_title_display()

    def changeEvent(self, event: QEvent):
        """위젯의 상태 변화(Enabled 등)를 감시하고 처리합니다."""
        super().changeEvent(event) 
        
        if event.type() == QEvent.Type.EnabledChange:
            effect = self.graphicsEffect()
            if not isinstance(effect, QGraphicsOpacityEffect):
                effect = QGraphicsOpacityEffect(self)
                self.setGraphicsEffect(effect)
            
            if self.isEnabled():
                effect.setOpacity(1.0) 
            else:
                effect.setOpacity(0.5)

    def handle_value_changed(self):
        if self.param:
            if not self.param.is_not_support:
                value = self.param.value
                if value:
                    display_value = self.converter.convert_iface_pres_to_dp_pres(value)
                    self.setValue(display_value)
                else:
                    self.setValue(0.0)
    
    def handle_is_err_changed(self):
        pass
    
    def handle_is_not_support_changed(self):
        pass

    def getParamWriteValue(self) -> str:
        param_value_str = self.converter.convert_dp_pres_to_iface_pres_str(self.value())
        return param_value_str