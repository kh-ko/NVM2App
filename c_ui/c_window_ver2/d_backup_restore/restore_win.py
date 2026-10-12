from dataclasses import dataclass

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QFileDialog, QMessageBox, QTreeWidgetItem

from b_core.b_datatype import param_enum as p_enum
from b_core.c_manager.app_log_manager import AppLogManager
from b_core.e_worker_ver2.parameter_run_worker import SequenceEnd, SequenceReport, StartResult
from b_core.f_helper import backup_file_helper
from b_core.g_protocol.packet_spec import Verdict
from b_core.g_protocol.spec_registry import SpecRegistry
from c_ui.b_control_ver2.b_base.trees import BaseTreeWidget
from c_ui.c_window_ver2.service_win import ServiceWin
from c_ui.c_window_ver2.x_message.param_result_message_box import show_param_write_warning


@dataclass
class RestoreItem:
    """백업 파일 한 행 = 복원 작업 하나."""
    name: str                                # 파일에 기재된 '<path>.<name>' (표시/로그용)
    packet: str                              # 그대로 전송할 쓰기 패킷
    tree_item: QTreeWidgetItem | None = None # 체크박스 트리의 대응 아이템


class RestoreWin(ServiceWin):
    """백업 파일(backup_win.py 가 저장한 형식)을 장비로 복원하는 창 — 본문은 파일 내용 체크박스 트리, 툴바는
    Load File(백업 txt) / Restore / Abort (Refresh 없음).

    복원 = 워커의 RAW 시퀀스(param_worker.raw_write): 체크된 항목의 패킷을 파일 순서대로 보내고, 끝나면 sig_sequence_report
    로 항목별 결과가 온다 (data-protocol-2, 2026-10-12). 시퀀스 중에는 워커 is_working 으로 트리·Restore·Load File 이 잠기고
    Abort 만 살아 있다.

    파일의 각 행 뒷부분이 그대로 전송 가능한 쓰기 패킷이다. 행 내용은 스키마와 대조하지 않는다.
    - 복원 시작 시 Access Mode 를 Local 로 전환한다 (raw 쓰기는 기존 Apply 의 Local 전환 정책을 우회하므로 여기서 직접 수행.
      REMOTE 복원은 기존 쓰기 정책과 동일하게 하지 않는다). 전환 실패는 항목 집계와 따로 요약에 표시한다 (F090).
    - 판정은 raw_packet_spec 의 spec — 장비 거부(오류 코드)는 재시도 없이 실패, 잡음(접두 불일치·빈 응답)은 RETRY_MAX 까지
      재시도 뒤 실패. 실패해도 다음 항목으로 진행하고 끝에 실패 목록을 요약 표시한다. read-back 은 하지 않는다.
    - Abort·끊김으로 중단되면 장비는 부분 복원 상태이므로 요약에 "k/n 항목까지 쓰고 중단" 을 표시한다 (2026-10-12 결정).
    - 완료·Abort 뒤에는 param_worker.reconnect() 로 열린 창 전부가 다시 읽는다 (N077).

    is_fu_restore=True (펌웨어 업데이트 후 복원 모드):
    - initial_file_path 가 있으면 창이 뜬 직후 그 파일을 자동 로드한다
    - 헤더의 장비 정보 비교(펌웨어 버전 불일치 경고)를 건너뛴다 — 업데이트로
      버전이 달라진 것이 정상이므로 (로그에만 남긴다)
    """

    RETRY_MAX = 3        # 항목당 잡음 재시도 횟수
    LOCAL_TAG = "local"  # Local 전환 패킷의 꼬리표 — 항목 꼬리표(파일 순서 번호)와 구분

    def __init__(self, parent=None, win_name = None, is_fu_restore = False, initial_file_path = None):
        super().__init__(parent, win_name, has_refresh=False)
        self.is_fu_restore = is_fu_restore
        self._initial_file_path = initial_file_path
        self.loaded_items: list[RestoreItem] = []     # 파일 순서
        self._restore_items: list[RestoreItem] = []   # 이번 복원의 대상 스냅샷 (꼬리표 = 이 목록의 번호)

        # 진행 로그는 이 창의 LogView(상태바 Log View 버튼)로 확인한다
        self._log = AppLogManager().get_logger(self.win_name)

        # Load File 은 백업 파일(txt) 전용 — ParamWin 의 JSON param 파일 Load File 과는 이름만 같다
        self.toolbar.add_action("Load File", self.on_clicked_load_backup_file)
        self.toolbar.add_action("Restore", self.on_clicked_restore)
        self.toolbar.add_action("Abort", self.on_clicked_abort)
        self.toolbar.set_action_enabled("Abort", False)   # 복원 시퀀스가 도는 동안만 활성

        self.param_worker.sig_sequence_report.connect(self.handle_sequence_report)

        # 헤더(파일 저장 시점 장비 정보)와 비교할 현재 값들을 refresh 로 읽어온다
        # (이 창에는 param 위젯이 없으므로 직접 등록)
        self.user_iface_param = self.param_manager.get_by_full_path("System.Identification.Configuration.User Interface")
        self.param_worker.add_read_param_ptr(self.user_iface_param)

        self.firmware_version_param = self.param_manager.get_by_full_path("System.Identification.Firmware.Firmware Version")
        self.param_worker.add_read_param_ptr(self.firmware_version_param)

        # Local 전환 쓰기 패킷용 (읽기 등록은 하지 않는다)
        self.acc_mode_param = self.param_manager.get_by_full_path("System.Access Mode")

        # 바디: 로드된 백업 파일 내용 체크박스 트리 — 기본 전체 체크,
        # 사용자가 복원 대상을 추가/해제할 수 있다
        self._updating_checks = False  # 코드에 의한 일괄 체크 변경 중 itemChanged 재진입 가드
        self.tree = BaseTreeWidget(self)
        self.tree.itemChanged.connect(self.handle_changed_tree_item)
        self.set_body(self.tree)  # 잠금 대상 = 트리 (워커 동작 중 — 복원 시퀀스 포함)

    def on_start(self):
        # 자동 로드는 창이 표시된 뒤에 — 로드 결과 메시지 박스가 창 위에 뜨게 한다
        if self._initial_file_path:
            QTimer.singleShot(0, self.load_initial_file)

    def locked_actions(self):
        return ("Restore", "Load File")

    # ------------------------------------------------------------ 파일 로드
    def on_clicked_load_backup_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Load Backup File",
            "",
            "Text Files (*.txt);;All Files (*)")

        if not file_path:
            return

        self.load_backup_file(file_path)

    def load_initial_file(self):
        self._log.info(f"[FU Restore]: auto-loading backup file {self._initial_file_path}")
        self.load_backup_file(self._initial_file_path)

    def load_backup_file(self, file_path: str):
        """백업 파일을 읽어 복원 트리를 구성한다 (Load File 버튼과 자동 로드의 공통 경로)."""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                lines = f.read().splitlines()
        except OSError as e:
            self._log.error(f"[Error]: Failed to read file. {e}")
            QMessageBox.critical(self, "Error", f"An error occurred while reading the file:\n{e}")
            return

        # 헤더가 있으면 현재 장비 정보와 비교 — 다르면 진행 여부를 묻는다.
        # 헤더 없는 파일(구버전 형식)도 허용하되, 장비 일치 확인이 불가함을 알린다.
        # FU 복원은 펌웨어 버전이 달라진 것이 정상이므로 비교를 건너뛴다
        header = backup_file_helper.parse_header(lines[0]) if lines else None
        if header is not None:
            if self.is_fu_restore:
                self._log.info(f"[Load]: device check skipped (firmware update flow), file header = {header}")
            elif not self._confirm_header(header):
                return

        if header is None:
            self._log.warning("[Load]: file has no header — device match cannot be verified")

        # 행 내용은 해석하지 않고 그대로 싣는다 — 형식 불량 행만 건너뛴다
        self.loaded_items = []
        skipped_format = 0

        for line in lines:
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue  # 빈 행/헤더(주석) 행

            parsed = backup_file_helper.parse_item_line(stripped)
            if parsed is None:
                self._log.error(f"[Load Skip]: invalid line format = {stripped}")
                skipped_format += 1
                continue

            name, packet = parsed
            self.loaded_items.append(RestoreItem(name, packet))

        self._rebuild_restore_tree()

        summary = f"Loaded {len(self.loaded_items)} items."
        if skipped_format:
            summary += (f"\nSkipped {skipped_format} items (invalid format)."
                        "\nSee Log View for details.")
        if header is None:
            summary += "\n\nNote: this file has no header, so the device match (firmware / interface) was not verified."

        self._log.info(f"[File Loaded]: {file_path} — {summary}")

        if not self.loaded_items:
            QMessageBox.warning(self, "Warning", f"No restorable items in the file.\n{summary}")
            return

        QMessageBox.information(self, "Success", summary)

    def _confirm_header(self, header: dict) -> bool:
        """헤더의 장비 정보와 현재 값 비교. 불일치 시 사용자에게 진행 여부 질문.

        비교는 양쪽 값이 모두 확인된 경우에만 한다 — 파일의 '-'(저장 시점
        미확인)나 현재 값 미확인(미연결 등)은 비교 불가로 보고 통과시킨다."""
        mismatches = []

        file_fw = header.get("fw")
        current_fw = self.firmware_version_param.value if self.firmware_version_param is not None else None
        if file_fw and file_fw != backup_file_helper.UNKNOWN_VALUE and current_fw is not None \
                and file_fw != str(current_fw):
            mismatches.append(f"- Firmware Version: file = {file_fw}, device = {current_fw}")

        file_iface = header.get("iface")
        current_iface = self.user_iface_param.value if self.user_iface_param is not None else None
        if file_iface and file_iface != backup_file_helper.UNKNOWN_VALUE and current_iface is not None \
                and file_iface != str(current_iface):
            file_desc = p_enum.SysUserInterfaceEnum.get_desc(int(file_iface)) if file_iface.isdigit() else file_iface
            current_desc = p_enum.SysUserInterfaceEnum.get_desc(current_iface)
            mismatches.append(f"- User Interface: file = {file_desc}, device = {current_desc}")

        if not mismatches:
            return True

        detail = "\n".join(mismatches)
        reply = QMessageBox.question(
            self, "Device Mismatch",
            "The backup file was saved from a different device configuration:\n"
            f"{detail}\n\nDo you want to continue loading anyway?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No)

        return reply == QMessageBox.StandardButton.Yes

    # ------------------------------------------------------------ 체크박스 트리
    def _rebuild_restore_tree(self):
        self._updating_checks = True
        try:
            self.tree.clear()

            folder_items: dict[str, QTreeWidgetItem] = {}

            def get_folder_item(folder_path: str) -> QTreeWidgetItem:
                item = folder_items.get(folder_path)
                if item is not None:
                    return item

                head, separator, name = folder_path.rpartition(".")

                item = QTreeWidgetItem([name if separator else folder_path])
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                item.setCheckState(0, Qt.CheckState.Unchecked)

                if separator:
                    get_folder_item(head).addChild(item)
                else:
                    self.tree.addTopLevelItem(item)

                folder_items[folder_path] = item
                return item

            # 파일 등장 순서 그대로 구성 — 복원 순서의 기준이 된다.
            # 파일의 '<path>.<name>' 을 마지막 '.' 기준으로 폴더/항목명으로 나눈다.
            # 기본은 전체 체크 (파일에 든 것 = 복원할 것)
            for entry in self.loaded_items:
                folder, separator, name = entry.name.rpartition(".")

                item = QTreeWidgetItem([name if separator else entry.name])
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                item.setCheckState(0, Qt.CheckState.Checked)

                if separator:
                    get_folder_item(folder).addChild(item)
                else:
                    self.tree.addTopLevelItem(item)

                entry.tree_item = item

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

    def _get_checked_items(self) -> list[RestoreItem]:
        # loaded_items 순회로 파일 순서를 유지한다
        return [entry for entry in self.loaded_items
                if entry.tree_item.checkState(0) == Qt.CheckState.Checked]

    # ------------------------------------------------------------ 복원 실행 (워커 RAW 시퀀스)
    def on_clicked_restore(self):
        if not self.loaded_items:
            QMessageBox.information(self, "Information", "Load a backup file first.")
            return

        targets = self._get_checked_items()
        if not targets:
            QMessageBox.information(self, "Information", "There are no parameters checked for restore.")
            return

        # Local 전환 쓰기를 맨 앞에 (전환 후 REMOTE 복원하지 않는 것은 기존
        # 쓰기 정책과 동일한 의도된 동작)
        jobs: list[tuple[str, str]] = []
        acc = self.acc_mode_param
        acc_write_spec = SpecRegistry().get_write_spec(acc) if acc is not None else None
        if acc_write_spec is not None:
            # enum 값의 encode 는 실패하지 않으므로 BuildFailure 검사는 두지 않는다
            jobs.append((self.LOCAL_TAG, acc_write_spec.build_request({acc: str(p_enum.AccModeEnum.LOCAL.value)})))

        jobs += [(str(index), item.packet) for index, item in enumerate(targets)]

        result = self.param_worker.raw_write(jobs, max_retry=self.RETRY_MAX)
        if result != StartResult.OK:
            show_param_write_warning(self, result)   # NOT_CONNECTED / BUSY — 진행률·잠금은 워커 시그널이 맡는다
            return

        self._restore_items = targets
        self.toolbar.set_action_enabled("Abort", True)
        self._log.info(f"[Restore Start !!!]: {len(targets)} items")

    def on_clicked_abort(self):
        self.param_worker.abort_sequence()   # 결과는 handle_sequence_report(end=ABORTED) 로

    def handle_sequence_report(self, report: SequenceReport):
        self.toolbar.set_action_enabled("Abort", False)

        local_failed = False
        failed: list[str] = []
        done = 0
        for result in report.results:
            is_local = result.tag == self.LOCAL_TAG
            name = "System.Access Mode (Local switch)" if is_local else self._restore_items[int(result.tag)].name
            if result.outcome.verdict is Verdict.OK:
                self._log.info(f"[Success]: Parameter = {name}")
            else:
                self._log.error(f"[Write Failed]: Parameter = {name}, {result.outcome.reason.name}")
            if is_local:
                local_failed = result.outcome.verdict is not Verdict.OK
            else:
                done += 1
                if result.outcome.verdict is not Verdict.OK:
                    failed.append(name)

        if report.end is SequenceEnd.COMPLETED:
            self._log.info("[Restore Completed !!!]")
        else:
            self._log.error(f"[Restore Aborted]: {report.end.name.lower()} after {done}/{len(self._restore_items)} items")

        self._show_restore_summary(report.end, done, failed, local_failed)

        # 복원된 값·codec 문맥을 열린 창 전부가 다시 읽는다 — 재접속 경로 (N077). 끊겼으면 포트가 닫혀 있어 False 로 끝난다
        self.param_worker.reconnect()

    def _show_restore_summary(self, end: SequenceEnd, done: int, failed: list[str], local_failed: bool):
        total = len(self._restore_items)
        head = (f"Restore completed ({total} items)." if end is SequenceEnd.COMPLETED
                else f"Restore {end.name.lower()} after {done} of {total} items — the device is partially restored.")
        local_note = "\nThe switch to Local mode failed — see Log View." if local_failed else ""

        if not failed and end is SequenceEnd.COMPLETED and not local_failed:
            QMessageBox.information(self, "Success", head)
            return

        if failed:
            shown = "\n- ".join(failed[:10])
            more = "" if len(failed) <= 10 else f"\n... and {len(failed) - 10} more"
            head += f"\n{len(failed)} failed item(s):\n- {shown}{more}"
        QMessageBox.warning(self, "Warning", f"{head}{local_note}\n\nSee Log View for details.")
