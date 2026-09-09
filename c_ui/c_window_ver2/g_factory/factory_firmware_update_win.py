"""Factory >> Firmware Update 창 (ver1 FactoryFirmwareUpdateWin 재작성).

동작 흐름 (ver1 과 동일한 사용자 절차):
  Update 클릭
  -> 출처 선택 [Network / Local Files]
     (Network 면 워커가 FTP 버전 목록을 가져오는 동안 대기 박스 -> 버전 선택)
  -> 어댑터 선택 [RS232 / USB] -> COM 포트 선택
  -> 재연결용 ServicePort 설정 스냅샷 후 ServicePort 닫기 (워커가 같은 포트를 직접 연다)
  -> (RS232) 부트모드 진입 안내 3장
  -> FirmwareRunWorker.start_write(): (다운로드) -> 파일 로드 -> (USB: 핀/부트모드)
     -> CPU1 -> CPU2 -> (USB: 자동 리부트)      ... 진행바 갱신
  -> 성공: (RS232) 정상 부팅 복귀 안내 2장
     -> 업데이트 전 연결이 있었으면 ParameterRunWorker.start_reboot_wait() 로
        재부팅 완료(SN 응답)까지 대기 -> 재연결 refresh 완료 -> 공장 파라미터 복원 질문
        -> 복원이면 WO param 쓰기 (reconnect param 이라 워커가 한 번 더 재부팅 대기)
        -> 재연결 후 RestoreWin(FU 모드) 을 연다 — 업데이트 전 저장한 백업 파일이
           있으면(backup_file_path) 자동 로드, 없으면 빈 복원 창
        -> 공장 초기화를 Skip 해도 백업 파일이 있으면 RestoreWin 을 연다 (사용자 요청)
  -> 실패: 오류 메시지, 진행바는 실패 지점에서 멈춘 채 유지

백업 파일 경로는 MainWin 이 넘긴다: Firmware Update 메뉴 -> (연결 중이면) 백업
질문 -> BackupWin(FU 모드) -> 닫힐 때 경로와 함께 이 창을 띄운다.

GUI 표시 정책: 사용자에게 보이는 것은 [Update Method / Adapter Type / COM Port]
와 진행바 하나뿐이다. 워커의 세부 단계(커널/소거/검증...)는 GUI 에 노출하지
않는다 — 단계 이름이 보이면 문의가 늘어난다 (사용자 요청). 세부 단계와 결과는
LogView 에만 기록된다. 진행바는 이번 작업에서 수행될 단계 수로 영역을 균등
분할하고, 진행률이 있는 단계(다운로드/커널/앱/검증)는 그 구간 안을 채운다.
재연결 대기가 마지막 구간이므로 장비가 돌아와야 100% 가 된다.

ver1 에서 달라진 점:
- 선택 도중 취소 시 창을 닫지 않고 IDLE 로 돌아온다 (ver1 은 self.close()).
  COM 포트 선택 전에는 ServicePort 를 닫지 않는다 (ver1 은 취소해도 닫힌 채 남았다).
- FTP 조회/다운로드가 UI 스레드에서 사라졌다 — 워커 시그널 + 대기 박스.
- 진행 로그(MyConsoleList)는 LogView(상태바 Log View 버튼)로 대체. 워커/창 모두
  log_source = win_name 이라 한 뷰에 모인다. 바이트 단위 [Progress] 로그는 없앴다.
- 실행 중 창 닫기/Abort: 확인 후 워커 중단 + 종료 대기 (ver1 은 실행 중 닫으면
  QThread 파괴 크래시).
- 재부팅 대기 박스에 Cancel 을 둔다 — RS232 어댑터에서 사용자가 스위치/리셋을
  놓치면 장비가 영영 응답하지 않으므로 앱 종료 외의 탈출구가 필요하다.
  취소하면 포트는 닫힌 채(단선과 동일)이고 Connection > Connect 로 재연결한다.
- 창 상단에 System.Identification.Firmware 폴더 카드를 둔다 — 업데이트 전후의
  Firmware Version 을 같은 창에서 확인하고, 재연결 refresh 완료 시그널의
  근거(읽기 param)가 된다.
- 본문은 항상 활성 상태다 — ParamWin 기본(첫 refresh 완료까지 잠금)은 미연결
  상태에서 창을 열면 본문이 영영 잠긴 채 남는다. 이 창의 본문은 표시 전용이라
  잠글 이유가 없다 (ver1 도 content_widget.setEnabled(True) 를 명시했다).
"""

import os
from enum import Enum, auto

from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import QHBoxLayout, QMessageBox, QWidget

from b_core.a_define import file_folder_path as path_def
from b_core.c_manager.app_log_manager import AppLogManager
from b_core.e_worker_ver2.firmware_run_worker import (AdapterType, FirmwarePhase,
                                                      FirmwareRunWorker, FirmwareSource,
                                                      FirmwareWriteJob, list_com_port_names)
from b_core.e_worker_ver2.parameter_run_worker import StartResult

from c_ui.b_control_ver2.b_base.containers import PanelWidget
from c_ui.b_control_ver2.b_base.labels import CheckLabel
from c_ui.b_control_ver2.b_base.statusbars import BaseProgressBar
from c_ui.b_control_ver2.d_param.param_win import ParamWin

from c_ui.c_window_ver2.d_backup_restore.restore_win import RestoreWin
from c_ui.c_window_ver2.win_manager import WinManager
from c_ui.c_window_ver2.x_message.firmware_update_message_box import (
    ask_abort_update, ask_adapter_type, ask_com_port, ask_network_version,
    ask_restore_factory_params, ask_update_method, show_rs232_boot_mode_guide,
    show_rs232_reboot_guide)
from c_ui.c_window_ver2.x_message.param_result_message_box import show_param_write_warning
from c_ui.c_window_ver2.x_message.wait_message_box import (show_busy_wait_message_box,
                                                           show_wait_message_box)

# 어댑터/출처에 따라 수행되지 않는 단계 — 진행바 분할 계산에서 제외한다
_USB_ONLY_PHASES = (FirmwarePhase.SET_EEPROM_IO_PIN, FirmwarePhase.SET_BOOT_MODE,
                    FirmwarePhase.AUTO_REBOOT)
_NETWORK_ONLY_PHASES = (FirmwarePhase.DOWNLOAD,)

# 쓰기 완료 후 장비 재부팅/재연결 대기 — 진행바의 마지막 구간 (워커 단계가 아니다)
_STEP_RECONNECT = "reconnect"


class _Stage(Enum):
    IDLE        = auto()
    LISTING     = auto()  # FTP 버전 목록 조회 중 (대기 박스)
    WRITING     = auto()  # 펌웨어 쓰기 스레드 실행 중
    WAIT_REBOOT = auto()  # 쓰기 완료 -> 장비 재부팅/재연결 대기 (param_worker REBOOT)
    RESTORING   = auto()  # 공장 파라미터 복원 쓰기 -> 재부팅/재연결 대기


class _InfoRow(QWidget):
    """[체크 아이콘 + 문구] 한 행 — 선택 결과 표시용."""

    def __init__(self, text: str, parent=None):
        super().__init__(parent)
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        self.check = CheckLabel(text)
        row.addWidget(self.check, 1)

    def set_text(self, text: str):
        self.check.setText(text)

    def set_checked(self, checked: bool):
        self.check.set_checked(checked)


class _ProgressRow(QWidget):
    """[체크 아이콘 + 문구 + 전체 진행바] 한 행 — 업데이트 전체 진행 표시용."""

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
        self.progress.setValue(max(0, min(100, percent)))

    def set_checked(self, checked: bool):
        self.check.set_checked(checked)
        if checked:
            self.progress.setValue(100)

    def reset(self):
        self.check.set_checked(False)
        self.progress.setValue(0)


class FactoryFirmwareUpdateWin(ParamWin):

    # 오버라이드 핸들러가 super().__init__() 중에도 호출될 수 있으므로 클래스 기본값
    _stage = _Stage.IDLE
    _wait_box = None
    content_widget = None

    def __init__(self, parent=None, win_name=None, backup_file_path: str | None = None):
        # 상단 폴더 카드 = Firmware ID/Version/Interface Version (RO) — 읽기 param 이
        # 등록되어 재연결 refresh 가 EMPTY 가 아니게 되고 sig_finish_refresh 가 온다.
        # 모니터링 주기는 1초 — 버전 문자열을 100ms 마다 읽을 이유가 없다
        super().__init__(parent=parent, win_name=win_name, paths=["System.Identification.Firmware"],
                         filter_param_paths=[], is_editblock_win=False, label_width=210,
                         folder_max_width=None, monitor_tick=1000)
        self.setWindowTitle("Factory >> Firmware Update")
        self.resize(750, 450)

        self._log = AppLogManager().get_logger(self.win_name)
        self._job: FirmwareWriteJob | None = None
        self._saved_port_setting: tuple | None = None  # 업데이트 전 ServicePort 설정 (재연결용)

        # 업데이트 전 저장한 백업 파일 — 공장 초기화 후 RestoreWin 이 자동 로드한다.
        # 파일이 사라졌으면(이동/삭제) 없는 것으로 취급한다
        if backup_file_path and os.path.isfile(backup_file_path):
            self._backup_file_path = backup_file_path
        else:
            self._backup_file_path = None
            if backup_file_path:
                self._log.warning(f"[Backup File] not found — ignored: {backup_file_path}")

        # 진행바 분할: 이번 작업에서 수행될 단계 목록과 현재 위치
        self._steps: list = []
        self._step_index = 0

        self.toolbar.remove_action("Refresh")
        self.toolbar.add_action("Update", self.on_clicked_update)
        self.toolbar.add_action("Abort", self.on_clicked_abort)
        self.toolbar.set_action_enabled("Abort", False)

        self.fw_worker = FirmwareRunWorker(self, log_source=self.win_name)
        self.fw_worker.sig_version_list_finished.connect(self.handle_version_list_finished)
        self.fw_worker.sig_write_phase_changed.connect(self.handle_write_phase_changed)
        self.fw_worker.sig_write_progress_changed.connect(self.handle_write_progress_changed)
        self.fw_worker.sig_write_finished.connect(self.handle_write_finished)

        self._build_body()
        self.content_widget.setEnabled(True)  # 모듈 주석 '본문은 항상 활성' 참고

    def additional_param_settings(self):
        # WO 버튼 param — 업데이트 후 복원 질문에 Restore 를 고르면 쓴다 (reconnect param)
        self.restore_factory_param = self.param_manager.get_by_full_path("System.Services.Restore Factory Parameters")

    # ------------------------------------------------------------ GUI 구성
    def _build_body(self):
        """폴더 카드(ParamWin) 아래에 [선택 결과 3행 + 전체 진행바] 패널을 덧붙인다."""
        panel = PanelWidget(title="Firmware Update")

        # 백업 파일 행은 MainWin 의 백업 단계 결과라 이 창에서는 바뀌지 않는다
        if self._backup_file_path is not None:
            self.row_backup = _InfoRow(f"Backup File : {os.path.basename(self._backup_file_path)}")
            self.row_backup.set_checked(True)
        else:
            self.row_backup = _InfoRow("Backup File : (none)")

        self.row_method = _InfoRow("Update Method : -")
        self.row_adapter = _InfoRow("Adapter Type : -")
        self.row_port = _InfoRow("COM Port : -")
        self.row_progress = _ProgressRow("Progress")

        for row in (self.row_backup, self.row_method, self.row_adapter, self.row_port, self.row_progress):
            panel.add_widget(row)

        self.content_layout.addWidget(panel)

    def _reset_body(self):
        self.row_method.set_text("Update Method : -")
        self.row_adapter.set_text("Adapter Type : -")
        self.row_port.set_text("COM Port : -")
        for row in (self.row_method, self.row_adapter, self.row_port):
            row.set_checked(False)
        self.row_progress.reset()
        self._steps = []
        self._step_index = 0

    def _set_stage(self, stage: _Stage):
        self._stage = stage
        self.toolbar.set_action_enabled("Update", stage == _Stage.IDLE)
        self.toolbar.set_action_enabled("Abort", stage == _Stage.WRITING)

    def _close_wait_box(self):
        if self._wait_box is not None:
            box = self._wait_box
            self._wait_box = None
            box.accept()

    def handle_changed_working(self, working: bool):
        # 본문은 표시 전용 — 워커 동작 여부와 무관하게 항상 활성 (모듈 주석 참고)
        if self.content_widget is not None:
            self.content_widget.setEnabled(True)

    # ------------------------------------------------------------ 진행바 분할
    @staticmethod
    def _build_steps(job: FirmwareWriteJob, has_reconnect: bool) -> list:
        """이번 작업에서 수행될 단계 목록 (FirmwarePhase 정의 순서 = 실행 순서)."""
        steps = []
        for phase in FirmwarePhase:
            if phase in _USB_ONLY_PHASES and job.adapter_type != AdapterType.USB:
                continue
            if phase in _NETWORK_ONLY_PHASES and job.network_version is None:
                continue
            steps.append(phase)
        if has_reconnect:
            steps.append(_STEP_RECONNECT)
        return steps

    def _update_progress(self, fraction: float):
        """현재 단계 구간(1/단계수) 안을 fraction(0~1)만큼 채운 전체 백분율."""
        if not self._steps:
            return
        fraction = max(0.0, min(1.0, fraction))
        percent = int((self._step_index + fraction) / len(self._steps) * 100)
        self.row_progress.set_value(percent)

    # ------------------------------------------------------------ 사용자 액션
    def on_clicked_update(self):
        if self._stage != _Stage.IDLE:
            return

        source = ask_update_method(self)
        if source is None:
            return

        self._reset_body()

        if source == FirmwareSource.NETWORK:
            # 버전 목록은 워커가 가져온다 — 결과는 handle_version_list_finished 로
            self._set_stage(_Stage.LISTING)
            self._wait_box = show_wait_message_box(self, "Firmware Update",
                                                   "Fetching the firmware version list from FTP...")
            if not self.fw_worker.start_version_list():
                self._close_wait_box()
                self._set_stage(_Stage.IDLE)
            return

        self.row_method.set_text("Update Method : Local Files")
        self.row_method.set_checked(True)
        self._continue_selection(network_version=None)

    def on_clicked_abort(self):
        if self._stage != _Stage.WRITING:
            return
        if ask_abort_update(self):
            self.fw_worker.abort()  # 결과는 handle_write_finished(False, ...) 로

    def on_clicked_cancel_reboot_wait(self):
        # 재부팅 대기 취소 — 워커가 sig_reboot_finished(False) 를 내고 포트는 닫힌 채 남는다
        self.param_worker.cancel_reboot()

    # ------------------------------------------------------------ 선택 흐름
    def handle_version_list_finished(self, ok: bool, versions: list, msg: str):
        if self._stage != _Stage.LISTING:
            return

        self._close_wait_box()

        if not ok:
            QMessageBox.critical(self, "FTP Error", msg)
            self._set_stage(_Stage.IDLE)
            return

        if not versions:
            QMessageBox.warning(self, "Warning", "No firmware version list found on the server.")
            self._set_stage(_Stage.IDLE)
            return

        version = ask_network_version(self, versions)
        if version is None:
            self._cancel_selection()
            return

        self.row_method.set_text(f"Update Method : Network ({version})")
        self.row_method.set_checked(True)
        self._continue_selection(network_version=version)

    def _continue_selection(self, network_version: str | None):
        """출처가 정해진 뒤의 공통 절차: 어댑터 -> 포트 -> 파일 검사 -> 포트 닫기 -> 쓰기 시작."""
        adapter_type = ask_adapter_type(self)
        if adapter_type is None:
            self._cancel_selection()
            return
        self.row_adapter.set_text(f"Adapter Type : {adapter_type.name}")
        self.row_adapter.set_checked(True)

        port_name = ask_com_port(self, list_com_port_names(), self.svc_port.get_port_name())
        if port_name is None:
            self._cancel_selection()
            return
        self.row_port.set_text(f"COM Port : {port_name}")
        self.row_port.set_checked(True)

        is_network = network_version is not None

        # 앱 파일은 어댑터 종류별로 다르다 (FTP 파일명 규칙과 동일). 커널은 공통
        if adapter_type == AdapterType.RS232:
            flash_cpu1, flash_cpu2 = path_def.RSRC_APP_CPU1_FILE, path_def.RSRC_APP_CPU2_FILE
        else:
            flash_cpu1, flash_cpu2 = path_def.RSRC_APP_CPU1_NEW_FILE, path_def.RSRC_APP_CPU2_NEW_FILE

        job = FirmwareWriteJob(adapter_type=adapter_type, port_name=port_name,
                               kernel_cpu1=path_def.RSRC_KERNEL_CPU1_FILE,
                               kernel_cpu2=path_def.RSRC_KERNEL_CPU2_FILE,
                               flash_cpu1=flash_cpu1, flash_cpu2=flash_cpu2,
                               network_version=network_version)

        # 로컬 파일 사전 검사 — Network 모드의 앱 파일은 다운로드가 만들므로 커널만 본다
        required = {"CPU1 Kernel": job.kernel_cpu1, "CPU2 Kernel": job.kernel_cpu2}
        if not is_network:
            required["CPU1 Firmware"] = job.flash_cpu1
            required["CPU2 Firmware"] = job.flash_cpu2

        missing = [name for name, file_path in required.items() if not os.path.isfile(file_path)]
        if missing:
            msg = "Firmware file(s) not found in 2_resource/temp:\n - " + "\n - ".join(missing)
            self._log.error(f"[Cancelled] {msg}")
            QMessageBox.warning(self, "Warning", msg)
            self._cancel_selection()
            return

        # 재연결용 설정 스냅샷은 닫기 전에 — close() 가 ServicePort 의 설정을 지운다.
        # 업데이트 전 미연결이면 None (완료 후 재부팅 대기 없이 끝낸다)
        svc = self.svc_port
        if svc.connect_info:
            self._saved_port_setting = (svc.port_name, svc.baudrate, svc.data_bits,
                                        svc.parity, svc.stop_bits, svc.termination)
        else:
            self._saved_port_setting = None

        # 워커가 같은 COM 포트를 직접 열므로 ServicePort 는 여기서 닫는다 —
        # 끊김 시그널은 ParamWin 의 공통 처리(상태바/param_worker 중지)가 받는다
        svc.close()

        if adapter_type == AdapterType.RS232:
            show_rs232_boot_mode_guide(self)

        self._job = job
        self._steps = self._build_steps(job, has_reconnect=self._saved_port_setting is not None)
        self._step_index = 0
        self.row_progress.reset()

        self._set_stage(_Stage.WRITING)
        if not self.fw_worker.start_write(job):
            self._log.error("[Cancelled] firmware worker is busy")
            self._set_stage(_Stage.IDLE)

    def _cancel_selection(self):
        self._log.info("[Cancelled] firmware update selection cancelled by user")
        self._set_stage(_Stage.IDLE)

    # ------------------------------------------------------------ 쓰기 진행/완료
    def handle_write_phase_changed(self, phase: FirmwarePhase):
        if phase in self._steps:
            self._step_index = self._steps.index(phase)
            self._update_progress(0.0)

    def handle_write_progress_changed(self, phase: FirmwarePhase, done: int, total: int):
        # 현재 단계의 진행률만 반영한다 (늦게 도착한 이전 단계 시그널 무시)
        if total > 0 and self._steps and self._steps[self._step_index] == phase:
            self._update_progress(done / total)

    def handle_write_finished(self, ok: bool, msg: str):
        if self._stage != _Stage.WRITING:
            return

        if not ok:
            # 진행바는 실패 지점에 멈춘 채 둔다 — 세부 사유는 메시지와 LogView 로
            self._set_stage(_Stage.IDLE)
            QMessageBox.critical(self, "Firmware Update Failed", msg)
            return

        if self._job is not None and self._job.adapter_type == AdapterType.RS232:
            show_rs232_reboot_guide(self)

        if self._saved_port_setting is None:
            self.row_progress.set_checked(True)
            self._set_stage(_Stage.IDLE)
            QMessageBox.information(self, "Firmware Update",
                                    "Firmware update is completed.\n\n"
                                    "The service port was not connected before the update — "
                                    "reconnect the device via Connection > Connect.")
            return

        # 마지막 구간 = 재연결 대기. 장비 재부팅 -> SN 응답 확인 -> ServicePort 재연결
        # -> refresh 는 param_worker 몫. 대기 박스는 handle_started_reboot,
        # 완료 후 절차는 handle_finished_refresh
        if _STEP_RECONNECT in self._steps:
            self._step_index = self._steps.index(_STEP_RECONNECT)
            self._update_progress(0.0)

        self._set_stage(_Stage.WAIT_REBOOT)
        if not self.param_worker.start_reboot_wait(self._saved_port_setting):
            self._log.error("[Reboot Wait] could not start (worker busy)")
            self._set_stage(_Stage.IDLE)
            QMessageBox.warning(self, "Warning",
                                "Firmware update is completed, but the reconnection wait could not start.\n"
                                "Reconnect the device via Connection > Connect.")

    # ------------------------------------------------------------ 재부팅 대기 / 재연결
    def handle_started_reboot(self):
        # 믹스인의 박스(App 종료만 가능) 대신 Cancel 이 있는 박스 — 모듈 주석 참고
        if self._reboot_wait_box is not None:
            return

        self._reboot_wait_box = show_busy_wait_message_box(
            self, "Reboot",
            "The device is rebooting.\nWaiting for reconnection...",
            quit_text="Cancel")
        self._reboot_wait_box.quit_button.clicked.connect(self.on_clicked_cancel_reboot_wait)

    def handle_finished_reboot(self, is_success: bool):
        super().handle_finished_reboot(is_success)  # 대기 박스 닫기

        if is_success or self._stage not in (_Stage.WAIT_REBOOT, _Stage.RESTORING):
            return

        # 취소됨 — 포트는 닫힌 채(단선과 동일). 나머지 절차는 사용자가 수동으로
        self._log.warning("[Reboot Wait] cancelled by user — reconnect manually")
        self._set_stage(_Stage.IDLE)
        QMessageBox.information(self, "Reboot Wait Cancelled",
                                "Reconnection wait was cancelled.\n"
                                "Reconnect the device via Connection > Connect after it has rebooted.")

    def handle_finished_refresh(self):
        # 재연결 refresh 완료 = 새 펌웨어로 부팅한 장비와 통신 확인
        if self._stage == _Stage.WAIT_REBOOT:
            self.row_progress.set_checked(True)
            self._log.info("[Reconnected] device is back after firmware update")

            has_backup = self._backup_file_path is not None
            if self.restore_factory_param is not None and ask_restore_factory_params(self, has_backup):
                param = self.restore_factory_param
                result = self.param_worker.write([(param, param.btn_str_value)])
                if result == StartResult.OK:
                    # reconnect param 이므로 워커가 쓰기 후 재부팅 대기로 들어간다
                    self._log.info("[Restore] factory parameters restore requested")
                    self._set_stage(_Stage.RESTORING)
                    return
                show_param_write_warning(self, result)

            # 공장 초기화를 건너뛰어도(또는 쓰기 시작 실패) 백업 파일이 있으면 복원 창은 연다
            self._set_stage(_Stage.IDLE)
            if has_backup:
                QMessageBox.information(self, "Firmware Update",
                                        "Firmware update is completed.\n\n"
                                        "The Restore window will open with the backup file saved before the update.")
                self._open_restore_win()
            else:
                QMessageBox.information(self, "Firmware Update", "Firmware update is completed.")

        elif self._stage == _Stage.RESTORING:
            # 공장 초기화 재부팅 후 재연결 확인 — 이어서 백업 복원 창을 연다
            self._log.info("[Restore] factory parameters restored — device reconnected")
            self._set_stage(_Stage.IDLE)
            QMessageBox.information(self, "Firmware Update",
                                    "Firmware update and factory parameter restore are completed.\n\n"
                                    "The Restore window will open to restore the parameter backup.")
            self._open_restore_win()

    def _open_restore_win(self):
        # 부모는 MainWin — 이 창을 닫아도 복원 창은 남아야 한다.
        # win_id 를 일반 Restore 창과 분리해 기존 창이 재사용(파일 미로드)되는 것을 막는다
        WinManager().show_window(win_class=RestoreWin, win_name="Firmware Restore",
                                 win_id="ParamWin_FirmwareRestore", parent=self.parent(),
                                 is_modal=False, is_fu_restore=True,
                                 initial_file_path=self._backup_file_path)

    # ------------------------------------------------------------ 종료
    def closeEvent(self, event: QCloseEvent):
        if self.fw_worker.is_running:
            if not ask_abort_update(self):
                event.ignore()
                return
            self.fw_worker.abort()

        # 실행 중 QThread 파괴 = 앱 abort — 중단 완료까지 기다린 뒤 닫는다
        self.fw_worker.cleanup()
        self._close_wait_box()
        super().closeEvent(event)  # param_worker.cleanup()
