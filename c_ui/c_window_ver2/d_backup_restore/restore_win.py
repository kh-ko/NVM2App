from dataclasses import dataclass

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QFileDialog, QMessageBox, QTreeWidgetItem

from b_core.b_datatype import param_enum as p_enum
from b_core.b_datatype.general_enum import SvcPortErrType
from b_core.c_manager.app_log_manager import AppLogManager
from b_core.f_helper import backup_file_helper
from b_core.g_protocol.spec_registry import SpecRegistry
from c_ui.b_control_ver2.b_base.trees import BaseTreeWidget
from c_ui.b_control_ver2.d_param.param_win import ParamWin


@dataclass
class RestoreItem:
    """백업 파일 한 행 = 복원 작업 하나."""
    name: str                                # 파일에 기재된 '<path>.<name>' (표시/로그용)
    packet: str                              # 그대로 전송할 쓰기 패킷
    tree_item: QTreeWidgetItem | None = None # 체크박스 트리의 대응 아이템


class RestoreWin(ParamWin):
    """백업 파일(backup_win.py 가 저장한 형식)을 장비로 복원하는 창.

    파일의 각 행 뒷부분이 그대로 전송 가능한 쓰기 패킷이므로, 체크된 항목을
    파일 순서대로 raw_write_request 로 재생한다. 행 내용은 스키마와 대조하지
    않는다 — 장비가 거부하는 항목은 쓰기 실패로 로그에 남는다.
    - 복원 시작 시 Access Mode 를 Local 로 전환한다 (raw 쓰기는 기존 Apply
      의 Local 전환 정책을 우회하므로 여기서 직접 수행. REMOTE 복원은 기존
      쓰기 정책과 동일하게 하지 않는다)
    - 항목 실패는 RETRY_MAX 회 재시도 후 로그에 남기고 계속 진행, 완료 시
      실패 목록을 요약 표시한다
    - 검증은 쓰기 응답 접두어 확인만 (backup_file_helper.expected_write_response_prefix)
      — read-back 은 하지 않는다

    is_fu_restore=True (펌웨어 업데이트 후 복원 모드):
    - initial_file_path 가 있으면 창이 뜬 직후 그 파일을 자동 로드한다
    - 헤더의 장비 정보 비교(펌웨어 버전 불일치 경고)를 건너뛴다 — 업데이트로
      버전이 달라진 것이 정상이므로 (로그에만 남긴다)
    """

    # handle_changed_connection_info 오버라이드가 super().__init__() 중에도
    # 호출되므로 (미연결 상태로 창을 열 때) 클래스 기본값으로 존재해야 한다
    _is_restore_running = False

    RETRY_MAX = 3  # 항목당 실패 재시도 횟수

    def __init__(self, parent=None, win_name = None, is_fu_restore = False, initial_file_path = None):
        super().__init__(parent=parent, win_name = win_name, paths = [], filter_param_paths = [], is_editblock_win=False, label_width=210, folder_max_width=None)
        self.is_fu_restore = is_fu_restore
        self._initial_file_path = initial_file_path
        self.loaded_items: list[RestoreItem] = []   # 파일 순서
        self.restore_jobs: list[RestoreItem] = []   # 실행 스냅샷 (Local 전환 포함)
        self.failed_items: list[str] = []
        self._job_index = 0
        self._retry_count = 0

        # 진행 로그는 이 창의 LogView(상태바 Log View 버튼)로 확인한다
        self._log = AppLogManager().get_logger(self.win_name)

        self.toolbar.remove_action("Refresh")
        # ParamWin 의 Load File(JSON param 파일용, 이 창에선 숨김)을 백업 파일
        # 전용 로드로 교체한다 — 액션 이름 키 충돌 방지를 위해 제거 후 추가
        self.toolbar.remove_action("Load File")
        self.toolbar.add_action("Load File", self.on_clicked_load_backup_file)
        self.toolbar.add_action("Restore", self.on_clicked_restore)

        self.param_worker.sig_raw_write_result.connect(self.handle_raw_write_result)

        # 바디: 로드된 백업 파일 내용 체크박스 트리 — 기본 전체 체크,
        # 사용자가 복원 대상을 추가/해제할 수 있다
        self._updating_checks = False  # 코드에 의한 일괄 체크 변경 중 itemChanged 재진입 가드
        self.tree = BaseTreeWidget(self)
        self.tree.itemChanged.connect(self.handle_changed_tree_item)

        # ParamWin 의 폴더 카드 스크롤 영역은 이 창에서 쓰지 않으므로 트리로 교체.
        # content_widget 재지정으로 handle_changed_working 의 잠금 대상도 트리가 된다
        old_central = self.takeCentralWidget()
        old_central.deleteLater()
        self.setCentralWidget(self.tree)
        self.content_widget = self.tree

        # 자동 로드는 창이 표시된 뒤에 — 로드 결과 메시지 박스가 창 위에 뜨게 한다
        if self._initial_file_path:
            QTimer.singleShot(0, self.load_initial_file)

    def additional_param_settings(self):
        # 헤더(파일 저장 시점 장비 정보)와 비교할 현재 값들을 refresh 로 읽어온다
        # (이 창에는 param 위젯이 없으므로 직접 등록)
        self.user_iface_param = self.param_manager.get_by_full_path("System.Identification.Configuration.User Interface")
        self.param_worker.add_read_param_ptr(self.user_iface_param)

        self.firmware_version_param = self.param_manager.get_by_full_path("System.Identification.Firmware.Firmware Version")
        self.param_worker.add_read_param_ptr(self.firmware_version_param)

        # Local 전환 쓰기 패킷용 (읽기 등록은 하지 않는다)
        self.acc_mode_param = self.param_manager.get_by_full_path("System.Access Mode")

    # ------------------------------------------------------------ 파일 로드
    def on_clicked_load_backup_file(self):
        if self._is_restore_running:
            return

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
        if self._is_restore_running:
            return

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

    # ------------------------------------------------------------ 복원 실행
    def on_clicked_restore(self):
        if self._is_restore_running:
            return

        if not self.svc_port.connect_info:
            QMessageBox.warning(self, "Connection Error",
                                "Communication is not connected. Please check the connection status.")
            return

        if not self.loaded_items:
            QMessageBox.information(self, "Information", "Load a backup file first.")
            return

        targets = self._get_checked_items()
        if not targets:
            QMessageBox.information(self, "Information", "There are no parameters checked for restore.")
            return

        # Local 전환 쓰기를 맨 앞에 (전환 후 REMOTE 복원하지 않는 것은 기존
        # 쓰기 정책과 동일한 의도된 동작)
        jobs: list[RestoreItem] = []
        acc = self.acc_mode_param
        acc_write_spec = SpecRegistry().get_write_spec(acc) if acc is not None else None
        if acc_write_spec is not None:
            jobs.append(RestoreItem(f"{acc.path}.{acc.name}",
                                    acc_write_spec.build_request({acc: str(p_enum.AccModeEnum.LOCAL.value)})))

        jobs += targets

        self.restore_jobs = jobs
        self.failed_items = []
        self._job_index = 0
        self._retry_count = 0

        self._is_restore_running = True
        self.toolbar.set_action_enabled("Restore", False)
        self.toolbar.set_action_enabled("Load File", False)
        self.tree.setEnabled(False)  # 진행 중 체크 변경 방지
        self.statusbar.set_progress(0)
        self._log.info(f"[Restore Start !!!]: {len(targets)} items")
        self._send_current_job()

    def _send_current_job(self):
        self.param_worker.raw_write_request(str(self._job_index), self.restore_jobs[self._job_index].packet)

    def handle_changed_connection_info(self, info: str):
        super().handle_changed_connection_info(info)

        # 연결이 끊기면 진행 중 복원을 중단한다 — raw 쓰기는 워커 상태 머신
        # 밖이라 handle_disconnected() 로는 멈추지 않는다.
        # (in-flight 응답은 _is_restore_running 가드로 폐기됨)
        if not info and self._is_restore_running:
            self._log.error("[Restore Aborted]: connection lost")
            self._finish_restore()

    def handle_raw_write_result(self, tag: str, req_msg: str, resp_msg: str, err_type: SvcPortErrType):
        if not self._is_restore_running:
            return

        try:
            job_index = int(tag)
        except ValueError:
            return

        if job_index != self._job_index:
            return  # 중단/재시작 이후 도착한 늦은 응답 폐기

        job = self.restore_jobs[job_index]

        # 성공 판정: 통신 정상 + (판정 규칙이 있는 프로토콜이면) 응답 접두어 확인
        expected = backup_file_helper.expected_write_response_prefix(job.packet)
        if err_type != SvcPortErrType.NONE:
            is_success, err_msg = False, f"err_type = {err_type.name}"
        elif expected is not None and not resp_msg.startswith(expected):
            is_success, err_msg = False, f"packet = {resp_msg}"
        else:
            is_success, err_msg = True, ""

        if not is_success:
            if self._retry_count < self.RETRY_MAX:
                self._retry_count += 1
                self._log.error(f"[Write Error]: Parameter = {job.name}, {err_msg} "
                                f"— retry {self._retry_count}/{self.RETRY_MAX}")
                self._send_current_job()
                return

            # 재시도 소진 — 실패 기록 후 다음 항목으로 진행 (합의된 정책)
            self._log.error(f"[Write Failed]: Parameter = {job.name}, {err_msg}")
            self.failed_items.append(job.name)
        else:
            self._log.info(f"[Success]: Parameter = {job.name}")

        self._retry_count = 0
        self._job_index += 1
        self.statusbar.set_progress(int((self._job_index / len(self.restore_jobs)) * 100))

        if self._job_index < len(self.restore_jobs):
            self._send_current_job()
        else:
            self._log.info("[Restore Completed !!!]")
            self._finish_restore()
            self._show_restore_summary()

    def _finish_restore(self):
        self._is_restore_running = False
        self.toolbar.set_action_enabled("Restore", True)
        self.toolbar.set_action_enabled("Load File", True)
        self.tree.setEnabled(True)
        self.statusbar.set_progress(0)

    def _show_restore_summary(self):
        # 첫 작업(Local 전환)은 복원 항목 수에서 제외하고 집계한다
        item_count = len(self.restore_jobs) - (1 if self.acc_mode_param is not None else 0)

        if not self.failed_items:
            QMessageBox.information(self, "Success",
                                    f"Restore completed successfully. ({item_count} items)")
            return

        shown = "\n- ".join(self.failed_items[:10])
        more = "" if len(self.failed_items) <= 10 else f"\n... and {len(self.failed_items) - 10} more"
        QMessageBox.warning(self, "Warning",
                            f"Restore completed with {len(self.failed_items)} failed items "
                            f"(out of {item_count}):\n- {shown}{more}\n\nSee Log View for details.")
