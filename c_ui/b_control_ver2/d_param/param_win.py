import json

from PySide6.QtCore import Qt
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import (QFileDialog, QMainWindow, QMessageBox,
                               QScrollArea, QVBoxLayout, QWidget)

from b_core.b_datatype.general_enum import ParamAccType
from b_core.b_datatype.parameter import Parameter
from b_core.c_manager.parameter_manager import ParamManager
from b_core.d_dal.service_port import ServicePort
from b_core.e_worker_ver2.parameter_run_worker import ParameterRunWorker

from c_ui.b_control_ver2.b_base.toolbars import BaseToolBar
from c_ui.b_control_ver2.b_base.statusbars import BaseStatusBar
from c_ui.b_control_ver2.b_base.containers import BaseFlowLayout
from c_ui.b_control_ver2.d_param.param_folder_widget import ParamFolderWidget
from c_ui.b_control_ver2.d_param.param_values import ParamWriteOnlyEnumValueWidget

from c_ui.c_window_ver2.win_manager import WinManager
from c_ui.c_window_ver2.log_view_win import LogViewWin
from c_ui.c_window_ver2.param_worker_win_mixin import ParamWorkerWinMixin

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
        data_to_save = []

        for folder_widget in self.folder_widgets:
            for param_widget in folder_widget.widgets:
                param = param_widget.param
                if param.acc == ParamAccType.RW and param.is_nor_backup:
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