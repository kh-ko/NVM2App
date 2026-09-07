"""트리 컨트롤 모음.

- BaseTreeWidget: 앱 표준 트리. 체크박스 항목(ItemIsUserCheckable) 등 항목
  구성은 사용처 몫.

[주의] 폴더-하위 체크 연동에 Qt 의 ItemIsAutoTristate 를 쓰지 말 것 —
항목 수천 개에서 자식별 전파가 부모 재계산을 반복해 느리고, 변경된 자식들의
리페인트가 마우스 이동/스크롤 전까지 지연된다 (BackupWin 실측). 전파는
사용처가 itemChanged 에서 수동으로 수행하고 viewport().update() 로 마무리할 것
(예: backup_win.py 의 handle_changed_tree_item)."""

from PySide6.QtWidgets import QTreeWidget

from c_ui.b_control_ver2.a_theme import style
from c_ui.b_control_ver2.a_theme.color_styled import ColorStyled, WidgetColors
from c_ui.b_control_ver2.a_theme.tokens import tokens


class BaseTreeWidget(QTreeWidget, ColorStyled):
    """앱 표준 트리. 헤더 없는 단일 컬럼이 기본이다."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setHeaderHidden(True)

        t = tokens()
        self._init_colors(WidgetColors(text=t.text, border=t.border, bg=t.panel_bg))

    def _build_qss(self, c: WidgetColors) -> str:
        t = tokens()
        return f"""
            BaseTreeWidget {{
                color: {c.text};
                background-color: {c.bg};
                border: 1px solid {c.border};
                border-radius: 4px;
                outline: 0px;
            }}
            BaseTreeWidget:disabled {{
                color: {style.disabled(c.text)};
                border: 1px solid {style.disabled(c.border)};
            }}
            BaseTreeWidget::item {{
                padding: 2px 4px;
            }}
            BaseTreeWidget::item:hover {{
                background-color: {t.selection_bg};
            }}
            BaseTreeWidget::item:selected {{
                background-color: {t.selection_bg};
                color: {t.selection_text};
            }}
        """
