from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFileDialog, QMessageBox, QTreeWidgetItem

from b_core.b_datatype.general_enum import ParamAccType, SvcPortErrType
from b_core.b_datatype.parameter import Parameter
from b_core.b_datatype.param_enum import SysUserInterfaceEnum
from b_core.c_manager.app_log_manager import AppLogManager
from b_core.f_helper import backup_file_helper, firmware_util
from c_ui.b_control_ver2.b_base.trees import BaseTreeWidget
from c_ui.b_control_ver2.d_param.param_win import ParamWin

# 사용자 인터페이스 값에 따라 트리에 포함할 Interface 폴더 판정용
_DEVICENET_IFACE_VALUES = {SysUserInterfaceEnum.DEVICENET.value,
                           SysUserInterfaceEnum.DEVICENET_LEGACY_MKS.value,
                           SysUserInterfaceEnum.DEVICENET_APSYSTEM.value,
                           SysUserInterfaceEnum.DEVICENET_NORCAL.value}
_RS232_IFACE_VALUES = {SysUserInterfaceEnum.RS232.value,
                       SysUserInterfaceEnum.RS232_ANALOG_OUTPUT.value,
                       SysUserInterfaceEnum.RS485_ANALOG_OUTPUT.value}


class BackupWin(ParamWin):

    # handle_changed_connection_info 오버라이드가 super().__init__() 중에도
    # 호출되므로 (미연결 상태로 창을 열 때) 클래스 기본값으로 존재해야 한다
    _is_backup_running = False

    def __init__(self, parent=None, win_name = None, is_fu_backup = False):
        super().__init__(parent=parent, win_name = win_name, paths = [], filter_param_paths = [], is_editblock_win=False, label_width=210, folder_max_width=None)
        self.is_fu_backup = is_fu_backup
        self.backup_params = []
        self.backup_contents = []

        # 진행 로그는 이 창의 LogView(상태바 Log View 버튼)로 확인한다 —
        # param_worker 와 같은 source(win_name)를 쓰므로 한 뷰에 모인다
        self._log = AppLogManager().get_logger(self.win_name)

        self.toolbar.remove_action("Refresh")
        self.toolbar.add_action("Backup", self.on_clicked_backup)
        self.param_worker.sig_single_read_result.connect(self.handle_single_read_result)

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

        # ParamWin 의 폴더 카드 스크롤 영역은 이 창에서 쓰지 않으므로 트리로 교체.
        # content_widget 재지정으로 handle_changed_working 의 잠금 대상도 트리가 된다
        old_central = self.takeCentralWidget()
        old_central.deleteLater()
        self.setCentralWidget(self.tree)
        self.content_widget = self.tree

    def additional_param_settings(self):
        # 트리 구성 필터에 쓰이는 User Interface / Firmware Version 값을
        # refresh 로 읽어온다 (이 창에는 param 위젯이 없으므로 직접 등록)
        self.user_iface_param = self.param_manager.get_by_full_path("System.Identification.Configuration.User Interface")
        self.param_worker.add_read_param_ptr(self.user_iface_param)

        self.firmware_version_param = self.param_manager.get_by_full_path("System.Identification.Firmware.Firmware Version")
        self.param_worker.add_read_param_ptr(self.firmware_version_param)

    # ------------------------------------------------------------ 체크박스 트리
    def _is_iface_included(self, path: str) -> bool:
        """Interface 계열 폴더 포함 판정 — 공용 Scaling 은 항상, 그 외는 현재
        User Interface 값에 해당하는 폴더만 포함한다 (값 미확인 시 Scaling 만)."""
        if not path.startswith("Interface"):
            return True

        if path.startswith("Interface.Scaling"):
            return True

        user_iface_value = self.user_iface_param.value if self.user_iface_param is not None else None

        if user_iface_value in _DEVICENET_IFACE_VALUES and path.startswith("Interface DeviceNet"):
            return True
        if user_iface_value in _RS232_IFACE_VALUES and path.startswith("Interface RS232/RS485"):
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

    # ------------------------------------------------------------ 백업 실행
    def on_clicked_backup(self):
        if self._is_backup_running:
            return

        if not self.svc_port.connect_info:
            QMessageBox.warning(self, "Connection Error",
                                "Communication is not connected. Please check the connection status.")
            return

        self.backup_params = self._get_checked_params()
        self.backup_contents = []

        if not self.backup_params:
            QMessageBox.information(self, "Information", "There are no parameters checked for backup.")
            return

        self._is_backup_running = True
        self.toolbar.set_action_enabled("Backup", False)
        self.tree.setEnabled(False)  # 진행 중 체크 변경 방지
        self.statusbar.set_progress(0)
        self._log.info("[Backup Start !!!]")
        self.param_worker.single_read_request(self.backup_params[0])

    def handle_changed_connection_info(self, info: str):
        super().handle_changed_connection_info(info)

        # 연결이 끊기면 진행 중 백업을 중단한다 — single read 는 워커 상태 머신
        # 밖이라 handle_disconnected() 로는 멈추지 않는다.
        # (in-flight 응답은 _is_backup_running 가드로 폐기됨)
        if not info and self._is_backup_running:
            self._log.error("[Backup Aborted]: connection lost")
            self._finish_backup()

    def handle_single_read_result(self, req_msg:str, resp_msg: str, param: Parameter, err_type:SvcPortErrType):
        if not self._is_backup_running:
            return

        if err_type != SvcPortErrType.NONE:
            # 연결된 상태의 일시적 오류만 재시도한다 (끊김은 connection_info 경유 중단)
            self._log.error(f"[Port Error]: Parameter = {param.path}.{param.name}, packet = {req_msg}, err_type = {err_type.name}")
            self.param_worker.single_read_request(param)
            return

        resp_check_prefix = f"p:000B{param.id}{param.index:02X}"

        if resp_msg.startswith(resp_check_prefix) == False:
            self._log.error(f"[Packet Error]: Parameter = {param.path}.{param.name}, packet = {resp_msg}")
        else:
            self._log.info(f"[Success]: Parameter = {param.path}.{param.name}")
            value = resp_msg[16:]
            content = f"{param.path}.{param.name}, p:01{param.id}{param.index:02X}{value}"
            self.backup_contents.append(content)

        try:
            current_idx = self.backup_params.index(param)
            next_idx = current_idx + 1

            self.statusbar.set_progress(int((next_idx / len(self.backup_params)) * 100))

            if next_idx < len(self.backup_params):
                next_param = self.backup_params[next_idx]
                self.param_worker.single_read_request(next_param)
            else:
                self._log.info("[Backup Completed Successfully !!!]")
                self._finish_backup()
                self.save_backup_to_file()

        except ValueError:
            self._log.error(f"[Error]: Parameter {param.name} is not in backup list.")
            self._finish_backup()

    def _finish_backup(self):
        self._is_backup_running = False
        self.toolbar.set_action_enabled("Backup", True)
        self.tree.setEnabled(True)
        self.statusbar.set_progress(0)

    def save_backup_to_file(self):
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Backup File",
            "",
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

            file_data = "\n".join([header] + self.backup_contents)

            with open(file_path, "w", encoding="utf-8") as f:
                f.write(file_data)
        except OSError as e:
            self._log.error(f"[Error]: Failed to save file. {e}")
            QMessageBox.critical(self, "Error", f"An error occurred while saving the file:\n{e}")
            return

        self._log.info(f"[File Saved]: Successfully saved to {file_path}")
        QMessageBox.information(self, "Success", "Backup file saved successfully.")
