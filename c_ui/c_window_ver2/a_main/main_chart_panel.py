"""메인 실시간 차트 패널.

CompoundData 스트림(20~30ms 간격 샘플, 200ms 마다 배치 수신)을
position(왼쪽 Y축) / pressure(오른쪽 Y축) 4개 곡선으로 그린다.
X축은 사용자가 선택한 시간창(30s~10min, 그래프 하단 콤보)만 보여주며
최신 샘플을 따라 슬라이딩한다.

화면 구성: [posi 설정 열 | 차트 | pres 설정 열]
- 좌/우 열에 각 축의 곡선 on/off 체크박스와 범위 설정(Auto/Full/Custom + min/max).
- 패널 컨트롤은 전부 즉시 적용 (Apply 없음) — 체크박스/X Range 콤보와 동일 정책.

성능 원칙 — 실시간 표방이므로 사용자 인터랙션보다 부하 최소화가 우선:
- 마우스 줌/팬, 컨텍스트 메뉴, 오토레인지 버튼 전부 비활성화.
- 데이터는 고정 용량 numpy 이중 버퍼 — 복사 없는 슬라이스 뷰 사용.
- setData 는 X 시간창에 보이는 구간만 전달한다 (searchsorted 로 시작점 계산)
  — 그리기 비용이 보관 이력 길이와 무관해지고, Y Auto 범위도
  '화면에 보이는 데이터' 기준이 된다.
- 꺼진 곡선은 setData 자체를 생략한다 (다시 켤 때 1회 갱신).
- iface->dp 표시 단위 변환은 append 시 스칼라로 수행 (배치당 수십 회 수준).
  컨버터의 단위/스케일이 바뀌면 과거 데이터와 표시 단위가 섞이므로 차트를 비운다.

곡선 on/off, 축 범위 모드, X 시간창은 LocalSettingManager 의 chart 설정을
단일 진실로 삼는다 — 컨트롤이든 외부 코드든 설정만 바꾸면 변경 시그널로
전부 동기화된다.
"""

import os
import shutil
import time

import numpy as np
import pyqtgraph as pg

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFontMetrics
from PySide6.QtWidgets import QFileDialog, QHBoxLayout, QMessageBox, QVBoxLayout

from b_core.b_datatype import param_enum as p_enum
from b_core.c_manager.local_setting_manager import LocalSettingManager
from b_core.f_helper.chart_csv_file_helper import ChartCSVFileHelper

from c_ui.a_converter.position_converter_manager import PosiConverterManager
from c_ui.a_converter.pressure_converter_manager import PresConverterManager, PresConvertType
from c_ui.b_control_ver2.a_theme.tokens import tokens
from c_ui.b_control_ver2.b_base import icons
from c_ui.b_control_ver2.b_base.buttons import BaseButton
from c_ui.b_control_ver2.b_base.inputs import BaseCheckBox
from c_ui.b_control_ver2.b_base.labels import BaseLabel
from c_ui.b_control_ver2.b_base.containers import PanelWidget
from c_ui.b_control_ver2.c_values.read_write_values import ReadWriteEnumValueWidget, ReadWriteFloatValueWidget
from c_ui.c_window_ver2.c_analysis.chart_analysis_win import ChartAnalysisWin

# 보관 샘플 수 — 최악 20ms 간격 기준으로도 최대 시간창(10min)을 채울 수 있는 크기.
# 넘치면 오래된 샘플부터 밀려난다.
_CAPACITY = 30000

# 좌/우 설정 열(패널 카드) 폭
_SIDE_WIDTH = 150

# 이중 버퍼의 행 인덱스
_ROW_TIME = 0
_ROW_POSI_ACT = 1
_ROW_POSI_TGT = 2
_ROW_PRES_ACT = 3
_ROW_PRES_TGT = 4


class MainChartPanel(PanelWidget):

    def __init__(self, parent=None):
        super().__init__(title=None, fit=True, parent=parent)

        self.local_setting = LocalSettingManager()
        self.posi_converter = PosiConverterManager()
        self.pres_converter = PresConverterManager()

        # [이중 버퍼] 뒤쪽 절반이 차면 최근 _CAPACITY 개를 앞으로 복사한다.
        # 유효 구간은 항상 [ _end - _size : _end ] 슬라이스 뷰 (복사 없음)
        self._buf = np.full((5, _CAPACITY * 2), np.nan)
        self._end = 0
        self._size = 0
        self._t0_ms = None  # 첫 샘플 시각 — X축(초)의 원점

        self._recorder = None  # Record 중일 때만 ChartCSVFileHelper 인스턴스 (기록 세션)

        self._build_chart()
        # 차트 열(_chart_area)을 완성한 뒤 main_row 에 조립한다
        self._build_x_window_row()

        # [posi 설정 열 | 차트 | pres 설정 열]
        main_row = QHBoxLayout()
        main_row.setContentsMargins(0, 0, 0, 0)
        main_row.setSpacing(0)
        main_row.addLayout(self._build_side_column("posi", "Pos.Act", "Pos.Tgt"))
        main_row.addLayout(self._chart_area, 1)
        main_row.addLayout(self._build_side_column("pres", "Pres.Act", "Pres.Tgt"))
        self.content_layout.addLayout(main_row)
        self.content_layout.setStretchFactor(main_row, 1)
        self.main_layout.setStretchFactor(self.content_widget, 1)

        # [주의] 싱글턴 시그널 연결은 바운드 메서드 규칙을 따른다 (람다 좀비 방지)
        ls = self.local_setting
        ls.sig_posi_chart_enable_actual_changed.connect(self.handle_posi_enable_actual_changed)
        ls.sig_posi_chart_enable_target_changed.connect(self.handle_posi_enable_target_changed)
        ls.sig_pres_chart_enable_actual_changed.connect(self.handle_pres_enable_actual_changed)
        ls.sig_pres_chart_enable_target_changed.connect(self.handle_pres_enable_target_changed)
        ls.sig_posi_chart_range_mode_changed.connect(self.handle_posi_range_setting_changed)
        ls.sig_posi_chart_range_custom_min_changed.connect(self.handle_posi_range_setting_changed)
        ls.sig_posi_chart_range_custom_max_changed.connect(self.handle_posi_range_setting_changed)
        ls.sig_posi_decimal_places_changed.connect(self.handle_posi_range_setting_changed)
        ls.sig_pres_chart_range_mode_changed.connect(self.handle_pres_range_setting_changed)
        ls.sig_pres_chart_range_custom_min_changed.connect(self.handle_pres_range_setting_changed)
        ls.sig_pres_chart_range_custom_max_changed.connect(self.handle_pres_range_setting_changed)
        ls.sig_pres_decimal_places_changed.connect(self.handle_pres_range_setting_changed)
        ls.sig_chart_x_window_sec_changed.connect(self.handle_x_window_changed)

        # 컨버터 단위/스케일 변경 -> 표시 단위가 바뀌므로 과거 데이터를 비우고 범위 재적용
        self.posi_converter.sig_posi_range_changed.connect(self.handle_posi_converter_changed)
        self.pres_converter.sig_pres_range_changed.connect(self.handle_pres_converter_changed)

        # 초기 상태 적용
        self.handle_posi_enable_actual_changed()
        self.handle_posi_enable_target_changed()
        self.handle_pres_enable_actual_changed()
        self.handle_pres_enable_target_changed()
        self.handle_posi_range_setting_changed()
        self.handle_pres_range_setting_changed()
        self.handle_x_window_changed()

    # ------------------------------------------------------------ GUI 구성
    def _build_chart(self):
        t = tokens()

        self.plot_widget = pg.PlotWidget(background=t.panel_bg)
        self.plot_item = self.plot_widget.getPlotItem()

        # Y 범위를 padding=0 으로 정확히 잡으면 양끝 tick 라벨(예: 0/100)이
        # 위젯 경계에 걸려 절반이 잘린다 — 라벨 높이의 절반만큼 상하 여백 확보
        self.plot_item.layout.setContentsMargins(0, 10, 0, 10)

        # 인터랙션 전부 차단 (부하/오조작 방지). X 범위는 코드가 시간창으로 직접 제어한다
        self.plot_item.setMenuEnabled(False)
        self.plot_item.hideButtons()
        posi_vb = self.plot_item.getViewBox()
        posi_vb.setMouseEnabled(False, False)
        posi_vb.disableAutoRange(axis=pg.ViewBox.XAxis)

        # 오른쪽 축 = pressure 전용 ViewBox (X는 왼쪽과 링크)
        self.pres_viewbox = pg.ViewBox()
        self.pres_viewbox.setMouseEnabled(False, False)
        self.plot_item.showAxis("right")
        self.plot_item.scene().addItem(self.pres_viewbox)
        self.plot_item.getAxis("right").linkToView(self.pres_viewbox)
        self.pres_viewbox.setXLink(posi_vb)
        posi_vb.sigResized.connect(self.handle_posi_viewbox_resized)

        # 좌=position / 우=pressure 구분은 tick 라벨 색으로 한다 (축선/눈금은 회색 통일)
        for axis_name, color in (("left", t.chart_posi_target), ("right", t.chart_pres_target)):
            axis = self.plot_item.getAxis(axis_name)
            axis.setPen(pg.mkPen(t.chart_grid))
            axis.setTextPen(pg.mkPen(color))

        # Y 그리드(가로선) — 축의 grid 기능(showGrid)은 짧은 눈금(tick)을 전장
        # 선으로 대체해버려 축 눈금 표시가 사라진다. 그래서 눈금은 양쪽 축 모두
        # 살리고, 그리드는 좌측(position) 축 major 눈금 위치에 수평선 풀을
        # 직접 그린다 (major 만 — 선이 많으면 복잡해 보이므로).
        self._grid_lines = []
        posi_vb.sigYRangeChanged.connect(self.handle_posi_yrange_changed)

        # X축은 축선만 남기고 tick 라벨/눈금을 없앤다 — 차트 바로 밑의
        # 시각 라벨 2개(왼쪽 끝/오른쪽 끝)가 라벨 역할을 대신한다.
        # (축 API 로 양끝만 라벨링하면 매 갱신마다 tick 재설정 + 끝점 라벨
        #  잘림 문제가 있어 BaseLabel setText 2회가 훨씬 싸다)
        bottom_axis = self.plot_item.getAxis("bottom")
        bottom_axis.setStyle(showValues=False, tickLength=0)
        bottom_axis.setPen(pg.mkPen(t.text))

        # 곡선 4개 — key 는 로컬 설정 이름과 1:1 대응. target 은 점선으로 구분한다.
        # pres 곡선(pres_viewbox 소속)이 posi 곡선 아래에 그려지므로(실측),
        # 겹칠 때도 보이도록 pres 쪽을 약간 더 두껍게 그린다
        self._curves = {
            "posi_chart_enable_actual": pg.PlotDataItem(pen=pg.mkPen(t.chart_posi_target, width=1)),
            "posi_chart_enable_target": pg.PlotDataItem(pen=pg.mkPen(t.chart_posi_target, width=1, style=Qt.DashLine)),
            "pres_chart_enable_actual": pg.PlotDataItem(pen=pg.mkPen(t.chart_pres_target, width=2)),
            "pres_chart_enable_target": pg.PlotDataItem(pen=pg.mkPen(t.chart_pres_target, width=2, style=Qt.DashLine)),
        }
        self._curve_rows = {
            "posi_chart_enable_actual": _ROW_POSI_ACT,
            "posi_chart_enable_target": _ROW_POSI_TGT,
            "pres_chart_enable_actual": _ROW_PRES_ACT,
            "pres_chart_enable_target": _ROW_PRES_TGT,
        }
        self.plot_item.addItem(self._curves["posi_chart_enable_actual"])
        self.plot_item.addItem(self._curves["posi_chart_enable_target"])
        self.pres_viewbox.addItem(self._curves["pres_chart_enable_actual"])
        self.pres_viewbox.addItem(self._curves["pres_chart_enable_target"])

        # 차트 + 시각 라벨 행을 간격 0 으로 딱 붙인다 (main_row 조립은 __init__ 에서)
        self._chart_area = QVBoxLayout()
        self._chart_area.setContentsMargins(5, 0, 5, 0)
        self._chart_area.setSpacing(0)
        self._chart_area.addWidget(self.plot_widget, 1)

        self.lbl_x_left = BaseLabel("-")     # 창 왼쪽 끝 시각 = 오른쪽 끝 - X range
        self.lbl_x_right = BaseLabel("-")    # 창 오른쪽 끝 시각 = 최신 샘플 시각 (hh:mm:ss)

        time_row = QHBoxLayout()
        time_row.setContentsMargins(0, 0, 0, 0)
        time_row.setSpacing(0)
        time_row.addWidget(self.lbl_x_left)
        time_row.addStretch()
        time_row.addWidget(self.lbl_x_right)
        self._chart_area.addLayout(time_row)

    def _build_side_column(self, prefix, actual_label, target_label):
        """차트 옆의 설정 열: [Legend 패널(체크박스) + Range 패널(모드/Min/Max)] 카드 박싱."""
        t = tokens()
        if not hasattr(self, "_checkboxes"):
            self._checkboxes = {}
            self._range_widgets = {}

        column = QVBoxLayout()
        column.setContentsMargins(0, 0, 0, 0)
        column.setSpacing(0)

        target_color = t.chart_posi_target if prefix == "posi" else t.chart_pres_target
        title_prefix = "Pos." if prefix == "posi" else "Pres."

        legend_panel = PanelWidget(title=f"{title_prefix} Legends")
        legend_panel.setFixedWidth(_SIDE_WIDTH)
        column.addWidget(legend_panel)

        for kind, label, color in (("actual", actual_label, target_color),
                                   ("target", target_label, target_color)):
            checkbox = BaseCheckBox(label)
            checkbox.set_colors(text=color)
            legend_panel.add_widget(checkbox)
            self._checkboxes[f"{prefix}_chart_enable_{kind}"] = checkbox

        range_panel = PanelWidget(title=f"{title_prefix} Range")
        range_panel.setFixedWidth(_SIDE_WIDTH)
        column.addWidget(range_panel, 1)

        mode_widget = ReadWriteEnumValueWidget(
            enum_class=p_enum.ChartRangeModeEnum, label_text="Mode", is_vertical_mode=True)
        range_panel.add_widget(mode_widget)

        min_widget = ReadWriteFloatValueWidget(label_text="Min", is_vertical_mode=True)
        max_widget = ReadWriteFloatValueWidget(label_text="Max", is_vertical_mode=True)
        for widget in (min_widget, max_widget):
            widget.set_range(-3.4028235e+38, 3.4028235e+38)  # float32 전 범위
            # Custom 모드에서만 편집 가능
            widget.reg_enable_condition(mode_widget, [p_enum.ChartRangeModeEnum.CUSTOM.value])
            range_panel.add_widget(widget)


        self._range_widgets[f"{prefix}_chart_range_mode"] = mode_widget
        self._range_widgets[f"{prefix}_chart_range_custom_min"] = min_widget
        self._range_widgets[f"{prefix}_chart_range_custom_max"] = max_widget

        # 사용자 편집 -> 즉시 로컬 설정 반영 (저장/전파는 _Setting 이 전담)
        self._checkboxes[f"{prefix}_chart_enable_actual"].sig_edited_by_user.connect(
            self.on_clicked_posi_actual_checkbox if prefix == "posi" else self.on_clicked_pres_actual_checkbox)
        self._checkboxes[f"{prefix}_chart_enable_target"].sig_edited_by_user.connect(
            self.on_clicked_posi_target_checkbox if prefix == "posi" else self.on_clicked_pres_target_checkbox)
        mode_widget.sig_edited_by_user.connect(
            self.on_edited_posi_range_widget if prefix == "posi" else self.on_edited_pres_range_widget)
        min_widget.sig_edited_by_user.connect(
            self.on_edited_posi_range_widget if prefix == "posi" else self.on_edited_pres_range_widget)
        max_widget.sig_edited_by_user.connect(
            self.on_edited_posi_range_widget if prefix == "posi" else self.on_edited_pres_range_widget)

        return column

    def _build_x_window_row(self):
        # X축 시간창 선택 (즉시 적용 — Apply 없음).
        # 전체 폭이 아니라 차트 열(_chart_area) 하단에만 배치한다.
        # 사이드 카드의 Mode 와 동일하게 c_values enum 위젯으로 통일 — 동기화는
        # set_value+commit, 미지의 설정값은 placeholder 로 자동 처리된다
        self.x_window_widget = ReadWriteEnumValueWidget(
            enum_class=p_enum.ChartXWindowEnum, label_text="X Range", label_width=55)
        self.x_window_widget.setFixedWidth(180)
        self.x_window_widget.sig_edited_by_user.connect(self.on_selected_x_window)

        # Record 토글 버튼 — 대기: [● Record] / 기록 중: [■ Stop - hh:mm:ss].
        # 경과 시간은 데이터 수신과 무관하게 흘러야 하므로 update_chart 가 아니라
        # 전용 1초 타이머로 버튼 라벨을 갱신한다
        self.record_btn = BaseButton("Record", icons.GLYPH_RECORD, glyph_color=tokens().danger)
        self.record_btn.setFixedWidth(170)
        self.record_btn.clicked.connect(self.on_clicked_record)
        self._record_timer = QTimer(self)
        self._record_timer.setInterval(1000)
        self._record_timer.timeout.connect(self.handle_record_timer_timeout)

        # Capture 버튼 — 현재 화면에 표시된 구간을 스냅샷해 분석 윈도우를 연다
        self.capture_btn = BaseButton("Capture", icons.GLYPH_CAPTURE)
        self.capture_btn.clicked.connect(self.on_clicked_capture)

        row = QHBoxLayout()
        row.setContentsMargins(0, 5, 0, 5)  # 시각 라벨 행과 살짝 띄운다
        row.setSpacing(5)
        row.addWidget(self.x_window_widget)
        row.addWidget(self.record_btn)
        row.addWidget(self.capture_btn)
        row.addStretch()
        self._chart_area.addLayout(row)

    # ------------------------------------------------------------ 데이터 수신
    def update_chart(self, data_list):
        """MainWin 이 200ms 주기로 전달하는 CompoundData 배치를 버퍼에 추가하고 1회 다시 그린다."""
        if not data_list:
            return

        capacity2 = self._buf.shape[1]

        # 기록 중이면 배치를 CSV 행으로도 모은다 (차트와 같은 표시(dp) 값)
        record_rows = [] if self._recorder is not None else None
        pres_unit = p_enum.SensUnitEnum.get_desc(self.local_setting.pres_unit) if record_rows is not None else None

        for data in data_list:
            if self._t0_ms is None:
                self._t0_ms = data.timestamp

            # 이중 버퍼 압축 — 뒤쪽 절반이 가득 차면 최근 구간을 앞으로 복사
            if self._end == capacity2:
                self._buf[:, :_CAPACITY] = self._buf[:, capacity2 - _CAPACITY:capacity2]
                self._end = _CAPACITY

            posi_act = self._to_plot(self.posi_converter.convert_posi_to_dp(data.act_posi))
            posi_tgt = self._to_plot(self.posi_converter.convert_posi_to_dp(data.target_posi))
            pres_act = self._to_plot(self.pres_converter.convert_iface_pres_to_dp_pres(data.act_pres, PresConvertType.AUTO))
            pres_tgt = self._to_plot(self.pres_converter.convert_iface_pres_to_dp_pres(data.target_pres, PresConvertType.AUTO))

            i = self._end
            self._buf[_ROW_TIME, i] = (data.timestamp - self._t0_ms) / 1000.0
            self._buf[_ROW_POSI_ACT, i] = posi_act
            self._buf[_ROW_POSI_TGT, i] = posi_tgt
            self._buf[_ROW_PRES_ACT, i] = pres_act
            self._buf[_ROW_PRES_TGT, i] = pres_tgt

            self._end += 1
            self._size = min(self._size + 1, _CAPACITY)

            if record_rows is not None:
                record_rows.append((data.timestamp, posi_act, posi_tgt, pres_act, pres_tgt, pres_unit))

        if record_rows is not None:
            self._recorder.append(record_rows)

        self._redraw()

    @staticmethod
    def _to_plot(value):
        # 컨버터 미준비 등으로 변환 불가한 샘플은 NaN — connect="finite" 로 선이 끊겨 표시된다
        return np.nan if value is None else value

    def _visible_slice(self):
        """X 시간창에 들어오는 버퍼 구간 (vis_start, end, t_end). 데이터 없으면 None."""
        if self._size == 0:
            return None

        start = self._end - self._size
        x = self._buf[_ROW_TIME]
        t_end = x[self._end - 1]

        # 시간은 단조 증가이므로 이진 탐색으로 창 시작 인덱스를 찾는다
        window = self.local_setting.chart_x_window_sec
        vis_start = start + int(np.searchsorted(x[start:self._end], t_end - window))
        return vis_start, self._end, t_end

    def _set_curve_data(self, name, visible):
        vis_start, end, _ = visible
        self._curves[name].setData(
            self._buf[_ROW_TIME, vis_start:end],
            self._buf[self._curve_rows[name], vis_start:end], connect="finite")

    def _apply_x_range(self, t_end):
        # 항상 최신 샘플이 오른쪽 끝 — '오른쪽 끝 = 현재시간' 라벨이 항상 참이 되도록
        # 데이터가 창을 채우기 전에도 슬라이딩한다 (초기엔 왼쪽이 빈 채로 흘러감)
        window = self.local_setting.chart_x_window_sec
        self.plot_item.getViewBox().setXRange(t_end - window, t_end, padding=0)
        self._update_time_labels(t_end)

    def _update_time_labels(self, t_end):
        if self._t0_ms is None:
            self.lbl_x_left.setText("-")
            self.lbl_x_right.setText("-")
            return

        # 샘플 timestamp 는 epoch ms (compound worker 의 time.time() 기반).
        # 음수 epoch 는 Windows localtime 이 OSError 를 내므로 0 으로 클램프 (방어)
        right_epoch = max(0.0, (self._t0_ms / 1000.0) + t_end)
        left_epoch = max(0.0, right_epoch - self.local_setting.chart_x_window_sec)
        self.lbl_x_left.setText(time.strftime("%H:%M:%S", time.localtime(left_epoch)))
        self.lbl_x_right.setText(time.strftime("%H:%M:%S", time.localtime(right_epoch)))

    def _redraw(self):
        visible = self._visible_slice()
        if visible is None:
            return

        for name in self._curves:
            if not getattr(self.local_setting, name):
                continue  # 꺼진 곡선은 그리지 않는다 (켤 때 1회 갱신)
            self._set_curve_data(name, visible)

        self._apply_x_range(visible[2])
        self._update_pres_axis_width()

    def clear_chart(self):
        self._end = 0
        self._size = 0
        self._t0_ms = None
        for curve in self._curves.values():
            curve.setData([], [])
        self._apply_x_range(0.0)

    # ------------------------------------------------------------ 곡선 on/off
    def _sync_curve(self, name):
        enabled = getattr(self.local_setting, name)
        self._checkboxes[name].setChecked(enabled)
        self._curves[name].setVisible(enabled)

        # 꺼져 있는 동안 setData 를 생략했으므로 켜는 순간 한 번 따라잡는다
        if enabled:
            visible = self._visible_slice()
            if visible is not None:
                self._set_curve_data(name, visible)

    def handle_posi_enable_actual_changed(self):
        self._sync_curve("posi_chart_enable_actual")

    def handle_posi_enable_target_changed(self):
        self._sync_curve("posi_chart_enable_target")

    def handle_pres_enable_actual_changed(self):
        self._sync_curve("pres_chart_enable_actual")

    def handle_pres_enable_target_changed(self):
        self._sync_curve("pres_chart_enable_target")

    def on_clicked_posi_actual_checkbox(self):
        self.local_setting.posi_chart_enable_actual = self._checkboxes["posi_chart_enable_actual"].isChecked()

    def on_clicked_posi_target_checkbox(self):
        self.local_setting.posi_chart_enable_target = self._checkboxes["posi_chart_enable_target"].isChecked()

    def on_clicked_pres_actual_checkbox(self):
        self.local_setting.pres_chart_enable_actual = self._checkboxes["pres_chart_enable_actual"].isChecked()

    def on_clicked_pres_target_checkbox(self):
        self.local_setting.pres_chart_enable_target = self._checkboxes["pres_chart_enable_target"].isChecked()

    # ------------------------------------------------------------ X축 시간창
    def on_selected_x_window(self):
        seconds = self.x_window_widget.get_value()
        if seconds is not None:
            self.local_setting.chart_x_window_sec = seconds

    def handle_x_window_changed(self):
        # 위젯 동기화 (설정에 없는 값이면 빈 표시 + placeholder — enum 위젯 계약)
        self.x_window_widget.set_value(self.local_setting.chart_x_window_sec)
        self.x_window_widget.commit()

        # 창이 넓어지면 이전에 안 그리던 구간까지 필요하므로 곡선도 다시 그린다
        visible = self._visible_slice()
        if visible is None:
            self._apply_x_range(0.0)
            return

        for name in self._curves:
            if getattr(self.local_setting, name):
                self._set_curve_data(name, visible)

        self._apply_x_range(visible[2])

    # ------------------------------------------------------------ 기록 (Record)
    def on_clicked_record(self):
        if self._recorder is None:
            self._recorder = ChartCSVFileHelper()
            self.record_btn.set_icon(icons.GLYPH_STOP, tokens().danger)
            self.record_btn.setText("Stop - 00:00:00")
            self._record_timer.start()
            return

        record_dir = self._recorder.stop()
        self._recorder = None
        self._record_timer.stop()
        self.record_btn.set_icon(icons.GLYPH_RECORD, tokens().danger)
        self.record_btn.setText("Record")

        # 저장 폴더 이름 입력 — getExistingDirectory 는 새 이름 입력이 불가하므로
        # 파일 저장 다이얼로그를 '폴더 경로 입력'으로 사용한다
        suggested = os.path.join(os.path.expanduser("~"), os.path.basename(record_dir))
        while True:
            target, _ = QFileDialog.getSaveFileName(self, "Save Record As Folder", suggested)
            if not target:
                # 취소 — 데이터 유실 방지를 위해 임시 폴더는 지우지 않고 남겨둔다
                QMessageBox.information(self, "Record",
                                        f"Save canceled. Recorded data remains in:\n{record_dir}")
                return

            if os.path.exists(target):
                QMessageBox.warning(self, "Record", "Folder already exists. Choose another name.")
                continue

            break

        try:
            shutil.move(record_dir, target)
        except OSError as error:
            QMessageBox.warning(self, "Record",
                                f"Move failed ({error}). Recorded data remains in:\n{record_dir}")
            return

        QMessageBox.information(self, "Record", f"Recorded data saved to:\n{target}")

    def on_clicked_capture(self):
        # 캡처 = 현재 X 시간창에 표시 중인 구간의 스냅샷 (복사본 — 이후 실시간
        # 갱신과 무관). 분석 윈도우는 스냅샷만 다루므로 여러 개 띄워도 안전하다.
        visible = self._visible_slice()
        if visible is None:
            QMessageBox.information(self, "Capture", "No data to capture.")
            return

        vis_start, end, _ = visible
        win = ChartAnalysisWin(parent=self.window())
        win.setAttribute(Qt.WA_DeleteOnClose)
        win.set_capture_data(
            t0_ms=self._t0_ms,
            times=self._buf[_ROW_TIME, vis_start:end].copy(),
            posi_act=self._buf[_ROW_POSI_ACT, vis_start:end].copy(),
            posi_tgt=self._buf[_ROW_POSI_TGT, vis_start:end].copy(),
            pres_act=self._buf[_ROW_PRES_ACT, vis_start:end].copy(),
            pres_tgt=self._buf[_ROW_PRES_TGT, vis_start:end].copy(),
            pres_unit=self.local_setting.pres_unit)  # SensUnitEnum 값 — 창이 단위 변환에 사용
        win.show()

    def handle_record_timer_timeout(self):
        if self._recorder is None:
            return

        elapsed = int(time.time() - self._recorder.start_time)
        hours, remainder = divmod(elapsed, 3600)
        minutes, seconds = divmod(remainder, 60)
        self.record_btn.setText(f"Stop - {hours:02d}:{minutes:02d}:{seconds:02d}")

    # ------------------------------------------------------------ 축 범위 (Y)
    def _apply_y_range(self, viewbox, mode, full_min, full_max, custom_min, custom_max):
        if mode == p_enum.ChartRangeModeEnum.AUTO.value:
            # Auto 는 '화면(시간창)에 보이는 데이터' 기준 — setData 를 가시 구간만
            # 전달하므로 pyqtgraph 오토레인지가 자연히 그 기준이 된다
            viewbox.enableAutoRange(axis=pg.ViewBox.YAxis)
            return

        viewbox.disableAutoRange(axis=pg.ViewBox.YAxis)

        if mode == p_enum.ChartRangeModeEnum.FULL.value:
            y_min, y_max = full_min, full_max
        else:  # CUSTOM
            y_min, y_max = custom_min, custom_max

        # min >= max 로 설정된 경우 Qt 경고/이상 표시 방지용 최소 간격 확보
        if y_max <= y_min:
            y_max = y_min + 1.0

        viewbox.setYRange(y_min, y_max, padding=0)

    def _sync_range_widgets(self, prefix, decimal_places):
        """좌/우 열의 Range 모드/Min/Max 위젯을 로컬 설정값으로 동기화한다."""
        mode_widget = self._range_widgets[f"{prefix}_chart_range_mode"]
        mode_widget.set_value(getattr(self.local_setting, f"{prefix}_chart_range_mode"))
        mode_widget.commit()

        for suffix in ("custom_min", "custom_max"):
            widget = self._range_widgets[f"{prefix}_chart_range_{suffix}"]
            widget.set_decimals(decimal_places)
            widget.set_value(getattr(self.local_setting, f"{prefix}_chart_range_{suffix}"))
            widget.commit()
            # set_value 가 setEnabled(True) 로 복구하므로 Custom 조건을 다시 평가한다
            widget.on_enable_condition_changed()

    def handle_posi_range_setting_changed(self):
        self._sync_range_widgets("posi", self.local_setting.posi_decimal_places)
        self._apply_y_range(
            self.plot_item.getViewBox(),
            self.local_setting.posi_chart_range_mode,
            0.0, 100.0,
            self.local_setting.posi_chart_range_custom_min,
            self.local_setting.posi_chart_range_custom_max)

    def handle_pres_range_setting_changed(self):
        full_max = self.pres_converter.get_dp_max_pres(PresConvertType.AUTO)
        if full_max is None:
            full_max = 100.0  # 컨버터 미준비 시 대체값 (스펙)

        self._sync_range_widgets("pres", self.local_setting.pres_decimal_places)
        self._apply_y_range(
            self.pres_viewbox,
            self.local_setting.pres_chart_range_mode,
            0.0, full_max,
            self.local_setting.pres_chart_range_custom_min,
            self.local_setting.pres_chart_range_custom_max)

        self._update_pres_axis_width()

    def on_edited_posi_range_widget(self, _widget):
        # 편집된 위젯만이 아니라 그룹 전체를 반영해도 무해하다 (같은 값 대입은 no-op)
        self._apply_range_widgets("posi")

    def on_edited_pres_range_widget(self, _widget):
        self._apply_range_widgets("pres")

    def _apply_range_widgets(self, prefix):
        for suffix in ("mode", "custom_min", "custom_max"):
            name = f"{prefix}_chart_range_{suffix}"
            value = self._range_widgets[name].get_value()

            # 편집 중간 상태(빈 칸 등)는 반영하지 않는다
            if value is None:
                continue

            setattr(self.local_setting, name, value)

    # ------------------------------------------------------------ 우측 축 폭
    _pres_axis_width_key = None  # 폭 재계산 생략용 캐시 (범위/자리수가 그대로면 스킵)

    def _update_pres_axis_width(self):
        """우측(pressure) 축 폭을 라벨 폭에 맞춰 직접 지정한다.

        보조 ViewBox 에 링크된 축은 pyqtgraph 의 자동 폭 확장이 라벨 폭을
        따라가지 못해 tick 라벨이 잘린다 — 현재 표시 범위의 양끝 값을
        자리수 설정으로 포맷해 본 문자열 폭 + 눈금 여백으로 계산한다.
        (실제 tick 은 이보다 짧은 표기를 쓰므로 과소평가는 없다)"""
        y_lo, y_hi = self.pres_viewbox.state["viewRange"][1]
        decimals = self.local_setting.pres_decimal_places

        key = (round(y_lo, 6), round(y_hi, 6), decimals)
        if key == self._pres_axis_width_key:
            return
        self._pres_axis_width_key = key

        sample = max((f"{v:.{decimals}f}" for v in (y_lo, y_hi)), key=len)
        text_width = QFontMetrics(self.plot_widget.font()).horizontalAdvance(sample)
        self.plot_item.getAxis("right").setWidth(text_width + 12)

    # ------------------------------------------------------------ 외부 변화 대응
    def handle_posi_converter_changed(self):
        # 표시 단위/스케일이 바뀌면 과거 데이터와 단위가 섞이므로 비우고 다시 시작한다
        self.clear_chart()
        self.handle_posi_range_setting_changed()

    def handle_pres_converter_changed(self):
        self.clear_chart()
        self.handle_pres_range_setting_changed()

    def handle_posi_yrange_changed(self, *args):
        self._update_grid_lines()

    def handle_posi_viewbox_resized(self):
        # 오른쪽 축 ViewBox 는 레이아웃에 속하지 않으므로 왼쪽과 지오메트리를 수동 동기화
        self.pres_viewbox.setGeometry(self.plot_item.getViewBox().sceneBoundingRect())
        # 눈금 간격은 픽셀 높이에도 의존하므로 리사이즈 시 그리드도 재배치
        self._update_grid_lines()

    def _update_grid_lines(self):
        posi_vb = self.plot_item.getViewBox()
        y_min, y_max = posi_vb.state["viewRange"][1]
        height = max(1, int(posi_vb.height()))

        # 좌측 축이 실제로 쓰는 눈금 계산을 그대로 빌린다 (major 레벨만)
        levels = self.plot_item.getAxis("left").tickValues(y_min, y_max, height)
        values = levels[0][1] if levels else []

        # 수평선 풀 재사용 — 부족하면 생성, 남으면 숨김
        while len(self._grid_lines) < len(values):
            pen = pg.mkPen(pg.mkColor(tokens().chart_grid + "78"), width=1)  # 반투명 회색
            line = pg.InfiniteLine(angle=0, movable=False, pen=pen)
            line.setZValue(-10)  # 곡선 뒤에 깔리게
            posi_vb.addItem(line, ignoreBounds=True)  # Auto 범위 계산에 미포함
            self._grid_lines.append(line)

        for line, value in zip(self._grid_lines, values):
            line.setPos(value)
            line.setVisible(True)
        for line in self._grid_lines[len(values):]:
            line.setVisible(False)
