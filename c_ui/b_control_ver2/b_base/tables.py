"""표 컨트롤 모음.

- WrapHeaderView: 가로 헤더 — 제목이 열 폭보다 길면 단어 단위로 줄바꿈해 그리고, 헤더 높이를
  가장 긴 제목에 맞춘다. 열 폭을 끌어 바꾸면 높이를 다시 계산한다.
- BaseTableWidget: 앱 표준 읽기 전용 표 (편집·선택·포커스 없음, 가로 헤더 = WrapHeaderView).
  행/열/항목 구성은 사용처 몫이며, 항목 글자색 같은 데이터 의존 표시는 사용처가
  QTableWidgetItem 에 직접 준다. 테마 색은 BaseTreeWidget 과 같은 계약(ColorStyled)으로 입는다.
"""

from PySide6.QtCore import QRect, QSize, Qt
from PySide6.QtWidgets import QAbstractItemView, QHeaderView, QStyle, QTableWidget

from c_ui.b_control_ver2.a_theme import style
from c_ui.b_control_ver2.a_theme.color_styled import ColorStyled, WidgetColors
from c_ui.b_control_ver2.a_theme.tokens import tokens


class WrapHeaderView(QHeaderView):
    """줄바꿈 가로 헤더.

    Qt 헤더는 제목을 한 줄로만 그린다. 기본 정렬 플래그에 TextWordWrap 을 섞으면 스타일이 글자를
    줄바꿈해 그리지만 높이는 한 줄 기준이라 잘리므로, sectionSizeFromContents 에서 현재 열 폭에
    맞춘 줄바꿈 높이를 돌려준다. 열 폭 변경(sectionResized) 시 헤더 기하를 다시 잡아 높이를 갱신한다."""

    # 글자와 섹션 테두리 사이 여백 (QSS padding 3px 6px + 스타일 기본 여백을 넉넉히 덮는 값)
    TEXT_MARGIN = 12

    def __init__(self, parent=None):
        super().__init__(Qt.Horizontal, parent)
        self.setDefaultAlignment(Qt.AlignCenter | Qt.AlignmentFlag(Qt.TextFlag.TextWordWrap.value))
        self.setHighlightSections(False)
        self.sectionResized.connect(self.handle_section_resized)

    def _text_margin(self) -> int:
        return self.style().pixelMetric(QStyle.PM_HeaderMargin, None, self) * 2 + self.TEXT_MARGIN

    def sectionSizeFromContents(self, logical_index: int) -> QSize:
        base = super().sectionSizeFromContents(logical_index)
        model = self.model()
        if model is None:
            return base

        text = model.headerData(logical_index, self.orientation(), Qt.DisplayRole)
        text = "" if text is None else str(text)
        width = self.sectionSize(logical_index) or base.width()
        margin = self._text_margin()
        rect = self.fontMetrics().boundingRect(QRect(0, 0, max(1, width - margin), 0),
                                               int(Qt.TextWordWrap | Qt.AlignCenter), text)
        return QSize(base.width(), max(base.height(), rect.height() + margin))

    def handle_section_resized(self, *_args):
        # 열 폭이 바뀌면 줄 수가 달라진다 — 헤더 기하 갱신(geometriesChanged)으로 표가 높이를 다시 잡는다
        self.updateGeometries()


class BaseTableWidget(QTableWidget, ColorStyled):
    """앱 표준 읽기 전용 표. selectable_rows=True 면 행 하나를 고를 수 있다 (itemSelectionChanged 로 알림)."""

    def __init__(self, rows: int = 0, columns: int = 0, parent=None, selectable_rows: bool = False):
        super().__init__(rows, columns, parent)
        self.setHorizontalHeader(WrapHeaderView(self))
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)
        if selectable_rows:
            self.setSelectionMode(QAbstractItemView.SingleSelection)
            self.setSelectionBehavior(QAbstractItemView.SelectRows)
            self.setFocusPolicy(Qt.StrongFocus)
        else:
            self.setSelectionMode(QAbstractItemView.NoSelection)
            self.setFocusPolicy(Qt.NoFocus)
        self.verticalHeader().setHighlightSections(False)
        self.verticalHeader().setDefaultSectionSize(24)

        t = tokens()
        self._init_colors(WidgetColors(text=t.text, border=t.border, bg=t.panel_bg))

    # ------------------------------------------------------------ 스타일
    def _build_qss(self, c: WidgetColors) -> str:
        t = tokens()
        return f"""
            BaseTableWidget {{
                color: {c.text};
                background-color: {c.bg};
                border: 1px solid {c.border};
                border-radius: 4px;
                gridline-color: {c.border};
                outline: 0px;
            }}
            BaseTableWidget:disabled {{
                color: {style.disabled(c.text)};
                border: 1px solid {style.disabled(c.border)};
            }}
            BaseTableWidget::item {{
                padding: 2px 6px;
            }}
            BaseTableWidget::item:selected {{
                background-color: {t.selection_bg};
                color: {t.selection_text};
            }}
            BaseTableWidget QHeaderView::section {{
                color: {c.text};
                background-color: {t.table_header_bg};
                border: 0px;
                border-right: 1px solid {c.border};
                border-bottom: 1px solid {c.border};
                padding: 3px 6px;
            }}
            BaseTableWidget QTableCornerButton::section {{
                background-color: {t.table_header_bg};
                border: 0px;
                border-right: 1px solid {c.border};
                border-bottom: 1px solid {c.border};
            }}
        """
