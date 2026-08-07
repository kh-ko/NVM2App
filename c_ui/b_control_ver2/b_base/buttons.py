"""버튼 컨트롤 모음.

- BaseButton: 앱 표준 버튼. 아이콘(글리프)을 설정하면 [아이콘 + 라벨],
  설정하지 않으면 [라벨만] 구성이 된다. set_icon() 으로 런타임 변경/제거.
- CheckButton: 체크 토글 아이콘이 고정된 버튼 (기존 MyButtonCheck).

기존 base_button.py + icon_button.py
(= ver1 의 my_buttoncheck / my_buttonedit / my_buttonwarn)
를 이 파일 하나로 통합.
(툴바용 버튼 BaseToolButton / LampToolButton 은 toolbars.py 에 있다)

예:
    BaseButton("Save")                                   # 라벨만
    BaseButton("Edit", icons.GLYPH_EDIT)                 # 아이콘 + 라벨
    BaseButton("Warn", icons.GLYPH_WARN,
               glyph_color=tokens().warning)
    btn.set_icon(icons.GLYPH_WARN)                       # 아이콘 추가/변경
    btn.set_icon(None)                                   # 아이콘 제거 -> 라벨만
    CheckButton("Enable")                                # 체크 토글 버튼
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QHBoxLayout, QPushButton, QSizePolicy)

from c_ui.b_control_ver2.b_base.labels import (BaseLabel, IconLabel,
                                             IconLabelCheck, IconLabelUncheck)
from c_ui.b_control_ver2.a_theme import style
from c_ui.b_control_ver2.a_theme.color_styled import ColorStyled, WidgetColors
from c_ui.b_control_ver2.a_theme.tokens import tokens


class BaseButton(QPushButton, ColorStyled):
    def __init__(self, text: str = "", glyph: str | None = None, *,
                 glyph_color: str | None = None, border: bool = True, parent=None):
        # 네이티브 텍스트는 사용하지 않는다 — 텍스트/아이콘 모두 내부 라벨로 합성
        super().__init__("", parent)

        self.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Minimum)

        # 주의: 'layout' 속성명은 QWidget.layout() 을 가리므로 사용 금지
        self._root_layout = QHBoxLayout(self)
        left_right_margin = 10 if border else 0
        top_bottom_margin = 5 if border else 0
        self._root_layout.setContentsMargins(left_right_margin, top_bottom_margin, left_right_margin, top_bottom_margin)
        self._root_layout.setSpacing(5)
        self._root_layout.setSizeConstraint(QHBoxLayout.SetMinimumSize)

        self.lbl_icon = None

        self.lbl_text = BaseLabel(text)
        self.lbl_text.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.lbl_text.setAlignment(Qt.AlignCenter)
        self._root_layout.addWidget(self.lbl_text, 1)

        t = tokens()
        self._init_colors(
            WidgetColors(text=t.text, border=t.border, hover_border=t.border_hover),
            border_enabled=border)

        if glyph is not None:
            self.set_icon(glyph, glyph_color)

    # ------------------------------------------------------------ 아이콘
    def set_icon(self, glyph: str | None, color: str | None = None) -> None:
        """아이콘 추가/변경. glyph=None 이면 제거하여 라벨만 남긴다."""
        if glyph is None:
            if self.lbl_icon is not None:
                self._root_layout.removeWidget(self.lbl_icon)
                self.lbl_icon.deleteLater()
                self.lbl_icon = None
            return

        if self.lbl_icon is None:
            self.lbl_icon = IconLabel(glyph, color)
            self.lbl_icon.setAttribute(Qt.WA_TransparentForMouseEvents)
            self._root_layout.insertWidget(0, self.lbl_icon, 0)
        else:
            self.lbl_icon.set_glyph(glyph, color)

    # ------------------------------------------------------------ 텍스트
    # 텍스트는 내부 라벨이 담당하므로 QPushButton API 를 라벨로 리다이렉트
    def setText(self, text: str) -> None:
        self.lbl_text.setText(text)

    def text(self) -> str:
        return self.lbl_text.text()

    # ------------------------------------------------------------ 색상
    def set_colors(self, *, text=None, border=None, bg=None,
                   hover_border=None, focus_border=None) -> None:
        super().set_colors(text=text, border=border, bg=bg,
                           hover_border=hover_border, focus_border=focus_border)
        # 텍스트 색은 내부 라벨에도 전파 (라벨은 자체 스타일시트를 갖기 때문)
        if text is not None:
            self.lbl_text.set_colors(text=text)

    def _build_qss(self, c: WidgetColors) -> str:
        border = self._effective_border()
        return f"""
            BaseButton {{
                background-color: {c.bg};
                border: 1px solid {border};
                border-radius: 4px;
                color: {c.text};
            }}
            BaseButton:disabled {{
                background-color: {style.disabled(c.bg)};
                border: 1px solid {style.disabled(border)};
                color: {style.disabled(c.text)};
            }}
            BaseButton:hover {{
                border: 1px solid {c.hover_border};
            }}
            BaseButton:pressed {{
                background-color: {tokens().pressed_bg};
            }}
        """


class CheckButton(BaseButton):
    """체크 토글 버튼. 토글은 외부에서 set_check() 로 제어한다.

    고정 아이콘 객체 2개(IconLabelCheck / IconLabelUncheck)를 두고
    visible 전환으로 상태를 표현한다 (아이콘 객체 자체는 불변)."""

    def __init__(self, text: str = "", *, checked: bool = False,
                 border: bool = True, parent=None):
        super().__init__(text=text, border=border, parent=parent)

        self.icon_check = IconLabelCheck()
        self.icon_uncheck = IconLabelUncheck()
        for icon in (self.icon_check, self.icon_uncheck):
            icon.setAttribute(Qt.WA_TransparentForMouseEvents)
        self._root_layout.insertWidget(0, self.icon_check, 0)
        self._root_layout.insertWidget(1, self.icon_uncheck, 0)

        self._checked = checked
        self.set_check(checked)

    def set_icon(self, glyph: str | None, color: str | None = None) -> None:
        """체크 아이콘 고정 — 일반 아이콘 설정 불가."""
        pass

    def set_check(self, checked: bool) -> None:
        self._checked = checked
        self.icon_check.setVisible(checked)
        self.icon_uncheck.setVisible(not checked)

    def is_checked(self) -> bool:
        return self._checked