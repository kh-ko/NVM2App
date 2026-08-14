"""컨테이너 위젯 컨트롤 모음.

- BaseGroupBox: 타이틀이 테두리 선에 걸치는 그룹박스.
- PanelWidget: [타이틀 행 / 구분선 / 콘텐츠] 구성의 카드형 패널
  (기존 my_card_widget.py 의 MyCardWidget 대응. 배경은 panel_bg 토큰,
  구분선은 테두리색을 따라간다).
  title=None 이면 타이틀 행/구분선 없이 콘텐츠만 담고,
  fit=True 면 바깥 여백/간격 0 으로 꽉 채운다 (차트 패널 등).
- ScrolledPanelWidget: PanelWidget 과 동일 모양 — 내용이 넘치면 타이틀은
  고정한 채 콘텐츠 영역만 세로 스크롤된다.
- BaseValueBox: 값 표시 위젯 n개를 세로로 담는 박스 컨테이너
  (placeholder 전환 장치 포함 — 비트맵/enum 나열 등 상위 레이어가 채운다).
- BaseListWidget: 기본 리스트 위젯 (기존 my_list_widget.py 의 MyListWidget 대응).
- BaseSplitter: 핸들이 1px 인 스플리터 (기존 my_splitter.py 의 MySplitter 대응).
- BaseFlowLayout: 아이템을 왼쪽->오른쪽으로 배치하다 폭이 모자라면 다음 줄로
  내려가는 흐름 레이아웃 (기존 my_flow_layout.py 의 MyFlowLayout 계승).
  줄이 확정되면 그 줄의 아이템들이 남는 폭을 균등 분배해 가로를 꽉 채운다.

base 레이어 규칙: 기본 커스텀 컨트롤 — 스타일 + 기본 합성을 모두 관장하되,
값 계약(set_value 등)과 앱 도메인 의미는 모른다.

QGroupBox 네이티브 타이틀은 텍스트만 가능해서, 타이틀 행에 위젯(dirty 마커 등)을
얹으려면 오버레이 합성이 필요하다:
- 네이티브 타이틀은 color: transparent 로 숨기고 (여백 확보용으로만 사용)
- 오버레이 타이틀(title_widget + BaseLabel)을 resizeEvent 에서 (10, 0) 위치로 이동
- 상위 레이어는 add_title_widget() / add_title_stretch() 로 타이틀 행을 확장
"""

from PySide6.QtCore import Signal
from PySide6.QtCore import QEvent, QRect, QSize, Qt
from PySide6.QtGui import QEnterEvent
from PySide6.QtWidgets import (QFrame, QGroupBox, QHBoxLayout, QLayout,
                               QListWidget, QScrollArea, QSplitter, QVBoxLayout,
                               QWidget)

from c_ui.b_control_ver2.b_base.buttons import BaseButton
from c_ui.b_control_ver2.b_base.labels import BaseLabel, LabelRole
from c_ui.b_control_ver2.a_theme import style
from c_ui.b_control_ver2.a_theme.color_styled import ColorStyled, WidgetColors
from c_ui.b_control_ver2.a_theme.tokens import tokens

class BaseGroupBox(QGroupBox, ColorStyled):
    def __init__(self, title="", border=True, parent=None):
        # 네이티브 타이틀은 QSS 에서 color: transparent 로 숨기고
        # (여백 확보용으로만 사용) 오버레이 라벨로 실제 타이틀을 그린다.
        super().__init__(title, parent)
        self.setProperty("isHovered", False)

        self.title_widget = QWidget(self)
        self.title_layout = QHBoxLayout(self.title_widget)
        self.title_layout.setContentsMargins(0, 0, 0, 0)
        self.title_layout.setSpacing(0)

        self.title_label = BaseLabel(title)
        self.title_label.setWordWrap(False)
        self.title_layout.addWidget(self.title_label)

        t = tokens()
        if border:
            colors = WidgetColors(border=t.border, hover_border=t.border_hover)
        else:
            colors = WidgetColors(border="transparent", hover_border="transparent")
        self._init_colors(colors, border_enabled=border)

    def add_title_widget(self, widget, stretch: int = 0):
        """타이틀 행에 위젯 추가 (dirty 마커 등)."""
        self.title_layout.addWidget(widget, stretch)

    def add_title_stretch(self):
        """타이틀 행 끝에 신축 공간 추가."""
        self.title_layout.addStretch()

    def _build_qss(self, c: WidgetColors) -> str:
        border = self._effective_border()
        return f"""
            BaseGroupBox {{
                background-color: {c.bg};
                font-size: 14px;
                font-weight: normal;
                margin-top: 10px;
                border: 1px solid {border};
                border-radius: 4px;
                color: transparent;
            }}
            BaseGroupBox:disabled {{
                border: 1px solid {style.disabled(border)};
            }}
            BaseGroupBox[isHovered="true"] {{
                border: 1px solid {c.hover_border};
            }}
        """

    def enterEvent(self, event: QEnterEvent):
        self.setProperty("isHovered", True)
        self.style().unpolish(self)  # 스타일 강제 초기화
        self.style().polish(self)    # 스타일 재적용 (변경된 속성 반영)
        super().enterEvent(event)

    def leaveEvent(self, event: QEvent):
        self.setProperty("isHovered", False)
        self.style().unpolish(self)
        self.style().polish(self)
        super().leaveEvent(event)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # 타이틀 위젯을 (x=10, y=0) 위치로 이동 (테두리 선에 걸치는 느낌)
        self.title_widget.move(10, 0)
        # 내용물 길이에 맞춰 위젯 크기 자동 조절
        self.title_widget.resize(self.title_widget.sizeHint())


class PanelWidget(QWidget, ColorStyled):
    sig_clicked_title_btn = Signal()

    def __init__(self, title, is_big_title = False, btn_icon=None, fit=False, btn_text=None, parent=None):
        super().__init__(parent)

        self.setAttribute(Qt.WA_StyledBackground, True)

        self.main_layout = QVBoxLayout(self)
        if fit:
            self.main_layout.setContentsMargins(0, 0, 0, 0)
            self.main_layout.setSpacing(0)            
        else:
            self.main_layout.setContentsMargins(10, 10, 10, 10)
            self.main_layout.setSpacing(5)

        if title is not None:
            self.title_layout = QHBoxLayout()
            self.title_layout.setContentsMargins(0, 0, 0, 0)

            # 1. 상단 타이틀
            if is_big_title:
                self.lbl_title = BaseLabel(text=title, role=LabelRole.TITLE)
            else:
                self.lbl_title = BaseLabel(text=title, role=LabelRole.DESCRIPTION)

            self.lbl_title.setWordWrap(False)
            self.title_layout.addWidget(self.lbl_title)
            self.title_layout.addStretch()

            # 타이틀 우측 버튼 — btn_icon/btn_text 가 주어진 경우에만 생성.
            # 사용측은 sig_clicked_title_btn 에 connect 한다 (버튼 유무와 무관하게 시그널은 항상 존재)
            self.title_button = None
            if btn_icon is not None or btn_text is not None:
                self.title_button = BaseButton(btn_text if btn_text else "", btn_icon, border = False)
                self.title_button.clicked.connect(self.sig_clicked_title_btn)
                self.title_layout.addWidget(self.title_button)

            self.main_layout.addLayout(self.title_layout)

            # 2. 타이틀/콘텐츠 구분선 — 색은 _build_qss 에서 테두리색과 함께 관리
            self.separator = QFrame()
            self.separator.setObjectName("panelSeparator")
            self.separator.setFixedHeight(1) # 선의 두께를 명시적으로 1px로 지정
            self.main_layout.addWidget(self.separator)

        # 3. 하단 컨텐츠를 담을 빈 위젯 & 레이아웃
        # (qdarktheme 전역 QWidget 배경 규칙이 서브클래스가 아닌 plain QWidget 도
        #  칠하므로, objectName 선택자로 투명 배경을 명시해야 한다)
        self.content_widget = QWidget()
        self.content_widget.setObjectName("panelContent")
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(5)
        self.main_layout.addWidget(self.content_widget)
        self.main_layout.addStretch()

        t = tokens()
        self._init_colors(WidgetColors(bg=t.panel_bg, border=t.border))

    def add_widget(self, widget):
        self.content_layout.addWidget(widget)

    def _build_qss(self, c: WidgetColors) -> str:
        border = self._effective_border()
        return f"""
            PanelWidget {{
                background-color: {c.bg};
                border: 1px solid {border};
            }}
            PanelWidget:disabled {{
                border: 1px solid {style.disabled(border)};
            }}
            QFrame#panelSeparator {{
                background-color: {border};
                border: none;
                margin-top: 5px;
                margin-bottom: 5px;
            }}
            QFrame#panelSeparator:disabled {{
                background-color: {style.disabled(border)};
            }}
            QWidget#panelContent {{
                background-color: transparent;
            }}
        """

class ScrolledPanelWidget(PanelWidget):
    """PanelWidget 과 모양이 동일하되, 내용이 넘치면 타이틀/구분선은 고정한 채
    콘텐츠 영역만 세로 스크롤되는 패널.

    PanelWidget 이 구성한 [content_widget + 하단 stretch] 를 QScrollArea 구조로
    재배치한다. add_widget() 등 사용법은 PanelWidget 과 동일하다."""

    def __init__(self, title, is_big_title = False, btn_icon=None, btn_text=None, parent=None):
        super().__init__(title, is_big_title, btn_icon, btn_text, parent)

        # 부모가 넣은 content_widget 과 하단 stretch 를 빼낸다
        self.main_layout.removeWidget(self.content_widget)

        last_item = self.main_layout.itemAt(self.main_layout.count() - 1)
        if last_item is not None and last_item.spacerItem() is not None:
            self.main_layout.removeItem(last_item)

        # 콘텐츠 영역을 스크롤 영역으로 감싼다 (가로 스크롤 없이 세로만)
        self.scroll_area = QScrollArea()
        self.scroll_area.setObjectName("panelScroll")
        self.scroll_area.setFrameShape(QFrame.NoFrame)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        # 뷰포트도 plain QWidget 이라 qdarktheme 전역 배경에 노출 — 투명 규칙 대상
        self.scroll_area.viewport().setObjectName("panelScrollViewport")
        self.scroll_area.setWidget(self.content_widget)
        self.main_layout.addWidget(self.scroll_area, 1)

        # 내용이 뷰포트보다 작을 때 위쪽 정렬 유지 (stretch 대신 정렬로 처리 —
        # stretch 방식은 add_widget 이 stretch 뒤에 붙는 문제가 생긴다)
        self.content_layout.setAlignment(Qt.AlignTop)

    def _build_qss(self, c: WidgetColors) -> str:
        # 스크롤 영역/뷰포트는 패널 배경이 그대로 비치도록 투명 처리
        return super()._build_qss(c) + """
            QScrollArea#panelScroll {
                background-color: transparent;
                border: none;
            }
            QWidget#panelScrollViewport {
                background-color: transparent;
            }
        """


class BaseValueBox(QWidget, ColorStyled):
    """값 표시 위젯 n개를 세로로 수납하는 박스 컨테이너.

    - add_value_widget(widget): 행 추가 (위→아래 순서 유지).
    - box=True: 테두리 박스 스타일 (BaseLabel 의 box 옵션과 동일 컨셉).
      QSS padding 은 plain QWidget 레이아웃에 반영되지 않으므로 안쪽 여백은
      레이아웃 마진으로 확보한다.
    - placeholder: set_placeholder_visible(True) 면 수납된 위젯을 전부 숨기고
      setPlaceholderText() 로 설정한 문구 한 줄만 표시한다.

    base 레이어 규칙에 따라 값 계약(set_value 등)과 'Unknown'/'Not Support'
    같은 문구의 의미는 모른다 — 값 구성/문구 결정은 상위(c_values) 몫이다."""

    def __init__(self, box=False, parent=None):
        super().__init__(parent)
        # plain QWidget 서브클래스는 이 속성이 있어야 QSS 배경/테두리가 그려진다
        self.setAttribute(Qt.WA_StyledBackground, True)
        self._boxed = box

        self._root_layout = QVBoxLayout(self)
        self._root_layout.setContentsMargins(*((5, 5, 5, 5) if box else (0, 0, 0, 0)))
        self._root_layout.setSpacing(5)

        self._placeholder_label = BaseLabel("")
        self._placeholder_label.setVisible(False)
        self._root_layout.addWidget(self._placeholder_label)

        self._value_widgets = []
        self._placeholder_visible = False

        self._init_colors(WidgetColors(border=tokens().border))

    def add_value_widget(self, widget):
        self._value_widgets.append(widget)
        self._root_layout.addWidget(widget)
        # placeholder 표시 중에 추가된 행은 곧바로 숨겨 문구만 보이게 유지한다
        if self._placeholder_visible:
            widget.setVisible(False)

    def setPlaceholderText(self, text: str):
        """placeholder 문구 설정 — 라인에딧의 setPlaceholderText 대응 (문구 결정은 호출측)."""
        self._placeholder_label.setText(text)

    def set_placeholder_visible(self, visible: bool):
        """True 면 수납 위젯 전부 숨김 + placeholder 만 표시, False 면 복원."""
        self._placeholder_visible = visible
        self._placeholder_label.setVisible(visible)
        for widget in self._value_widgets:
            widget.setVisible(not visible)

    def _build_qss(self, c: WidgetColors) -> str:
        border = self._effective_border()
        if self._boxed:
            box = f"border: 1px solid {border}; border-radius: 4px;"
            box_disabled = f"border: 1px solid {style.disabled(border)}; border-radius: 4px;"
        else:
            box = box_disabled = ""

        return f"""
            BaseValueBox {{
                background-color: {c.bg};
                {box}
            }}
            BaseValueBox:disabled {{
                background-color: {style.disabled(c.bg)};
                {box_disabled}
            }}
        """


class BaseListWidget(QListWidget, ColorStyled):
    """기본 리스트 위젯. 선택 항목은 selection_* 토큰으로 강조한다."""

    def __init__(self, parent=None):
        super().__init__(parent)

        t = tokens()
        self._init_colors(WidgetColors(text=t.text, border=t.border, bg=t.popup_bg))

    def _build_qss(self, c: WidgetColors) -> str:
        t = tokens()
        border = self._effective_border()
        return f"""
            BaseListWidget {{
                color: {c.text};
                background-color: {c.bg};
                border: 1px solid {border};
                border-radius: 0px;
                padding: 0px;
            }}
            BaseListWidget:disabled {{
                color: {style.disabled(c.text)};
                border: 1px solid {style.disabled(border)};
            }}
            BaseListWidget::item {{
                padding: 5px;
                border-radius: 0px;
            }}
            BaseListWidget::item:selected {{
                background-color: {t.selection_bg};
                color: {t.selection_text};
                font-weight: bold;
            }}
        """

class BaseSplitter(QSplitter, ColorStyled):
    """기본 스플리터. 핸들은 1px 투명선이 기본 —
    구분선을 보이게 하려면 set_colors(bg=...) 로 핸들 색을 지정한다."""

    def __init__(self, orientation: Qt.Orientation = Qt.Horizontal, parent=None):
        super().__init__(orientation, parent)
        self.setHandleWidth(1)

        self._init_colors(WidgetColors())  # bg 기본값 = transparent

    def _build_qss(self, c: WidgetColors) -> str:
        return f"""
            BaseSplitter::handle {{
                background-color: {c.bg};
                margin: 0px;
                padding: 0px;
            }}
            /* 가로 스플리터일 경우 폭 1px 고정 */
            BaseSplitter::handle:horizontal {{
                width: 1px;
            }}
            /* 세로 스플리터일 경우 높이 1px 고정 */
            BaseSplitter::handle:vertical {{
                height: 1px;
            }}
        """


class BaseFlowLayout(QLayout):
    """아이템을 왼쪽 -> 오른쪽으로 배치하다 폭이 모자라면 다음 줄로 내려가는
    흐름 레이아웃 (기존 my_flow_layout.py 의 MyFlowLayout 계승).

    - 줄 구성(한 줄에 몇 개)은 item_width(줄 구성 기준 폭)로 판단한다.
      None 이면 무제한 폭으로 간주해 한 줄에 1개씩 — 가로 분할이 일어나지
      않고 아이템이 항상 전체 폭을 채운다.
    - 줄이 확정되면 그 줄의 아이템들이 남는 폭을 균등 분배해 가로를 꽉 채운다
      (justify — 나머지 픽셀은 앞쪽 아이템에 1px 씩 배분). 따라서 아이템 폭은
      item_width ~ 2*item_width 사이에서 늘어나다 다음 열이 들어갈 수 있을 때
      분할된다.
    - heightForWidth 를 제공하므로 QScrollArea(widgetResizable) 안에서도
      콘텐츠 높이가 뷰포트 폭에 맞춰 올바르게 계산된다."""

    def __init__(self, parent=None, margin=0, spacing=5, item_width=None):
        super().__init__(parent)
        self.setContentsMargins(margin, margin, margin, margin)
        self.setSpacing(spacing)
        self._items = []

        # 줄 구성 기준 폭 — 아이템 하나가 '원하는 폭'으로 간주되어 한 줄에 몇 개
        # 들어갈지 결정한다. None 이면 무제한 폭으로 간주 -> 한 줄에 1개씩
        # (가로 분할 없이 항상 세로 나열, 아이템은 전체 폭을 채운다)
        self._item_width = item_width

    def set_item_width(self, item_width):
        """줄 구성 기준 폭 변경 (None = 무제한 -> 분할 없음). 즉시 재배치한다."""
        self._item_width = item_width
        self.invalidate()

    # ------------------------------------------------------------ QLayout 필수 구현
    def addItem(self, item):
        self._items.append(item)

    def count(self):
        return len(self._items)

    def itemAt(self, index):
        if 0 <= index < len(self._items):
            return self._items[index]
        return None

    def takeAt(self, index):
        if 0 <= index < len(self._items):
            return self._items.pop(index)
        return None

    def expandingDirections(self):
        return Qt.Orientations(0)  # 스스로 늘어나지 않는다 — 부모가 폭을 정한다

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, width):
        return self._do_layout(QRect(0, 0, width, 0), test_only=True)

    def setGeometry(self, rect):
        super().setGeometry(rect)
        self._do_layout(rect, test_only=False)

    def sizeHint(self):
        return self.minimumSize()

    def minimumSize(self):
        size = QSize()
        for item in self._items:
            size = size.expandedTo(item.minimumSize())

        margins = self.contentsMargins()
        size += QSize(margins.left() + margins.right(), margins.top() + margins.bottom())
        return size

    # ------------------------------------------------------------ 배치 계산
    def _do_layout(self, rect, test_only) -> int:
        """rect 폭 기준으로 흐름 배치를 계산하고 필요한 전체 높이를 반환한다.

        test_only=True 면 지오메트리를 건드리지 않고 높이 계산만 한다
        (heightForWidth 경로). 줄 구성은 item_width(줄 구성 기준 폭)로 판단하고,
        줄이 확정되면 그 줄의 아이템들에게 남는 폭을 균등 분배해 가로를 꽉
        채운다. 줄 높이는 그 줄에서 가장 큰 아이템 높이(sizeHint)다."""
        margins = self.contentsMargins()
        effective = rect.adjusted(margins.left(), margins.top(), -margins.right(), -margins.bottom())
        spacing = max(self.spacing(), 0)

        def flush_row(row_items, row_y) -> int:
            """한 줄을 확정 배치하고 줄 높이를 반환한다 — 폭 균등 분배(justify)."""
            available = effective.width() - spacing * (len(row_items) - 1)
            item_width = max(1, available // len(row_items))
            remainder = available % len(row_items)

            x = effective.x()
            row_height = 0
            for i, item in enumerate(row_items):
                # 나머지 픽셀을 앞쪽 아이템에 1px 씩 배분해 정확히 꽉 채운다
                width = item_width + (1 if i < remainder else 0)
                height = item.sizeHint().height()
                row_height = max(row_height, height)

                if not test_only:
                    item.setGeometry(QRect(x, row_y, width, height))
                x += width + spacing

            return row_height

        # 줄 구성 기준 폭 — item_width 미지정(None)이면 유효 폭 전체로 간주해
        # 어떤 폭에서도 한 줄에 1개만 들어간다 (가로 분할 없음)
        base_width = self._item_width if self._item_width is not None else effective.width()

        y = effective.y()
        row_items = []
        row_width = 0

        for item in self._items:
            needed = base_width + (spacing if row_items else 0)

            # 현재 줄에 안 들어가면 지금까지의 줄을 확정하고 새 줄 시작
            if row_items and row_width + needed > effective.width():
                y += flush_row(row_items, y) + spacing
                row_items = [item]
                row_width = base_width
            else:
                row_items.append(item)
                row_width += needed

        if row_items:
            y += flush_row(row_items, y)

        return y - rect.y() + margins.bottom()