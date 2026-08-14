"""입력 위젯 컨트롤 모음.

- BaseLineEdit: 텍스트 입력.
- BaseFloatLineEdit: 실수 전용 라인에딧 (validator+fixup, 스핀박스 대응 API).
- BaseHexLineEdit: 16진수(정수) 전용 라인에딧 (BaseFloatLineEdit 의 hex 대응).
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
from PySide6.QtCore import QLocale, QSignalBlocker, Qt, Signal
from PySide6.QtGui import QDoubleValidator, QValidator
from PySide6.QtWidgets import (QCheckBox, QComboBox, QDoubleSpinBox, QLineEdit,
                               QSizePolicy)

from b_core.f_helper.float_util import SIG_DIGITS, to_sig_str

from c_ui.b_control_ver2.a_theme import style
from c_ui.b_control_ver2.a_theme.color_styled import ColorStyled, WidgetColors
from c_ui.b_control_ver2.a_theme.tokens import tokens


class BaseCheckBox(QCheckBox, ColorStyled):
    """체크박스 입력.

    clicked 는 Qt 가 사용자 조작(클릭/스페이스)에서만 발생시킨다.

    중간 상태(PartiallyChecked)는 코드 전용이다 — setCheckState(Partially...)
    가 tristate 를 자동으로 켜더라도, 사용자 클릭은 항상 2상태로만 확정된다
    (중간 상태에서 클릭하면 Checked). '값 없음' 표시(비트맵 위젯 등)에 중간
    상태를 쓰면서 사용자에게 3상태 순환을 노출하지 않기 위한 규칙이다."""

    sig_edited_by_user = Signal(QWidget)
    sig_assigned_by_code = Signal(QWidget)

    def __init__(self, text="", parent=None):
        super().__init__(text, parent)

        self.clicked.connect(self._on_user_clicked)

        self._init_colors(WidgetColors(text=tokens().text))

    def _on_user_clicked(self, checked: bool):
        self.sig_edited_by_user.emit(self)

    def nextCheckState(self):
        # 사용자 클릭의 다음 상태 — tristate 여부와 무관하게 2상태 토글
        # (중간 상태 클릭 -> Checked 확정). 사용자 조작이므로 코드 할당 알림이
        # 나가면 안 된다 — 오버라이드된 setCheckState 대신 원본을 직접 호출
        next_state = Qt.CheckState.Unchecked if self.checkState() == Qt.CheckState.Checked else Qt.CheckState.Checked
        QCheckBox.setCheckState(self, next_state)

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
        self.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)

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


class _FloatFixupValidator(QDoubleValidator):
    """BaseFloatLineEdit 전용 — fixup 판단을 위젯의 클램프/포맷 정책에 위임한다.

    유효숫자 모드(위젯의 _decimals 가 None)에서는 소수 자릿수를 제한하지 않는
    대신(decimals=-1), 유효숫자(float_util.SIG_DIGITS)로 표현할 수 없는
    정밀도의 입력을 Intermediate 로 판정한다 — 확정(Enter/포커스 아웃) 시
    fixup 이 유효숫자 자릿수로 반올림해 수습한다."""

    def __init__(self, owner):
        # 기본 범위는 QDoubleSpinBox 와 동일 (0.0~99.99), 자릿수는 무제한(-1) —
        # 유효숫자 모드의 정밀도 제한은 validate 에서 별도로 판정한다
        super().__init__(0.0, 99.99, -1, owner)

        self.setNotation(QDoubleValidator.StandardNotation)  # 과학표기(1.5e+4) 불허

        # 로케일 C 고정 — 소수점은 '.' 만, "1,234" 식 자릿수 구분자 불허
        locale = QLocale.c()
        locale.setNumberOptions(QLocale.RejectGroupSeparator)
        self.setLocale(locale)

        self._owner = owner

    def validate(self, text: str, pos: int):
        state, text, pos = super().validate(text, pos)

        # 유효숫자 모드: 6자리로 표현 불가한 정밀도는 확정 불가(Intermediate) —
        # 자릿수 세기 대신 '6자리 반올림 시 값이 변하는가'로 판정한다
        # (1000000 처럼 후행 0 만 긴 수는 통과, 0.123456789 는 걸린다)
        if state == QDoubleValidator.Acceptable and self._owner._decimals is None:
            try:
                value = float(text)
                if float(f"{value:.{SIG_DIGITS}g}") != value:
                    return QDoubleValidator.Intermediate, text, pos
            except ValueError:
                pass

        return state, text, pos

    def fixup(self, text: str) -> str:
        return self._owner._fixup_text(text)


class BaseFloatLineEdit(BaseLineEdit):
    """실수 전용 라인에딧 — QDoubleSpinBox 와 동일한 setRange/setDecimals/setValue/value() API.

    (QSS 는 BaseLineEdit 선택자가 파생 클래스에도 매칭되므로 재정의 불필요)

    [주의] QDoubleValidator 는 범위 초과 입력을 Invalid 가 아닌 Intermediate 로
    판정하고, QLineEdit 은 Acceptable 상태가 아니면 editingFinished 를 발화하지
    않는다. 그래서 fixup() 에서 클램프+재포맷으로 Acceptable 을 보장한다
    (Enter/포커스 아웃 모두 fixup 을 경유) — 덕분에 sig_edited_by_user 발화
    조건이 BaseLineEdit 과 동일하게 유지된다. 해석 불가 텍스트("", "-", ".")로
    확정을 시도하면 마지막 유효값으로 복원한다 (스핀박스의 보정 동작과 동일).

    '값 없음' 상태 (enum 콤보의 setCurrentIndex(-1) 과 동일 의미론):
    - setValue(None) 은 텍스트를 비워 placeholder 가 노출되게 한다. 이 상태는
      코드만 만들 수 있고, 사용자가 클릭했다 나가도 유지된다 (확정 미발생).
    - 사용자가 유효값을 지우고 확정하면 마지막 유효값으로 복원된다 —
      사용자는 '값 없음' 상태를 만들 수 없다.
    - 값 없음 상태에서 value() 는 None 을 반환한다.

    자릿수 모드 — setDecimals() 호출 여부로 갈린다:
    - 기본(미호출): 유효숫자 6자리 모드. 표시는 후행 0 없는 유효숫자 6자리
      (지수 표기는 풀어쓴다 — 예: 0.00000123456789 -> "0.00000123457"),
      코드 할당과 사용자 확정 모두 6자리로 반올림된다.
    - setDecimals(n) 호출 후: 고정 소수점 n자리 모드 (기존 동작)."""

    def __init__(self, parent=None):
        super().__init__("", parent)

        # None = 유효숫자(6자리) 모드, 정수 = 고정 소수점 자릿수 모드
        self._decimals: int | None = None

        self._validator = _FloatFixupValidator(self)
        self.setValidator(self._validator)

        # fixup 의 '해석 불가 시 복원' 기준값. 코드 할당과 사용자 확정에서 갱신된다.
        self._last_value = 0.0
        with QSignalBlocker(self):
            self.setText(self._format(0.0))

        self.editingFinished.connect(self._update_last_value)

    # ------------------------------------------------------------ 내부
    def _update_last_value(self):
        value = self.value()
        if value is not None:
            self._last_value = value

    def _format(self, value) -> str:
        if self._decimals is not None:
            return f"{value:.{self._decimals}f}"

        # 유효숫자 모드 — 앱 전역 정책의 단일 구현(float_util.to_sig_str)에 위임
        return to_sig_str(value)

    def _clamp(self, value):
        return min(max(value, self._validator.bottom()), self._validator.top())

    def _fixup_text(self, text) -> str:
        try:
            value = float(text)
        except ValueError:
            # 코드가 만든 '값 없음' 상태는 빈 표시를 유지하고 (빈 텍스트는 Acceptable 이
            # 아니므로 확정 시그널도 발생하지 않는다), 사용자가 유효값을 지운 경우는
            # 마지막 유효값으로 복원한다 — enum 콤보의 빈 상태 의미론과 동일
            if self._last_value is None:
                return ""
            value = self._last_value

        return self._format(self._clamp(value))

    def _render_current(self):
        # 표시 전용 재포맷/클램프 — 스핀박스의 setRange/setDecimals 처럼 알림 없음
        value = self.value()
        if value is None:
            return

        with QSignalBlocker(self):
            self.setText(self._format(self._clamp(value)))

    # ------------------------------------------------------------ 스핀박스 대응 API
    def setRange(self, min_value: float, max_value: float):
        self._validator.setRange(min_value, max_value, self._validator.decimals())
        self._render_current()

    def setDecimals(self, decimals: int):
        # 고정 소수점 모드로 전환 (유효숫자 모드로 되돌리는 API 는 두지 않는다 —
        # 자릿수를 정한 위젯은 그 정책을 유지하는 것이 계약)
        self._decimals = decimals
        self._validator.setRange(self._validator.bottom(), self._validator.top(), decimals)
        self._render_current()

    def setValue(self, value: float | None):
        # None = '값 없음' — 코드 전용 상태. 비워서 placeholder 를 노출한다.
        # 범위 밖 값도 '값 없음' 처리한다 — 클램프하면 표시값이 실제(장비)값과
        # 달라지는 거짓 표시가 되기 때문. (사용자 입력의 fixup 클램프는 입력
        # 보정이므로 별개 — 이 규칙은 코드 할당에만 적용된다)
        if value is not None and not (self._validator.bottom() <= value <= self._validator.top()):
            value = None

        if value is None:
            self._last_value = None
            self.clear()  # sig_assigned_by_code 1회 발화
            return

        self._last_value = value
        self.setText(self._format(self._last_value))  # sig_assigned_by_code 1회 발화

    def value(self):
        # 표시 텍스트를 그대로 해석 — 편집 중간 상태("", "-", "." 등)는 None
        try:
            return float(self.text())
        except ValueError:
            return None

class _HexFixupValidator(QValidator):
    """BaseHexLineEdit 전용 — 16진수 문자만 허용, fixup 판단은 위젯 정책에 위임한다.

    QDoubleValidator 의 전략을 그대로 따른다: 범위 초과는 Invalid 가 아닌
    Intermediate 로 판정해 타이핑을 막지 않고, 확정 시 fixup 클램프로 수습한다."""

    _HEX_CHARS = set("0123456789abcdefABCDEF")

    def __init__(self, owner):
        super().__init__(owner)
        self._owner = owner

    def validate(self, text: str, pos: int):
        if text == "":
            return QValidator.Intermediate, text, pos

        # "0x" 접두사 없이 hex 문자만 허용 (표시 포맷과 입력 포맷 통일)
        if any(ch not in self._HEX_CHARS for ch in text):
            return QValidator.Invalid, text, pos

        if self._owner._minimum <= int(text, 16) <= self._owner._maximum:
            return QValidator.Acceptable, text, pos
        return QValidator.Intermediate, text, pos

    def fixup(self, text: str) -> str:
        return self._owner._fixup_text(text)


class BaseHexLineEdit(BaseLineEdit):
    """16진수(정수) 전용 라인에딧 — BaseFloatLineEdit 와 대응하는
    setRange/setDigits/setValue/value() API. 값 타입은 int, 표시는 대문자
    0 패딩 hex (기본 8자리 = 32bit).

    (QSS 는 BaseLineEdit 선택자가 파생 클래스에도 매칭되므로 재정의 불필요)

    [주의] QLineEdit 은 Acceptable 상태가 아니면 editingFinished 를 발화하지
    않는다. validator 는 hex 문자가 아니면 Invalid(타이핑 차단), 범위 초과면
    Intermediate 로 판정하고, fixup() 에서 클램프+재포맷으로 Acceptable 을
    보장한다 (Enter/포커스 아웃 모두 fixup 을 경유) — 덕분에 sig_edited_by_user
    발화 조건이 BaseLineEdit 과 동일하게 유지된다. 해석 불가 텍스트("")로
    확정을 시도하면 마지막 유효값으로 복원한다 (BaseFloatLineEdit 와 동일).

    '값 없음' 상태 (enum 콤보의 setCurrentIndex(-1) 과 동일 의미론):
    - setValue(None) 은 텍스트를 비워 placeholder 가 노출되게 한다. 이 상태는
      코드만 만들 수 있고, 사용자가 클릭했다 나가도 유지된다 (확정 미발생).
    - 사용자가 유효값을 지우고 확정하면 마지막 유효값으로 복원된다 —
      사용자는 '값 없음' 상태를 만들 수 없다.
    - 값 없음 상태에서 value() 는 None 을 반환한다."""

    def __init__(self, parent=None):
        super().__init__("", parent)

        # 범위/자릿수는 위젯이 소유한다 (QDoubleValidator 같은 보관처가 없으므로)
        self._minimum = 0
        self._maximum = 0xFFFFFFFF
        self._digits = 8

        self._validator = _HexFixupValidator(self)
        self.setValidator(self._validator)

        # fixup 의 '해석 불가 시 복원' 기준값. 코드 할당과 사용자 확정에서 갱신된다.
        self._last_value = 0
        with QSignalBlocker(self):
            self.setText(self._format(0))

        self.editingFinished.connect(self._update_last_value)

    # ------------------------------------------------------------ 내부
    def _update_last_value(self):
        value = self.value()
        if value is not None:
            self._last_value = value

    def _format(self, value) -> str:
        return f"{value:0{self._digits}X}"

    def _clamp(self, value):
        return min(max(value, self._minimum), self._maximum)

    def _fixup_text(self, text) -> str:
        try:
            value = int(text, 16)
        except ValueError:
            # 코드가 만든 '값 없음' 상태는 빈 표시를 유지하고 (빈 텍스트는 Acceptable 이
            # 아니므로 확정 시그널도 발생하지 않는다), 사용자가 유효값을 지운 경우는
            # 마지막 유효값으로 복원한다 — enum 콤보의 빈 상태 의미론과 동일
            if self._last_value is None:
                return ""
            value = self._last_value

        return self._format(self._clamp(value))

    def _render_current(self):
        # 표시 전용 재포맷/클램프 — 스핀박스의 setRange/setDecimals 처럼 알림 없음
        value = self.value()
        if value is None:
            return

        with QSignalBlocker(self):
            self.setText(self._format(self._clamp(value)))

    # ------------------------------------------------------------ 스핀박스 대응 API
    def setRange(self, min_value: int, max_value: int):
        self._minimum = min_value
        self._maximum = max_value
        self._render_current()

    def setDigits(self, digits: int):
        """표시 자릿수(0 패딩 폭). 예: 8 -> '0000ABCD'"""
        self._digits = digits
        self._render_current()

    def setValue(self, value: int | None):
        # None = '값 없음' — 코드 전용 상태. 비워서 placeholder 를 노출한다.
        # 범위 밖 값도 '값 없음' 처리한다 — 클램프하면 표시값이 실제(장비)값과
        # 달라지는 거짓 표시가 되기 때문. (사용자 입력의 fixup 클램프는 입력
        # 보정이므로 별개 — 이 규칙은 코드 할당에만 적용된다)
        if value is not None and not (self._minimum <= value <= self._maximum):
            value = None

        if value is None:
            self._last_value = None
            self.clear()  # sig_assigned_by_code 1회 발화
            return

        self._last_value = value
        self.setText(self._format(self._last_value))  # sig_assigned_by_code 1회 발화

    def value(self):
        # 표시 텍스트를 그대로 해석 — 편집 중간 상태("")는 None
        try:
            return int(self.text(), 16)
        except ValueError:
            return None





