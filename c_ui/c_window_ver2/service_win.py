"""ServiceWin — ParameterRunWorker·툴바·상태바를 가진 창의 골격 (2단계 8위, 2026-10-06 ① 적용).

ParamWin(폴더 카드 창)이 이 골격 위에 있다. 폴더 카드가 필요 없는 창 7개(Backup/Restore/Sensor Analysis/Cluster Monitor/
Firmware Update/About/Application Update)는 ② 까지 ParamWin 을 상속한 채 되돌리는 코드를 갖는다 (Refresh 액션 제거 5곳,
'항상 활성' 오버라이드 3곳, content_widget 직접 교체 6곳, 생성자 중 핸들러 호출 때문에 둔 클래스 기본값 7곳) — ② 에서 제거한다.
계약은 다음 셋이다.

1. 2단계 초기화 — __init__ 은 위젯만 만든다. 시그널 구독·초기 연결 동기화·잠금 확정은 start() 가 하고, WinManager.show_window 가
   생성 직후·show() 직전에 1회 부른다 (테스트는 직접 부른다). 그래서 서브클래스의 __init__ 이 끝난 뒤에만 핸들러가 불리며,
   "오버라이드 핸들러가 super().__init__() 중에도 불린다" 는 이유로 두던 클래스 기본값이 필요 없어진다 (N095/N072 뿌리).
2. 잠금 단일 지점 — 본문·툴바 액션의 활성 여부는 _sync_lock_state() 한 곳이 정한다: 입력은 워커 is_working, 편집 잠금
   (_edit_locked), 창의 정책(locks_content). 창은 이 함수를 오버라이드하지 않고 locked_actions() / edit_locked_actions() 로
   잠글 액션 이름만 돌려준다. 본문을 트리·표·차트로 바꾸는 창은 set_body() 로 바꾸며, 그 안에서 잠금이 재확정된다.
3. 선택 구성 — has_refresh(Refresh 액션), with_param_worker(워커 없는 창: About), locks_content(표시 전용 창: FU/About/Update 는
   False). 되돌리는 코드 대신 생성 인자로 고른다.

이관 계획(부분 적용 가능, 단계마다 tools/run_tests.py 7/7 이 게이트):
  ① (적용) WinManager.show_window 가 start() 를 부르고, ParamWin 이 ServiceWin 위로
  ② 폴더 카드 없는 창 7개를 ServiceWin 직계로 이관 (되돌리는 코드 제거)
  ③ ParamWin 을 c_window_ver2/param_win.py 로, 인터페이스 창 2종을 e_iface/ 로 이동, d_param 에는 위젯만 남김 (F061/F062)
ParamWorkerWinMixin(쓰기 정책·재부팅 대기·연결 상태바)은 이 파일에 있고 MainWin 도 계속 쓴다 (param_win 이 재수출).

① 에서 의도적으로 달라진 동작 (2026-10-06 사용자 결정):
- 창 제목 = win_name — ParamWin 계열은 그동안 제목이 비어 있었다. 자기 제목이 있는 창(FU/About/Update)은 super().__init__() 뒤에 덮어쓴다.
- 툴바 잠금: 모든 ParamWin 에서 워커 동작 중(refresh/write/PENDING/재부팅 대기) Apply·Save File·Load File·Enable Edit 이 비활성
  (전에는 본문만 잠기고 Apply 는 눌러서 BUSY 경고를 받았다); 편집 잠금 창은 Save File 도 편집 잠금 중 비활성 (전에는 Load File 만).
- 트리/표/차트 본문 창(Backup/Restore/Cluster Monitor/Sensor Analysis)은 여는 순간부터 초기 refresh·PENDING 동안 본문이 잠긴다
  (전에는 교체된 본문이 첫 전환까지 열려 있었다 — N072/F081 의 뿌리).
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import QApplication, QMainWindow, QWidget

from b_core.c_manager.parameter_manager import ParamManager
from b_core.d_dal.service_port import ServicePort
from b_core.e_worker_ver2.parameter_run_worker import ParameterRunWorker, StartResult

from c_ui.b_control_ver2.b_base.statusbars import BaseStatusBar
from c_ui.b_control_ver2.b_base.toolbars import BaseToolBar
from c_ui.c_window_ver2.log_view_win import LogViewWin
from c_ui.c_window_ver2.win_manager import WinManager
from c_ui.c_window_ver2.x_message.param_result_message_box import (
    ask_local_switch, show_param_refresh_warning, show_param_write_skipped, show_param_write_warning)
from c_ui.c_window_ver2.x_message.wait_message_box import show_busy_wait_message_box

"""ParameterRunWorker 를 소유한 윈도우 공통 동작 믹스인.

MainWin / ParamWin 등 param_worker 를 가진 창마다 문자 단위로 복사되던
쓰기 정책(Local 전환 확인 재시도) / refresh / 연결·SN 상태바 처리를 한곳으로
모은다. 앞으로 만들 설정 창들도 이 믹스인을 상속하면 된다.

사용 조건 — 호스트 클래스가 준비해야 하는 속성:
- self.param_worker : ParameterRunWorker
- self.statusbar    : BaseStatusBar (라벨 0 = 연결 정보, 라벨 1 = SN)
- self.sn_param     : Parameter (System.Identification.Serial Number)

연결 끊김 시 추가 동작(예: MainWin 의 compound 폴링 중지)이 필요한 창은
handle_changed_connection_info 를 오버라이드해 super() 호출 전후로 수행한다.
"""
class ParamWorkerWinMixin:

    _reboot_wait_box = None  # 재부팅 대기 중일 때만 인스턴스에 박스 참조가 얹힌다

    def single_param_write(self, param, value):
        self.multiple_param_write([(param, value)])

    def multiple_param_write(self, pairs: list):
        result = self.param_worker.write(pairs)

        # Local 전환 후 재시도 여부는 윈도우가 결정한다 (x_message 는 표시 전용)
        if result == StartResult.NEED_LOCAL_SWITCH:
            if not ask_local_switch(self):
                return
            result = self.param_worker.write(pairs, switch_to_local=True)

        show_param_write_warning(self, result)

    def start_param_refresh(self):
        result = self.param_worker.refresh()
        show_param_refresh_warning(self, result)

    def handle_skipped_write(self, params: list):
        # 워커가 codec 문맥 미준비로 요청 없이 건너뛴 쓰기 — 시퀀스 종료 시 한 번 알림
        # (호스트 창은 param_worker.sig_write_skipped 를 이 슬롯에 연결한다)
        show_param_write_skipped(self, params)

    def handle_changed_connection_info(self, info: str):
        is_connected = bool(info)
        self.statusbar.set_connected(is_connected)
        self.statusbar.set_label_text(0, info if info else "Disconnected")

        if is_connected:
            self.start_param_refresh()
        else:
            # 연결이 끊겼으므로 모든 동작을 중지하고 idle 로 — REBOOT 대기만 예외
            self.param_worker.handle_disconnected()

    def handle_changed_sn_param(self):
        self.statusbar.set_label_text(1, f"SN:{self.sn_param.value}" if self.sn_param.value is not None else "SN:-")

    def handle_changed_param_worker_progress(self, progress: int):
        self.statusbar.set_progress(progress)

    def handle_started_reboot(self):
        # 재부팅 유발 param 쓰기 후 워커가 SN probe 폴링을 시작했다 —
        # 재연결까지 무한 진행 표시로 이 창 입력을 막는다 (닫기는 이 창 몫).
        # 재부팅 중 다른 동작은 금지이므로 취소는 없고, 완전 잠김 방지용
        # 비상구로 App 종료 버튼만 둔다
        if self._reboot_wait_box is not None:
            return

        self._reboot_wait_box = show_busy_wait_message_box(
            self, "Reboot",
            "The device is rebooting.\nWaiting for reconnection...",
            quit_text="Quit App")
        self._reboot_wait_box.quit_button.clicked.connect(self.on_clicked_quit_app)

    def handle_finished_reboot(self, is_success: bool):
        # True = 재부팅 후 통신 복구 (재연결 refresh 는 connect_info_changed 경유)
        if self._reboot_wait_box is not None:
            box = self._reboot_wait_box
            self._reboot_wait_box = None
            box.accept()

    def on_clicked_quit_app(self):
        # 재부팅 대기 중 완전 잠김 방지용 비상구 — 앱 전체를 종료한다.
        # [주의] busy 다이얼로그는 닫기 거부(reject 무시)로 만들어져 있어,
        # 떠 있는 채로 quit() 하면 Qt6 가 '닫히지 않는 창'으로 보고 종료
        # 요청을 중단한다 (실측) — 반드시 먼저 accept() 로 닫고 종료한다.
        # (워커들의 cleanup 은 aboutToQuit 연결로 수행된다)
        if self._reboot_wait_box is not None:
            box = self._reboot_wait_box
            self._reboot_wait_box = None
            box.accept()

        QApplication.quit()



class ServiceWin(ParamWorkerWinMixin, QMainWindow):
    """워커·툴바·상태바 골격. 폴더 카드 창은 ParamWin(ServiceWin), 그 밖의 창은 이 클래스를 직접 상속한다.

    생성자 인자
      win_name          로그 출처·LogView 필터·워커 이름. None 이면 클래스 이름.
      has_refresh       툴바에 Refresh 액션을 둘지 (Backup/Restore/FU/About/Update 는 False).
      with_param_worker ParameterRunWorker 를 소유할지 (About 은 False — 상태바 연결 표시만 한다).
      locks_content     워커 동작·편집 잠금에 따라 본문을 잠글지 (표시 전용 창은 False — 툴바 액션 잠금은 그대로 적용).
      monitor_tick      워커 모니터링 주기(ms).

    서브클래스가 쓰는 훅
      set_body(central, lock_target=None)  본문을 놓는다 (한 번 이상 호출). lock_target 이 잠금 대상, 없으면 central.
      locked_actions()                     워커 동작 중 비활성화할 툴바 액션 이름들 (예: Backup 창의 "Backup").
      edit_locked_actions()                편집 잠금 중에도 비활성화할 액션 이름들 (ParamWin: Apply/Save File/Load File).
      on_start()                           start() 의 마지막 — 초기 연결 동기화가 끝난 뒤 창별 시작 동작(타이머, 자동 로드 등).
      on_working_changed(working)          워커 동작 변화에 창별로 덧붙일 일 (잠금 자체는 건드리지 않는다).
      handle_finished_refresh()            refresh 완료 (MainWin 의 compound 폴링 재개 같은 후속).
    쓰기 정책·재부팅 대기 박스·연결 상태바는 ParamWorkerWinMixin 이 제공한다.
    """

    def __init__(self, parent=None, win_name: str | None = None, *, has_refresh: bool = True,
                 with_param_worker: bool = True, locks_content: bool = True, monitor_tick: int = 100):
        super().__init__(parent)
        self.win_name = win_name or type(self).__name__
        self.has_refresh = has_refresh
        self.locks_content = locks_content
        self.content_widget: QWidget | None = None
        self._edit_locked = False
        self._started = False
        self.setWindowTitle(self.win_name)
        self.resize(750, 450)

        self.toolbar = BaseToolBar(self)
        self.addToolBar(Qt.TopToolBarArea, self.toolbar)
        if has_refresh:
            self.toolbar.add_action("Refresh", self.on_clicked_refresh)

        self.statusbar = BaseStatusBar(parent=self, label_count=2)
        self.statusbar.btn_log.clicked.connect(self.on_clicked_log_view)
        self.setStatusBar(self.statusbar)

        self.param_manager = ParamManager()
        self.svc_port = ServicePort()
        self.sn_param = self.param_manager.get_by_full_path("System.Identification.Serial Number")

        # 워커 — 액션별 1:1 연결. 시그널 구독은 생성자에서 해도 된다: 워커는 start() 전에는 아무 요청도 보내지 않는다
        self.param_worker: ParameterRunWorker | None = None
        if with_param_worker:
            self.param_worker = ParameterRunWorker(self, log_source=self.win_name, monitor_tick=monitor_tick)
            self.param_worker.sig_finish_refresh.connect(self.handle_finished_refresh)
            self.param_worker.sig_reboot_started.connect(self.handle_started_reboot)
            self.param_worker.sig_reboot_finished.connect(self.handle_finished_reboot)
            self.param_worker.sig_progress_changed.connect(self.handle_changed_param_worker_progress)
            self.param_worker.sig_is_working_changed.connect(self.handle_changed_working)
            self.param_worker.sig_write_skipped.connect(self.handle_skipped_write)

    # ------------------------------------------------------------ 2단계 초기화
    def start(self) -> None:
        """시그널 구독 + 초기 연결 동기화(연결 중이면 refresh) + 잠금 확정 + on_start(). 멱등.

        WinManager.show_window 가 생성 직후·show() 직전에 부른다. 서브클래스 __init__ 이 모두 끝난 뒤라
        핸들러가 미완성 객체를 만나지 않는다. 테스트는 창을 만든 뒤 직접 부른다."""
        if self._started:
            return
        self._started = True

        self.sn_param.sig_value_changed.connect(self.handle_changed_sn_param)
        self.handle_changed_sn_param()
        self.svc_port.connect_info_changed.connect(self.handle_changed_connection_info)
        self.handle_changed_connection_info(self.svc_port.connect_info)
        # 잠금 확정은 워커 시그널과 같은 경로(handle_changed_working)로 — ② 이관 전의 파생 창이 그 메서드를
        # 오버라이드하고 있어 _sync_lock_state 를 직접 부르면 그 창의 정책을 우회한다 (검토 지적)
        self.handle_changed_working(self.is_working)
        self.on_start()

    def on_start(self) -> None:
        """start() 의 마지막 훅 — 창별 시작 동작 (샘플 타이머, 백업 파일 자동 로드, 표 행 구성 등)."""

    # ------------------------------------------------------------ 본문
    def set_body(self, central: QWidget, lock_target: QWidget | None = None) -> None:
        """중앙 위젯을 central 로 놓고 잠금 대상을 lock_target(없으면 central)로 둔다. 이전 중앙 위젯은 파괴한다.
        교체 뒤 잠금을 다시 확정하므로, 연결 직후 PENDING 중에 바꿔도 본문이 열린 채 남지 않는다."""
        old = self.takeCentralWidget()
        if old is not None:
            old.deleteLater()
        self.setCentralWidget(central)
        self.content_widget = lock_target if lock_target is not None else central
        self._sync_lock_state()

    # ------------------------------------------------------------ 잠금 단일 지점
    @property
    def is_working(self) -> bool:
        return self.param_worker is not None and self.param_worker.is_working

    def locked_actions(self) -> tuple[str, ...]:
        """워커 동작(refresh/write/PENDING/재부팅 대기) 중 비활성화할 툴바 액션 이름들."""
        return ()

    def edit_locked_actions(self) -> tuple[str, ...]:
        """편집 잠금(_edit_locked) 중에도 비활성화할 툴바 액션 이름들 — 워커 동작 중에도 당연히 잠긴다."""
        return ()

    def _sync_lock_state(self) -> None:
        """본문·툴바 액션의 활성 여부를 정하는 유일한 곳. 오버라이드하지 않는다 — 입력(locks_content, 잠금 목록)으로 조정한다."""
        busy = self.is_working
        if self.locks_content and self.content_widget is not None:
            self.content_widget.setEnabled(not busy and not self._edit_locked)
        for name in self.locked_actions():
            self.toolbar.set_action_enabled(name, not busy)
        for name in self.edit_locked_actions():
            self.toolbar.set_action_enabled(name, not busy and not self._edit_locked)

    def set_edit_locked(self, locked: bool) -> None:
        """편집 잠금 전환 (ParamWin 의 Enable Edit). 잠금 상태 반영까지 한다."""
        self._edit_locked = locked
        self._sync_lock_state()

    def handle_changed_working(self, working: bool) -> None:
        self.on_working_changed(working)
        self._sync_lock_state()

    def on_working_changed(self, working: bool) -> None:
        """워커 동작 변화에 창별로 덧붙일 일 (예: ParamWin 은 편집 잠금 창을 다시 잠근다). 활성/비활성은 건드리지 않는다."""

    # ------------------------------------------------------------ 툴바 공통
    def on_clicked_refresh(self) -> None:
        self.start_param_refresh()

    def on_clicked_log_view(self) -> None:
        # win_id 를 창 이름으로 분리 — 다른 창의 LogViewWin 과 WinManager 키가 겹치면 sources 필터가 무시된다
        WinManager().show_window(win_class=LogViewWin, win_id=f"LogViewWin_{self.win_name}",
                                 parent=self, sources={self.win_name})

    def handle_finished_refresh(self) -> None:
        """refresh 완료 후속 — 기본은 없음."""

    # ------------------------------------------------------------ 믹스인 보강 (워커 없는 창)
    def start_param_refresh(self) -> None:
        if self.param_worker is not None:
            super().start_param_refresh()

    def handle_changed_connection_info(self, info: str) -> None:
        if self.param_worker is not None:
            super().handle_changed_connection_info(info)   # 상태바 + refresh / handle_disconnected
            return
        self.statusbar.set_connected(bool(info))
        self.statusbar.set_label_text(0, info if info else "Disconnected")

    # ------------------------------------------------------------ 종료
    def closeEvent(self, event: QCloseEvent) -> None:
        # 재부팅 대기 중이면 대기 박스를 함께 닫는다 — WindowModal 박스는 부모가 닫혀도 살아남아 이어지는
        # QApplication.quit() 을 거부한다 (재부팅 대기 중에도 앱 닫기는 항상 가능, 2026-09-29 결정)
        if self._reboot_wait_box is not None:
            box = self._reboot_wait_box
            self._reboot_wait_box = None
            box.accept()

        # WA_DeleteOnClose 로 파괴되기 전에 워커 스레드를 명시적으로 정리한다 — 누락 시 QThread fatal 로 앱 전체가 abort
        if self.param_worker is not None:
            self.param_worker.cleanup()
        event.accept()
