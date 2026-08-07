"""로그 실시간 뷰 창.

AppLogManager 의 링버퍼를 백필한 뒤 sig_logged 를 구독해 실시간 표시한다.
카테고리별 색상: TX=파랑, RX=초록, ERROR=빨강, 그 외=기본 글자색 (log_* 토큰).

sources 로 표시할 로그 출처를 제한할 수 있다 — 각 윈도우가 자기 컴포넌트
구성으로 열어 '현재 윈도우의 동작' 만 확인하는 용도. None 이면 전체 표시.
전역 로그(get_logger(..., is_global=True) — ServicePort, ParamManager,
stderr 등)는 sources 필터와 무관하게 항상 표시된다.

    LogViewWin(parent=self, sources={"MainWin"})
"""

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QListWidgetItem, QMainWindow

from b_core.c_manager.app_log_manager import AppLogManager, LogCategory, LogEntry

from c_ui.b_control_ver2.a_theme.tokens import tokens
from c_ui.b_control_ver2.b_base.containers import BaseListWidget
from c_ui.b_control_ver2.b_base.toolbars import BaseToolBar


class LogViewWin(QMainWindow):

    MAX_ITEMS = 2000  # 뷰 자체 상한 — 초과 시 오래된 줄부터 제거

    # parent 가 첫 파라미터인 것은 WinManager.show_window() 의
    # win_class(parent, ...) 호출 규약에 맞추기 위함이다.
    def __init__(self, parent=None, sources: set[str] | None = None):
        super().__init__(parent)
        self.setWindowTitle("Log View")
        self.resize(900, 500)

        self._sources = set(sources) if sources else None

        self.toolbar = BaseToolBar(self)
        self.addToolBar(Qt.TopToolBarArea, self.toolbar)
        self.toolbar.add_action("Clear", self.on_clicked_clear)

        t = tokens()
        self._category_colors = {
            LogCategory.TX: QColor(t.log_tx),
            LogCategory.RX: QColor(t.log_rx),
            LogCategory.ERROR: QColor(t.log_error),
        }
        self._default_color = QColor(t.text)

        self.list_widget = BaseListWidget()
        self.list_widget.setUniformItemSizes(True)  # 줄 높이 동일 가정 -> 레이아웃 비용 절감
        self.setCentralWidget(self.list_widget)

        # 최근분 백필 후 실시간 구독
        manager = AppLogManager()
        for entry in manager.snapshot(self._sources):
            self._append_entry(entry)
        self.list_widget.scrollToBottom()

        manager.sig_logged.connect(self.handle_logged)

    def on_clicked_clear(self):
        self.list_widget.clear()

    def handle_logged(self, entry: LogEntry):
        # 전역(is_global) 로그는 sources 필터와 무관하게 항상 표시
        if self._sources is not None and not entry.is_global and entry.source not in self._sources:
            return

        self._append_entry(entry)
        self.list_widget.scrollToBottom()

    def _append_entry(self, entry: LogEntry):
        while self.list_widget.count() >= self.MAX_ITEMS:
            self.list_widget.takeItem(0)

        item = QListWidgetItem(entry.to_line())
        item.setForeground(self._category_colors.get(entry.category, self._default_color))
        self.list_widget.addItem(item)

    def closeEvent(self, event):
        # 창이 닫히면 구독 해제 (닫힌 창으로의 시그널 전달 방지)
        try:
            AppLogManager().sig_logged.disconnect(self.handle_logged)
        except (TypeError, RuntimeError):
            pass
        super().closeEvent(event)
