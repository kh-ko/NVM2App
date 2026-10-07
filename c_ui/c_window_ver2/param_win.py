"""ParamWin — 폴더 카드 창 (ServiceWin 골격 위). 2단계 8위 ③(2026-10-06) 에서 b_control_ver2/d_param 에서 이곳으로 옮겼다 —
d_param 에는 위젯(param_folder_widget / param_values)만 남아 컨트롤 레이어가 창 계층을 역참조하지 않는다 (F061/F062).

ServiceWin 이 툴바·상태바·워커·2단계 초기화(start)·잠금 단일 지점을 맡고, 이 클래스는 폴더 카드 본문과
Save File / Load File / Apply / Enable Edit, enable 조건 배선만 가진다. ParamWorkerWinMixin 은 service_win 에 있다
(MainWin 이 거기서 가져온다). 인터페이스 창 2종(DeviceNet / EtherCAT)은 e_iface/ 에, 압력 제어기 창(ParamPresCtrlWin)은 이 파일에.
폴더 카드 위에 다른 본문을 더하는 창(Firmware Update: 카드 아래 진행 패널, Cluster Monitor: 표 + 고른 장치의 폴더 카드)도
이 클래스 위에 있다 — ServiceWin 의 선택 구성(has_refresh/locks_content)을 그대로 넘겨 받는다.
"""

import json

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFileDialog, QMessageBox, QScrollArea, QWidget

from b_core.b_datatype.general_enum import ParamAccType
from b_core.b_datatype.param_enum import PresCtrlSelEnum

from c_ui.b_control_ver2.a_theme.tokens import tokens
from c_ui.b_control_ver2.b_base.containers import BaseFlowLayout
from c_ui.b_control_ver2.d_param.param_folder_widget import ParamFolderWidget
from c_ui.b_control_ver2.d_param.param_values import ParamWriteOnlyEnumValueWidget, ParamWriteOnlyPosiValueWidget
from c_ui.c_window_ver2.service_win import ServiceWin


class ParamWin(ServiceWin):
    def __init__(self, parent=None, win_name = None, paths : list[str] = None, filter_param_paths : list[str] = None, is_editblock_win=False, label_width=210, folder_max_width=None, monitor_tick: int = 100,
                 has_refresh: bool = True, locks_content: bool = True):
        super().__init__(parent, win_name if win_name is not None else paths[0],
                         has_refresh=has_refresh, locks_content=locks_content, monitor_tick=monitor_tick)

        self.is_editblock_win = is_editblock_win
        self._edit_locked = is_editblock_win  # 편집 잠금 창은 잠긴 채 시작 — 반영은 set_body / start 의 _sync_lock_state

        self.action_save_file = self.toolbar.add_action("Save File", self.on_clicked_save_file)
        self.action_load_file = self.toolbar.add_action("Load File", self.on_clicked_load_file)
        self.action_apply = self.toolbar.add_action("Apply", self.on_clicked_apply)
        if self.is_editblock_win:
            self.toolbar.add_action("Enable Edit", self.on_clicked_enable_edit)

        self.scroll_area = QScrollArea(self)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        body = QWidget()
        # 폴더 카드는 흐름 배치 — 창이 좁으면 세로 1열, 넓어지면 여러 열로 개행
        self.content_layout = BaseFlowLayout(body, margin=10, spacing=10)
        self.scroll_area.setWidget(body)
        self.set_body(self.scroll_area, body)  # 잠금 대상은 스크롤 안의 본문

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
        widget_by_param_path = {}
        for param_widget in all_param_widgets:
            widget_by_param_path.setdefault(param_widget.param.full_path, param_widget)

        for param_widget in all_param_widgets:
            if param_widget.param.enable_conditions is None:
                continue

            for condition in param_widget.param.enable_conditions:
                ref_widget = widget_by_param_path.get(condition.ref_path)
                if ref_widget is not None:
                    param_widget.reg_enable_condition(ref_widget, condition.values)

        # 시그널 구독·초기 연결 동기화(연결 중이면 refresh)·잠금 확정은 ServiceWin.start() 가 한다 —
        # WinManager.show_window 가 생성 직후·show 직전에 부른다 (서브클래스 __init__ 이 끝난 뒤)

    # 특수 param window일 경우 따로 설정할 param이 있다면 이 메서드를 override
    def additional_param_settings(self):
        pass

    # Load File 이 항목을 위젯에 적용하기 직전 훅 — 파일 내용에 따라 창 상태
    # (예: EtherCAT 창의 Advanced Range 모드)를 맞춰야 하는 창이 override 한다
    def before_apply_loaded_items(self, loaded_items):
        pass

    # closeEvent(재부팅 박스 닫기 + 워커 cleanup) / Refresh / Log View / 쓰기 정책 / 연결·SN 상태바는 ServiceWin 과
    # ParamWorkerWinMixin 이 제공한다

    def on_clicked_save_file(self):
        # 백업 대상: RW + nor_backup param 만 (ver1 과 동일 기준).
        # 값은 위젯의 export_backup_value() 로 뽑는다 — 컨버터 위젯은 이 훅을
        # 오버라이드해 표시 단위 그대로 저장한다. 항목은 path/name 으로 식별한다
        # (2026-09-11 결정 B: 프로토콜 id 는 정체성이 아니므로 기록하지 않는다).
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
        # save_file 의 대칭: 같은 스키마(path/name 으로 대상 식별)를 읽어
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

        # (path, name) -> 위젯 매핑 (RW 만 — save 와 동일 기준)
        widget_map = {}
        for folder_widget in self.folder_widgets:
            for param_widget in folder_widget.widgets:
                param = param_widget.param
                if param.acc == ParamAccType.RW:
                    widget_map[(param.path, param.name)] = param_widget

        applied = 0
        failed_items = []
        for item in loaded_data:
            if not isinstance(item, dict) or not all(k in item for k in ("path", "name", "value")):
                continue

            param_widget = widget_map.get((item["path"], item["name"]))
            if param_widget is None:
                continue  # 이 창에 없는 param 항목은 무시 (부분 백업 파일 허용)

            if not param_widget.isVisible():
                continue  # 숨겨진(현재 모드가 다루지 않는) 항목도 무시 — save 와 대칭

            if item["value"] is None:
                continue  # 저장 당시 값 없음(Unknown) — 적용하지 않고 집계에도 넣지 않는다 (N096, 사용자 결정)

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
        # 값은 위젯의 도메인 값(숫자 또는 문자열)을 그대로 넘긴다 — 선로 문자열은 spec 의 codec 이
        # 선로값을 만든 뒤 한 번만 포맷한다 (여기서 문자열화하면 6자리 절단이 두 번 일어난다)
        # 편집 가능한(활성·표시 중) 위젯의 dirty 값만 — 조건으로 비활성화됐거나 숨은 위젯의 편집은 보내지 않는다 (F064).
        # 미확정 입력의 클램프·확정은 툴바가 액션 실행 전에 처리한다 (BaseToolBar.confirm_focused_edit)
        write_pairs = []
        for folder_widget in self.folder_widgets:
            for param_widget in folder_widget.widgets:
                if param_widget.is_editable() and param_widget.is_dirty():
                    write_pairs.append((param_widget.param, param_widget.get_value()))

        self.multiple_param_write(write_pairs)                    

    def on_clicked_enable_edit(self):
        if not self.is_working:
            self.set_edit_locked(False)  # 본문·Apply·Save File·Load File 이 함께 풀린다 (edit_locked_actions)

    def on_clicked_write_only_component(self, param_component):
        # WO enum(모드 선택형)은 콤보에서 고른 현재 값을, 위치 입력형은 입력한 백분율(도메인 값 —
        # 선로 문자열은 spec 의 codec 이 만든다)을, 버튼형은 스키마에 고정된 btn_str_value 를 보낸다
        if isinstance(param_component, ParamWriteOnlyEnumValueWidget):
            self.single_param_write(param_component.param, param_component.get_value_str())
        elif isinstance(param_component, ParamWriteOnlyPosiValueWidget):
            value = param_component.get_value()
            if value is not None:
                self.single_param_write(param_component.param, value)
        else:
            self.single_param_write(param_component.param, param_component.param.btn_str_value)

    # ------------------------------------------------------------ 잠금 (ServiceWin._sync_lock_state 의 입력)
    def locked_actions(self):
        # Enable Edit 은 워커 동작 중에만 잠긴다 — 편집 잠금 중에는 눌러서 풀 수 있어야 한다
        return ("Enable Edit",) if self.is_editblock_win else ()

    def edit_locked_actions(self):
        # 워커 동작 중과 편집 잠금 중에 잠긴다 (2026-10-06 결정 — 전에는 Apply 를 눌러 BUSY 경고를 받았다).
        # 편집 잠금 중 Load File 도 잠그는 이유: 잠긴 위젯에 값을 넣어 dirty 로 만든 뒤 Apply 로 쓰는 우회 경로 차단
        return ("Apply", "Save File", "Load File")

    def on_working_changed(self, working: bool):
        if self.is_editblock_win:
            self._edit_locked = True  # 워커 동작이 시작/종료될 때마다 편집 잠금 상태로 되돌린다

class ParamPresCtrlWin(ParamWin):
    def __init__(self, parent=None, win_name = None, paths : list[str] = None, filter_param_paths : list[str] = None, is_editblock_win=False, label_width=210, folder_max_width=None):

        super().__init__(parent=parent, win_name = win_name, paths = paths, filter_param_paths = filter_param_paths, is_editblock_win=is_editblock_win, label_width=label_width, folder_max_width=folder_max_width)

    def additional_param_settings(self):
        self.controller_selector_used_param = self.param_manager.get_by_full_path("Pressure Control.Basic.Controller Selector Used")
        self.param_worker.add_read_param_ptr(self.controller_selector_used_param)
        self.controller_selector_used_param.sig_value_changed.connect(self.handle_changed_controller_selector_used)
        # 창을 열 때 값이 이미 있으면(다른 창이 읽어 둠) 시그널이 오지 않으므로 1회 평가
        self.handle_changed_controller_selector_used()

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
