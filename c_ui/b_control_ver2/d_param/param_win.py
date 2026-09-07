import json

from PySide6.QtCore import Qt
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import (QFileDialog, QMainWindow, QMessageBox,
                               QScrollArea, QVBoxLayout, QWidget, QApplication)

from b_core.b_datatype.general_enum import ParamAccType
from b_core.b_datatype.parameter import Parameter
from b_core.b_datatype.param_enum import EtherCATDataTypeEnum, PresCtrlSelEnum
from b_core.c_manager.app_log_manager import AppLogManager
from b_core.c_manager.parameter_manager import ParamManager
from b_core.f_helper import eds_file_helper, ethercat_xml_file_helper
from b_core.d_dal.service_port import ServicePort
from b_core.e_worker_ver2.parameter_run_worker import ParameterRunWorker, StartResult

from c_ui.b_control_ver2.a_theme import tokens
from c_ui.b_control_ver2.b_base.toolbars import BaseToolBar
from c_ui.b_control_ver2.b_base.statusbars import BaseStatusBar
from c_ui.b_control_ver2.b_base.containers import BaseFlowLayout
from c_ui.b_control_ver2.d_param.param_folder_widget import ParamFolderWidget
from c_ui.b_control_ver2.d_param.param_values import ParamWriteOnlyEnumValueWidget

from c_ui.c_window_ver2.win_manager import WinManager
from c_ui.c_window_ver2.log_view_win import LogViewWin
from c_ui.c_window_ver2.x_message.param_result_message_box import (
    ask_local_switch, show_param_refresh_warning, show_param_write_warning)
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

class ParamWin(ParamWorkerWinMixin, QMainWindow):
    def __init__(self, parent=None, win_name = None, paths : list[str] = None, filter_param_paths : list[str] = None, is_editblock_win=False, label_width=210, folder_max_width=None):
        super().__init__(parent)
        self.resize(750, 450)

        if win_name is None:
            self.win_name = paths[0]
        else:
            self.win_name = win_name

        self.is_editblock_win = is_editblock_win

        self.toolbar = BaseToolBar(self)
        self.addToolBar(Qt.TopToolBarArea, self.toolbar)
        self.toolbar.add_action("Refresh", self.on_clicked_refresh)
        self.action_save_file = self.toolbar.add_action("Save File", self.on_clicked_save_file)
        self.action_load_file = self.toolbar.add_action("Load File", self.on_clicked_load_file)
        self.action_apply = self.toolbar.add_action("Apply", self.on_clicked_apply)

        if self.is_editblock_win:
            self.toolbar.add_action("Enable Edit", self.on_clicked_enable_edit)
            # 편집 잠금 중에는 Load File 도 함께 잠근다 — 잠긴 위젯에 값을 넣어
            # dirty 로 만든 뒤 Apply 로 쓰는 우회 경로를 막기 위함
            self.action_load_file.setEnabled(False)

        self.scroll_area = QScrollArea(self)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        self.content_widget = QWidget()
        # 폴더 카드는 흐름 배치 — 창이 좁으면 세로 1열, 넓어지면 여러 열로 개행
        self.content_layout = BaseFlowLayout(self.content_widget, margin=10, spacing=10)

        self.scroll_area.setWidget(self.content_widget)

        self.setCentralWidget(self.scroll_area)

        self.statusbar = BaseStatusBar(parent=self, label_count=2)
        self.statusbar.btn_log.clicked.connect(self.on_clicked_log_view)
        self.setStatusBar(self.statusbar)

        self.content_widget.setEnabled(False)

        '''
        기능 설정
        '''
        self.param_manager = ParamManager()

        self.param_worker = ParameterRunWorker(self, log_source=self.win_name)
        self.param_worker.sig_finish_refresh.connect(self.handle_finished_refresh)
        self.param_worker.sig_reboot_started.connect(self.handle_started_reboot)
        self.param_worker.sig_reboot_finished.connect(self.handle_finished_reboot)
        self.param_worker.sig_progress_changed.connect(self.handle_changed_param_worker_progress)
        self.param_worker.sig_is_working_changed.connect(self.handle_changed_working)

        self.sn_param = self.param_manager.get_by_full_path("System.Identification.Serial Number")
        self.sn_param.sig_value_changed.connect(self.handle_changed_sn_param)
        self.handle_changed_sn_param()

        self.folder_widgets = []

        for path in paths:
            # 폴더별 param 목록을 한 번의 순회로 그룹핑 (폴더마다 전체 param 재스캔 방지)
            for folder, params in self.param_manager.get_params_grouped(path, filter_param_paths).items():
                folder_widget = ParamFolderWidget(force_title=None, folder_path=folder, params=params, label_width=label_width)
                if folder_widget.get_param_count() > 0:
                    self.folder_widgets.append(folder_widget)
                    self.content_layout.addWidget(folder_widget)
                else:
                    del folder_widget

        # folder_max_width: 폴더 카드의 줄 구성 기준 폭 — None 이면 무제한(가로
        # 분할 없이 세로 1열). 폴더가 1개뿐이면 분할할 것이 없으므로 적용하지
        # 않는다 (카드가 창 폭을 그대로 채움)
        if folder_max_width is not None and len(self.folder_widgets) >= 2:
            self.content_layout.set_item_width(folder_max_width)

        self.additional_param_settings()

        for folder_widget in self.folder_widgets:
            for param_widget in folder_widget.widgets:
                if param_widget.param.acc == ParamAccType.RO:
                    self.param_worker.add_read_param_ptr(param_widget.param)
                else:
                    self.param_worker.add_write_param_ptr(param_widget.param)

                # WO 컴포넌트(버튼 등)는 클릭 즉시 쓰기 — dirty 가 없어 Apply
                # 경로에 잡히지 않으므로 이 연결이 유일한 쓰기 경로다
                if param_widget.param.acc == ParamAccType.WO:
                    param_widget.sig_edited_by_user.connect(self.on_clicked_write_only_component)

        # 조건부 툴바 액션 (ver1 init_toolbar 컨셉):
        # - Save/Load File: 백업 대상(is_nor_backup) param 이 있을 때만
        # - Apply: RW param 이 있을 때만
        all_param_widgets = [param_widget
                             for folder_widget in self.folder_widgets
                             for param_widget in folder_widget.widgets]

        has_backup_param = any(pw.param.is_nor_backup for pw in all_param_widgets)
        if not has_backup_param:
            self.action_save_file.setVisible(False)
            self.action_load_file.setVisible(False)

        has_rw_param = any(pw.param.acc == ParamAccType.RW for pw in all_param_widgets)
        if not has_rw_param:
            self.action_apply.setVisible(False)

        # param 의 enable 조건 배선 (ver1 init_end 대응) — 참조 param(id) 위젯의
        # 값이 조건 목록에 있을 때만 해당 위젯이 활성화된다. 참조 탐색은 이 창에
        # 올라온 위젯으로 한정하며, 참조가 이 창에 없으면 조건을 걸 수 없어
        # 건너뛴다 (항상 활성으로 남으므로 화면에서 바로 드러난다)
        widget_by_param_id = {}
        for param_widget in all_param_widgets:
            widget_by_param_id.setdefault(param_widget.param.id, param_widget)

        for param_widget in all_param_widgets:
            if param_widget.param.enable_conditions is None:
                continue

            for condition in param_widget.param.enable_conditions:
                ref_widget = widget_by_param_id.get(condition.ref_id)
                if ref_widget is not None:
                    param_widget.reg_enable_condition(ref_widget, condition.values)

        # 연결 시그널/초기 상태 반영은 위젯·param 등록이 끝난 뒤에 한다 —
        # 등록 전에 하면 (a) 연결 상태에서 빈 refresh(EMPTY)가 한 번 낭비되고,
        # (b) 미연결 상태에서는 별도 refresh 호출의 NOT_CONNECTED 모달이
        # 창이 show() 되기 전(__init__ 안)에 떠 버린다. 초기 refresh 는
        # 아래 handle_changed_connection_info() 가 연결 상태일 때만 수행한다
        self.svc_port = ServicePort()
        self.svc_port.connect_info_changed.connect(self.handle_changed_connection_info)
        self.handle_changed_connection_info(self.svc_port.connect_info)

    # 특수 param window일 경우 따로 설정할 param이 있다면 이 메서드를 override
    def additional_param_settings(self):
        pass

    # Load File 이 항목을 위젯에 적용하기 직전 훅 — 파일 내용에 따라 창 상태
    # (예: EtherCAT 창의 Advanced Range 모드)를 맞춰야 하는 창이 override 한다
    def before_apply_loaded_items(self, loaded_items):
        pass

    def closeEvent(self, event: QCloseEvent):
        # WA_DeleteOnClose 로 파괴되기 전에 워커 스레드를 명시적으로 정리한다.
        # 워커의 destroyed->cleanup 안전망은 창의 자식으로 파괴될 때 동작하지
        # 않아, 누락 시 QThread fatal 로 앱 전체가 abort 된다 (실측)
        self.param_worker.cleanup()
        event.accept()

    # 쓰기 정책/refresh/연결·SN 상태바 처리는 ParamWorkerWinMixin 이 제공한다

    def on_clicked_refresh(self):
        self.start_param_refresh()

    def on_clicked_save_file(self):
        # 백업 대상: RW + nor_backup param 만 (ver1 과 동일 기준).
        # 값은 위젯의 export_backup_value() 로 뽑는다 — 컨버터 위젯은 이 훅을
        # 오버라이드해 표시 단위 그대로 저장한다. 파일 스키마는 ver1 과 호환.
        # 숨겨진 위젯은 제외한다 — 숨김 = 현재 창 모드가 다루지 않는 항목
        # (예: EtherCAT 창의 Advanced Range 전환)
        data_to_save = []

        for folder_widget in self.folder_widgets:
            for param_widget in folder_widget.widgets:
                param = param_widget.param
                if param.acc == ParamAccType.RW and param.is_nor_backup and param_widget.isVisible():
                    item = {
                        "path": param.path,
                        "name": param.name,
                        "id": param.id,
                        "index": str(param.index),
                        "value": param_widget.export_backup_value(),
                    }

                    # 단위 개념이 있는 값(pres)은 저장 당시 표시 단위를 함께 기록 —
                    # 로드 시 단위가 달라져 있으면 위젯이 환산한다
                    unit = param_widget.export_backup_unit()
                    if unit is not None:
                        item["unit"] = unit

                    data_to_save.append(item)

        if not data_to_save:
            QMessageBox.information(self, "Information", "There are no items to save.")
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Parameter File",
            "",
            "JSON Files (*.json);;All Files (*)")

        if not file_path:
            return

        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data_to_save, f, indent=4, ensure_ascii=False)
        except OSError as e:
            QMessageBox.critical(self, "Error", f"An error occurred while saving the file:\n{e}")
            return

        QMessageBox.information(self, "Success", "File saved successfully.")

    def on_clicked_load_file(self):
        # save_file 의 대칭: 같은 스키마(id/index 로 대상 식별)를 읽어
        # import_backup_value() 로 위젯에 넣는다. commit 하지 않으므로 값이
        # 달라진 위젯은 dirty 로 표시되고, 실제 쓰기는 Apply 가 수행한다.
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Load Parameter File",
            "",
            "JSON Files (*.json);;All Files (*)")

        if not file_path:
            return

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                loaded_data = json.load(f)
        except (OSError, json.JSONDecodeError) as e:
            QMessageBox.critical(self, "Error", f"An error occurred while reading the file:\n{e}")
            return

        if not isinstance(loaded_data, list):
            QMessageBox.warning(self, "Warning",
                                "Invalid file format. The selected file is not a valid parameter file.")
            return

        # 적용 전에 창이 파일 내용에 맞춰 상태(모드 등)를 조정할 기회 —
        # 아래의 visible 필터가 이 조정 결과를 따라가므로 반드시 적용 전이어야 한다
        self.before_apply_loaded_items(loaded_data)

        # (id, index) -> 위젯 매핑 (RW 만 — save 와 동일 기준)
        widget_map = {}
        for folder_widget in self.folder_widgets:
            for param_widget in folder_widget.widgets:
                param = param_widget.param
                if param.acc == ParamAccType.RW:
                    widget_map[(param.id, str(param.index))] = param_widget

        applied = 0
        failed_items = []
        for item in loaded_data:
            if not isinstance(item, dict) or not all(k in item for k in ("id", "index", "value")):
                continue

            param_widget = widget_map.get((item["id"], item["index"]))
            if param_widget is None:
                continue  # 이 창에 없는 param 항목은 무시 (부분 백업 파일 허용)

            if not param_widget.isVisible():
                continue  # 숨겨진(현재 모드가 다루지 않는) 항목도 무시 — save 와 대칭

            try:
                param_widget.import_backup_value(item["value"], item.get("unit"))
            except Exception as e:
                # 값 형식 불량(예: 숫자 자리에 문자열) — 해당 항목만 건너뛰고 알림에 모은다
                failed_items.append(f"{item.get('path', '?')}.{item.get('name', '?')} ({e})")
                continue

            applied += 1

        if failed_items:
            shown = "\n- ".join(failed_items[:10])
            more = "" if len(failed_items) <= 10 else f"\n... and {len(failed_items) - 10} more"
            QMessageBox.warning(self, "Warning",
                                f"Some items had invalid values and were skipped:\n- {shown}{more}")

        QMessageBox.information(self, "Success",
                                f"Parameter data loaded successfully. ({applied}/{len(loaded_data)} items)")

    def on_clicked_apply(self):
        write_pairs = []
        for folder_widget in self.folder_widgets:
            for param_widget in folder_widget.widgets:
                if param_widget.is_dirty():
                    write_pairs.append((param_widget.param, param_widget.get_value_str()))

        self.multiple_param_write(write_pairs)                    

    def on_clicked_enable_edit(self):
        if self.param_worker.is_working == False:
            self.content_widget.setEnabled(True)
            self.action_load_file.setEnabled(True)  # 편집 해제와 함께 Load File 잠금도 푼다
        else:
            pass

    def on_clicked_write_only_component(self, param_component):
        # WO enum(모드 선택형)은 콤보에서 고른 현재 값을, 버튼형은 스키마에
        # 고정된 btn_str_value 를 보낸다
        if isinstance(param_component, ParamWriteOnlyEnumValueWidget):
            self.single_param_write(param_component.param, param_component.get_value_str())
        else:
            self.single_param_write(param_component.param, param_component.param.btn_str_value)

    def on_clicked_log_view(self):
        # win_id 를 창 이름으로 분리 — MainWin 등 다른 창의 LogViewWin 과
        # WinManager 키("LogViewWin")가 겹치면 sources 필터가 무시된다
        WinManager().show_window(win_class=LogViewWin, win_id=f"LogViewWin_{self.win_name}",
                                 parent=self, sources={self.win_name})

    def handle_changed_working(self, working: bool):
        if self.is_editblock_win:
            # 워커 동작이 시작/종료될 때마다 편집 잠금 상태로 되돌린다 — Load File 도 동기
            self.content_widget.setEnabled(False)
            self.action_load_file.setEnabled(False)
        else:
            self.content_widget.setEnabled(not working)

    def handle_finished_refresh(self):
        pass

    # 재부팅 대기 다이얼로그(handle_started_reboot / handle_finished_reboot /
    # on_clicked_quit_app)는 ParamWorkerWinMixin 이 제공한다

class ParamPresCtrlWin(ParamWin):
    def __init__(self, parent=None, win_name = None, paths : list[str] = None, filter_param_paths : list[str] = None, is_editblock_win=False, label_width=210, folder_max_width=None):

        super().__init__(parent=parent, win_name = win_name, paths = paths, filter_param_paths = filter_param_paths, is_editblock_win=is_editblock_win, label_width=label_width, folder_max_width=folder_max_width)

    def additional_param_settings(self):
        self.controller_selector_used_param = self.param_manager.get_by_full_path("Pressure Control.Basic.Controller Selector Used")
        self.param_worker.add_read_param_ptr(self.controller_selector_used_param)
        self.controller_selector_used_param.sig_value_changed.connect(self.handle_changed_controller_selector_used)

    def handle_changed_controller_selector_used(self):
        used_controller = self.controller_selector_used_param.value

        # self.content_layout 의 자식들의 테두리 색생을 상황에 맞춰서 변경해야된다.
        # 예 used_controller 가 1 이면 self.content_layout 첫번째 자식(folder_widget)만 선택 색상으로 되고, 나머지는 원래 테두리 색상이 되어야 한다.

        used_index = None
        if used_controller is not None:
            index = used_controller - PresCtrlSelEnum.CONTROLLER_1.value
            if 0 <= index < len(self.folder_widgets):
                used_index = index

        t = tokens()
        for index, folder_widget in enumerate(self.folder_widgets):
            folder_widget.set_colors(border=t.selection_text if index == used_index else t.border)

class ParamIfaceDentWin(ParamWin):
    def __init__(self, parent=None, win_name = None, paths : list[str] = None, filter_param_paths : list[str] = None, is_editblock_win=False, label_width=210, folder_max_width=None):

        super().__init__(parent=parent, win_name = win_name, paths = paths, filter_param_paths = filter_param_paths, is_editblock_win=is_editblock_win, label_width=label_width, folder_max_width=folder_max_width)
        self.toolbar.add_action("Create EDS", self.on_clicked_create_eds)

    def additional_param_settings(self):
        # EDS 생성(Param16)에 쓰이는 클러스터 param — 이 창의 폴더 밖이므로 직접 읽기 등록
        self.param_worker.add_read_param_ptr(self.param_manager.get_by_full_path("Cluster.Settings.Number of Valves"))

    def on_clicked_create_eds(self):
        file_path, _ = QFileDialog.getSaveFileName(self, "Save EDS File", "", "EDS Files (*.eds);;All Files (*)")
        if not file_path:
            return

        try:
            eds_file_helper.create_eds_file(file_path)
        except Exception as e:
            AppLogManager().get_logger(self.win_name).error(f"EDS 파일 생성 실패: {e}")
            QMessageBox.critical(self, "Error", f"Failed to create EDS file.\nError details: {e}")
            return

        QMessageBox.information(self, "Success", "EDS file has been created successfully.")

class ParamIfaceEtherCatWin(ParamWin):
    def __init__(self, parent=None, win_name = None, paths : list[str] = None, filter_param_paths : list[str] = None, is_editblock_win=False, label_width=210, folder_max_width=None):

        super().__init__(parent=parent, win_name = win_name, paths = paths, filter_param_paths = filter_param_paths, is_editblock_win=is_editblock_win, label_width=label_width, folder_max_width=folder_max_width)
        self.toolbar.add_action("Create XML", self.on_clicked_create_xml)
        self.action_advanced_range = self.toolbar.add_action("Enable Advanced Range", self.on_clicked_toggle_advanced_range)

        # 초기 모드: Basic — Scaling 폴더 숨김, Range 전체 표시
        self._apply_advanced_range_mode(False)

    def additional_param_settings(self):
        # Range 폴더들의 Data type 위젯 수집 — 프로토콜상 param 은 폴더별로
        # 따로지만 UI 에서는 하나의 값으로 일괄 운용한다. 경로/이름은 바뀔 수
        # 있으므로 전용 enum(EtherCATDataTypeEnum) 사용 여부로 걸러낸다
        self.data_type_widgets = [pw
                                  for fw in self.folder_widgets
                                  for pw in fw.widgets
                                  if pw.param.ref_list is EtherCATDataTypeEnum]

        for pw in self.data_type_widgets:
            pw.sig_edited_by_user.connect(self.handle_edited_data_type)

        # Advanced Range 모드 전환 대상 — Scaling 폴더 전체(EtherCAT 전용 +
        # 공용 Interface.Scaling)와, Range 폴더의 Data type 을 제외한
        # 나머지(= Data Value 들)
        self.scaling_folder_widgets = [fw for fw in self.folder_widgets
                                       if fw.folder_path.startswith(("Interface EtherCAT.Scaling", "Interface.Scaling"))]
        self.range_data_value_widgets = [pw
                                         for fw in self.folder_widgets
                                         for pw in fw.widgets
                                         if pw.param.path.startswith("Interface EtherCAT.Range")
                                         and pw.param.ref_list is not EtherCATDataTypeEnum]

    def handle_edited_data_type(self, edited_widget):
        value = edited_widget.get_value()
        for pw in self.data_type_widgets:
            if pw is not edited_widget:
                pw.set_value(value)   # 코드 할당 -> dirty, Apply 가 일괄로 쓴다

    def _apply_advanced_range_mode(self, is_advanced: bool):
        """Advanced: Scaling 폴더 표시 + Range 의 Data Value 숨김 / Basic: 반대.

        숨겨지는 쪽의 RW 편집은 원복한다 — Apply 는 dirty 기준으로 동작하므로
        (visible 무관), 숨은 편집이 장비로 새어 나가면 안 된다"""
        self.is_advanced_range = is_advanced

        hidden_widgets = (self.range_data_value_widgets if is_advanced
                          else [pw for fw in self.scaling_folder_widgets for pw in fw.widgets])
        for pw in hidden_widgets:
            if pw.param.acc != ParamAccType.RO:
                pw.handle_param_value_changed()  # set_value(param.value) + commit — dirty 원복

        for fw in self.scaling_folder_widgets:
            fw.setVisible(is_advanced)
        for pw in self.range_data_value_widgets:
            pw.setVisible(not is_advanced)

        self.action_advanced_range.setText("Disable Advanced Range" if is_advanced else "Enable Advanced Range")

    def on_clicked_toggle_advanced_range(self):
        self._apply_advanced_range_mode(not self.is_advanced_range)

    def before_apply_loaded_items(self, loaded_items):
        # 파일에 Scaling 항목이 있으면 Advanced, 없으면 Basic 으로 맞춘 뒤 적용 —
        # 이후의 visible 필터가 반대편(숨겨진) 항목을 자동으로 걸러낸다
        scaling_keys = {(pw.param.id, str(pw.param.index))
                        for fw in self.scaling_folder_widgets
                        for pw in fw.widgets}
        has_scaling = any(isinstance(item, dict)
                          and (item.get("id"), item.get("index")) in scaling_keys
                          for item in loaded_items)
        self._apply_advanced_range_mode(has_scaling)

    def on_clicked_create_xml(self):
        file_path, _ = QFileDialog.getSaveFileName(self, "Save XML File", "", "XML Files (*.xml);;All Files (*)")
        if not file_path:
            return

        try:
            ethercat_xml_file_helper.create_xml_file(file_path)
        except Exception as e:
            AppLogManager().get_logger(self.win_name).error(f"XML 파일 생성 실패: {e}")
            QMessageBox.critical(self, "Error", f"Failed to create XML file.\nError details: {e}")
            return

        QMessageBox.information(self, "Success", "XML file has been created successfully.")       