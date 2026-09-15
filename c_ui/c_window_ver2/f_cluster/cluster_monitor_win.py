"""Cluster Monitor 창 — 클러스터 장치(Device 0 ~ N-1)의 Status 표와, 고른 장치의 Setting / Control 패널.

위: Status 표. 행 = 장치, 열 = Cluster.Device n.Status 의 param 17개 (스키마 순서). 표시 장치 수는
Cluster.Settings.Number of Valves 값이며, 값이 바뀌면 행과 워커의 읽기 등록을 다시 맞춘다
(유휴 모니터링은 다음 라운드부터 새 목록을 돈다 — 재 refresh 하지 않는다). 각 장치의 상태는
NV1 패킷 1건(i:93XX, Nv1ReadSpec)으로 읽힌다 — 17개 param 을 등록해도 워커가 spec 기준으로
묶으므로 장치당 요청 1건이다.

아래: 표에서 고른 장치의 Setting(좌) / Control(우) 폴더 (2026-09-15 사용자 배치안). 폴더는 ParamWin 의
ParamFolderWidget 그대로라 RW 는 편집 → Apply 로 쓰고(Option 6개는 NV1 조합 쓰기 1건, NV2 는 각 1건),
WO(Target Position 입력, Restart 버튼)는 클릭 즉시 쓴다. 장치를 고르면 그 장치의 RW param 을 워커 쓰기
목록에 등록하고 refresh 로 현재 값을 읽어 온다 (사용자 동작이 아니므로 미연결 등은 조용히 넘긴다).
다른 장치를 고르면 이전 폴더는 파괴한다 (param 시그널은 바운드 메서드라 자동 해제). 선택이 없거나
장치 수가 줄어 선택 행이 사라지면 안내 패널로 돌아간다.

표 갱신: 셀마다 위젯을 두지 않고, 상태 param 전부의 값/오류 시그널을 바운드 메서드 하나로 받아
0 ms 단발 타이머로 합친 뒤 표 전체를 다시 채운다 (최대 30 × 17 셀, 바뀐 셀만 setText).
param 은 앱 수명 객체라 창이 닫힐 때 바운드 메서드 연결이 자동 해제된다 (람다 연결 금지 규칙).

값 표시: 위치(posi) 는 LocalSetting 자릿수(PosiConverterManager.format_dp), 배율/실수는 유효숫자
6자리(to_sig_str), enum 은 설명 문자열. 값 없음 "-", Not Support "Not Support", 오류는 글자색 danger
(값이 있으면 마지막 값을 붉게 유지). 툴바는 Refresh 와 Apply (Save/Load 는 백업 대상이 없어 숨김).
"""

import re

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QBrush, QColor
from PySide6.QtWidgets import QHBoxLayout, QHeaderView, QTableWidgetItem, QVBoxLayout, QWidget

from b_core.b_datatype.general_enum import ParamAccType, ParamDisplayType
from b_core.f_helper.float_util import to_sig_str

from c_ui.a_converter.position_converter_manager import PosiConverterManager
from c_ui.b_control_ver2.a_theme.tokens import tokens
from c_ui.b_control_ver2.b_base.containers import PanelWidget
from c_ui.b_control_ver2.b_base.labels import BaseLabel
from c_ui.b_control_ver2.b_base.tables import BaseTableWidget
from c_ui.b_control_ver2.d_param.param_folder_widget import ParamFolderWidget
from c_ui.b_control_ver2.d_param.param_win import ParamWin

NUM_VALVES_PATH = "Cluster.Settings.Number of Valves"
_STATUS_FOLDER = re.compile(r"Cluster\.Device (\d+)\.Status")
_NUMERIC_TYPES = (ParamDisplayType.POSI, ParamDisplayType.SCALE, ParamDisplayType.REAL)
_PLACEHOLDER_TEXT = "Select a device in the status table."


class ClusterMonitorWin(ParamWin):

    COLUMN_WIDTH = 100   # 열 기본 폭(px) — 17열이 1100px 창에 대략 들어가고, 긴 제목은 헤더가 2~3줄로 접는다
    LABEL_WIDTH = 210    # Setting / Control 폴더의 라벨 폭 (다른 ParamWin 과 동일)
    PANEL_FOLDERS = ("Setting", "Control")   # 하단 좌 / 우

    # handle_changed_num_valves 는 super().__init__() 중에도 호출될 수 있으므로 (표 생성 전)
    # 클래스 기본값으로 존재해야 한다
    table = None

    def __init__(self, parent=None, win_name=None):
        super().__init__(parent=parent, win_name=win_name, paths=[], filter_param_paths=[],
                         is_editblock_win=False, label_width=self.LABEL_WIDTH, folder_max_width=None, monitor_tick=10)
        self.resize(1100, 820)

        self.posi_converter = PosiConverterManager()
        self._device_count = 0
        self._selected_device: int | None = None
        self._syncing_rows = False   # 행 수 변경 중 — 표 선택 시그널을 무시한다
        self._cell_colors: dict[tuple[int, int], str] = {}
        self._panels: list[QWidget] = []

        self._build_central()

        # 값/오류 변경을 합쳐 한 번만 다시 채운다 (창의 자식 타이머 — 창과 함께 파괴)
        self._update_timer = QTimer(self)
        self._update_timer.setSingleShot(True)
        self._update_timer.setInterval(0)
        self._update_timer.timeout.connect(self._update_table)

        for params in self._status_params:
            for param in params:
                param.sig_value_changed.connect(self.handle_changed_status_param)
                param.sig_is_err_changed.connect(self.handle_changed_status_param)
                param.sig_is_not_support_changed.connect(self.handle_changed_status_param)

        # [주의] 싱글턴 시그널 연결은 바운드 메서드 규칙을 따른다 (람다 좀비 방지)
        self.posi_converter.sig_posi_range_changed.connect(self.handle_changed_posi_range)

        # Apply 는 고른 장치의 Setting / Control 을 쓴다 — 폴더가 나중에 생기므로 ParamWin 의
        # 'RW 없음 → 숨김' 판정을 되돌린다
        self.action_apply.setVisible(True)

        # 장치 수가 이미 알려져 있으면(값 캐시) 바로 행을 만든다 — 아니면 첫 읽기의 값 변경이 만든다
        self.handle_changed_num_valves()
        self.content_widget.setEnabled(not self.param_worker.is_working)

    def additional_param_settings(self):
        # 장치 상태 param 을 장치 번호별로 모아 둔다 (스키마 순서 = 열 순서). 읽기 등록은 장치 수에 따른다
        numbered = []
        for folder, params in self.param_manager.get_params_grouped("Cluster").items():
            matched = _STATUS_FOLDER.fullmatch(folder)
            if matched:
                numbered.append((int(matched.group(1)), params))
        numbered.sort(key=lambda item: item[0])
        self._status_params: list[list] = [params for _, params in numbered]

        self.num_valves_param = self.param_manager.get_by_full_path(NUM_VALVES_PATH)
        self.param_worker.add_read_param_ptr(self.num_valves_param)
        self._status_read_start = len(self.param_worker.read_param_list)  # 이 뒤가 장치 상태 등록 구간
        self.num_valves_param.sig_value_changed.connect(self.handle_changed_num_valves)

    # ------------------------------------------------------------ GUI 구성
    def _build_central(self):
        columns = self._status_params[0] if self._status_params else []

        self.table = BaseTableWidget(0, len(columns), self, selectable_rows=True)
        self.table.setHorizontalHeaderLabels([self._column_title(param) for param in columns])
        # 열 폭은 고정 기본값 — 긴 제목은 헤더(WrapHeaderView)가 줄바꿈한다. 값 갱신 때마다
        # 재계산(ResizeToContents)하면 "100.00" ↔ "30.00" 같은 길이 변화로 열이 흔들리므로 쓰지 않는다.
        # 가장 긴 값("Remote Locked", "Not Support")이 한 줄에 들어가는 폭이며, 사용자가 끌어 바꿀 수 있다
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Interactive)
        header.setMinimumSectionSize(60)
        header.setDefaultSectionSize(self.COLUMN_WIDTH)
        header.setStretchLastSection(True)
        self.table.itemSelectionChanged.connect(self.handle_changed_table_selection)

        # 하단: 고른 장치의 Setting(좌) / Control(우). 고르기 전에는 안내 패널
        self._panel_row = QHBoxLayout()
        self._panel_row.setContentsMargins(0, 0, 0, 0)
        self._panel_row.setSpacing(10)
        self._show_placeholder_panels()

        central = QWidget(self)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(10, 10, 10, 5)
        layout.setSpacing(10)
        layout.addWidget(self.table, 1)
        layout.addLayout(self._panel_row)

        # ParamWin 의 폴더 카드 스크롤 영역은 이 창에서 쓰지 않으므로 교체.
        # content_widget 재지정으로 handle_changed_working 의 잠금 대상도 표+패널이 된다
        old_central = self.takeCentralWidget()
        old_central.deleteLater()
        self.setCentralWidget(central)
        self.content_widget = central

    @staticmethod
    def _column_title(param) -> str:
        # 위치 값은 백분율 표시 — 이름에 단위가 없으면 붙여 준다
        if param.display_type == ParamDisplayType.POSI and "%" not in param.name:
            return f"{param.name} (%)"
        return param.name

    @staticmethod
    def _alignment(param):
        if param.display_type in _NUMERIC_TYPES:
            return Qt.AlignRight | Qt.AlignVCenter
        return Qt.AlignCenter

    # ------------------------------------------------------------ 하단 패널
    def _set_panels(self, panels: list[QWidget]):
        """하단 좌/우 패널을 교체한다 (이전 패널은 파괴)."""
        for old in self._panels:
            self._panel_row.removeWidget(old)
            old.setParent(None)
            old.deleteLater()
        self._panels = panels
        for panel in panels:
            self._panel_row.addWidget(panel, 1)

    def _show_placeholder_panels(self):
        panels = []
        for title in self.PANEL_FOLDERS:
            panel = PanelWidget(title=title)
            panel.add_widget(BaseLabel(_PLACEHOLDER_TEXT))
            panels.append(panel)
        self._set_panels(panels)

    def handle_changed_table_selection(self):
        if self._syncing_rows:
            return
        rows = {index.row() for index in self.table.selectedIndexes()}
        self._select_device(min(rows) if rows else None)

    def _select_device(self, device: int | None):
        if device == self._selected_device:
            return
        self._selected_device = device

        # 이전 장치의 편집 대상은 등록 해제 — 폴더 파괴로 위젯 바인딩도 함께 사라진다
        self.param_worker.clear_write_param()
        self.folder_widgets = []

        if device is None:
            self._show_placeholder_panels()
            return

        panels = []
        for folder_name in self.PANEL_FOLDERS:
            folder_path = f"Cluster.Device {device}.{folder_name}"
            folder = ParamFolderWidget(force_title=f"Device {device} {folder_name}", folder_path=folder_path,
                                       params=self.param_manager.get_params_in_folder(folder_path),
                                       label_width=self.LABEL_WIDTH)
            panels.append(folder)
            self.folder_widgets.append(folder)

            # ParamWin 생성자와 같은 배선: RW 는 쓰기 목록(refresh 가 현재 값을 읽는다), WO 는 클릭 즉시 쓰기
            for param_widget in folder.widgets:
                if param_widget.param.acc == ParamAccType.RW:
                    self.param_worker.add_write_param_ptr(param_widget.param)
                elif param_widget.param.acc == ParamAccType.WO:
                    param_widget.sig_edited_by_user.connect(self.on_clicked_write_only_component)

        self._set_panels(panels)

        # 고른 장치의 설정값을 읽어 온다 — 사용자의 Refresh 동작이 아니므로 미연결 등은 조용히 넘긴다
        self.param_worker.refresh()

    # ------------------------------------------------------------ 장치 수
    def handle_changed_num_valves(self):
        if self.table is None:
            return

        value = self.num_valves_param.value
        count = 0 if value is None else max(0, min(int(value), len(self._status_params)))
        if count == self._device_count:
            return
        self._device_count = count

        # 읽기 등록을 장치 수에 맞춘다 — 유휴 모니터링은 다음 라운드부터 새 목록을 돈다
        self.param_worker.clear_read_param(self._status_read_start)
        for params in self._status_params[:count]:
            for param in params:
                self.param_worker.add_read_param_ptr(param)

        # 행 수를 바꾸는 동안 Qt 가 현재 행/선택을 옮기므로(행 제거 시 이웃 행으로) 선택 동기화를 막고,
        # 끝난 뒤 우리 상태(_selected_device)를 표에 다시 반영한다. 고른 장치의 행이 사라졌으면 해제
        self._syncing_rows = True
        try:
            self.table.setRowCount(count)
            for row in range(count):
                self.table.setVerticalHeaderItem(row, QTableWidgetItem(f"Device {row}"))
                for col, param in enumerate(self._status_params[row]):
                    if self.table.item(row, col) is None:
                        item = QTableWidgetItem("-")
                        item.setTextAlignment(self._alignment(param))
                        self.table.setItem(row, col, item)

            if self._selected_device is not None and self._selected_device >= count:
                self._select_device(None)
            self.table.clearSelection()
            if self._selected_device is not None:
                self.table.selectRow(self._selected_device)
        finally:
            self._syncing_rows = False

        self._cell_colors = {key: color for key, color in self._cell_colors.items() if key[0] < count}
        self._update_table()

    # ------------------------------------------------------------ 표 갱신
    def handle_changed_status_param(self):
        self._update_timer.start()

    def handle_changed_posi_range(self):
        # 자릿수 변경 — 값은 재디코드하지 않으므로 표시만 다시 만든다
        self._update_timer.start()

    def _update_table(self):
        t = tokens()
        for row in range(self._device_count):
            for col, param in enumerate(self._status_params[row]):
                text, is_err = self._cell_text(param)
                item = self.table.item(row, col)
                if item.text() != text:
                    item.setText(text)

                color = t.danger if is_err else t.text
                if self._cell_colors.get((row, col)) != color:
                    item.setForeground(QBrush(QColor(color)))
                    self._cell_colors[(row, col)] = color

    def _cell_text(self, param) -> tuple[str, bool]:
        """(표시 문자열, 오류 표시 여부)."""
        if param.is_not_support:
            return "Not Support", False

        value = param.value
        if value is None:
            return "-", param.is_err

        if param.display_type == ParamDisplayType.POSI:
            text = self.posi_converter.format_dp(value)
        elif param.display_type == ParamDisplayType.ENUM:
            text = param.ref_list.get_desc(value, f"Unknown ({value})")
        else:
            text = to_sig_str(value)

        return (text if text else str(value)), param.is_err
