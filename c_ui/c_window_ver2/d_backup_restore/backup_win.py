from datetime import datetime

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import QFileDialog, QMessageBox, QTreeWidgetItem

from b_core.b_datatype.general_enum import ParamAccType
from b_core.b_datatype.parameter import Parameter
from b_core.b_datatype.param_enum import SysUserInterfaceEnum
from b_core.c_manager.app_log_manager import AppLogManager
from b_core.e_worker_ver2.parameter_run_worker import SequenceEnd, SequenceReport, StartResult
from b_core.f_helper import backup_file_helper, firmware_util
from b_core.g_protocol.packet_spec import Verdict
from b_core.g_protocol.spec_registry import SpecRegistry
from c_ui.b_control_ver2.b_base.trees import BaseTreeWidget
from c_ui.c_window_ver2.service_win import ServiceWin
from c_ui.c_window_ver2.x_message.backup_restore_message_box import ask_save_partial_backup
from c_ui.c_window_ver2.x_message.firmware_update_message_box import (NoBackupChoice,
                                                                       ask_close_without_backup)
from c_ui.c_window_ver2.x_message.param_result_message_box import show_param_write_warning

# 사용자 인터페이스 값에 따라 트리에 포함할 Interface 폴더 판정용
_DEVICENET_IFACE_VALUES = {SysUserInterfaceEnum.DEVICENET.value,
                           SysUserInterfaceEnum.DEVICENET_LEGACY_MKS.value,
                           SysUserInterfaceEnum.DEVICENET_APSYSTEM.value,
                           SysUserInterfaceEnum.DEVICENET_NORCAL.value}
_RS232_IFACE_VALUES = {SysUserInterfaceEnum.RS232.value,
                       SysUserInterfaceEnum.RS232_ANALOG_OUTPUT.value,
                       SysUserInterfaceEnum.RS485_ANALOG_OUTPUT.value}
_ETHERCAT_IFACE_VALUES = {SysUserInterfaceEnum.ETHERCAT.value}


class BackupWin(ServiceWin):
    """파라미터 백업 창 — 본문은 백업 대상 체크박스 트리, 툴바는 Backup / Abort (Refresh 없음).

    백업 = 워커의 CAPTURE 시퀀스(param_worker.capture): 체크된 param 을 읽기 spec 으로 읽고, 잡음은 RETRY_MAX 까지 재시도,
    끝나면 sig_sequence_report 로 작업별 결과가 온다 (data-protocol-2, 2026-10-12). 시퀀스 중에는 워커 is_working 으로 트리와
    Backup 이 잠기고 Abort 만 살아 있다. 성공한 param 의 str_value(선로 원문)로 파일 행을 만들며, 누락(재시도 소진·거부·미지원·
    spec 없음)이 있으면 목록을 보이고 그것 없이 저장할지 묻는다 (F085/F086/F087). 끊김·Abort 로 중단되면 로그만 남기고 파일은
    만들지 않는다.

    is_fu_backup=True (펌웨어 업데이트 전 백업 모드):
    - 기본 체크 대상이 fu_backup param 으로 바뀐다
    - 파일 저장이 끝나면 창을 스스로 닫는다 (다음 단계인 펌웨어 업데이트로 바로 이어진다)
    - 파일을 저장하지 않고 닫으면 [백업 없이 진행 / 창 유지 / 업데이트 취소] 를 묻는다
    - 닫힐 때 sig_fu_backup_closed(진행 여부, 저장 파일 경로) 를 낸다 — MainWin 이
      받아 펌웨어 업데이트 창을 띄운다 (경로가 "" 이면 백업 없음)
    """

    sig_fu_backup_closed = Signal(bool, str)  # FU 모드 전용: (continue_update, saved_file_path)

    RETRY_MAX = 3  # 항목당 잡음 재시도 횟수 (복원과 같음, 2026-10-12 결정)

    def __init__(self, parent=None, win_name = None, is_fu_backup = False):
        super().__init__(parent, win_name, has_refresh=False)
        self.is_fu_backup = is_fu_backup
        self._fu_saved_file = None  # FU 모드에서 저장된 백업 파일 경로
        self._backup_params: list[Parameter] = []  # 이번 백업의 대상 스냅샷 (파일 순서 = 스키마 순서, 누락 계산용)

        # 진행 로그는 이 창의 LogView(상태바 Log View 버튼)로 확인한다 —
        # param_worker 와 같은 source(win_name)를 쓰므로 한 뷰에 모인다
        self._log = AppLogManager().get_logger(self.win_name)

        self.toolbar.add_action("Backup", self.on_clicked_backup)
        self.toolbar.add_action("Abort", self.on_clicked_abort)
        self.toolbar.set_action_enabled("Abort", False)   # 백업 시퀀스가 도는 동안만 활성
        self.param_worker.sig_sequence_report.connect(self.handle_sequence_report)

        # 트리 구성 필터에 쓰이는 User Interface / Firmware Version 값을 refresh 로 읽어온다
        # (이 창에는 param 위젯이 없으므로 직접 등록)
        self.user_iface_param = self.param_manager.get_by_full_path("System.Identification.Configuration.User Interface")
        self.param_worker.add_read_param_ptr(self.user_iface_param)

        self.firmware_version_param = self.param_manager.get_by_full_path("System.Identification.Firmware.Firmware Version")
        self.param_worker.add_read_param_ptr(self.firmware_version_param)

        # 바디: 백업 가능 param(RW + nor_backup) 체크박스 트리 —
        # 기본 체크 상태로 시작하고 사용자가 자유롭게 추가/해제할 수 있다.
        # 실제 백업은 체크된 항목만 수행
        self._updating_checks = False  # 코드에 의한 일괄 체크 변경 중 itemChanged 재진입 가드
        self.tree = BaseTreeWidget(self)
        self._build_param_tree()
        self._apply_default_checks()
        self.tree.itemChanged.connect(self.handle_changed_tree_item)

        # 트리는 User Interface / Firmware Version 값 기준으로 구성되므로 값이
        # (최초 확인 포함) 바뀌면 재구성한다 — 값은 refresh/모니터링이 읽어온다
        if self.user_iface_param is not None:
            self.user_iface_param.sig_value_changed.connect(self.handle_changed_user_iface)
        if self.firmware_version_param is not None:
            self.firmware_version_param.sig_value_changed.connect(self.handle_changed_firmware_version)

        self.set_body(self.tree)  # 잠금 대상 = 트리 (워커 동작 중 — 백업 시퀀스 포함)

    def locked_actions(self):
        return ("Backup",)

    # ------------------------------------------------------------ 체크박스 트리
    def _is_iface_included(self, path: str) -> bool:
        """Interface 계열 폴더 포함 판정 — 공용 Scaling 은 항상, 그 외는 현재
        User Interface 값에 해당하는 폴더만 포함한다 (값 미확인 시 Scaling 만).
        기준은 MainToolBar.set_iface 와 같다 (DeviceNet 4종 / RS232·RS485 3종 / EtherCAT)."""
        if not path.startswith("Interface"):
            return True

        if path.startswith("Interface.Scaling"):
            return True

        user_iface_value = self.user_iface_param.value if self.user_iface_param is not None else None

        if user_iface_value in _DEVICENET_IFACE_VALUES and path.startswith("Interface DeviceNet"):
            return True
        if user_iface_value in _RS232_IFACE_VALUES and path.startswith("Interface RS232/RS485"):
            return True
        if user_iface_value in _ETHERCAT_IFACE_VALUES and path.startswith("Interface EtherCAT"):
            return True

        return False

    def _is_baud_rate_included(self, param: Parameter) -> bool:
        """Cluster Baud Rate V1/V2 포함 판정 — 펌웨어 버전으로 하나만 포함한다.

        MainWin.on_clicked_cluster_setting() 과 동일 기준: 6.2.3(0x623) 미만은
        V1, 이상은 V2. 버전 미확인 시 양쪽 다 제외 (iface 필터의 '미확인 시
        Scaling 만' 과 같은 컨셉 — 값이 확인되면 트리가 재구성된다)."""
        if param.path != "Cluster.Settings" or param.name not in ("Baud Rate V1", "Baud Rate V2"):
            return True

        firmware_value = self.firmware_version_param.value if self.firmware_version_param is not None else None
        firmware_code = firmware_util.to_version_code(firmware_value)
        if firmware_code is None:
            return False

        if firmware_code < 0x623:
            return param.name == "Baud Rate V1"
        return param.name == "Baud Rate V2"

    def _is_cluster_setting_included(self, param: Parameter) -> bool:
        """Cluster Number of Valves / Cluster Address 포함 판정.

        MainWin.on_clicked_cluster_setting() 과 동일 기준: User Interface 가
        CLUSTER_SLAVE 면 Cluster Address 만, 그 외에는 Number of Valves 만.
        값 미확인 시 양쪽 다 제외 (값이 확인되면 트리가 재구성된다)."""
        if param.path != "Cluster.Settings" or param.name not in ("Number of Valves", "Cluster Address"):
            return True

        user_iface_value = self.user_iface_param.value if self.user_iface_param is not None else None
        if user_iface_value is None:
            return False

        if user_iface_value == SysUserInterfaceEnum.CLUSTER_SLAVE.value:
            return param.name == "Cluster Address"
        return param.name == "Number of Valves"

    def _rebuild_param_tree(self):
        # 필터 기준 값 변경 시 트리 재구성 — 구조가 바뀌므로 체크 편집은
        # 기본 상태로 초기화된다
        self.tree.clear()
        self._build_param_tree()
        self._apply_default_checks()

    def handle_changed_user_iface(self):
        self._rebuild_param_tree()

    def handle_changed_firmware_version(self):
        self._rebuild_param_tree()

    def _build_param_tree(self):
        self._item_by_param: dict[Parameter, QTreeWidgetItem] = {}
        folder_items: dict[str, QTreeWidgetItem] = {}

        def get_folder_item(folder_path: str) -> QTreeWidgetItem:
            item = folder_items.get(folder_path)
            if item is not None:
                return item

            head, sep, name = folder_path.rpartition(".")

            item = QTreeWidgetItem([name if sep else folder_path])
            # [주의] 폴더-하위 체크 연동에 ItemIsAutoTristate 를 쓰지 않는다 —
            # 항목 수천 개에서 자식별 전파가 부모 재계산을 반복해 느리고, 변경된
            # 자식들의 리페인트가 마우스 이동/스크롤 전까지 지연된다 (실측).
            # 전파는 handle_changed_tree_item 이 수동으로 수행한다
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(0, Qt.CheckState.Unchecked)

            if sep:
                get_folder_item(head).addChild(item)
            else:
                self.tree.addTopLevelItem(item)

            folder_items[folder_path] = item
            return item

        # 스키마(json) 등장 순서 그대로 구성 — 백업 순서의 기준이 된다.
        # 트리 요소 = RW + nor_backup (RO 는 복원(쓰기) 불가, WO 는 읽기 불가)
        # + 현재 User Interface 에 해당하는 Interface 폴더만.
        # 폴더 노드는 필요 시에만 생성되므로 대상 없는 폴더는 트리에 안 생긴다
        for param in self.param_manager.get_param_list():
            if param.acc != ParamAccType.RW or not param.is_nor_backup:
                continue

            if not self._is_iface_included(param.path):
                continue

            if not self._is_baud_rate_included(param):
                continue

            if not self._is_cluster_setting_included(param):
                continue

            item = QTreeWidgetItem([param.name])
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(0, Qt.CheckState.Unchecked)
            get_folder_item(param.path).addChild(item)
            self._item_by_param[param] = item

    def _apply_default_checks(self):
        # 일반 백업: 트리 요소 전체 체크 / FU 백업: is_fu_backup param 만 체크
        self._updating_checks = True
        try:
            for param, item in self._item_by_param.items():
                is_checked = param.is_fu_backup if self.is_fu_backup else True
                item.setCheckState(0, Qt.CheckState.Checked if is_checked else Qt.CheckState.Unchecked)

            self.tree.recompute_all_folder_check_states()
        finally:
            self._updating_checks = False

        self.tree.viewport().update()

    # ------------------------------------------------------------ 체크 전파 (수동)
    def handle_changed_tree_item(self, item: QTreeWidgetItem, column: int):
        # 사용자 클릭에 의한 체크 변경만 처리한다 (코드 일괄 변경은 가드로 차단)
        if self._updating_checks:
            return

        self._updating_checks = True
        try:
            if item.childCount() > 0:
                self.tree.set_subtree_check_state(item, item.checkState(0))
            self.tree.update_ancestor_check_states(item.parent())
        finally:
            self._updating_checks = False

        self.tree.viewport().update()

    def _get_checked_params(self) -> list[Parameter]:
        # _item_by_param 은 param 목록(스키마) 순서를 유지한다
        return [param for param, item in self._item_by_param.items()
                if item.checkState(0) == Qt.CheckState.Checked]

    # ------------------------------------------------------------ 백업 실행 (워커 CAPTURE 시퀀스)
    def on_clicked_backup(self):
        params = self._get_checked_params()
        if not params:
            QMessageBox.information(self, "Information", "There are no parameters checked for backup.")
            return

        result = self.param_worker.capture(params, max_retry=self.RETRY_MAX)
        if result != StartResult.OK:
            show_param_write_warning(self, result)   # NOT_CONNECTED / BUSY — 진행률·잠금은 워커 시그널이 맡는다
            return

        self._backup_params = params
        self.toolbar.set_action_enabled("Abort", True)
        self._log.info(f"[Backup Start !!!]: {len(params)} items")

    def on_clicked_abort(self):
        self.param_worker.abort_sequence()   # 결과는 handle_sequence_report(end=ABORTED) 로

    def handle_sequence_report(self, report: SequenceReport):
        self.toolbar.set_action_enabled("Abort", False)

        # 성공한 param 의 선로 원문은 보고서가 읽은 자리에서 떠 둔 사본(lines)으로 — 값은 보통 읽기처럼 param 에도 반영됐다.
        # 실패는 사유와 함께 로그에
        captured: dict[Parameter, str] = {}
        for result in report.results:
            names = ", ".join(f"{p.path}.{p.name}" for p in result.params)
            if result.outcome.verdict is Verdict.OK:
                captured.update(result.lines)
                self._log.info(f"[Success]: Parameter = {names}")
            else:
                self._log.error(f"[Read Failed]: Parameter = {names}, {result.outcome.reason.name}")

        if report.end is not SequenceEnd.COMPLETED:
            # 사용자 취소 / 끊김 — 파일은 만들지 않는다 (끊김은 상태바가 보인다, 2026-10-12 결정)
            self._log.error(f"[Backup Aborted]: {report.end.name.lower()} ({len(report.results)}/{report.total} reads done)")
            return

        # 누락 = 체크했는데 성공하지 못한 것 (재시도 소진·거부·미지원·spec 없음) — 스키마 순서 유지
        missing = [p for p in self._backup_params if p not in captured]
        self._log.info("[Backup Completed]" + (f": {len(missing)} missing" if missing else " Successfully !!!"))

        if missing and not ask_save_partial_backup(self, [f"{p.path}.{p.name}" for p in missing]):
            self._log.info("[Save Cancelled]: partial backup not saved")
            return

        # 파일 행은 쓰기 패킷 그대로 — 읽은 선로 원문을 codec 없이 build_request_line 으로 (복원 독립성, 결정 10). 순서는 스키마 순서
        registry = SpecRegistry()
        contents = [f"{p.path}.{p.name}, {registry.get_write_spec(p).build_request_line(captured[p])}"
                    for p in self._backup_params if p in captured]
        self.save_backup_to_file(contents)

    def save_backup_to_file(self, contents: list[str]):
        # FU 모드는 파일명을 제안한다 — 업데이트 후 복원 창이 이 파일을 자동 로드하므로
        # 어떤 장비의 어느 시점 백업인지 이름만으로 알 수 있게 한다
        default_name = ""
        if self.is_fu_backup:
            sn = self.sn_param.value if self.sn_param is not None and self.sn_param.value is not None else "unknown"
            default_name = f"fu_backup_{sn}_{datetime.now():%Y%m%d_%H%M%S}.txt"

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Backup File",
            default_name,
            "Text Files (*.txt);;All Files (*)")

        if not file_path:
            self._log.info("[Save Cancelled]: File save cancelled by user.")
            return

        try:
            # 헤더에 저장 시점 장비 정보를 기록한다 — 복원(RestoreWin)이 현재
            # 장비와 비교해 다른 장비/인터페이스 파일 복원을 경고하는 근거
            firmware_value = self.firmware_version_param.value if self.firmware_version_param is not None else None
            user_iface_value = self.user_iface_param.value if self.user_iface_param is not None else None
            header = backup_file_helper.build_header(firmware_value, user_iface_value)

            file_data = "\n".join([header] + contents)

            with open(file_path, "w", encoding="utf-8") as f:
                f.write(file_data)
        except OSError as e:
            self._log.error(f"[Error]: Failed to save file. {e}")
            QMessageBox.critical(self, "Error", f"An error occurred while saving the file:\n{e}")
            return

        self._log.info(f"[File Saved]: Successfully saved to {file_path}")

        if self.is_fu_backup:
            # 저장 완료 = FU 백업 단계 끝. 창을 닫으면 closeEvent 가 경로와 함께 알린다
            self._fu_saved_file = file_path
            QMessageBox.information(self, "Success",
                                    "Backup file saved successfully.\n"
                                    "The Firmware Update window will open next.")
            self.close()
            return

        QMessageBox.information(self, "Success", "Backup file saved successfully.")

    def closeEvent(self, event: QCloseEvent):
        if self.is_fu_backup:
            if self._fu_saved_file is None:
                choice = ask_close_without_backup(self)
                if choice == NoBackupChoice.STAY:
                    event.ignore()
                    return
                continue_update = choice == NoBackupChoice.CONTINUE
                self._log.info("[FU Backup]: closed without backup file — "
                               + ("continue to firmware update" if continue_update else "firmware update cancelled"))
            else:
                continue_update = True

            self.sig_fu_backup_closed.emit(continue_update, self._fu_saved_file or "")

        super().closeEvent(event)  # param_worker.cleanup()
