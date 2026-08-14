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

from PySide6.QtWidgets import QApplication

from b_core.e_worker_ver2.parameter_run_worker import StartResult
from c_ui.c_window_ver2.x_message.param_result_message_box import (
    ask_local_switch, show_param_refresh_warning, show_param_write_warning)
from c_ui.c_window_ver2.x_message.wait_message_box import show_busy_wait_message_box


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
