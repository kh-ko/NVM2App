
from PySide6.QtWidgets import QListView
from PySide6.QtGui import QColor
from PySide6.QtCore import QAbstractListModel
from c_ui.b_control_packet.base.base_console_list import BaseConsoleList
from PySide6.QtWidgets import QHBoxLayout
from PySide6.QtWidgets import QSizePolicy
from PySide6.QtCore import Qt

from c_ui.b_control_packet.base.base_button import BaseButton
from c_ui.b_control_packet.base.base_label import BaseLabel
from c_ui.b_control_packet.controls.my_iconwarn import MyIconWarn
from b_core.b_datatype.general_enum import LogType

COLOR_ERROR = QColor(Qt.red)
COLOR_NORMAL = QColor(Qt.white)

class MyConsoleModel(QAbstractListModel):
    def __init__(self, max_rows=1000, parent=None):
        super().__init__(parent)
        self._logs = []
        self._max_rows = max_rows

    def rowCount(self, parent=None):
        return len(self._logs)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        log_type, log_str = self._logs[index.row()]
        
        # 1. 화면에 로그 텍스트를 출력할 때
        if role == Qt.DisplayRole:
            return log_str
            
        # 2. 로그 텍스트의 글자 색상(Foreground)을 지정할 때
        elif role == Qt.ForegroundRole:
            if log_type == LogType.ERROR:
                return COLOR_ERROR
            else:
                return COLOR_NORMAL
                
        return None

    def add_log(self, log_type: LogType, log_str):
        if len(self._logs) >= self._max_rows:
            chunk_size = min(200, self._max_rows // 10)
            self.beginRemoveRows(self.index(0).parent(), 0, chunk_size - 1)
            del self._logs[:chunk_size]
            self.endRemoveRows()

        self.beginInsertRows(self.index(0).parent(), len(self._logs), len(self._logs))
        self._logs.append((log_type, log_str))
        self.endInsertRows()

    def clear(self):
        self.beginResetModel()
        self._logs = []
        self.endResetModel()

    def get_all_text(self):
        return "\n".join([log_str for _, log_str in self._logs])

class MyConsoleList(BaseConsoleList):
    def __init__(self, max_rows=1000, parent=None):
        super().__init__(parent = parent)

        self.model : MyConsoleModel = MyConsoleModel(max_rows)
        self.setModel(self.model)
        #self.setLayoutMode(QListView.Batched)
        #self.setBatchSize(100)
        self.setWordWrap(False)
        self.setUniformItemSizes(True)

    def rowCount(self, parent=None):
        return self.model.rowCount(parent)

    def add_log(self, log_type: LogType, log_str):
        # 스크롤이 가장 하단에 위치되어있을때만 add_log 이후에 scrollToBottom() 호출되도록
        is_at_bottom = self.verticalScrollBar().value() == self.verticalScrollBar().maximum()

        self.model.add_log(log_type, log_str)
        
        if is_at_bottom:
            self.scrollToBottom()

    def clear(self):
        self.model.clear()

    def get_all_text(self):
        return self.model.get_all_text()        