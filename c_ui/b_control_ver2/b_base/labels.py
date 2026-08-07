"""라벨 컨트롤 모음.

- BaseLabel: 기본 라벨.
  - role=LabelRole.TITLE/DESCRIPTION 으로 역할별 폰트 크기 지정 (상속 클래스 공통 적용).
  - box=True 로 테두리+배경+패딩 박스 스타일 (기존 base_labelcolorbox).
  - sig_assigned_by_code(widget): setText() 코드 할당 알림 — inputs.py 의
    공통 입력 시그널 계약과 동일 규칙. (라벨은 표시 전용이라 사용자 편집
    시그널은 없다. C++ 내부 호출은 오버라이드를 거치지 않으므로 미발화)
- IconLabel: Material Icons 글리프 라벨 (role 규칙 동일 적용).
- IconLabelCheck / IconLabelUncheck / IconLabelEdit / IconLabelWarn:
  글리프+색이 고정된 프리셋 (기존 ver1 의 MyIconCheck / MyIconEdit / MyIconWarn 대응).
  체크 토글이 필요한 곳은 IconLabelCheck + IconLabelUncheck 두 객체를 만들고
  visible 을 전환하는 방식을 사용한다 (아이콘 객체 자체는 불변).

기존 base_label.py + text_label.py + icons.py 의 라벨 클래스를 이 파일로 통합.
(글리프 상수는 icons.py 에 유지. 기존 my_label / my_labeltitle /
my_labeldescription 은 BaseLabel + role 로 대체)
"""

from enum import Enum, auto

from PySide6.QtCore import Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication, QLabel, QWidget

from c_ui.b_control_ver2.b_base import icons
from c_ui.b_control_ver2.a_theme import style
from c_ui.b_control_ver2.a_theme.color_styled import ColorStyled, WidgetColors
from c_ui.b_control_ver2.a_theme.tokens import tokens


class LabelRole(Enum):
    BODY = auto()          # 기본 (앱 기본 폰트 크기 그대로)
    TITLE = auto()         # 앱 기본 폰트의 1.2배
    DESCRIPTION = auto()   # 앱 기본 폰트의 0.8배

_ROLE_FACTOR = {LabelRole.BODY: 1.0, LabelRole.TITLE: 1.2, LabelRole.DESCRIPTION: 0.8}


def _role_pixel_size(role: LabelRole) -> int | None:
    """역할에 따른 폰트 픽셀 크기. 앱 폰트가 pixelSize 기반이 아니면 None."""
    base_pixel_size = QApplication.font().pixelSize()
    if base_pixel_size <= 0:
        return None
    return int(base_pixel_size * _ROLE_FACTOR[role])


class BaseLabel(QLabel, ColorStyled):
    """기본 라벨. role 로 폰트 크기, box=True 로 박스 스타일 지정."""

    sig_assigned_by_code = Signal(QWidget)  # setText() 코드 할당 알림

    def __init__(self, text="", role: LabelRole = LabelRole.BODY, box=False, parent=None):
        super().__init__(text, parent)
        self._boxed = box
        self.setWordWrap(not box)

        # BODY 는 앱 기본 폰트를 건드리지 않는다
        if role is not LabelRole.BODY:
            pixel_size = _role_pixel_size(role)
            if pixel_size is not None:
                font = self.font()
                font.setPixelSize(pixel_size)
                self.setFont(font)

        t = tokens()
        self._init_colors(WidgetColors(text=t.text, border="transparent"))
    
    def set_boxed(self, boxed: bool):
        self._boxed = boxed
        self.setWordWrap(not boxed)   # __init__ 의 box 규칙과 동일하게 유지
        self._apply_style()

    def setText(self, text: str):
        super().setText(text)
        self.sig_assigned_by_code.emit(self)

    def _build_qss(self, c: WidgetColors) -> str:
        border = self._effective_border()
        if self._boxed:
            box = f"border: 1px solid {border}; border-radius: 4px; padding: 4px;"
            box_disabled = (f"border: 1px solid {style.disabled(border)}; "
                            f"border-radius: 4px; padding: 4px;")
        else:
            box = box_disabled = ""

        return f"""
            BaseLabel {{
                color: {c.text};
                background-color: {c.bg};
                {box}
            }}
            BaseLabel:disabled {{
                color: {style.disabled(c.text)};
                background-color: {style.disabled(c.bg)};
                {box_disabled}
            }}
        """


class IconLabel(BaseLabel):
    """Material Icons 글리프 라벨. role 폰트 크기 규칙은 BaseLabel 과 동일."""

    def __init__(self, glyph="", color: str | None = None,
                 role: LabelRole = LabelRole.BODY, parent=None):
        super().__init__(text=glyph, role=role, parent=parent)

        # 폰트 패밀리를 Material Icons 로 교체 (role 크기는 유지)
        font = QFont("Material Icons")
        pixel_size = _role_pixel_size(role)
        if pixel_size is not None:
            font.setPixelSize(pixel_size)
        self.setFont(font)

        if color is not None:
            self.set_colors(text=color)

    def set_glyph(self, glyph: str, color: str | None = None) -> None:
        self.setText(glyph)
        if color is not None:
            self.set_colors(text=color)


class IconLabelCheck(IconLabel):
    """체크됨 아이콘 (success 색)."""

    def __init__(self, role: LabelRole = LabelRole.BODY, parent=None):
        super().__init__(icons.GLYPH_CHECK, tokens().success, role=role, parent=parent)


class IconLabelUncheck(IconLabel):
    """체크 해제 아이콘 (border 색)."""

    def __init__(self, role: LabelRole = LabelRole.BODY, parent=None):
        super().__init__(icons.GLYPH_UNCHECK, tokens().border, role=role, parent=parent)


class IconLabelEdit(IconLabel):
    """편집(설정) 아이콘 (기본 글자색)."""

    def __init__(self, role: LabelRole = LabelRole.BODY, parent=None):
        super().__init__(icons.GLYPH_EDIT, role=role, parent=parent)


class IconLabelWarn(IconLabel):
    """경고 아이콘 (warning 색)."""

    def __init__(self, role: LabelRole = LabelRole.BODY, parent=None):
        super().__init__(icons.GLYPH_WARN, tokens().warning, role=role, parent=parent)
