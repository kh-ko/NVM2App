"""Help >> Update 창 (ver1 HelpNvmUpdateWin 재작성) — FTP 배포본으로 앱 자체 업데이트.

동작 흐름:
  창 열림 -> 릴리스 노트(version_info.txt) 조회 (워커 + 대기 박스)
  -> 좌측 버전 목록 / 우측 선택 버전의 수정 내용 표시 (최신이 위, 기본 선택)
  -> Update 클릭 -> 확인 질문 -> 워커: zip 다운로드 -> 압축 해제 ... 진행바 갱신
  -> 성공: 설치 스크립트 기동 후 앱 종료 (스크립트가 파일 교체 후 앱을 재실행한다)
  -> 실패/중단: 메시지, 진행바는 멈춘 자리 유지

GUI 표시 정책: 사용자에게 보이는 것은 [Installed Version / Selected Version]
과 진행바 하나뿐이다. 다운로드/압축 해제/스크립트 같은 세부 단계는 LogView
(상태바 Log View 버튼)에만 기록된다 (펌웨어 업데이트 창과 같은 정책).

ParamWin 을 상속하는 이유: 장비 param 은 다루지 않지만 상태바(연결 정보/SN/
Log View)와 창 규약(win_name, closeEvent 정리)을 다른 창들과 통일하기 위함
(사용자 결정). 그에 따른 되돌림은 펌웨어 창과 같은 수준이다:
- paths=[] 라 Save/Load/Apply 는 ParamWin 이 스스로 숨기고, Refresh 만 제거한다.
- 본문은 항상 활성 — param 이 없어 sig_finish_refresh 가 오지 않으므로
  ParamWin 기본(첫 refresh 까지 잠금)대로면 본문이 영영 잠긴다.
- monitor_tick=1000 — 읽을 param 이 없는 모니터를 100ms 로 돌릴 이유가 없다.
- 미연결 시 상태바 경고색은 정상 표시이므로 그대로 둔다.

ver1 에서 달라진 점:
- FTP 조회/다운로드/압축 해제가 UI 스레드에서 사라졌다 — 워커 시그널 + 대기 박스.
- 버전마다 카드 + 버튼을 동적으로 만들던 스크롤 목록 대신 [버전 목록 | 수정
  내용] 마스터-디테일 + 툴바 Update 버튼 (ConnectionConnectWin 과 같은 구성).
- FTP 실패 시 하드코딩 폴백 노트를 보여주지 않는다 — 서버에 없는 버전은
  설치할 수도 없으므로 빈 목록 + 오류 메시지가 정직하다. 다시 조회하려면
  창을 다시 연다.
- 소스 실행(python main.py) 상태에서는 설치를 거부한다.
- 실행 중 창 닫기: 확인 후 워커 중단 + 종료 대기 (ver1 은 QThread 파괴 크래시).
"""

from enum import Enum, auto

from PySide6.QtCore import Qt
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import (QApplication, QHBoxLayout, QListWidgetItem, QMessageBox,
                               QVBoxLayout, QWidget)

from b_core.a_define import app_info
from b_core.c_manager.app_log_manager import AppLogManager
from b_core.e_worker_ver2.app_update_run_worker import ABORT_MESSAGE, AppUpdateRunWorker
from b_core.f_helper import app_update_helper
from b_core.f_helper.app_update_helper import ReleaseNote

from c_ui.b_control_ver2.b_base.containers import (BaseListWidget, BaseSplitter, PanelWidget,
                                                   ScrolledPanelWidget)
from c_ui.b_control_ver2.b_base.labels import BaseLabel, CheckLabel
from c_ui.b_control_ver2.b_base.statusbars import BaseProgressBar
from c_ui.b_control_ver2.d_param.param_win import ParamWin

from c_ui.c_window_ver2.x_message.app_update_message_box import (ask_abort_download,
                                                                 ask_install_version,
                                                                 show_source_run_notice)
from c_ui.c_window_ver2.x_message.wait_message_box import show_wait_message_box

_NOTES_PLACEHOLDER = "Select a version from the list."
_NOTES_UNAVAILABLE = "Release notes are not available. (See Log View for the error)"


class _Stage(Enum):
    IDLE       = auto()
    LISTING    = auto()  # 릴리스 노트 조회 중 (대기 박스)
    PREPARING  = auto()  # zip 다운로드 -> 압축 해제 스레드 실행 중
    INSTALLING = auto()  # 설치 스크립트 기동 -> 앱 종료 직전


class _ProgressRow(QWidget):
    """[체크 아이콘 + 문구 + 진행바] 한 행 — 업데이트 전체 진행 표시용."""

    def __init__(self, text: str, parent=None):
        super().__init__(parent)
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(10)

        self.check = CheckLabel(text)
        row.addWidget(self.check)

        self.progress = BaseProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setFixedHeight(18)
        row.addWidget(self.progress, 1)

    def set_value(self, percent: int):
        self.progress.setRange(0, 100)
        self.progress.setValue(max(0, min(100, percent)))

    def set_busy(self):
        # 전체 크기를 모를 때(서버가 SIZE 미지원) — 무한 진행 표시
        self.progress.setRange(0, 0)

    def set_checked(self, checked: bool):
        self.check.set_checked(checked)
        if checked:
            self.set_value(100)

    def reset(self):
        self.check.set_checked(False)
        self.set_value(0)


class HelpNvmUpdateWin(ParamWin):

    # 오버라이드 핸들러가 super().__init__() 중에도 호출될 수 있으므로 클래스 기본값
    _stage = _Stage.IDLE
    _wait_box = None
    content_widget = None

    def __init__(self, parent=None, win_name: str = "Application Update"):
        super().__init__(parent=parent, win_name=win_name, paths=[], filter_param_paths=[],
                         is_editblock_win=False, label_width=210, folder_max_width=None,
                         monitor_tick=1000)
        self.setWindowTitle("Help >> Update")

        self._log = AppLogManager().get_logger(self.win_name)
        self._notes: list[ReleaseNote] = []
        self._selected_version: str | None = None

        self.toolbar.remove_action("Refresh")
        self.toolbar.add_action("Update", self.on_clicked_update)
        self.toolbar.add_action("Abort", self.on_clicked_abort)

        self.update_worker = AppUpdateRunWorker(self, log_source=self.win_name)
        self.update_worker.sig_release_notes_finished.connect(self.handle_release_notes_finished)
        self.update_worker.sig_prepare_progress.connect(self.handle_prepare_progress)
        self.update_worker.sig_prepare_finished.connect(self.handle_prepare_finished)

        self._build_body()
        self._set_stage(_Stage.IDLE)
        self._start_listing()

    # ------------------------------------------------------------ GUI 구성
    def _build_body(self):
        """ParamWin 의 폴더 카드 스크롤 영역은 쓰지 않으므로 중앙 위젯을 교체한다
        (BackupWin 과 같은 방식). content_widget 도 재지정한다."""
        old_central = self.takeCentralWidget()
        old_central.deleteLater()

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        self.content_widget = central_widget
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        # 상단: 사용자 결정 사항 + 진행바 (세부 단계는 LogView 에만)
        panel = PanelWidget(title="Application Update")
        self.row_installed = CheckLabel(f"Installed Version : v{app_info.APP_VERSION}", checked=True)
        self.row_selected = CheckLabel("Selected Version : -")
        self.row_progress = _ProgressRow("Progress")
        for row in (self.row_installed, self.row_selected, self.row_progress):
            panel.add_widget(row)
        main_layout.addWidget(panel)

        # 하단: [버전 목록 | 선택 버전의 수정 내용]
        self.splitter = BaseSplitter(Qt.Horizontal)
        main_layout.addWidget(self.splitter, 1)

        self.version_list = BaseListWidget()
        self.version_list.currentRowChanged.connect(self.on_changed_version_item)
        self.splitter.addWidget(self.version_list)

        self.notes_panel = ScrolledPanelWidget(title="Release Notes")
        self.lbl_notes = BaseLabel(_NOTES_PLACEHOLDER)
        self.lbl_notes.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        self.lbl_notes.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.notes_panel.add_widget(self.lbl_notes)
        self.splitter.addWidget(self.notes_panel)

        self.splitter.setSizes([250, 500])
        self.content_widget.setEnabled(True)  # 모듈 주석 '본문은 항상 활성' 참고

    def _set_stage(self, stage: _Stage):
        self._stage = stage
        is_idle = stage == _Stage.IDLE
        self.toolbar.set_action_enabled("Update", is_idle and self._selected_version is not None)
        self.toolbar.set_action_enabled("Abort", stage == _Stage.PREPARING)
        self.version_list.setEnabled(is_idle)

    def _close_wait_box(self):
        if self._wait_box is not None:
            box = self._wait_box
            self._wait_box = None
            box.accept()

    def _set_notes(self, version: str | None):
        if version is None:
            self.notes_panel.lbl_title.setText("Release Notes")
            self.lbl_notes.setText(_NOTES_PLACEHOLDER if self._notes else _NOTES_UNAVAILABLE)
            return

        note = next((n for n in self._notes if n.version == version), None)
        self.notes_panel.lbl_title.setText(f"Release Notes : {version}")
        self.lbl_notes.setText(note.notes if note is not None and note.notes else "(no notes)")

    def handle_changed_working(self, working: bool):
        # 본문은 표시 전용 — param 워커 동작 여부와 무관하게 항상 활성 (모듈 주석 참고)
        if self.content_widget is not None:
            self.content_widget.setEnabled(True)

    # ------------------------------------------------------------ 릴리스 노트 조회
    def _start_listing(self):
        self._set_stage(_Stage.LISTING)
        self._wait_box = show_wait_message_box(self, "Application Update",
                                               "Fetching the release notes from FTP...")
        if not self.update_worker.start_release_notes():
            self._close_wait_box()
            self._set_stage(_Stage.IDLE)

    def handle_release_notes_finished(self, ok: bool, notes: list, msg: str):
        if self._stage != _Stage.LISTING:
            return

        self._close_wait_box()
        self._notes = list(notes) if ok else []

        # 목록 재구성 — currentRowChanged 로 선택/노트 표시가 따라온다
        self.version_list.clear()
        for note in self._notes:
            text = note.version
            if app_update_helper.is_installed_version(note.version):
                text += "  (installed)"
            item = QListWidgetItem(text)
            item.setData(Qt.UserRole, note.version)
            self.version_list.addItem(item)

        if self._notes:
            self.version_list.setCurrentRow(0)  # 최신 버전 기본 선택
        else:
            self.on_changed_version_item(-1)

        self._set_stage(_Stage.IDLE)

        if not ok:
            QMessageBox.critical(self, "FTP Error", msg)
        elif not self._notes:
            QMessageBox.warning(self, "Warning", "No release was found on the server.")

    def on_changed_version_item(self, row: int):
        item = self.version_list.item(row) if row >= 0 else None
        self._selected_version = item.data(Qt.UserRole) if item is not None else None

        if self._selected_version is None:
            self.row_selected.setText("Selected Version : -")
            self.row_selected.set_checked(False)
        else:
            self.row_selected.setText(f"Selected Version : {self._selected_version}")
            self.row_selected.set_checked(True)

        self._set_notes(self._selected_version)
        self._set_stage(self._stage)  # Update 활성 여부 갱신

    # ------------------------------------------------------------ 사용자 액션
    def on_clicked_update(self):
        if self._stage != _Stage.IDLE or self._selected_version is None:
            return

        version = self._selected_version

        # 소스 실행 중 설치 = 프로젝트 폴더에 배포본을 덮어쓰는 것 — 다운로드 전에 거부
        if not app_update_helper.is_deployed_exe():
            self._log.warning(f"[Cancelled] running from source - install refused: {version}")
            show_source_run_notice(self)
            return

        if not ask_install_version(self, version, app_update_helper.is_installed_version(version)):
            self._log.info(f"[Cancelled] update cancelled by user: {version}")
            return

        self.row_progress.reset()
        self._set_stage(_Stage.PREPARING)
        if not self.update_worker.start_prepare(version):
            self._log.error("[Cancelled] update worker is busy")
            self._set_stage(_Stage.IDLE)

    def on_clicked_abort(self):
        if self._stage != _Stage.PREPARING:
            return
        if ask_abort_download(self):
            self.update_worker.abort()  # 결과는 handle_prepare_finished(False, "", ABORT_MESSAGE) 로

    # ------------------------------------------------------------ 준비 진행/완료
    def handle_prepare_progress(self, done: int, total: int):
        if self._stage != _Stage.PREPARING:
            return
        if total > 0:
            self.row_progress.set_value(int(done * 100 / total))
        else:
            self.row_progress.set_busy()

    def handle_prepare_finished(self, ok: bool, package_root: str, msg: str):
        if self._stage != _Stage.PREPARING:
            return

        if not ok:
            # 진행바는 멈춘 자리에 둔다 — 세부 사유는 메시지와 LogView 로
            self._set_stage(_Stage.IDLE)
            if msg == ABORT_MESSAGE:
                QMessageBox.information(self, "Application Update", "The update was aborted.")
            else:
                QMessageBox.critical(self, "Application Update Failed", msg)
            return

        self.row_progress.set_checked(True)
        self._set_stage(_Stage.INSTALLING)

        try:
            script_path = app_update_helper.launch_installer(package_root)
        except Exception as e:
            self._log.error(f"[Install] could not start the installer: {e}")
            self._set_stage(_Stage.IDLE)
            QMessageBox.critical(self, "Application Update Failed",
                                 f"The update package is ready, but the installer could not be started.\n\n{e}")
            return

        # 스크립트가 exe 잠금 해제(=앱 종료)를 기다린다 — 여기서 앱을 끝낸다.
        # 워커 정리는 aboutToQuit 연결로 수행된다
        self._log.info(f"[Install] installer started ({script_path}) - quitting application")
        QApplication.quit()

    # ------------------------------------------------------------ 종료
    def closeEvent(self, event: QCloseEvent):
        if self._stage == _Stage.PREPARING:
            if not ask_abort_download(self):
                event.ignore()
                return
            self.update_worker.abort()

        # 실행 중 QThread 파괴 = 앱 abort — 중단 완료까지 기다린 뒤 닫는다
        # (릴리스 노트 조회 중이면 접속 타임아웃 안팎 블로킹될 수 있다)
        self.update_worker.cleanup()
        self._close_wait_box()
        super().closeEvent(event)  # param_worker.cleanup()
