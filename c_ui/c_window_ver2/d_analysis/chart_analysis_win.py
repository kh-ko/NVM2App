"""차트 분석 윈도우 (Capture / CSV 뷰어).

데이터 소스 두 가지:
- Capture: 메인 차트 패널이 캡처 시점에 화면에 표시하던 구간(dp 값)을 넘겨준다.
- Open CSV: ChartCSVFileHelper 가 저장한 CSV 파일(들)을 읽어 표시한다.
  파싱/병합/정렬은 헬퍼의 read_csv_files() 가 담당하고 (포맷 소유자),
  이 창은 단위 변환과 표시만 맡는다.

압력 단위:
- 내부 저장은 캐노니컬 단위(Torr)로 통일한다 — 캡처/CSV 값을 로드 시점에
  각 행의 원 단위에서 캐노니컬로 변환해 두므로, CSV 에 단위가 섞여 있어도
  일관된 시리즈가 된다.
- 상단 Pres Unit 콤보로 표시 단위를 바꾸면 캐노니컬 -> 선택 단위의
  gain/offset 한 번으로 전체를 재표시한다 (PresConverterManager 의 공개
  단위 환산 API get_unit_conversion — 통신 상태와 무관한 정적 계산).

라이브러리는 메인과 같은 pyqtgraph 를 쓰되 분석용으로 인터랙션을 전부 연다.
(무료 대안 검토 결과 — 줌/팬/크로스헤어/영역 통계 같은 대화형 분석은
pyqtgraph 가 적합하고, matplotlib 은 미설치 의존성이라 빌드 부담만 는다)

분석 기능:
- 마우스 줌/팬 (X 링크된 이중 Y축 — 좌 position %, 우 pressure 표시 단위)
- X축 눈금/판독은 실제 시각 기반 (줌이 깊어지면 소수점 초까지)
- Cursor 패널: 커서 위치의 시각(ms)과 4개 시리즈 값 테이블
- Region 패널: 드래그로 잡은 구간의 시리즈별 Min/Avg/Max 테이블

이 윈도우는 스냅샷 데이터만 다룬다 — 싱글턴 시그널에 연결하지 않으므로
WA_DeleteOnClose 로 파괴되어도 좀비 연결 문제가 없다.
"""

import os
import time

import numpy as np
import pyqtgraph as pg

from PySide6.QtCore import Qt
from PySide6.QtGui import QBrush, QColor, QFontMetrics
from PySide6.QtWidgets import (QAbstractItemView, QFileDialog, QHBoxLayout, QHeaderView,
                               QMainWindow, QMessageBox, QTableWidget, QTableWidgetItem,
                               QVBoxLayout, QWidget)

from b_core.b_datatype import param_enum as p_enum
from b_core.f_helper.chart_csv_file_helper import ChartCSVFileHelper

from c_ui.a_converter.pressure_converter_manager import PresConverterManager
from c_ui.b_control_ver2.a_theme.tokens import tokens
from c_ui.b_control_ver2.b_base.labels import BaseLabel
from c_ui.b_control_ver2.b_base.toolbars import BaseToolBar
from c_ui.b_control_ver2.b_base.containers import PanelWidget
from c_ui.b_control_ver2.c_values.read_write_values import ReadWriteEnumValueWidget

_SERIES = ("posi_actual", "posi_target", "pres_actual", "pres_target")
_PRES_SERIES = ("pres_actual", "pres_target")
_SERIES_LABELS = {"posi_actual": "Pos.Act", "posi_target": "Pos.Tgt",
                  "pres_actual": "Pres.Act", "pres_target": "Pres.Tgt"}

# 내부 저장 캐노니컬 압력 단위
_CANONICAL_UNIT = p_enum.SensUnitEnum.TORR.value


class _TimeAxisItem(pg.AxisItem):
    """X축 눈금을 상대 초 대신 실제 시각(hh:mm:ss)으로 표시하는 축.

    데이터의 X 값은 여전히 상대 초(시작=0)이고, 여기에 시작 epoch 를 더해
    라벨만 시각으로 변환한다 — 크로스헤어/영역 통계 등 나머지 로직은
    상대 초 좌표계를 그대로 쓴다. 줌이 깊어지면(눈금 간격 < 1s) 소수점
    초까지 붙인다."""

    def __init__(self, orientation):
        super().__init__(orientation)
        self._start_epoch = None  # 초 단위 epoch (None 이면 상대 초 그대로 표시)

    def set_start_epoch(self, start_epoch_sec):
        self._start_epoch = start_epoch_sec
        self.picture = None
        self.update()

    def tickStrings(self, values, scale, spacing):
        if self._start_epoch is None:
            return super().tickStrings(values, scale, spacing)

        strings = []
        for value in values:
            epoch = self._start_epoch + value
            if epoch < 0:  # Windows localtime 은 음수 epoch 에서 OSError
                strings.append("")
                continue

            text = time.strftime("%H:%M:%S", time.localtime(epoch))
            if spacing < 1.0:  # 초 미만 줌 — 소수점 초 표시
                decimals = 3 if spacing < 0.1 else 1
                text += f"{epoch % 1:.{decimals}f}"[1:]  # "0.523" -> ".523"

            strings.append(text)

        return strings


class ChartAnalysisWin(QMainWindow):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Chart Analysis")
        self.resize(950, 620)

        self.pres_converter = PresConverterManager()  # 단위 환산표 재사용 목적

        # 데이터 (rebase: times[0] == 0.0). 압력은 캐노니컬(Torr) 보관 + 표시용 별도
        self._times = np.empty(0)
        self._series = {name: np.empty(0) for name in _SERIES}          # 표시 단위 기준
        self._pres_canonical = {name: np.empty(0) for name in _PRES_SERIES}
        self._start_epoch_ms = None
        self._display_unit = _CANONICAL_UNIT

        self.toolbar = BaseToolBar(self)
        self.addToolBar(Qt.TopToolBarArea, self.toolbar)
        self.toolbar.add_action("Open CSV", self.on_clicked_open_csv)
        self.toolbar.add_action("Fit View", self.on_clicked_fit_view)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(5)

        # 상단: 데이터 출처 + 압력 표시 단위 선택
        self.lbl_source = BaseLabel("-")

        self.pres_unit_widget = ReadWriteEnumValueWidget(enum_class=p_enum.SensUnitEnum, label_text="Pres Unit", label_width=80)
        # 내부 BaseComboBox 는 가로 Ignored 정책이라 콤보 몫의 폭 힌트가 0 으로
        # 계산된다 — 최소 폭을 명시하지 않으면 stretch 없는 배치에서 콤보가 사라진다
        self.pres_unit_widget.setMinimumWidth(240)
        self.pres_unit_widget.sig_edited_by_user.connect(self.on_edited_pres_unit)

        info_row = QHBoxLayout()
        info_row.setContentsMargins(0, 0, 0, 0)
        info_row.addWidget(self.lbl_source, 1)
        info_row.addWidget(self.pres_unit_widget)
        main_layout.addLayout(info_row)

        self._build_chart()
        main_layout.addWidget(self.plot_widget, 1)

        # 하단: Cursor / Region Stats 패널 (각각 QTable 로 정리)
        bottom_row = QHBoxLayout()
        bottom_row.setContentsMargins(0, 0, 0, 0)
        bottom_row.setSpacing(10)
        bottom_row.addWidget(self._build_cursor_panel(), 1)
        bottom_row.addWidget(self._build_region_panel(), 1)
        bottom_row.addStretch()
        main_layout.addLayout(bottom_row)

    # ------------------------------------------------------------ 차트 구성
    def _build_chart(self):
        t = tokens()

        # X축 눈금은 CSV/캡처의 실제 시각(hh:mm:ss)으로 표시한다
        self._time_axis = _TimeAxisItem(orientation="bottom")

        self.plot_widget = pg.PlotWidget(background=t.panel_bg, axisItems={"bottom": self._time_axis})
        self.plot_item = self.plot_widget.getPlotItem()
        self.plot_item.layout.setContentsMargins(0, 10, 0, 10)
        self.plot_item.setMenuEnabled(False)
        self.plot_item.hideButtons()

        posi_vb = self.plot_item.getViewBox()

        # 오른쪽 축 = pressure 전용 ViewBox (메인 차트와 동일 구성, 단 마우스는 연다)
        self.pres_viewbox = pg.ViewBox()
        self.plot_item.showAxis("right")
        self.plot_item.scene().addItem(self.pres_viewbox)
        self.plot_item.getAxis("right").linkToView(self.pres_viewbox)
        self.pres_viewbox.setXLink(posi_vb)
        posi_vb.sigResized.connect(self.handle_posi_viewbox_resized)

        for axis_name, color in (("left", t.chart_posi_target), ("right", t.chart_pres_target)):
            axis = self.plot_item.getAxis(axis_name)
            axis.setPen(pg.mkPen(t.chart_grid))
            axis.setTextPen(pg.mkPen(color))

        # 곡선 4개 — 메인 차트와 같은 색/선 스타일 (target 은 점선)
        self._curves = {
            "posi_actual": pg.PlotDataItem(pen=pg.mkPen(t.chart_posi_target, width=1)),
            "posi_target": pg.PlotDataItem(pen=pg.mkPen(t.chart_posi_target, width=1, style=Qt.DashLine)),
            "pres_actual": pg.PlotDataItem(pen=pg.mkPen(t.chart_pres_target, width=1)),
            "pres_target": pg.PlotDataItem(pen=pg.mkPen(t.chart_pres_target, width=1, style=Qt.DashLine)),
        }
        # 대용량 CSV 대비 — 화면 픽셀당 피크 보존 다운샘플링 + 화면 밖 클리핑.
        # 수백만 포인트에서도 페인트 비용이 화면 폭 기준으로 제한된다 (소량 데이터엔 무영향)
        for curve in self._curves.values():
            curve.setDownsampling(auto=True, method="peak")
            curve.setClipToView(True)

        self.plot_item.addItem(self._curves["posi_actual"])
        self.plot_item.addItem(self._curves["posi_target"])
        self.pres_viewbox.addItem(self._curves["pres_actual"])
        self.pres_viewbox.addItem(self._curves["pres_target"])

        # 영역 통계용 Region (X 구간) — 데이터 로드 시 전체 구간으로 초기화된다.
        # [주의] 경계선의 호버/드래그 히트박스 폭은 pen 폭에 비례한다
        # (InfiniteLine._computeBoundingRect: (max(pen,hoverPen)/2 + 1) px) —
        # 기본 폭 1이면 ±1.5px 라 정확히 선 위에 올려야만 호버가 잡히므로 넓힌다
        self.region = pg.LinearRegionItem(movable=True)
        for line in self.region.lines:
            line.setPen(pg.mkPen(t.chart_grid, width=3))
            line.setHoverPen(pg.mkPen(t.danger, width=5))
        self.region.setZValue(-5)
        posi_vb.addItem(self.region, ignoreBounds=True)
        self.region.sigRegionChanged.connect(self.handle_region_changed)

        # 크로스헤어 (세로선 + Cursor 패널 테이블 갱신)
        self._crosshair = pg.InfiniteLine(angle=90, movable=False,
                                          pen=pg.mkPen(t.chart_grid, width=1))
        self._crosshair.setZValue(10)
        self._crosshair.setVisible(False)
        posi_vb.addItem(self._crosshair, ignoreBounds=True)
        self._mouse_proxy = pg.SignalProxy(self.plot_widget.scene().sigMouseMoved,
                                           rateLimit=30, slot=self.handle_mouse_moved)

    def _make_series_table(self, columns):
        """시리즈 4행 x 지정 컬럼의 읽기 전용 테이블 (세로 헤더는 시리즈 색)."""
        t = tokens()
        colors = {"posi_actual": t.chart_posi_target, "posi_target": t.chart_posi_target,
                  "pres_actual": t.chart_pres_target, "pres_target": t.chart_pres_target}

        table = QTableWidget(len(_SERIES), len(columns))
        table.setHorizontalHeaderLabels(columns)
        table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        table.setSelectionMode(QAbstractItemView.NoSelection)
        table.setFocusPolicy(Qt.NoFocus)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        table.verticalHeader().setDefaultSectionSize(22)

        for row, name in enumerate(_SERIES):
            header_item = QTableWidgetItem(_SERIES_LABELS[name])
            header_item.setForeground(QBrush(QColor(colors[name])))
            table.setVerticalHeaderItem(row, header_item)

            for col in range(len(columns)):
                table.setItem(row, col, QTableWidgetItem("-"))

        # 4행이 딱 보이는 고정 높이 (스크롤 없음)
        height = (table.horizontalHeader().height()
                  + table.verticalHeader().defaultSectionSize() * len(_SERIES)
                  + table.frameWidth() * 2)
        table.setFixedHeight(height + 2)
        return table

    def _build_cursor_panel(self):
        panel = PanelWidget(title="Cursor")

        self.lbl_cursor_time = BaseLabel("-")
        panel.add_widget(self.lbl_cursor_time)

        self.cursor_table = self._make_series_table(["Value"])
        panel.add_widget(self.cursor_table)
        return panel

    def _build_region_panel(self):
        panel = PanelWidget(title="Region Stats")

        self.lbl_region_span = BaseLabel("-")
        panel.add_widget(self.lbl_region_span)

        self.region_table = self._make_series_table(["Min", "Avg", "Max"])
        panel.add_widget(self.region_table)
        return panel

    # ------------------------------------------------------------ 데이터 주입
    def set_capture_data(self, t0_ms, times, posi_act, posi_tgt, pres_act, pres_tgt, pres_unit):
        """메인 차트 패널의 캡처 스냅샷을 표시한다.

        times 는 패널 t0 기준 상대 초, pres_* 는 캡처 시점 표시 단위(pres_unit,
        SensUnitEnum 값) 기준이다."""
        gain, offset = self.pres_converter.get_unit_conversion(pres_unit, _CANONICAL_UNIT)

        start_epoch_ms = t0_ms + times[0] * 1000.0 if len(times) else t0_ms
        self._set_data(times - (times[0] if len(times) else 0.0),
                       np.asarray(posi_act, dtype=float), np.asarray(posi_tgt, dtype=float),
                       np.asarray(pres_act, dtype=float) * gain + offset,
                       np.asarray(pres_tgt, dtype=float) * gain + offset,
                       start_epoch_ms, display_unit=pres_unit)

        stamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(start_epoch_ms / 1000.0))
        self.lbl_source.setText(f"Capture @ {stamp}")

    def load_csv_files(self, paths):
        """기록 CSV(들)를 읽어 표시한다 — 파싱/병합/정렬은 포맷 소유자인
        ChartCSVFileHelper.read_csv_files() 몫이고, 이 창은 행마다 기록된
        단위를 캐노니컬로 변환해 일관된 시리즈로 만든 뒤 표시만 한다."""
        (timestamps, posi_act, posi_tgt,
         pres_act, pres_tgt, unit_codes) = ChartCSVFileHelper.read_csv_files(paths)

        start_epoch_ms = timestamps[0]

        # 행 단위 -> 캐노니컬 변환 (고유 단위별로 벡터화. 단위 미상(-1)은 캐노니컬로 간주)
        for unit in np.unique(unit_codes):
            from_unit = _CANONICAL_UNIT if unit < 0 else int(unit)
            gain, offset = self.pres_converter.get_unit_conversion(from_unit, _CANONICAL_UNIT)
            mask = unit_codes == unit
            pres_act[mask] = pres_act[mask] * gain + offset
            pres_tgt[mask] = pres_tgt[mask] * gain + offset

        # 표시 단위 초기값은 첫 행의 단위
        first_unit = int(unit_codes[0])
        self._set_data((timestamps - start_epoch_ms) / 1000.0,
                       posi_act, posi_tgt, pres_act, pres_tgt,
                       start_epoch_ms,
                       display_unit=_CANONICAL_UNIT if first_unit < 0 else first_unit)

        names = ", ".join(os.path.basename(p) for p in paths)
        self.lbl_source.setText(f"CSV: {names}")

    def _set_data(self, times, posi_act, posi_tgt, pres_act_canonical, pres_tgt_canonical,
                  start_epoch_ms, display_unit):
        self._times = np.asarray(times, dtype=float)
        self._series["posi_actual"] = np.asarray(posi_act, dtype=float)
        self._series["posi_target"] = np.asarray(posi_tgt, dtype=float)
        self._pres_canonical["pres_actual"] = np.asarray(pres_act_canonical, dtype=float)
        self._pres_canonical["pres_target"] = np.asarray(pres_tgt_canonical, dtype=float)
        self._start_epoch_ms = start_epoch_ms

        # X축 눈금 라벨을 실제 시각으로 변환할 기준 시각
        self._time_axis.set_start_epoch(start_epoch_ms / 1000.0 if start_epoch_ms is not None else None)

        for name in ("posi_actual", "posi_target"):
            self._curves[name].setData(self._times, self._series[name], connect="finite")

        # 압력 표시 단위 적용 (위젯 동기화 포함) + Fit
        self._display_unit = display_unit
        self.pres_unit_widget.set_value(display_unit)
        self.pres_unit_widget.commit()
        self._refresh_pres_display()
        self.on_clicked_fit_view()

    # ------------------------------------------------------------ 압력 표시 단위
    def on_edited_pres_unit(self, _widget):
        unit = self.pres_unit_widget.get_value()
        self.pres_unit_widget.commit()
        if unit is None:
            return

        self._display_unit = unit
        self._refresh_pres_display()

        # 단위가 바뀌면 압력 스케일이 달라지므로 압력축만 다시 맞춘다
        self.pres_viewbox.enableAutoRange(axis=pg.ViewBox.YAxis)

    def _refresh_pres_display(self):
        gain, offset = self.pres_converter.get_unit_conversion(_CANONICAL_UNIT, self._display_unit)

        for name in _PRES_SERIES:
            self._series[name] = self._pres_canonical[name] * gain + offset
            self._curves[name].setData(self._times, self._series[name], connect="finite")

        # 테이블 세로 헤더에 현재 단위 표기
        unit_desc = p_enum.SensUnitEnum.get_desc(self._display_unit)
        for table in (self.cursor_table, self.region_table):
            for row, name in enumerate(_SERIES):
                label = _SERIES_LABELS[name]
                if name in _PRES_SERIES:
                    label += f" ({unit_desc})"
                elif name.startswith("posi"):
                    label += " (%)"
                table.verticalHeaderItem(row).setText(label)

        self._update_pres_axis_width()
        self.handle_region_changed()

    # ------------------------------------------------------------ 툴바
    def on_clicked_open_csv(self):
        paths, _ = QFileDialog.getOpenFileNames(self, "Open Recorded CSV", "", "CSV Files (*.csv)")
        if not paths:
            return

        try:
            self.load_csv_files(paths)
        except Exception as error:
            QMessageBox.warning(self, "Open CSV", f"Failed to load:\n{error}")

    def on_clicked_fit_view(self):
        if len(self._times) == 0:
            return

        self.plot_item.getViewBox().autoRange()
        self.pres_viewbox.enableAutoRange(axis=pg.ViewBox.YAxis)

        # Region 은 전체 구간으로 초기화 (통계도 함께 갱신된다)
        self.region.setRegion((float(self._times[0]), float(self._times[-1])))

        # 경계선의 호버 히트박스 캐시를 새 뷰 변환 기준으로 강제 갱신 (안전장치)
        for line in self.region.lines:
            line.viewTransformChanged()

    # ------------------------------------------------------------ 분석 표시
    @staticmethod
    def _fmt_value(value):
        return "-" if value != value else f"{value:.6g}"

    def _fmt_wall_ms(self, t_rel):
        if self._start_epoch_ms is None:
            return "-"

        total_ms = max(0, int(round(self._start_epoch_ms + t_rel * 1000.0)))
        return time.strftime("%H:%M:%S", time.localtime(total_ms // 1000)) + f".{total_ms % 1000:03d}"

    def handle_region_changed(self):
        if len(self._times) == 0:
            return

        x_lo, x_hi = self.region.getRegion()
        self.lbl_region_span.setText(f"{self._fmt_wall_ms(x_lo)}  ~  {self._fmt_wall_ms(x_hi)}")

        mask = (self._times >= x_lo) & (self._times <= x_hi)
        for row, name in enumerate(_SERIES):
            values = self._series[name][mask] if mask.any() else np.empty(0)

            if len(values) == 0 or np.all(np.isnan(values)):
                stats = ("-", "-", "-")
            else:
                stats = (self._fmt_value(np.nanmin(values)),
                         self._fmt_value(np.nanmean(values)),
                         self._fmt_value(np.nanmax(values)))

            for col, text in enumerate(stats):
                self.region_table.item(row, col).setText(text)

    def handle_mouse_moved(self, event):
        if len(self._times) == 0:
            return

        pos = event[0]
        posi_vb = self.plot_item.getViewBox()
        if not self.plot_item.sceneBoundingRect().contains(pos):
            self._crosshair.setVisible(False)
            return

        x = posi_vb.mapSceneToView(pos).x()
        index = int(np.clip(np.searchsorted(self._times, x), 0, len(self._times) - 1))

        self._crosshair.setPos(self._times[index])
        self._crosshair.setVisible(True)

        self.lbl_cursor_time.setText(self._fmt_wall_ms(self._times[index]))
        for row, name in enumerate(_SERIES):
            self.cursor_table.item(row, 0).setText(self._fmt_value(self._series[name][index]))

    # ------------------------------------------------------------ 축/지오메트리
    def _update_pres_axis_width(self):
        # 보조 ViewBox 링크 축은 자동 폭 확장이 안 되므로 데이터 범위 기준으로 직접 지정
        pres = np.concatenate([self._series["pres_actual"], self._series["pres_target"]])
        if len(pres) == 0 or np.all(np.isnan(pres)):
            return

        sample = max((f"{v:.6g}" for v in (np.nanmin(pres), np.nanmax(pres))), key=len)
        width = QFontMetrics(self.plot_widget.font()).horizontalAdvance(sample)
        self.plot_item.getAxis("right").setWidth(width + 14)

    def handle_posi_viewbox_resized(self):
        self.pres_viewbox.setGeometry(self.plot_item.getViewBox().sceneBoundingRect())
