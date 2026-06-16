from PySide6.QtCore import Qt, QRect, QSize, QPoint
from PySide6.QtWidgets import QLayout

class MyFlowLayout(QLayout):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._item_list = []

    def __del__(self):
        item = self.takeAt(0)
        while item:
            item = self.takeAt(0)

    def addItem(self, item):
        self._item_list.append(item)

    def count(self):
        return len(self._item_list)

    def itemAt(self, index):
        if 0 <= index < len(self._item_list):
            return self._item_list[index]
        return None

    def takeAt(self, index):
        if 0 <= index < len(self._item_list):
            return self._item_list.pop(index)
        return None

    def expandingDirections(self):
        return Qt.Orientation(0)

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, width):
        return self._do_layout(QRect(0, 0, width, 0), True)

    def setGeometry(self, rect):
        super().setGeometry(rect)
        self._do_layout(rect, False)

    def sizeHint(self):
        return self.minimumSize()

    def minimumSize(self):
        size = QSize()
        for item in self._item_list:
            size = size.expandedTo(item.minimumSize())
        left, top, right, bottom = self.getContentsMargins()
        size += QSize(left + right, top + bottom)
        return size

    def _do_layout(self, rect, test_only):
        left, top, right, bottom = self.getContentsMargins()
        effective_rect = rect.adjusted(+left, +top, -right, -bottom)
        y = effective_rect.y()
        
        space_x = self.spacing() if self.spacing() >= 0 else 10
        space_y = self.spacing() if self.spacing() >= 0 else 10

        current_row = []
        current_row_width = 0

        # 한 줄의 배치를 확정하고 위젯 크기를 늘려주는 내부 함수
        def flush_row(row_items, current_y):
            if not row_items:
                return 0
            
            # 현재 줄에서 여백을 제외하고 위젯들이 가질 수 있는 실제 가로 총 너비
            total_space_x = space_x * (len(row_items) - 1)
            avail_width = effective_rect.width() - total_space_x
            
            # 각 위젯이 가져야 할 균등한 너비 계산 (남는 소수점 픽셀 처리 포함)
            widget_width = max(1, avail_width // len(row_items))
            remainder = avail_width % len(row_items)
            
            curr_x = effective_rect.x()
            max_h = 0
            
            for i, item in enumerate(row_items):
                # 여분의 픽셀을 앞쪽 위젯들에 1px씩 분배해서 정확히 꽉 채움
                w = widget_width + (1 if i < remainder else 0)
                h = item.sizeHint().height()
                max_h = max(max_h, h)
                
                if not test_only:
                    item.setGeometry(QRect(curr_x, current_y, w, h))
                curr_x += w + space_x
                
            return max_h

        # 모든 위젯을 돌며 줄바꿈 타이밍 계산
        for item in self._item_list:
            item_w = item.sizeHint().width()
            needed_width = item_w + (space_x if current_row else 0)
            
            # 가로 경계를 넘어가면 기존 줄을 화면에 배치(flush)하고 새 줄 시작
            if current_row_width + needed_width > effective_rect.width() and current_row:
                row_h = flush_row(current_row, y)
                y += row_h + space_y
                
                current_row = [item]
                current_row_width = item_w
            else:
                current_row.append(item)
                current_row_width += needed_width

        # 마지막에 남아있는 줄 배치
        if current_row:
            row_h = flush_row(current_row, y)
            y += row_h

        return y - rect.y() + bottom