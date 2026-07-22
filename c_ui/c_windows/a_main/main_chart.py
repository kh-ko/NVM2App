from PySide6.QtCore import QTimer
from typing import List
import numpy as np

import pyqtgraph as pg
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout
from PySide6.QtCore import Qt, QDateTime

from b_core.b_datatype.compound_data import CompoundData
from b_core.b_datatype.general_enum import MainChartTimeRangeEnum
from b_core.c_manager.local_setting_manager import LocalSettingManager

from c_ui.a_converter.position_converter_manager import PosiConverterManager
from c_ui.a_converter.pressure_converter_manager import PresConverterManager

from c_ui.b_control_packet.controls_with_label.l_enum_rw_widget import LEnumReadWriteWidget
from c_ui.b_control_packet.controls.my_labeldescription import MyLabelDescription

from c_ui.c_windows.a_main.main_chart_setting import MainChartSettingPanel

class MainChart(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.max_points = 60000
        self.ptr = 0
        self.timestamps = np.zeros(self.max_points)
        self.act_posis = np.zeros(self.max_points)
        self.target_posis = np.zeros(self.max_points)
        self.act_press = np.zeros(self.max_points)
        self.target_press = np.zeros(self.max_points)

        self.posi_chart_range_mode = 1
        self.pres_chart_range_mode = 1

        self.local_setting_manager = LocalSettingManager()
        self.posi_converter        = PosiConverterManager()
        self.pres_converter        = PresConverterManager()
        
        # 메인 레이아웃을 좌우(HBox)로 설정
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        self.posi_setting_panel = MainChartSettingPanel("Position", "#0000FF", "#0000FF")
        self.posi_setting_panel.setFixedWidth(150)
        self.posi_setting_panel.set_init_settings(self.local_setting_manager.posi_chart_enable_actual,
                                                self.local_setting_manager.posi_chart_enable_target,
                                                self.local_setting_manager.posi_chart_range_mode,
                                                self.local_setting_manager.posi_chart_range_custom_min,
                                                self.local_setting_manager.posi_chart_range_custom_max,
                                                self.local_setting_manager.posi_decimal_places)
        main_layout.addWidget(self.posi_setting_panel)

        # 차트와 X축 라벨을 담을 왼쪽 VBox 영역
        chart_layout = QVBoxLayout()
        chart_layout.setContentsMargins(0, 10, 0, 0)
        chart_layout.setSpacing(0)
        main_layout.addLayout(chart_layout, stretch=56) # 차트를 넓게 배치
        
        # PyQtGraph 테마 설정
        pg.setConfigOption('background', 'transparent')
        pg.setConfigOption('foreground', 'k')
        pg.setConfigOptions(antialias=False) # 퍼포먼스 향상을 위해 안티앨리어싱 비활성화
        
        # 플롯 위젯 생성 및 기본 X축 할당
        self.time_axis = pg.AxisItem(orientation='bottom')
        self.time_axis.setStyle(showValues=False) # PyQtGraph의 불안정한 내부 렌더링 텍스트를 아예 숨김
        self.time_axis.setHeight(10) # 텍스트가 없으므로 높이를 최소화

        self.plot_widget = pg.PlotWidget(axisItems={'bottom': self.time_axis})
        chart_layout.addWidget(self.plot_widget)
        self.plot_widget.setDownsampling(auto=True, mode='peak')
        self.plot_widget.setClipToView(True)
        
        # 완벽하게 처음과 끝에만 표시될 커스텀 네이티브 라벨
        time_label_layout = QHBoxLayout()
        time_label_layout.setContentsMargins(50, 0, 50, 10) # Y축 너비만큼 여백을 주어 차트 양끝에 맞춤
        
        self.lbl_start_time = MyLabelDescription("00:00:00")
        self.lbl_end_time = MyLabelDescription("00:00:00")
        self.lbl_start_time.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        self.lbl_end_time.setAlignment(Qt.AlignRight | Qt.AlignTop)
        
        time_label_layout.addWidget(self.lbl_start_time)
        time_label_layout.addStretch()
        time_label_layout.addWidget(self.lbl_end_time)
        
        chart_layout.addLayout(time_label_layout)

        self.control_layout = QHBoxLayout()
        self.control_layout.setContentsMargins(50, 0, 50, 10)
        self.time_combobox = LEnumReadWriteWidget(enum_class=MainChartTimeRangeEnum, label_text = "Range", label_width = 40)
        self.time_combobox.setMaximumWidth(150)
        self.time_combobox.set_value(MainChartTimeRangeEnum.SEC_30.value)
        self.time_combobox.commit()
        self.time_combobox.sig_value_changed.connect(self.on_time_range_changed)
        self.control_layout.addWidget(self.time_combobox)
        self.control_layout.addStretch()

        chart_layout.addLayout(self.control_layout)
        
        # 우측 패널 (TimeRange 및 추후 범례/체크박스가 위치할 곳)
        self.pres_setting_panel = MainChartSettingPanel("Pressure", "#FF0000", "#FF0000")
        self.pres_setting_panel.setFixedWidth(150)
        self.pres_setting_panel.set_init_settings(self.local_setting_manager.pres_chart_enable_actual,
                                                self.local_setting_manager.pres_chart_enable_target,
                                                self.local_setting_manager.pres_chart_range_mode,
                                                self.local_setting_manager.pres_chart_range_custom_min,
                                                self.local_setting_manager.pres_chart_range_custom_max,
                                                self.local_setting_manager.pres_decimal_places)
        
        main_layout.addWidget(self.pres_setting_panel) # 우측 패널 추가
        
        # 플롯 위젯 기본 설정 (왼쪽 Y축)
        from PySide6.QtWidgets import QApplication
        base_font = QApplication.font() # 앱 전체 기본 폰트 가져오기
        self.plot_widget.showGrid(x=False, y=True, alpha=0.3)
        self.plot_widget.setMouseEnabled(x=False, y=False) # 줌/팬 비활성화
        self.plot_widget.hideButtons()

        # 폰트 이질감 해소: 앱의 기본 폰트(QLabel 등에서 사용하는 폰트)를 가져와서 동일한 서체를 적용
        from PySide6.QtGui import QFont
        from PySide6.QtWidgets import QApplication
        
        base_font = QApplication.font() # 앱 전체 기본 폰트 가져오기
        self.axis_font = QFont(base_font.family()) # 서체(Family) 일치
        self.axis_font.setPixelSize(12)#  setPointSize(9) # 차트 축에 맞게 사이즈만 살짝 조절 (필요시 수정 가능)
        
        self.plot_widget.getPlotItem().layout.setContentsMargins(20, 0, 20, 0)
        
        self.time_axis.setTickFont(self.axis_font)
        
        # Posi (왼쪽 Y축) 전용 스타일: 파란색 계열 적용
        posi_color = '#0000FF' # 파란색
        label_style_posi = {'color': posi_color, 'font-family': base_font.family(), 'font-size': '12px'}
        # 1. 축의 기둥(Spine)과 기본 펜 색상 설정
        self.plot_widget.getAxis('left').setPen(pg.mkPen(color=posi_color, width=1)) 
        # 2. 숫자(Tick Label) 색상 설정
        self.plot_widget.getAxis('left').setTextPen(posi_color) 
        # 3. 눈금선(Tick Marks) 색상 설정
        self.plot_widget.getAxis('left').setTickPen(pg.mkPen(color='gray', width=1, style=Qt.DotLine)) 
        # 4. 축 라벨 텍스트 설정 (setPen 이후에 해야 색상이 덮어씌워지지 않음)
        self.plot_widget.setLabel('left', 'Position', **label_style_posi)
        self.plot_widget.getAxis('left').setTickFont(self.axis_font)
        self.plot_widget.getAxis('left').enableAutoSIPrefix(False)
        
        # 오른쪽 Y축(Pres) 설정
        self.view_pres = pg.ViewBox()
        self.plot_widget.scene().addItem(self.view_pres)
        self.plot_widget.getAxis('right').linkToView(self.view_pres)
        self.view_pres.setXLink(self.plot_widget)
        self.plot_widget.showAxis('right')
        self.plot_widget.getAxis('right').enableAutoSIPrefix(False)
        
        # Pres (오른쪽 Y축) 전용 스타일: 빨간색 계열 적용
        pres_color = '#FF0000' # 빨간색
        label_style_pres = {'color': pres_color, 'font-family': base_font.family(), 'font-size': '12px'}
        
        # 1. 축의 기둥(Spine)과 기본 펜 색상 설정
        self.plot_widget.getAxis('right').setPen(pg.mkPen(color=pres_color, width=1)) 
        # 2. 숫자(Tick Label) 색상 설정
        self.plot_widget.getAxis('right').setTextPen(pres_color) 
        # 3. 눈금선(Tick Marks) 색상 설정
        self.plot_widget.getAxis('right').setTickPen(pg.mkPen(color='gray', width=1, style=Qt.DotLine)) 
        # 4. 축 라벨 텍스트 설정 (setPen 이후에 해야 색상이 덮어씌워지지 않음)
        self.plot_widget.getAxis('right').setLabel('Pressure', **label_style_pres)
        self.plot_widget.getAxis('right').setTickFont(self.axis_font)
        self.view_pres.setMouseEnabled(x=False, y=False)
        
        # 리사이즈 시 우측 뷰박스 사이즈 연동
        def updateViews():
            self.view_pres.setGeometry(self.plot_widget.getViewBox().sceneBoundingRect())
            self.view_pres.linkedViewChanged(self.plot_widget.getViewBox(), self.view_pres.XAxis)

        self.plot_widget.getViewBox().sigResized.connect(updateViews)
        updateViews()
        
        # 왼쪽 시리즈 (Posi)
        self.curve_act_posi = self.plot_widget.plot(
            pen=pg.mkPen(color=(100, 150, 255), width=1), 
            name="Act Posi"
        )
        self.curve_target_posi = self.plot_widget.plot(
            pen=pg.mkPen('b', width=1, style=Qt.DashLine), 
            name="Target Posi"
        )
        
        # 오른쪽 시리즈 (Pres)
        self.curve_act_pres = pg.PlotCurveItem(
            pen=pg.mkPen(color=(255, 150, 150), width=1), 
            name="Act Pres"
        )
        self.curve_target_pres = pg.PlotCurveItem(
            pen=pg.mkPen('r', width=1, style=Qt.DashLine), 
            name="Target Pres"
        )
        
        self.view_pres.addItem(self.curve_act_pres)
        self.view_pres.addItem(self.curve_target_pres)
        
        # 내부 상태
        self.time_span_ms = 30 * 1000 # 30초
        self.jump_step_ms = int(self.time_span_ms / 10) # 1/10 간격 점프
        
        now_ms = QDateTime.currentMSecsSinceEpoch()
        self.current_x_max = now_ms + self.jump_step_ms
        self.current_x_min = self.current_x_max - self.time_span_ms
        
        self.posi_setting_panel.sig_changed_settings.connect(self.on_posi_setting_changed)
        self.pres_setting_panel.sig_changed_settings.connect(self.on_pres_setting_changed)
        # 차트 초기 화면을 현재 시간 기준으로 바로 세팅
        self.on_posi_setting_changed()
        self.on_pres_setting_changed()
        self._update_xaxis_bounds()

        self.local_setting_manager.sig_pres_decimal_places_changed.connect(self.handle_changed_pres_decimal_places)
        self.local_setting_manager.sig_posi_decimal_places_changed.connect(self.handle_changed_posi_decimal_places)
        self.pres_converter.sig_pres_range_changed.connect(self.handle_changed_pres_range)

        QTimer.singleShot(0, updateViews)

    def on_time_range_changed(self):
        self.time_combobox.commit()
        self.time_span_ms = self.time_combobox.get_value()
        self.jump_step_ms = int(self.time_span_ms / 10)
        
        if self.current_x_max is not None:
            self.current_x_min = self.current_x_max - self.time_span_ms
            self._update_xaxis_bounds()

    def on_posi_setting_changed(self):
        self.local_setting_manager.posi_chart_enable_actual = self.posi_setting_panel.chk_actual.isChecked()
        self.local_setting_manager.posi_chart_enable_target = self.posi_setting_panel.chk_target.isChecked()
        self.local_setting_manager.posi_chart_range_mode = self.posi_setting_panel.mode_combo.get_value()
        self.local_setting_manager.posi_chart_range_custom_min = self.posi_setting_panel.spin_min.get_value()
        self.local_setting_manager.posi_chart_range_custom_max = self.posi_setting_panel.spin_max.get_value()

        self.curve_act_posi.setVisible(self.local_setting_manager.posi_chart_enable_actual)
        self.curve_target_posi.setVisible(self.local_setting_manager.posi_chart_enable_target)

        self.posi_chart_range_mode = self.local_setting_manager.posi_chart_range_mode

        if self.posi_chart_range_mode == 0:  # Auto
            min_val, max_val = self._cal_posi_value_range()
            self.plot_widget.setYRange(min_val, max_val, padding=0)
        elif self.posi_chart_range_mode == 1:  # Full
            self.plot_widget.setYRange(0.0, 100.0, padding=0)
        elif self.posi_chart_range_mode == 2: # Custom
            self.plot_widget.setYRange(self.local_setting_manager.posi_chart_range_custom_min, self.local_setting_manager.posi_chart_range_custom_max, padding=0)

    def on_pres_setting_changed(self):
        self.local_setting_manager.pres_chart_enable_actual = self.pres_setting_panel.chk_actual.isChecked()
        self.local_setting_manager.pres_chart_enable_target = self.pres_setting_panel.chk_target.isChecked()
        self.local_setting_manager.pres_chart_range_mode = self.pres_setting_panel.mode_combo.get_value()
        self.local_setting_manager.pres_chart_range_custom_min = self.pres_setting_panel.spin_min.get_value()
        self.local_setting_manager.pres_chart_range_custom_max = self.pres_setting_panel.spin_max.get_value()

        self.curve_act_pres.setVisible(self.local_setting_manager.pres_chart_enable_actual)
        self.curve_target_pres.setVisible(self.local_setting_manager.pres_chart_enable_target)
        
        self.pres_chart_range_mode = self.local_setting_manager.pres_chart_range_mode

        if self.posi_chart_range_mode == 0:  # Auto
            min_val, max_val = self._cal_posi_value_range()
            self.plot_widget.setYRange(min_val, max_val, padding=0)
        if self.pres_chart_range_mode == 1:  # Full
            min_val = 0.0
            max_val = self.pres_converter.get_dp_max_pres()

            if max_val is None:
                max_val = 100.0
            
            self.view_pres.setYRange(min_val, max_val, padding=0)
        elif self.pres_chart_range_mode == 2: # Custom
            min_val, max_val = self._cal_pres_value_range()
            self.view_pres.setYRange(self.local_setting_manager.pres_chart_range_custom_min, self.local_setting_manager.pres_chart_range_custom_max, padding=0)

    def _update_xaxis_bounds(self):
        # 충분한 패딩(0.03)을 주어 좌우 가장자리의 텍스트 잘림을 완전히 방지합니다.
        self.plot_widget.setXRange(self.current_x_min, self.current_x_max, padding=0)
        
        # QDateTime의 예기치 않은 빈 문자열 반환을 방지하기 위해 파이썬 내장 datetime 사용
        import datetime
        start_str = datetime.datetime.fromtimestamp(self.current_x_min / 1000.0).strftime("%H:%M:%S")
        end_str = datetime.datetime.fromtimestamp(self.current_x_max / 1000.0).strftime("%H:%M:%S")
        
        # 네이티브 라벨에 시간 업데이트 (절대 사라지지 않음)
        self.lbl_start_time.set_text(start_str)
        self.lbl_end_time.set_text(end_str)

    def update_chart(self, new_data_list: List[CompoundData]):
        if not new_data_list:
            return

        n = len(new_data_list)

        new_timestamp = np.array([d.timestamp for d in new_data_list])
        new_act_posi = np.array([self.posi_converter.convert_posi_to_display_value(d.act_posi) for d in new_data_list])
        new_target_posi = np.array([self.posi_converter.convert_posi_to_display_value(d.target_posi) for d in new_data_list])
        new_act_pres = np.array([self.pres_converter.convert_iface_pres_to_dp_pres(d.act_pres) for d in new_data_list])
        new_target_pres = np.array([self.pres_converter.convert_iface_pres_to_dp_pres(d.target_pres) for d in new_data_list])

        if self.ptr + n <= self.max_points:
            # 아직 방이 남았을 때는 빈자리에 쏙 넣습니다.
            self.timestamps[self.ptr : self.ptr + n] = new_timestamp
            self.act_posis[self.ptr : self.ptr + n] = new_act_posi
            self.target_posis[self.ptr : self.ptr + n] = new_target_posi
            self.act_press[self.ptr : self.ptr + n] = new_act_pres
            self.target_press[self.ptr : self.ptr + n] = new_target_pres
            self.ptr += n
        else:
            # 방이 꽉 찼을 때는 오래된 데이터를 앞으로 n칸 밀어내고(삭제) 맨 뒤에 새 데이터를 덮어씁니다.
            # 이 작업은 파이썬이 아닌 C 내부에서 블록 단위로 처리되어 매우 빠릅니다.
            self.timestamps[:-n] = self.timestamps[n:]
            self.timestamps[-n:] = new_timestamp
            
            self.act_posis[:-n] = self.act_posis[n:]
            self.act_posis[-n:] = new_act_posi
            
            self.target_posis[:-n] = self.target_posis[n:]
            self.target_posis[-n:] = new_target_posi
            
            self.act_press[:-n] = self.act_press[n:]
            self.act_press[-n:] = new_act_pres
            
            self.target_press[:-n] = self.target_press[n:]
            self.target_press[-n:] = new_target_pres
            
        current_ts = self.timestamps[self.ptr - 1]
        if current_ts > self.current_x_max:
            diff = current_ts - self.current_x_max
            steps = int(diff / self.jump_step_ms) + 1
            self.current_x_max += steps * self.jump_step_ms
            self.current_x_min = self.current_x_max - self.time_span_ms
            self._update_xaxis_bounds()

        valid_ts = self.timestamps[:self.ptr]
        
        self.curve_act_posi.setData(valid_ts, self.act_posis[:self.ptr])
        self.curve_target_posi.setData(valid_ts, self.target_posis[:self.ptr])
        self.curve_act_pres.setData(valid_ts, self.act_press[:self.ptr])
        self.curve_target_pres.setData(valid_ts, self.target_press[:self.ptr])
            
        if self.posi_chart_range_mode == 0: # Auto
            min_posi, max_posi = self._cal_posi_value_range()
            self.plot_widget.setYRange(min_posi, max_posi, padding=0)

        if self.pres_chart_range_mode == 0: # Auto
            min_pres, max_pres = self._cal_pres_value_range()
            self.view_pres.setYRange(min_pres, max_pres, padding=0)

    def _cal_posi_value_range(self) -> tuple[float, float]:
        slice_idx = int(self.ptr * 2 / 3)

        if self.ptr < 1:
            return 0.0, 100.0

        if self.curve_act_posi.isVisible() and self.curve_target_posi.isVisible():
            recent_ap = self.act_posis[slice_idx:self.ptr]
            recent_tp = self.target_posis[slice_idx:self.ptr]
            max_posi = np.max([np.max(recent_ap), np.max(recent_tp)])
            min_posi = np.min([np.min(recent_ap), np.min(recent_tp)])
        elif self.curve_act_posi.isVisible():
            recent = self.act_posis[slice_idx:self.ptr]
            max_posi = np.max(recent)
            min_posi = np.min(recent)
        elif self.curve_target_posi.isVisible():
            recent = self.target_posis[slice_idx:self.ptr]
            max_posi = np.max(recent)
            min_posi = np.min(recent)
        else:
            return 0.0, 100.0
        
        margin_posi = (max_posi - min_posi) * 0.1
        margin_posi = margin_posi if margin_posi != 0 else 1.0
        return min_posi - margin_posi, max_posi + margin_posi

    def _cal_pres_value_range(self) -> tuple[float, float]:
        slice_idx = int(self.ptr * 2 / 3)

        if self.ptr < 1:
            return 0.0, 100.0

        if self.curve_act_pres.isVisible() and self.curve_target_pres.isVisible():
            recent_apr = self.act_press[slice_idx:self.ptr]
            recent_tpr = self.target_press[slice_idx:self.ptr]
            max_pres = np.max([np.max(recent_apr), np.max(recent_tpr)])
            min_pres = np.min([np.min(recent_apr), np.min(recent_tpr)])
        elif self.curve_act_pres.isVisible():
            recent = self.act_press[slice_idx:self.ptr]
            max_pres = np.max(recent)
            min_pres = np.min(recent)
        elif self.curve_target_pres.isVisible():
            recent = self.target_press[slice_idx:self.ptr]
            max_pres = np.max(recent)
            min_pres = np.min(recent)
        else:
            return 0.0, 100.0
        
        margin_pres = (max_pres - min_pres) * 0.1
        margin_pres = margin_pres if margin_pres != 0 else 1.0
        return min_pres - margin_pres, max_pres + margin_pres

    def handle_changed_pres_decimal_places(self):
        self.pres_setting_panel.set_decimal_places(self.local_setting_manager.pres_decimal_places)

    def handle_changed_posi_decimal_places(self):
        self.posi_setting_panel.set_decimal_places(self.local_setting_manager.posi_decimal_places)

    def handle_changed_pres_range(self):
        if self.pres_chart_range_mode == 1: # 0:Auto, 1:Full, 2:Custom
            min_val = 0.0
            max_val = self.pres_converter.get_dp_max_pres()
            if max_val is None:
                max_val = 100.0
            self.view_pres.setYRange(min_val, max_val, padding=0)
    
    
        

