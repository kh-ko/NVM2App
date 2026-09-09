"""센서 압력 실시간 분석 창.

세 압력 값을 하나의 Y축(표시 압력 단위)에 실시간 곡선으로 그린다:
- Pressure Control.Basic.Actual Pressure : MainWin 의 compound 폴링이
  set_force_value 로 계속 갱신한다 — 이 창은 읽기 등록 없이 값만 샘플링
- Sensor.Sensor 1/2.Basic.Actual Pressure Value : 이 창의 param_worker
  read 목록에 등록 — 유휴 모니터링이 주기적으로 읽어 값을 갱신한다
  (ServicePort 가 뮤텍스로 트랜잭션을 직렬화하므로 MainWin 폴링과 공존)

값 갱신 주기가 소스마다 달라 곡선 시간축을 맞추기 위해, 고정 주기
(SAMPLE_INTERVAL_MS) 타이머로 세 param.value 를 함께 샘플링한다.
표시 변환은 param 위젯과 동일 기준 — PresConverterManager 의
AUTO(제어 압력) / SENSOR1 / SENSOR2. 변환 불가(값 없음 등)는 NaN 으로
선이 끊겨 표시된다.

차트 구현은 MainChartPanel 의 성능 원칙을 따른다: 인터랙션 차단,
numpy 이중 버퍼, X 시간창 가시 구간만 setData, 컨버터 변경 시 차트 클리어.
"""

import time

import numpy as np
import pyqtgraph as pg

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QHBoxLayout, QVBoxLayout, QWidget

from b_core.b_datatype import param_enum as p_enum
from b_core.c_manager.local_setting_manager import LocalSettingManager

from c_ui.a_converter.pressure_converter_manager import PresConverterManager, PresConvertType
from c_ui.b_control_ver2.a_theme.tokens import tokens
from c_ui.b_control_ver2.b_base.containers import PanelWidget
from c_ui.b_control_ver2.b_base.inputs import BaseCheckBox
from c_ui.b_control_ver2.b_base.labels import BaseLabel
from c_ui.b_control_ver2.c_values.read_write_values import ReadWriteEnumValueWidget, ReadWriteFloatValueWidget
from c_ui.b_control_ver2.d_param.param_win import ParamWin

# 보관 샘플 수 — 200ms 샘플링으로 최대 시간창(10min = 3000샘플)을 여유 있게 채우는 크기
_CAPACITY = 4000

# 좌측 설정 열(패널 카드) 폭 — MainChartPanel 과 동일
_SIDE_WIDTH = 150

# 이중 버퍼의 행 인덱스
_ROW_TIME = 0
_ROW_ACT = 1
_ROW_SENS1 = 2
_ROW_SENS2 = 3


class SensorAnalysisWin(ParamWin):

    SAMPLE_INTERVAL_MS = 100

    # handle_changed_connection_info 오버라이드가 super().__init__() 중에도
    # 호출되므로 (타이머 생성 전) 클래스 기본값으로 존재해야 한다
    sample_timer = None

    def __init__(self, parent=None, win_name = None):
        super().__init__(parent=parent, win_name = win_name, paths = [], filter_param_paths = [], is_editblock_win=False, label_width=210, folder_max_width=None, monitor_tick = 10)
        self.resize(900, 500)

        self.local_setting = LocalSettingManager()
        self.pres_converter = PresConverterManager()

        # [이중 버퍼] MainChartPanel 과 동일 — 뒤쪽 절반이 차면 최근 구간을 앞으로 복사
        self._buf = np.full((4, _CAPACITY * 2), np.nan)
        self._end = 0
        self._size = 0
        self._t0 = None  # 첫 샘플 시각 (epoch sec) — X축(초)의 원점

        # 창 로컬 상태 (저장 안 함) — X 시간창 / 곡선 on-off / Y 범위 모드
        self._x_window_sec = p_enum.ChartXWindowEnum.MIN_1.value
        self._curve_enabled = {_ROW_ACT: True, _ROW_SENS1: True, _ROW_SENS2: True}
        self._range_mode = p_enum.ChartRangeModeEnum.AUTO.value
        self._range_min = 0.0
        self._range_max = 100.0

        self._build_chart_central()
        self._apply_y_range()

        # 고정 주기 샘플링 — 연결 중에만 돈다 (handle_changed_connection_info)
        self.sample_timer = QTimer(self)
        self.sample_timer.setInterval(self.SAMPLE_INTERVAL_MS)
        self.sample_timer.timeout.connect(self.handle_sample_timer_timeout)
        if self.svc_port.connect_info:
            self.sample_timer.start()

        # 컨버터 단위/스케일 변경 -> 표시 단위가 바뀌므로 과거 데이터를 비운다.
        # [주의] 싱글턴 시그널 연결은 바운드 메서드 규칙을 따른다 (람다 좀비 방지)
        self.pres_converter.sig_pres_range_changed.connect(self.handle_pres_converter_changed)

    def additional_param_settings(self):
        # Actual Pressure 는 MainWin compound 폴링이 갱신하므로 읽기 등록하지 않는다
        self.act_pres_param = self.param_manager.get_by_full_path("Pressure Control.Basic.Actual Pressure")

        # 센서 1/2 압력은 이 창이 직접 주기 읽기 (refresh 후 유휴 모니터링)
        self.sens1_pres_param = self.param_manager.get_by_full_path("Sensor.Sensor 1.Basic.Actual Pressure Value")
        self.param_worker.add_read_param_ptr(self.sens1_pres_param)

        self.sens2_pres_param = self.param_manager.get_by_full_path("Sensor.Sensor 2.Basic.Actual Pressure Value")
        self.param_worker.add_read_param_ptr(self.sens2_pres_param)

    # ------------------------------------------------------------ GUI 구성
    def _build_chart_central(self):
        t = tokens()

        self.plot_widget = pg.PlotWidget(background=t.panel_bg)
        self.plot_item = self.plot_widget.getPlotItem()
        self.plot_item.layout.setContentsMargins(0, 10, 0, 10)

        # 인터랙션 전부 차단 (부하/오조작 방지) — X/Y 범위는 코드가 제어한다
        self.plot_item.setMenuEnabled(False)
        self.plot_item.hideButtons()
        viewbox = self.plot_item.getViewBox()
        viewbox.setMouseEnabled(False, False)
        viewbox.disableAutoRange(axis=pg.ViewBox.XAxis)
        viewbox.enableAutoRange(axis=pg.ViewBox.YAxis)  # Y 는 가시 구간 기준 자동

        # 축 스타일은 MainChartPanel 과 동일 컨셉 — 축선/눈금은 회색(chart_grid),
        # tick 라벨 색으로 축의 값 종류를 구분한다. 이 창은 pressure 단일 축이므로
        # 왼쪽 축에 pres 색을 쓴다 (메인 차트의 오른쪽 pres 축과 동일 색)
        # 축 라벨은 쓰지 않는다 (메인 차트와 동일) — 라벨이 있으면 pyqtgraph 의
        # 자동 SI 배율이 작은 값에서 눈금을 나누고 "x0.0001" 을 붙인다
        left_axis = self.plot_item.getAxis("left")
        left_axis.setPen(pg.mkPen(t.chart_grid))
        left_axis.setTextPen(pg.mkPen(t.chart_pres_target))

        # X축은 축선만 — 시각 라벨 2개(왼쪽/오른쪽 끝)가 라벨을 대신한다 (메인 차트와 동일)
        bottom_axis = self.plot_item.getAxis("bottom")
        bottom_axis.setStyle(showValues=False, tickLength=0)
        bottom_axis.setPen(pg.mkPen(t.text))

        # Y 그리드(가로선) — 메인 차트와 동일 방식: showGrid 는 눈금(tick)을 전장
        # 선으로 대체해 축 눈금 표시가 사라지므로, 왼쪽 축 major 눈금 위치에
        # 수평선 풀을 직접 그린다
        self._grid_lines = []
        viewbox.sigYRangeChanged.connect(self.handle_yrange_changed)
        viewbox.sigResized.connect(self.handle_viewbox_resized)

        # 곡선 3개 — 색상은 기존 차트 토큰과 일관되게: 제어 압력=빨강(pres 계열),
        # Sensor 1=파랑, Sensor 2=초록. 범례는 좌측 사이드 패널의 체크박스가
        # 겸한다 (MainChartPanel 컨셉)
        self._curves = {
            _ROW_ACT: self.plot_item.plot(pen=pg.mkPen(t.chart_pres_target, width=2)),
            _ROW_SENS1: self.plot_item.plot(pen=pg.mkPen(t.chart_posi_target, width=1)),
            _ROW_SENS2: self.plot_item.plot(pen=pg.mkPen(t.log_rx, width=1)),
        }

        # 차트 밑: 시각 라벨 행 + [X Range 콤보] 행
        self.lbl_x_left = BaseLabel("-")
        self.lbl_x_right = BaseLabel("-")

        time_row = QHBoxLayout()
        time_row.setContentsMargins(0, 0, 0, 0)
        time_row.setSpacing(0)
        time_row.addWidget(self.lbl_x_left)
        time_row.addStretch()
        time_row.addWidget(self.lbl_x_right)

        self.x_window_widget = ReadWriteEnumValueWidget(
            enum_class=p_enum.ChartXWindowEnum, label_text="X Range", label_width=55)
        self.x_window_widget.setFixedWidth(180)
        self.x_window_widget.set_value(self._x_window_sec)
        self.x_window_widget.commit()
        self.x_window_widget.sig_edited_by_user.connect(self.on_selected_x_window)

        control_row = QHBoxLayout()
        control_row.setContentsMargins(0, 5, 0, 5)
        control_row.setSpacing(5)
        control_row.addWidget(self.x_window_widget)
        control_row.addStretch()

        # 차트 열: [차트 | 시각 라벨 | X Range 행]
        chart_area = QVBoxLayout()
        chart_area.setContentsMargins(5, 0, 5, 0)
        chart_area.setSpacing(0)
        chart_area.addWidget(self.plot_widget, 1)
        chart_area.addLayout(time_row)
        chart_area.addLayout(control_row)

        # [사이드 패널(Legend/Range) | 차트 열] — MainChartPanel 배치 컨셉
        central = QWidget(self)
        layout = QHBoxLayout(central)
        layout.setContentsMargins(10, 10, 10, 5)
        layout.setSpacing(0)
        layout.addLayout(self._build_side_column())
        layout.addLayout(chart_area, 1)

        # ParamWin 의 폴더 카드 스크롤 영역은 이 창에서 쓰지 않으므로 차트로 교체.
        # content_widget 재지정으로 handle_changed_working 의 잠금 대상도 차트가 된다
        old_central = self.takeCentralWidget()
        old_central.deleteLater()
        self.setCentralWidget(central)
        self.content_widget = central

    def _build_side_column(self):
        """차트 왼쪽의 설정 열: [Legend 패널(체크박스) + Range 패널(모드/Min/Max)].

        MainChartPanel 의 사이드 열과 동일 컨셉 — 체크박스가 범례를 겸하고
        (라벨 색 = 곡선 색), 컨트롤은 전부 즉시 적용이다. 상태는 창 로컬."""
        t = tokens()

        column = QVBoxLayout()
        column.setContentsMargins(0, 0, 0, 0)
        column.setSpacing(0)

        legend_panel = PanelWidget(title="Pres. Legends")
        legend_panel.setFixedWidth(_SIDE_WIDTH)
        column.addWidget(legend_panel)

        self._checkboxes = {}
        for row, label, color in ((_ROW_ACT, "Actual Pres", t.chart_pres_target),
                                  (_ROW_SENS1, "Sensor 1", t.chart_posi_target),
                                  (_ROW_SENS2, "Sensor 2", t.log_rx)):
            checkbox = BaseCheckBox(label)
            checkbox.set_colors(text=color)
            checkbox.setChecked(True)
            legend_panel.add_widget(checkbox)
            self._checkboxes[row] = checkbox

        self._checkboxes[_ROW_ACT].sig_edited_by_user.connect(self.on_clicked_act_checkbox)
        self._checkboxes[_ROW_SENS1].sig_edited_by_user.connect(self.on_clicked_sens1_checkbox)
        self._checkboxes[_ROW_SENS2].sig_edited_by_user.connect(self.on_clicked_sens2_checkbox)

        range_panel = PanelWidget(title="Pres. Range")
        range_panel.setFixedWidth(_SIDE_WIDTH)
        column.addWidget(range_panel, 1)

        self.range_mode_widget = ReadWriteEnumValueWidget(
            enum_class=p_enum.ChartRangeModeEnum, label_text="Mode", is_vertical_mode=True)
        range_panel.add_widget(self.range_mode_widget)

        self.range_min_widget = ReadWriteFloatValueWidget(label_text="Min", is_vertical_mode=True)
        self.range_max_widget = ReadWriteFloatValueWidget(label_text="Max", is_vertical_mode=True)
        for widget in (self.range_min_widget, self.range_max_widget):
            widget.set_range(-3.4028235e+38, 3.4028235e+38)  # float32 전 범위
            # Custom 모드에서만 편집 가능
            widget.reg_enable_condition(self.range_mode_widget, [p_enum.ChartRangeModeEnum.CUSTOM.value])
            range_panel.add_widget(widget)

        self._sync_range_widgets()

        self.range_mode_widget.sig_edited_by_user.connect(self.on_edited_range_widget)
        self.range_min_widget.sig_edited_by_user.connect(self.on_edited_range_widget)
        self.range_max_widget.sig_edited_by_user.connect(self.on_edited_range_widget)

        return column

    def _sync_range_widgets(self):
        self.range_mode_widget.set_value(self._range_mode)
        self.range_mode_widget.commit()

        for widget, value in ((self.range_min_widget, self._range_min),
                              (self.range_max_widget, self._range_max)):
            widget.set_decimals(self.local_setting.pres_decimal_places)
            widget.set_value(value)
            widget.commit()
            # set_value 가 setEnabled(True) 로 복구하므로 Custom 조건을 다시 평가한다
            widget.on_enable_condition_changed()

    # ------------------------------------------------------------ 샘플링
    def handle_sample_timer_timeout(self):
        now = time.time()
        if self._t0 is None:
            self._t0 = now

        # 이중 버퍼 압축 — 뒤쪽 절반이 가득 차면 최근 구간을 앞으로 복사
        capacity2 = self._buf.shape[1]
        if self._end == capacity2:
            self._buf[:, :_CAPACITY] = self._buf[:, capacity2 - _CAPACITY:capacity2]
            self._end = _CAPACITY

        i = self._end
        self._buf[_ROW_TIME, i] = now - self._t0
        self._buf[_ROW_ACT, i] = self._to_plot(
            self.pres_converter.convert_iface_pres_to_dp_pres(self.act_pres_param.value, PresConvertType.AUTO)
            if self.act_pres_param is not None else None)
        self._buf[_ROW_SENS1, i] = self._to_plot(
            self.pres_converter.convert_iface_pres_to_dp_pres(self.sens1_pres_param.value, PresConvertType.SENSOR1)
            if self.sens1_pres_param is not None else None)
        self._buf[_ROW_SENS2, i] = self._to_plot(
            self.pres_converter.convert_iface_pres_to_dp_pres(self.sens2_pres_param.value, PresConvertType.SENSOR2)
            if self.sens2_pres_param is not None else None)

        self._end += 1
        self._size = min(self._size + 1, _CAPACITY)

        self._redraw()

    @staticmethod
    def _to_plot(value):
        # 변환 불가(값 미수신/컨버터 미준비)는 NaN — connect="finite" 로 선이 끊겨 표시된다
        return np.nan if value is None else value

    # ------------------------------------------------------------ 그리기
    def _visible_slice(self):
        """X 시간창에 들어오는 버퍼 구간 (vis_start, end, t_end). 데이터 없으면 None."""
        if self._size == 0:
            return None

        start = self._end - self._size
        x = self._buf[_ROW_TIME]
        t_end = x[self._end - 1]

        vis_start = start + int(np.searchsorted(x[start:self._end], t_end - self._x_window_sec))
        return vis_start, self._end, t_end

    def _set_curve_data(self, row, visible):
        vis_start, end, _ = visible
        self._curves[row].setData(
            self._buf[_ROW_TIME, vis_start:end],
            self._buf[row, vis_start:end], connect="finite")

    def _redraw(self):
        visible = self._visible_slice()
        if visible is None:
            return

        for row in self._curves:
            if self._curve_enabled[row]:
                self._set_curve_data(row, visible)  # 꺼진 곡선은 그리지 않는다 (켤 때 1회 갱신)

        # 항상 최신 샘플이 오른쪽 끝 — 데이터가 창을 채우기 전에도 슬라이딩한다
        t_end = visible[2]
        self.plot_item.getViewBox().setXRange(t_end - self._x_window_sec, t_end, padding=0)
        self._update_time_labels(t_end)

    def _update_time_labels(self, t_end):
        if self._t0 is None:
            self.lbl_x_left.setText("-")
            self.lbl_x_right.setText("-")
            return

        right_epoch = max(0.0, self._t0 + t_end)
        left_epoch = max(0.0, right_epoch - self._x_window_sec)
        self.lbl_x_left.setText(time.strftime("%H:%M:%S", time.localtime(left_epoch)))
        self.lbl_x_right.setText(time.strftime("%H:%M:%S", time.localtime(right_epoch)))

    def clear_chart(self):
        self._end = 0
        self._size = 0
        self._t0 = None
        for curve in self._curves.values():
            curve.setData([], [])
        self._update_time_labels(0.0)

    # ------------------------------------------------------------ 이벤트
    def on_selected_x_window(self):
        seconds = self.x_window_widget.get_value()
        if seconds is not None:
            self._x_window_sec = seconds
            self._redraw()  # 창이 넓어지면 이전에 안 그리던 구간까지 다시 그린다

        # 창 로컬 즉시 적용 설정 — 편집 확정 즉시 commit 해 dirty 마커를 남기지 않는다
        # (Apply 로 쓰는 값이 아니므로. MainChartPanel 은 설정 변경 시그널 재동기화가 같은 역할)
        self.x_window_widget.commit()

    def handle_changed_connection_info(self, info: str):
        super().handle_changed_connection_info(info)

        # 연결 중에만 샘플링 — 끊긴 동안 마지막 값이 평평한 선으로 이어지는 것 방지
        if self.sample_timer is None:
            return

        if info:
            self.sample_timer.start()
        else:
            self.sample_timer.stop()

    def handle_pres_converter_changed(self):
        # 표시 단위/스케일이 바뀌면 과거 데이터와 단위가 섞이므로 비우고 다시 시작한다.
        # Full 범위 상한/소수 자릿수도 컨버터에 따라 달라지므로 함께 재적용한다
        self.clear_chart()
        self._sync_range_widgets()
        self._apply_y_range()

    # ------------------------------------------------------------ 곡선 on/off
    def _toggle_curve(self, row):
        enabled = self._checkboxes[row].isChecked()
        self._curve_enabled[row] = enabled
        self._curves[row].setVisible(enabled)

        # 꺼져 있는 동안 setData 를 생략했으므로 켜는 순간 한 번 따라잡는다
        if enabled:
            visible = self._visible_slice()
            if visible is not None:
                self._set_curve_data(row, visible)

    def on_clicked_act_checkbox(self):
        self._toggle_curve(_ROW_ACT)

    def on_clicked_sens1_checkbox(self):
        self._toggle_curve(_ROW_SENS1)

    def on_clicked_sens2_checkbox(self):
        self._toggle_curve(_ROW_SENS2)

    # ------------------------------------------------------------ Y 범위
    def on_edited_range_widget(self, _widget):
        # 편집된 위젯만이 아니라 그룹 전체를 반영해도 무해하다 (같은 값 대입은 no-op)
        mode = self.range_mode_widget.get_value()
        if mode is not None:
            self._range_mode = mode

        range_min = self.range_min_widget.get_value()
        if range_min is not None:
            self._range_min = range_min

        range_max = self.range_max_widget.get_value()
        if range_max is not None:
            self._range_max = range_max

        # 창 로컬 즉시 적용 설정 — 편집 확정 즉시 commit 해 dirty 마커를 남기지 않는다
        self.range_mode_widget.commit()
        self.range_min_widget.commit()
        self.range_max_widget.commit()

        self._apply_y_range()

    def _apply_y_range(self):
        viewbox = self.plot_item.getViewBox()

        if self._range_mode == p_enum.ChartRangeModeEnum.AUTO.value:
            # Auto 는 '화면(시간창)에 보이는 데이터' 기준 — setData 를 가시 구간만
            # 전달하므로 pyqtgraph 오토레인지가 자연히 그 기준이 된다
            viewbox.enableAutoRange(axis=pg.ViewBox.YAxis)
            return

        viewbox.disableAutoRange(axis=pg.ViewBox.YAxis)

        if self._range_mode == p_enum.ChartRangeModeEnum.FULL.value:
            full_max = self.pres_converter.get_dp_max_pres(PresConvertType.AUTO)
            y_min, y_max = 0.0, full_max if full_max is not None else 100.0  # 컨버터 미준비 시 대체값
        else:  # CUSTOM
            y_min, y_max = self._range_min, self._range_max

        # min >= max 로 설정된 경우 Qt 경고/이상 표시 방지용 최소 간격 확보
        if y_max <= y_min:
            y_max = y_min + 1.0

        viewbox.setYRange(y_min, y_max, padding=0)

    # ------------------------------------------------------------ Y 그리드
    def handle_yrange_changed(self, *args):
        self._update_grid_lines()

    def handle_viewbox_resized(self):
        # 눈금 간격은 픽셀 높이에도 의존하므로 리사이즈 시 그리드도 재배치
        self._update_grid_lines()

    def _update_grid_lines(self):
        # MainChartPanel._update_grid_lines 와 동일 방식 — 왼쪽 축이 실제로 쓰는
        # 눈금 계산을 그대로 빌려 major 위치에만 수평선을 놓는다
        viewbox = self.plot_item.getViewBox()
        y_min, y_max = viewbox.state["viewRange"][1]
        height = max(1, int(viewbox.height()))

        levels = self.plot_item.getAxis("left").tickValues(y_min, y_max, height)
        values = levels[0][1] if levels else []

        # 수평선 풀 재사용 — 부족하면 생성, 남으면 숨김
        while len(self._grid_lines) < len(values):
            pen = pg.mkPen(pg.mkColor(tokens().chart_grid + "78"), width=1)  # 반투명 회색
            line = pg.InfiniteLine(angle=0, movable=False, pen=pen)
            line.setZValue(-10)  # 곡선 뒤에 깔리게
            viewbox.addItem(line, ignoreBounds=True)  # Auto 범위 계산에 미포함
            self._grid_lines.append(line)

        for line, value in zip(self._grid_lines, values):
            line.setPos(value)
            line.setVisible(True)
        for line in self._grid_lines[len(values):]:
            line.setVisible(False)
