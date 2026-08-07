"""입력 위젯 컨트롤 모음.

- BaseLineEdit: 텍스트 입력.
- BaseDoubleSpinBox: 실수 스핀박스 입력.
- BaseCheckBox: 체크박스 입력.
- BaseComboBox: 콤보박스 선택 입력.

기존 base_lineedit.py + base_spinbox.py + base_checkbox.py + base_combobox.py
를 이 파일 하나로 통합.

== 공통 입력 시그널 계약 (상호 배타 — 겸용 시그널 없음) ==
- sig_edited_by_user(value): 사용자 편집 확정 전용.
  라인에디트/스핀박스는 Enter 또는 포커스 아웃, 체크박스는 클릭, 콤보박스는 선택.
- sig_edited_by_enter(value): Enter 로 확정한 경우 추가 발신 (라인에디트/스핀박스만).
  "포커스 아웃은 무시하고 Enter 로만 확정" 모드가 필요한 상위 레이어용.
  Enter 시에는 항상 발신 (값 변경 여부 무관 — Enter 는 의도적 확정 행위이므로).
- sig_editing_by_user(widget): 사용자 편집 '진행 중' 실시간 발신 (라인에디트/스핀박스만).
  타이핑/스핀 조작 순간마다 발생하며 중간값(예: "100" 입력 중의 1, 10)도 포함된다.
  ** 표시 전용(실시간 dirty 마커, 미리보기 등)으로만 사용할 것 — 확정 전 중간값이
  흘러가므로 쓰기(장비 전송) 경로에는 절대 연결 금지. 확정은 sig_edited_by_user. **
  (체크박스/콤보박스는 클릭 순간이 곧 확정이라 이 시그널이 없다)
- sig_assigned_by_code(value): 코드 할당 전용.
  코드에서 값 할당은 반드시 지정 setter 로 할 것:
  setText/clear, setValue/clear, setChecked/setCheckState, setCurrentIndex.
  (시그널 핸들러 안에서 setter 재호출 금지 — 재귀 발생)

C++ 내부 호출은 Python setter 오버라이드를 거치지 않으므로 코드 경로만 잡히고,
clicked/activated/textEdited/editingFinished 는 Qt 가 사용자 조작에서만(또는
setter 가 수정 플래그를 리셋하는 방식으로) 발생시킨다 — 두 경로가 자연 분리된다.

Qt 의 겸용 시그널(textChanged/valueChanged/stateChanged/currentIndexChanged)은
값 추적 용도로 사용하지 않는다. (타이핑 중 실시간 감지가 필요하면 사용자 전용인
textEdited 를 쓸 것)
"""

from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Signal
from PySide6.QtWidgets import (QCheckBox, QComboBox, QDoubleSpinBox, QLineEdit,
                               QSizePolicy)

from c_ui.b_control_ver2.a_theme import style
from c_ui.b_control_ver2.a_theme.color_styled import ColorStyled, WidgetColors
from c_ui.b_control_ver2.a_theme.tokens import tokens


class BaseCheckBox(QCheckBox, ColorStyled):
    """체크박스 입력.

    clicked 는 Qt 가 사용자 조작(클릭/스페이스)에서만 발생시킨다."""

    sig_edited_by_user = Signal(QWidget)    
    sig_assigned_by_code = Signal(QWidget)  

    def __init__(self, text="", parent=None):
        super().__init__(text, parent)

        self.clicked.connect(self._on_user_clicked)

        self._init_colors(WidgetColors(text=tokens().text))

    def _on_user_clicked(self, checked: bool):
        self.sig_edited_by_user.emit(self)

    def setChecked(self, checked: bool):
        super().setChecked(checked)
        self.sig_assigned_by_code.emit(self)

    def setCheckState(self, state):
        super().setCheckState(state)
        self.sig_assigned_by_code.emit(self)

    def _build_qss(self, c: WidgetColors) -> str:
        return f"""
            BaseCheckBox {{
                color: {c.text};
            }}
            BaseCheckBox:disabled {{
                color: {style.disabled(c.text)};
            }}
        """

class BaseComboBox(QComboBox, ColorStyled):
    """콤보박스 선택 입력. 휠 스크롤로 값이 바뀌는 사고 방지를 위해 wheelEvent 무시.

    activated 는 Qt 가 사용자 선택에서만 발생시킨다."""

    sig_edited_by_user = Signal(QWidget)    
    sig_assigned_by_code = Signal(QWidget)  

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)

        self.activated.connect(self._on_user_activated)

        t = tokens()
        self._init_colors(WidgetColors(text=t.text, border=t.border,
                                       hover_border=t.border_hover))

    def _on_user_activated(self, index: int):
        self.sig_edited_by_user.emit(self)

    def setCurrentIndex(self, index: int):
        super().setCurrentIndex(index)
        self.sig_assigned_by_code.emit(self)

    def wheelEvent(self, event):
        event.ignore()

    def _build_qss(self, c: WidgetColors) -> str:
        t = tokens()
        border = self._effective_border()
        return f"""
            BaseComboBox {{
                color: {c.text};
                border: 1px solid {border};
                border-radius: 4px;
                padding: 4px 8px;
                background-color: {c.bg};
                min-height: 24px;
            }}
            BaseComboBox:disabled {{
                color: {style.disabled(c.text)};
                border: 1px solid {style.disabled(border)};
                background-color: {style.disabled(c.bg)};
            }}
            BaseComboBox:hover {{
                border: 1px solid {c.hover_border};
            }}
            BaseComboBox::drop-down {{
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 20px;
                border-left: 1px solid {border};
            }}
            BaseComboBox QAbstractItemView {{
                font-size: 14px;
                border: 1px solid {border};
                border-radius: 4px;
                background-color: {t.popup_bg};
                outline: 0px;
                selection-background-color: {t.selection_bg};
                selection-color: {t.selection_text};
            }}
        """

class BaseDoubleSpinBox(QDoubleSpinBox, ColorStyled):
    """실수 스핀박스 입력. Enter 입력 시 포커스 해제(편집 세션 종료).

    - border=False 로 생성하면 평시/호버/포커스 테두리 전부 투명.
      (프레임(그룹박스) 안에 놓일 때 테두리가 이중으로 보이는 것 방지)
    - sig_edited_by_user 합성: QDoubleSpinBox 는 사용자 전용 네이티브 시그널이
      없으므로, 코드 할당 가드를 통과한 valueChanged(스핀 조작/타이핑)로
      '사용자가 만졌음'을 기록해 두고 editingFinished 시점에 기록이 있을 때만
      발신한다. (포커스 중 코드 할당 후 그냥 포커스 아웃하는 경우를 사용자
      편집으로 오인하지 않기 위함. 따라서 값을 만지지 않은 Enter 에서는
      sig_edited_by_user 는 미발생, sig_edited_by_enter 는 발생)"""

    sig_edited_by_user = Signal(QWidget)
    sig_edited_by_enter = Signal(QWidget)
    sig_editing_by_user = Signal(QWidget)   # 편집 진행 중 (표시 전용 — 계약 주석 참고)
    sig_assigned_by_code = Signal(QWidget)

    def __init__(self, border=True, parent=None):
        super().__init__(parent)

        self._assigning = False      # 코드 할당 중 가드
        self._user_touched = False   # 마지막 할당 이후 사용자가 값을 만졌는가

        self.lineEdit().returnPressed.connect(self._on_enter_pressed)
        self.valueChanged.connect(self._on_value_changed)
        self.editingFinished.connect(self._on_editing_finished)

        t = tokens()
        if border:
            colors = WidgetColors(text=t.text, border=t.border,
                                  hover_border=t.border_hover,
                                  focus_border=t.border_focus)
        else:
            colors = WidgetColors(text=t.text, border="transparent",
                                  hover_border="transparent",
                                  focus_border="transparent")
        self._init_colors(colors, border_enabled=border)

    def _on_enter_pressed(self):
        # clearFocus 가 유발하는 포커스 아웃에서 editingFinished(→ sig_edited_by_user)가
        # 먼저 처리된 뒤 Enter 식별 시그널이 나간다
        self.clearFocus()
        self.sig_edited_by_enter.emit(self)

    def _on_value_changed(self, _value):
        # _assigning 가드를 통과한 valueChanged = 사용자 조작 (스핀/타이핑).
        # keyboardTracking 기본값(True)이라 타이핑 중간값도 실시간으로 발신된다.
        if not self._assigning:
            self._user_touched = True
            self.sig_editing_by_user.emit(self)

    def _on_editing_finished(self):
        if self._user_touched:
            self._user_touched = False
            self.sig_edited_by_user.emit(self)

    def setValue(self, value: float):
        self._assigning = True
        try:
            super().setValue(value)
        finally:
            self._assigning = False
        self._user_touched = False
        self.sig_assigned_by_code.emit(self)

    def setDecimals(self, prec: int):
        # 자릿수 변경도 코드 경로다 — 자릿수 축소 시 Qt 가 현재 값을 반올림하며
        # valueChanged 를 발생시키는데, 이것이 사용자 터치(_user_touched)로
        # 기록되면 이후 포커스 아웃에서 sig_edited_by_user 가 오발화된다
        self._assigning = True
        try:
            super().setDecimals(prec)
        finally:
            self._assigning = False

    def clear(self):
        self._assigning = True
        try:
            super().clear()
        finally:
            self._assigning = False
        self._user_touched = False
        self.sig_assigned_by_code.emit(self)

    def _build_qss(self, c: WidgetColors) -> str:
        border = self._effective_border()
        return f"""
            BaseDoubleSpinBox {{
                border: 1px solid {border};
                border-radius: 4px;
                padding-right: 5px;
                background-color: {c.bg};
                color: {c.text};
            }}
            BaseDoubleSpinBox:disabled {{
                border: 1px solid {style.disabled(border)};
                background-color: {style.disabled(c.bg)};
                color: {style.disabled(c.text)};
            }}
            BaseDoubleSpinBox:focus {{
                border: 1px solid {c.focus_border};
            }}
            BaseDoubleSpinBox:hover {{
                border: 1px solid {c.hover_border};
            }}
        """

class BaseLineEdit(QLineEdit, ColorStyled):
    """텍스트 입력. Enter 입력 시 포커스 해제(편집 세션 종료).

    sig_edited_by_user: Qt 의 editingFinished 는 Enter 또는 '사용자가 수정한
    상태'의 포커스 아웃에서만 발생하고, setText() 는 수정 플래그를 리셋하므로
    코드 할당으로는 발생하지 않는다."""

    sig_edited_by_user = Signal(QWidget)
    sig_edited_by_enter = Signal(QWidget)
    sig_editing_by_user = Signal(QWidget)   # 편집 진행 중 (표시 전용 — 계약 주석 참고)
    sig_assigned_by_code = Signal(QWidget)

    def __init__(self, text="", parent=None):
        super().__init__(text, parent)

        self.returnPressed.connect(self._on_enter_pressed)
        self.editingFinished.connect(self._on_editing_finished)
        # textEdited 는 사용자 입력에서만 발생한다 (setText 는 미발생) — 가드 불필요
        self.textEdited.connect(self._on_text_edited)

        t = tokens()
        self._init_colors(WidgetColors(text=t.text, border=t.border,
                                       hover_border=t.border_hover,
                                       focus_border=t.border_focus))

    def _on_enter_pressed(self):
        self.clearFocus()
        self.sig_edited_by_enter.emit(self)

    def _on_editing_finished(self):
        self.sig_edited_by_user.emit(self)

    def _on_text_edited(self, _text):
        self.sig_editing_by_user.emit(self)

    def setText(self, text: str):
        super().setText(text)
        self.sig_assigned_by_code.emit(self)

    def clear(self):
        super().clear()
        self.sig_assigned_by_code.emit(self)

    def _build_qss(self, c: WidgetColors) -> str:
        border = self._effective_border()
        return f"""
            BaseLineEdit {{
                border: 1px solid {border};
                border-radius: 4px;
                padding-right: 5px;
                background-color: {c.bg};
                color: {c.text};
            }}
            BaseLineEdit:disabled {{
                border: 1px solid {style.disabled(border)};
                background-color: {style.disabled(c.bg)};
                color: {style.disabled(c.text)};
            }}
            BaseLineEdit:focus {{
                border: 1px solid {c.focus_border};
            }}
            BaseLineEdit:hover {{
                border: 1px solid {c.hover_border};
            }}
        """





