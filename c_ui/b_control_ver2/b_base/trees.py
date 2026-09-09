"""트리 컨트롤 모음.

- BaseTreeWidget: 앱 표준 트리. 체크박스 항목(ItemIsUserCheckable) 등 항목
  구성은 사용처 몫이며, 폴더-하위 체크 연동용 상태 헬퍼를 제공한다.

[주의] 폴더-하위 체크 연동에 Qt 의 ItemIsAutoTristate 를 쓰지 말 것 —
항목 수천 개에서 자식별 전파가 부모 재계산을 반복해 느리고, 변경된 자식들의
리페인트가 마우스 이동/스크롤 전까지 지연된다 (BackupWin 실측). 대신 사용처가
itemChanged 에서 (재진입 가드를 걸고) 아래 헬퍼로 수동 전파한 뒤
viewport().update() 로 마무리할 것 (예: backup_win.py 의 handle_changed_tree_item)."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QTreeWidget, QTreeWidgetItem

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

    # ------------------------------------------------------------ 체크 상태 헬퍼
    def set_subtree_check_state(self, item: QTreeWidgetItem, state: Qt.CheckState) -> None:
        """item 의 모든 하위 항목을 state 로 일괄 설정 (item 자신은 제외)."""
        for index in range(item.childCount()):
            child = item.child(index)
            child.setCheckState(0, state)
            self.set_subtree_check_state(child, state)

    def update_ancestor_check_states(self, item: QTreeWidgetItem | None) -> None:
        """item 부터 루트까지 조상 폴더들의 체크 상태를 자식 기준으로 갱신."""
        while item is not None:
            item.setCheckState(0, self._folder_state_from_children(item))
            item = item.parent()

    def recompute_all_folder_check_states(self) -> None:
        """전체 폴더 체크 상태를 말단(leaf) 상태 기준으로 재계산 (일괄 변경 후 호출)."""
        for index in range(self.topLevelItemCount()):
            self._recompute_folder_check_state(self.topLevelItem(index))

    def _folder_state_from_children(self, item: QTreeWidgetItem) -> Qt.CheckState:
        has_checked = has_unchecked = False
        for index in range(item.childCount()):
            state = item.child(index).checkState(0)
            if state == Qt.CheckState.PartiallyChecked:
                has_checked = has_unchecked = True
            elif state == Qt.CheckState.Checked:
                has_checked = True
            else:
                has_unchecked = True

        if has_checked and has_unchecked:
            return Qt.CheckState.PartiallyChecked
        return Qt.CheckState.Checked if has_checked else Qt.CheckState.Unchecked

    def _recompute_folder_check_state(self, item: QTreeWidgetItem) -> Qt.CheckState:
        # 하위 폴더부터 확정한 뒤 자신을 계산한다 (후위 순회)
        if item.childCount() == 0:
            return item.checkState(0)

        for index in range(item.childCount()):
            self._recompute_folder_check_state(item.child(index))

        state = self._folder_state_from_children(item)
        item.setCheckState(0, state)
        return state

    # ------------------------------------------------------------ 스타일
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
