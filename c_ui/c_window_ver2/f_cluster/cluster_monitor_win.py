"""Cluster Monitor 창 — 클러스터 장치(Device 0 ~ N-1)의 Status 를 표 한 장으로 보여 준다.

행 = 장치, 열 = Cluster.Device n.Status 의 param 17개 (스키마 순서). 표시 장치 수는
Cluster.Settings.Number of Valves 값이며, 값이 바뀌면 행과 워커의 읽기 등록을 다시 맞춘다
(유휴 모니터링은 다음 라운드부터 새 목록을 돈다 — 재 refresh 하지 않는다). 각 장치의 상태는
NV1 패킷 1건(i:93XX, Nv1ReadSpec)으로 읽힌다 — 17개 param 을 등록해도 워커가 spec 기준으로
묶으므로 장치당 요청 1건이다.

갱신: 셀마다 위젯을 두지 않고, 상태 param 전부의 값/오류 시그널을 바운드 메서드 하나로 받아
0 ms 단발 타이머로 합친 뒤 표 전체를 다시 채운다 (최대 30 × 17 셀, 바뀐 셀만 setText).
param 은 앱 수명 객체라 창이 닫힐 때 바운드 메서드 연결이 자동 해제된다 (람다 연결 금지 규칙).

값 표시: 위치(posi) 는 LocalSetting 자릿수(PosiConverterManager.format_dp), 배율/실수는 유효숫자
6자리(to_sig_str), enum 은 설명 문자열. 값 없음 "-", Not Support "Not Support", 오류는 글자색 danger
(값이 있으면 마지막 값을 붉게 유지). 읽기 전용 창이라 툴바는 Refresh 만 남는다 (ParamWin 이
RW/백업 param 이 없으면 나머지 액션을 숨긴다).
"""

import re

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QBrush, QColor
from PySide6.QtWidgets import QHeaderView, QTableWidgetItem, QVBoxLayout, QWidget

from b_core.b_datatype.general_enum import ParamDisplayType
from b_core.f_helper.float_util import to_sig_str

from c_ui.a_converter.position_converter_manager import PosiConverterManager
from c_ui.b_control_ver2.a_theme.tokens import tokens
from c_ui.b_control_ver2.b_base.tables import BaseTableWidget
from c_ui.b_control_ver2.d_param.param_win import ParamWin

NUM_VALVES_PATH = "Cluster.Settings.Number of Valves"
_STATUS_FOLDER = re.compile(r"Cluster\.Device (\d+)\.Status")
_NUMERIC_TYPES = (ParamDisplayType.POSI, ParamDisplayType.SCALE, ParamDisplayType.REAL)


class ClusterMonitorWin(ParamWin):

    COLUMN_WIDTH = 100  # 열 기본 폭(px) — 17열이 1100px 창에 대략 들어가고, 긴 제목은 헤더가 2~3줄로 접는다

    # handle_changed_num_valves 는 super().__init__() 중에도 호출될 수 있으므로 (표 생성 전)
    # 클래스 기본값으로 존재해야 한다
    table = None

    def __init__(self, parent=None, win_name=None):
        super().__init__(parent=parent, win_name=win_name, paths=[], filter_param_paths=[],
                         is_editblock_win=False, label_width=210, folder_max_width=None, monitor_tick=10)
        self.resize(1100, 600)

        self.posi_converter = PosiConverterManager()
        self._device_count = 0
        self._cell_colors: dict[tuple[int, int], str] = {}

        self._build_table_central()

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
    def _build_table_central(self):
        columns = self._status_params[0] if self._status_params else []

        self.table = BaseTableWidget(0, len(columns), self)
        self.table.setHorizontalHeaderLabels([self._column_title(param) for param in columns])
        # 열 폭은 고정 기본값 — 긴 제목은 헤더(WrapHeaderView)가 줄바꿈한다. 값 갱신 때마다
        # 재계산(ResizeToContents)하면 "100.00" ↔ "30.00" 같은 길이 변화로 열이 흔들리므로 쓰지 않는다.
        # 가장 긴 값("Remote Locked", "Not Support")이 한 줄에 들어가는 폭이며, 사용자가 끌어 바꿀 수 있다
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Interactive)
        header.setMinimumSectionSize(60)
        header.setDefaultSectionSize(self.COLUMN_WIDTH)
        header.setStretchLastSection(True)

        central = QWidget(self)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(10, 10, 10, 5)
        layout.addWidget(self.table)

        # ParamWin 의 폴더 카드 스크롤 영역은 이 창에서 쓰지 않으므로 표로 교체.
        # content_widget 재지정으로 handle_changed_working 의 잠금 대상도 표가 된다
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

        self.table.setRowCount(count)
        for row in range(count):
            self.table.setVerticalHeaderItem(row, QTableWidgetItem(f"Device {row}"))
            for col, param in enumerate(self._status_params[row]):
                if self.table.item(row, col) is None:
                    item = QTableWidgetItem("-")
                    item.setTextAlignment(self._alignment(param))
                    self.table.setItem(row, col, item)

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
