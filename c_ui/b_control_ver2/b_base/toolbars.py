"""툴바 컨트롤 모음.

- BaseToolBar: 앱 표준 툴바 (어두운 배경). add_action() 으로 등록한 액션을
  이름 키로 remove / enable 제어한다 (기존 base_toolbar.py 대응).
- BaseToolButton: 툴바용 버튼. 기존에는 BaseToolBar 의 QSS 가
  QToolButton[menuBtn="true"] 매직 프로퍼티로 스타일을 소유했으나,
  ver2 는 버튼이 자기 스타일을 소유한다 (툴바 밖에서도 동일하게 동작).
- LampToolButton: 램프(상태 표시등) 툴버튼 (기존 my_lamptoolbutton).

BaseToolBar 의 QSS 에 남아 있는 QToolButton / QMenu 블록은 의도된 자식 전파다:
- QToolButton 블록: addAction() 이 내부 생성하는 네이티브 버튼과
  확장(») 버튼 전용. (BaseToolButton 은 자체 스타일시트가 우선하므로 영향 없음)
- QMenu 블록: 툴바 버튼에 달리는 드롭다운 메뉴는 네이티브 QMenu 라
  부모(툴바) 스타일시트 전파로만 스타일링할 수 있다.
"""

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QColor, QPainter
from PySide6.QtWidgets import (QStyle, QStyleOptionToolButton, QToolBar,
                               QToolButton)

from c_ui.b_control_ver2.b_base import icons
from c_ui.b_control_ver2.a_theme.color_styled import ColorStyled, WidgetColors
from c_ui.b_control_ver2.a_theme.tokens import tokens


class BaseToolBar(QToolBar, ColorStyled):
    """앱 표준 툴바. 고정형(이동/플로팅 불가)이 기본이다."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMovable(False)
        self.setFloatable(False)

        self._actions: dict[str, QAction] = {}

        t = tokens()
        self._init_colors(WidgetColors(text=t.text_inverse,
                                       border=t.toolbar_border,
                                       bg=t.toolbar_bg))

    # ------------------------------------------------------------ 액션
    def add_action(self, name: str, slot) -> QAction:
        """텍스트 액션 추가. name 을 키로 remove / enable 제어한다."""
        action = self.addAction(name)
        action.triggered.connect(slot, Qt.QueuedConnection)
        self._actions[name] = action
        return action

    def remove_action(self, name: str) -> None:
        if name in self._actions:
            self.removeAction(self._actions[name])
            del self._actions[name]

    def set_action_enabled(self, name: str, enabled: bool) -> None:
        if name in self._actions:
            self._actions[name].setEnabled(enabled)

    # ------------------------------------------------------------ 스타일
    def _build_qss(self, c: WidgetColors) -> str:
        t = tokens()
        return f"""
            BaseToolBar {{
                background-color: {c.bg};
                border: 1px solid {c.border};
                spacing: 4px;
                padding: 2px;
                min-height: 30px;
            }}

            /* 이동 핸들 — setMovable(True) 로 전환한 경우에만 보인다.
               기본 점 무늬 대신 두 줄의 선으로 표현 */
            BaseToolBar::handle:horizontal {{
                image: none;
                width: 2px;
                margin: 4px 8px;
                border-left: 1px solid {t.toolbar_handle};
                border-right: 1px solid {t.toolbar_handle};
            }}
            BaseToolBar::handle:vertical {{
                image: none;
                height: 2px;
                margin: 8px 4px;
                border-top: 1px solid {t.toolbar_handle};
                border-bottom: 1px solid {t.toolbar_handle};
            }}

            BaseToolBar::separator {{
                width: 1px;
                background-color: {t.toolbar_separator};
                margin: 6px 4px;
            }}

            /* addAction() 이 내부 생성하는 네이티브 버튼 전용 (모듈 주석 참고) */
            QToolButton {{
                color: {c.text};
                background: transparent;
                border: none;
                border-radius: 4px;
                padding: 8px 12px;
            }}
            QToolButton:hover {{
                background-color: {t.toolbar_hover};
            }}
            QToolButton:disabled {{
                color: {t.toolbar_disabled};
                background: transparent;
            }}

            /* 공간 부족 시 나타나는 확장(») 버튼 */
            QToolButton#qt_toolbar_ext_button {{
                qproperty-toolButtonStyle: ToolButtonTextOnly;
                qproperty-text: "{icons.GLYPH_CHEVRON_RIGHT}";
                font-family: "Material Icons";
                font-size: 18px;
                background: transparent;
                border: none;
                color: {c.text};
                padding: 0px;
                margin: 0px;
            }}

            /* 툴바 버튼에 달리는 드롭다운 메뉴 */
            QMenu {{
                background-color: {c.bg};
                color: {c.text};
                border: 1px solid {c.border};
                padding: 4px 0px;
            }}
            QMenu::item {{
                padding: 6px 24px;
                background-color: transparent;
            }}
            QMenu::item:selected {{
                background-color: {t.toolbar_hover};
            }}
            QMenu::item:disabled {{
                color: {t.toolbar_disabled};
            }}
            QMenu::separator {{
                height: 1px;
                background-color: {t.toolbar_separator};
                margin: 4px 0px;
            }}
        """


class BaseToolButton(QToolButton, ColorStyled):
    """툴바용 기본 툴버튼."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_colors(WidgetColors(text=tokens().text_inverse))

    def _build_qss(self, c: WidgetColors) -> str:
        t = tokens()
        return f"""
            BaseToolButton {{
                color: {c.text};
                background: {c.bg};
                border: none;
                border-radius: 4px;
                padding: 6px;
            }}
            BaseToolButton:hover {{
                background-color: {t.toolbar_hover};
            }}
            BaseToolButton:disabled {{
                color: {t.toolbar_disabled};
                background: transparent;
            }}
            BaseToolButton::menu-indicator {{
                image: none;
            }}
        """


class LampToolButton(BaseToolButton):
    """램프(상태 표시등) 툴버튼.

    램프 색은 클래스 속성에 캐시하지 않고 paint 시점에 tokens() 에서 읽는다."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._is_accent_on = False

    def set_accent(self, state: bool) -> None:
        if self._is_accent_on != state:
            self._is_accent_on = state
            self.update()

    def _build_qss(self, c: WidgetColors) -> str:
        # 좌측에 램프 자리를 확보하기 위한 패딩 추가
        return super()._build_qss(c) + """
            LampToolButton {
                padding-left: 22px;
                padding-right: 12px;
            }
        """

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        option = QStyleOptionToolButton()
        self.initStyleOption(option)
        self.style().drawComplexControl(QStyle.ComplexControl.CC_ToolButton, option, painter, self)

        t = tokens()
        lamp_color = QColor(t.success if self._is_accent_on else t.border)
        painter.setBrush(lamp_color)
        painter.setPen(Qt.NoPen)

        radius = 3
        margin_x = 8

        rect = self.rect()
        x = margin_x
        y = int((rect.height() / 2) - radius)

        # 원형 램프 그리기
        painter.drawEllipse(x, y, radius * 2, radius * 2)
        painter.end()
