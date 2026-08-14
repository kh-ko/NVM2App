from typing import NamedTuple
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QHBoxLayout

from b_core.a_define import app_info
from b_core.b_datatype import param_enum as p_enum
from b_core.c_manager.app_log_manager import AppLogManager
from b_core.c_manager.parameter_manager import ParamManager
from b_core.d_dal.service_port import ServicePort
from b_core.e_worker_ver2.compound_run_worker import CompoundRunWorker
from b_core.e_worker_ver2.parameter_run_worker import ParameterRunWorker

from c_ui.b_control_ver2.d_param.param_win import ParamWin
from c_ui.b_control_ver2.b_base.statusbars import BaseStatusBar

from c_ui.c_window_ver2.win_manager import WinManager
from c_ui.c_window_ver2.a_main.main_toolbar import MainToolBar
from c_ui.c_window_ver2.a_main.main_chart_panel import MainChartPanel
from c_ui.c_window_ver2.a_main.main_status_panel import MainStatusPanel
from c_ui.c_window_ver2.a_main.main_pressure_panel import MainPressurePanel
from c_ui.c_window_ver2.a_main.main_position_panel import MainPositionPanel
from c_ui.c_window_ver2.a_main.main_control_panel import MainControlPanel

from c_ui.c_window_ver2.b_connection.connection_connect_win import ConnectionConnectWin
from c_ui.c_window_ver2.x_localsetting.local_posi_setting_win import LocalPosiSettingWin
from c_ui.c_window_ver2.x_localsetting.local_pres_setting_win import LocalPresSettingWin

from c_ui.c_window_ver2.log_view_win import LogViewWin
from c_ui.c_window_ver2.x_message.connection_message_box import ask_disconnect
from c_ui.c_window_ver2.x_message.not_ready_message_box import show_not_ready
from c_ui.c_window_ver2.param_worker_win_mixin import ParamWorkerWinMixin

class CompoundData(NamedTuple):
    timestamp: int
    access_mode: int
    control_mode: int
    act_posi: float
    target_posi: float
    act_pres: float
    target_pres: float
    speed: float
    pres_contoller_selector: int
    warning_bitmap: int
    error_bitmap: int
    error_number: int
    error_code: int

_COMPOUND_BANK = "Compound Commands.NVM For Sevice.Compound Commands 1"

_COMPOUND_REF_PATHS = [
    "System.Access Mode",                                       # [0]
    "System.Control Mode",                                      # [1]
    "Position Control.Basic.Actual Position",                   # [2]
    "Position Control.Basic.Target Position Used",              # [3]
    "Pressure Control.Basic.Actual Pressure",                   # [4]
    "Pressure Control.Basic.Target Pressure Used",              # [5]
    "Position Control.Basic.Position Control Speed Used (%)",   # [6]
    "Pressure Control.Basic.Controller Selector Used",          # [7]
    "System.Warning/Error.Warning Bitmap",                      # [8]
    "System.Warning/Error.Error Bitmap",                        # [9]
    "System.Warning/Error.Error Number",                        # [10]
    "System.Warning/Error.Error Code",                          # [11]
]

def _make_compound_data(timestamp_ms: int, values: list[str]) -> CompoundData:
    """워커 스레드에서 호출된다 — 형 변환을 UI 스레드 밖에서 수행."""
    return CompoundData(
        timestamp_ms,
        int(values[0]),    # access_mode
        int(values[1]),    # control_mode
        float(values[2]),  # act_posi
        float(values[3]),  # target_posi
        float(values[4]),  # act_pres
        float(values[5]),  # target_pres
        float(values[6]),  # speed
        int(values[7]),    # pres_contoller_selector
        int(values[8]),    # warning_bitmap
        int(values[9]),    # error_bitmap
        int(values[10]),   # error_number
        int(values[11]),   # error_code
    )

class MainWin(ParamWorkerWinMixin, QMainWindow):
    """
    애플리케이션의 메인 윈도우 클래스입니다.
    """
    def __init__(self):
        super().__init__()

        '''
        UI 설정
        '''
        self.win_name = "MainWin"

        # 1. 기본 윈도우 설정 (app_info에서 정의된 이름을 가져와 동적으로 설정)
        self.setWindowTitle(app_info.APP_DISPLAY_TITLE)
        self.resize(1024, 690)  # 초기 윈도우 크기 설정

        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)

        self.main_top_toolbar = MainToolBar(self)

        self.main_top_toolbar.local_btn.clicked.connect(self.on_clicked_local_btn, Qt.QueuedConnection)
        self.main_top_toolbar.remote_btn.clicked.connect(self.on_clicked_remote_btn, Qt.QueuedConnection)
        self.main_top_toolbar.refresh_btn.clicked.connect(self.on_clicked_refresh_btn, Qt.QueuedConnection)
        self.main_top_toolbar.action_connection_connect.triggered.connect(self.on_clicked_connection_connect, Qt.QueuedConnection)
        self.main_top_toolbar.action_connection_disconnect.triggered.connect(self.on_clicked_connection_disconnect, Qt.QueuedConnection)

        self.main_top_toolbar.action_connection_settings.triggered.connect(self.on_clicked_connection_settings, Qt.QueuedConnection)
        self.main_top_toolbar.action_sys_identification.triggered.connect(self.on_clicked_sys_identification, Qt.QueuedConnection)
        self.main_top_toolbar.action_sys_statistics.triggered.connect(self.on_clicked_sys_statistics, Qt.QueuedConnection)
        self.main_top_toolbar.action_sys_warning_error.triggered.connect(self.on_clicked_sys_warning_error, Qt.QueuedConnection)
        self.main_top_toolbar.action_sys_service.triggered.connect(self.on_clicked_sys_service, Qt.QueuedConnection)
        self.main_top_toolbar.action_valve_basic.triggered.connect(self.on_clicked_valve_basic, Qt.QueuedConnection)
        self.main_top_toolbar.action_valve_cycle.triggered.connect(self.on_clicked_valve_cycle, Qt.QueuedConnection)
        self.main_top_toolbar.action_valve_setting.triggered.connect(self.on_clicked_valve_setting, Qt.QueuedConnection)
        self.main_top_toolbar.action_sens_zero.triggered.connect(self.on_clicked_sens_zero, Qt.QueuedConnection)
        self.main_top_toolbar.action_sens_setting.triggered.connect(self.on_clicked_sens_setting, Qt.QueuedConnection)
        self.main_top_toolbar.action_posi_ctrl_setting.triggered.connect(self.on_clicked_posi_ctrl_setting, Qt.QueuedConnection)
        self.main_top_toolbar.action_pres_ctrl_gen_setting.triggered.connect(self.on_clicked_pres_ctrl_gen_setting, Qt.QueuedConnection)
        self.main_top_toolbar.action_pres_ctrl_controller_setting.triggered.connect(self.on_clicked_pres_ctrl_controller_setting, Qt.QueuedConnection)
        self.main_top_toolbar.action_learn.triggered.connect(self.on_clicked_learn, Qt.QueuedConnection)
        self.main_top_toolbar.action_learn_bank1_setting.triggered.connect(self.on_clicked_learn_bank1_setting, Qt.QueuedConnection)
        self.main_top_toolbar.action_learn_bank2_setting.triggered.connect(self.on_clicked_learn_bank2_setting, Qt.QueuedConnection)
        self.main_top_toolbar.action_learn_bank3_setting.triggered.connect(self.on_clicked_learn_bank3_setting, Qt.QueuedConnection)
        self.main_top_toolbar.action_learn_bank4_setting.triggered.connect(self.on_clicked_learn_bank4_setting, Qt.QueuedConnection)
        self.main_top_toolbar.action_learn_list_setting.triggered.connect(self.on_clicked_learn_list_setting, Qt.QueuedConnection)
        self.main_top_toolbar.action_pfo_setting.triggered.connect(self.on_clicked_pfo_setting, Qt.QueuedConnection)
        self.main_top_toolbar.action_iface_pwr_io.triggered.connect(self.on_clicked_iface_pwr_io, Qt.QueuedConnection)
        self.main_top_toolbar.action_iface_dnet.triggered.connect(self.on_clicked_iface_dnet, Qt.QueuedConnection)
        self.main_top_toolbar.action_iface_ethercat.triggered.connect(self.on_clicked_iface_ethercat, Qt.QueuedConnection)
        self.main_top_toolbar.action_iface_trace.triggered.connect(self.on_clicked_iface_trace, Qt.QueuedConnection)
        self.main_top_toolbar.action_cluster_master.triggered.connect(self.on_clicked_cluster_master, Qt.QueuedConnection)
        self.main_top_toolbar.action_cluster_monitor.triggered.connect(self.on_clicked_cluster_monitor, Qt.QueuedConnection)
        self.main_top_toolbar.action_compound_compound1.triggered.connect(self.on_clicked_compound_compound1, Qt.QueuedConnection)
        self.main_top_toolbar.action_compound_compound2.triggered.connect(self.on_clicked_compound_compound2, Qt.QueuedConnection)
        self.main_top_toolbar.action_compound_compound3.triggered.connect(self.on_clicked_compound_compound3, Qt.QueuedConnection)
        self.main_top_toolbar.action_compound_compound4.triggered.connect(self.on_clicked_compound_compound4, Qt.QueuedConnection)
        self.main_top_toolbar.action_advanced_backup.triggered.connect(self.on_clicked_advanced_backup, Qt.QueuedConnection)
        self.main_top_toolbar.action_advanced_restore.triggered.connect(self.on_clicked_advanced_restore, Qt.QueuedConnection)
        self.main_top_toolbar.action_advanced_legacy.triggered.connect(self.on_clicked_advanced_legacy, Qt.QueuedConnection)
        self.main_top_toolbar.action_analysis_sensor.triggered.connect(self.on_clicked_analysis_sensor, Qt.QueuedConnection)
        self.main_top_toolbar.action_analysis_chart.triggered.connect(self.on_clicked_analysis_chart, Qt.QueuedConnection)
        self.main_top_toolbar.action_analysis_terminal.triggered.connect(self.on_clicked_analysis_terminal, Qt.QueuedConnection)
        self.main_top_toolbar.action_fac_adc_calib.triggered.connect(self.on_clicked_fac_adc_calib, Qt.QueuedConnection)
        self.main_top_toolbar.action_fac_firmware_update.triggered.connect(self.on_clicked_fac_firmware_update, Qt.QueuedConnection)
        self.main_top_toolbar.action_help_update.triggered.connect(self.on_clicked_help_update, Qt.QueuedConnection)
        self.main_top_toolbar.action_help_about.triggered.connect(self.on_clicked_help_about, Qt.QueuedConnection)

        self.addToolBar(Qt.TopToolBarArea, self.main_top_toolbar)

        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self.chart_panel = MainChartPanel()
        main_layout.addWidget(self.chart_panel)

        self.bottom_area = QWidget()
        self.bottom_area.setFixedHeight(305)

        bottom_layout = QHBoxLayout(self.bottom_area)
        bottom_layout.setContentsMargins(0, 0, 0, 0) # 영역 간 마진 없애기
        bottom_layout.setSpacing(0)

        self.status_panel = MainStatusPanel()
        self.status_panel.sig_warn_err_clicked.connect(self.on_clicked_sys_warning_error, Qt.QueuedConnection)
        bottom_layout.addWidget(self.status_panel, 27)

        self.ctrl_panel = MainControlPanel(); 
        self.ctrl_panel.open_btn.clicked.connect(self.on_clicked_open_btn, Qt.QueuedConnection); 
        self.ctrl_panel.close_btn.clicked.connect(self.on_clicked_close_btn, Qt.QueuedConnection); 
        self.ctrl_panel.hold_btn.clicked.connect(self.on_clicked_hold_btn, Qt.QueuedConnection); 
        self.ctrl_panel.learn_btn.clicked.connect(self.on_clicked_learn_btn, Qt.QueuedConnection)
        bottom_layout.addWidget(self.ctrl_panel, 10)
            
        self.posi_panel = MainPositionPanel()
        bottom_layout.addWidget(self.posi_panel, 20)
        self.posi_panel.sig_clicked_title_btn.connect(self.on_posi_setting_edit_clicked, Qt.QueuedConnection)
        self.posi_panel.sig_setpoint.connect(self.on_posi_input_finished, Qt.QueuedConnection)
        #self.posi_panel.sig_btn_clicked.connect(self.on_clicked_posi_btn, Qt.QueuedConnection)
        #self.posi_panel.btn_edit.clicked.connect(self.on_clicked_posi_edit_btn, Qt.QueuedConnection)

        self.pres_panel = MainPressurePanel()
        bottom_layout.addWidget(self.pres_panel, 20)
        self.pres_panel.sig_clicked_title_btn.connect(self.on_pres_setting_edit_clicked, Qt.QueuedConnection)
        self.pres_panel.sig_setpoint.connect(self.on_pres_input_finished, Qt.QueuedConnection)
        #self.pres_panel.sig_btn_clicked.connect(self.on_clicked_pres_btn, Qt.QueuedConnection)
        #self.pres_panel.btn_edit.clicked.connect(self.on_clicked_pres_edit_btn, Qt.QueuedConnection)

        # 메인 레이아웃에 하단 영역 추가
        main_layout.addWidget(self.bottom_area)

        # 4. 상태바(Status Bar) 초기화
        self.statusbar = BaseStatusBar(parent=self, label_count=3)
        self.statusbar.labels[2].setFixedWidth(120)
        self.statusbar.btn_log.clicked.connect(self.on_clicked_log_view)
        self.setStatusBar(self.statusbar)

        '''
        기능 요소 설정
        '''
        self._log = AppLogManager().get_logger(self.win_name)
        self.param_manager = ParamManager()

        self.svc_port = ServicePort()
        self.svc_port.connect_info_changed.connect(self.handle_changed_connection_info)

        # 사용하는 Param 모두 획득
        self.sn_param                       = self.param_manager.get_by_full_path("System.Identification.Serial Number"                        )
        self.valve_type_param               = self.param_manager.get_by_full_path("System.Identification.Configuration.Valve Type"             )
        self.contract_method_param          = self.param_manager.get_by_full_path("System.Identification.Configuration.Contract Method"        )
        self.user_iface_param               = self.param_manager.get_by_full_path("System.Identification.Configuration.User Interface"         )
        self.revision1_param                = self.param_manager.get_by_full_path("System.Identification.Configuration.Revision 1"             )
        self.revision2_param                = self.param_manager.get_by_full_path("System.Identification.Configuration.Revision 2"             )
        self.revision3_param                = self.param_manager.get_by_full_path("System.Identification.Configuration.Revision 3"             )
        self.firmware_version_param         = self.param_manager.get_by_full_path("System.Identification.Firmware.Firmware Version"            )
        self.sens1_available_param          = self.param_manager.get_by_full_path("Sensor.Sensor 1.Basic.Available"                            )
        self.sens1_enable_param             = self.param_manager.get_by_full_path("Sensor.Sensor 1.Basic.Enable"                               )
        self.sens1_data_unit_param          = self.param_manager.get_by_full_path("Sensor.Sensor 1.Range.Data Unit"                            )
        self.sens1_scale_param              = self.param_manager.get_by_full_path("Sensor.Sensor 1.Basic.Scale"                                )
        self.sens1_upper_limit_param        = self.param_manager.get_by_full_path("Sensor.Sensor 1.Range.Upper Limit Data Value"               )
        self.sens1_lower_limit_param        = self.param_manager.get_by_full_path("Sensor.Sensor 1.Range.Lower Limit Data Value"               )
        self.sens1_vpd_param                = self.param_manager.get_by_full_path("Sensor.Sensor 1.Range.Voltage Per Decade [V]"               )
        self.sens2_available_param          = self.param_manager.get_by_full_path("Sensor.Sensor 2.Basic.Available"                            )
        self.sens2_enable_param             = self.param_manager.get_by_full_path("Sensor.Sensor 2.Basic.Enable"                               )
        self.sens2_data_unit_param          = self.param_manager.get_by_full_path("Sensor.Sensor 2.Range.Data Unit"                            )
        self.sens2_scale_param              = self.param_manager.get_by_full_path("Sensor.Sensor 2.Basic.Scale"                                )
        self.sens2_upper_limit_param        = self.param_manager.get_by_full_path("Sensor.Sensor 2.Range.Upper Limit Data Value"               )
        self.sens2_lower_limit_param        = self.param_manager.get_by_full_path("Sensor.Sensor 2.Range.Lower Limit Data Value"               )
        self.sens2_vpd_param                = self.param_manager.get_by_full_path("Sensor.Sensor 2.Range.Voltage Per Decade [V]"               )
        self.pres_unit_param                = self.param_manager.get_by_full_path("Interface.Scaling.Pressure.Pressure Unit"                   )
        self.pres_min_param                 = self.param_manager.get_by_full_path("Interface.Scaling.Pressure.Value Pressure Min"              )
        self.pres_full_scale_param          = self.param_manager.get_by_full_path("Interface.Scaling.Pressure.Value Pressure Sensor Full Scale")
        self.posi_unit_param                = self.param_manager.get_by_full_path("Interface.Scaling.Position.Position Unit"                   )
        self.posi_open_param                = self.param_manager.get_by_full_path("Interface.Scaling.Position.Value Open Position"             )
        self.posi_closest_param             = self.param_manager.get_by_full_path("Interface.Scaling.Position.Value Closest Position"          )

        self.acc_mode_param                 = self.param_manager.get_by_full_path("System.Access Mode"                                         )
        self.posi_ctrl_speed_param          = self.param_manager.get_by_full_path("Position Control.Basic.Position Control Speed Used (%)"     )
        self.pres_controller_selector_param = self.param_manager.get_by_full_path("Pressure Control.Basic.Controller Selector Used"            )   
        self.warn_bitmap_param              = self.param_manager.get_by_full_path("System.Warning/Error.Warning Bitmap"                        )               
        self.err_bitmap_param               = self.param_manager.get_by_full_path("System.Warning/Error.Error Bitmap"                          )                 
        self.ctrl_mode_param                = self.param_manager.get_by_full_path("System.Control Mode"                                        )
        self.target_posi_param              = self.param_manager.get_by_full_path("Position Control.Basic.Target.Target Position"              )
        self.act_posi_param                 = self.param_manager.get_by_full_path("Position Control.Basic.Actual Position"                     )
        self.target_used_posi_param         = self.param_manager.get_by_full_path("Position Control.Basic.Target Position Used"                )
        self.act_pres_param                 = self.param_manager.get_by_full_path("Pressure Control.Basic.Actual Pressure"                     )
        self.target_used_pres_param         = self.param_manager.get_by_full_path("Pressure Control.Basic.Target Pressure Used"                )
        self.target_pres_param              = self.param_manager.get_by_full_path("Pressure Control.Basic.Target.Target Pressure"              )

        # compound_worker 설정
        self.compound_worker = CompoundRunWorker(self, log_source=self.win_name)

        pairs = []
        for index, ref_path in enumerate(_COMPOUND_REF_PATHS):
            compound = self.param_manager.get_by_full_path(f"{_COMPOUND_BANK}.[{index}] (0x)")
            ref_param = self.param_manager.get_by_full_path(ref_path)

            if compound is None or ref_param is None:
                # param 트리 변경/경로 오타 추적용
                self._log.error(f"compound pair not found: slot [{index}], ref '{ref_path}' "
                                f"(compound={compound is not None}, ref={ref_param is not None})")
                continue

            pairs.append((compound, ref_param))

        terminator = self.param_manager.get_by_full_path(f"{_COMPOUND_BANK}.[{len(_COMPOUND_REF_PATHS)}] (0x)")
        if terminator is None:
            self._log.error(f"compound terminator not found: slot [{len(_COMPOUND_REF_PATHS)}]")
        else:
            pairs.append((terminator, None))

        self.compound_worker.configure(pairs, sample_factory=_make_compound_data)
        self.compound_worker.start()

        self.compound_timer = QTimer(self)
        self.compound_timer.setInterval(200)  # 200ms = 0.2초
        self.compound_timer.timeout.connect(self.handle_compound_data)
        self.compound_timer.start()

        # parameter_worker 설정
        self.param_worker = ParameterRunWorker(self, log_source=self.win_name)
        
        self.param_worker.add_init_param_ptr(self.sn_param               )    
        self.param_worker.add_init_param_ptr(self.valve_type_param       ) 
        self.param_worker.add_init_param_ptr(self.contract_method_param  )
        self.param_worker.add_init_param_ptr(self.user_iface_param       )    
        self.param_worker.add_init_param_ptr(self.revision1_param        )
        self.param_worker.add_init_param_ptr(self.revision2_param        )
        self.param_worker.add_init_param_ptr(self.revision3_param        )
        self.param_worker.add_init_param_ptr(self.firmware_version_param )
        self.param_worker.add_init_param_ptr(self.sens1_available_param  )  
        self.param_worker.add_init_param_ptr(self.sens1_enable_param     )
        self.param_worker.add_init_param_ptr(self.sens1_data_unit_param  )
        self.param_worker.add_init_param_ptr(self.sens1_scale_param      )
        self.param_worker.add_init_param_ptr(self.sens1_upper_limit_param)
        self.param_worker.add_init_param_ptr(self.sens1_lower_limit_param)
        self.param_worker.add_init_param_ptr(self.sens1_vpd_param        )
        self.param_worker.add_init_param_ptr(self.sens2_available_param  )  
        self.param_worker.add_init_param_ptr(self.sens2_enable_param     )
        self.param_worker.add_init_param_ptr(self.sens2_data_unit_param  )
        self.param_worker.add_init_param_ptr(self.sens2_scale_param      )
        self.param_worker.add_init_param_ptr(self.sens2_upper_limit_param)
        self.param_worker.add_init_param_ptr(self.sens2_lower_limit_param)
        self.param_worker.add_init_param_ptr(self.sens2_vpd_param        )
        self.param_worker.add_init_param_ptr(self.pres_unit_param        )
        self.param_worker.add_init_param_ptr(self.pres_min_param         )
        self.param_worker.add_init_param_ptr(self.pres_full_scale_param  )
        self.param_worker.add_init_param_ptr(self.posi_unit_param        )
        self.param_worker.add_init_param_ptr(self.posi_open_param        )
        self.param_worker.add_init_param_ptr(self.posi_closest_param     )

        self.param_worker.add_write_param_ptr(self.acc_mode_param        )
        self.param_worker.add_write_param_ptr(self.ctrl_mode_param       )
        self.param_worker.add_write_param_ptr(self.target_posi_param     )
        self.param_worker.add_write_param_ptr(self.target_pres_param     )

        self.param_worker.sig_finish_refresh.connect(self.handle_finished_refresh)
        self.param_worker.sig_reboot_started.connect(self.handle_started_reboot)
        self.param_worker.sig_reboot_finished.connect(self.handle_finished_reboot)
        self.param_worker.sig_progress_changed.connect(self.handle_changed_param_worker_progress)

        # MainWin 이벤트 처리 연결
        self.sn_param.sig_value_changed.connect(self.handle_changed_sn_param)
        self.acc_mode_param.sig_value_changed.connect(self.handle_changed_acc_mode_param)
        self.ctrl_mode_param.sig_value_changed.connect(self.handle_changed_ctrl_mode_param)
        self.user_iface_param.sig_value_changed.connect(self.handle_changed_user_iface_param)

        # status panel param 연결
        self.status_panel.set_ctrl_mode_param(self.ctrl_mode_param)
        self.status_panel.set_posi_ctrl_speed_param(self.posi_ctrl_speed_param)
        self.status_panel.set_pres_controller_selector_param(self.pres_controller_selector_param)
        self.status_panel.set_warn_bitmap_param(self.warn_bitmap_param)
        self.status_panel.set_err_bitmap_param(self.err_bitmap_param)

        # position panel param 연결
        self.posi_panel.set_actual_posi_param(self.act_posi_param)
        self.posi_panel.set_target_posi_used_param(self.target_used_posi_param)
        self.posi_panel.set_target_posi_param(self.target_posi_param)

        # Pressure panel param 연결
        self.pres_panel.set_actual_pres_param(self.act_pres_param)
        self.pres_panel.set_target_pres_used_param(self.target_used_pres_param)
        self.pres_panel.set_max_pres_param(self.pres_full_scale_param)
        self.pres_panel.set_target_pres_param(self.target_pres_param)

    # 쓰기 정책/refresh (single_param_write / multiple_param_write /
    # start_param_refresh)는 ParamWorkerWinMixin 이 제공한다

    '''
    사용자 시그널에 대한 슬롯
    '''
    def on_clicked_sys_warning_error(self):
        WinManager().show_window(win_class=ParamWin, win_name=None, win_id=["ParamWin_System.Warning/Error"], parent=self, is_modal=False, path="System.Warning/Error", filter_param_paths=[], is_editblock_win=False, label_width=210)

    def on_clicked_open_btn(self):
        self.single_param_write(self.ctrl_mode_param, f"{p_enum.ControlModeEnum.OPEN.value}")

    def on_clicked_close_btn(self):
        self.single_param_write(self.ctrl_mode_param, f"{p_enum.ControlModeEnum.CLOSE.value}")

    def on_clicked_hold_btn(self):
        self.single_param_write(self.ctrl_mode_param, f"{p_enum.ControlModeEnum.HOLD.value}")

    def on_clicked_learn_btn(self):
        # lean window 띄우도록 해야된다
        pass

    def on_posi_setting_edit_clicked(self):
        WinManager().show_window(win_class=LocalPosiSettingWin, parent=self)

    def on_pres_setting_edit_clicked(self):
        WinManager().show_window(win_class=LocalPresSettingWin, parent=self)

    def on_posi_input_finished(self, value : str):
        pairs = [(self.ctrl_mode_param, f"{p_enum.ControlModeEnum.POSITION.value}"), (self.target_posi_param, value)]
        self.multiple_param_write(pairs)

    def on_pres_input_finished(self, value : str):
        pairs = [(self.ctrl_mode_param, f"{p_enum.ControlModeEnum.PRESSURE.value}"), (self.target_pres_param, value)]
        self.multiple_param_write(pairs)
    
    def on_clicked_log_view(self):
        # compound worker 는 log_source=win_name 으로 생성했고 전역 로그(stderr 등)는
        # 필터와 무관하게 항상 표시되므로, 자기 이름 하나만 넘기면 된다
        WinManager().show_window(win_class=LogViewWin, parent=self, sources={self.win_name})

    def on_clicked_local_btn(self):
        self.single_param_write(self.acc_mode_param, f"{p_enum.AccModeEnum.LOCAL.value}")

    def on_clicked_remote_btn(self):
        self.single_param_write(self.acc_mode_param, f"{p_enum.AccModeEnum.REMOTE.value}")

    def on_clicked_refresh_btn(self):
        self.start_param_refresh()

    def on_clicked_connection_connect(self):
        WinManager().show_window(win_class=ConnectionConnectWin, parent=self, is_modal=True)

    def on_clicked_connection_disconnect(self):
        if ask_disconnect(self):
            ServicePort().close()

    # ---- 아직 구현되지 않은 툴바 액션 슬롯 ----
    # 기능이 구현되면 해당 슬롯의 본문만 교체한다 (연결부는 그대로).
    def on_clicked_connection_settings(self):
        # 가장 마지막에 구현할 예정 : 필수 기능이 아님
        show_not_ready(self)

    def on_clicked_sys_identification(self):
        WinManager().show_window(win_class=ParamWin, win_name=None, win_id="ParamWin_System.Identification", parent=self, is_modal=False, paths=["System.Identification"], filter_param_paths=[], is_editblock_win=True, label_width=210)

    def on_clicked_sys_statistics(self):
        WinManager().show_window(win_class=ParamWin, win_name=None, win_id="ParamWin_System.Statistics", parent=self, is_modal=False, paths=["System.Statistics"], filter_param_paths=[], is_editblock_win=False, label_width=210)

    def on_clicked_sys_service(self):
        WinManager().show_window(win_class=ParamWin, win_name=None, win_id="ParamWin_System.Services", parent=self, is_modal=False, paths=["System.Services"], filter_param_paths=[], is_editblock_win=False, label_width=210)

    def on_clicked_valve_basic(self):
        WinManager().show_window(win_class=ParamWin, win_name=None, win_id="ParamWin_Valve.Basic", parent=self, is_modal=False, paths=["Valve.Basic"], filter_param_paths=[], is_editblock_win=False, label_width=210)

    def on_clicked_valve_cycle(self):
        WinManager().show_window(win_class=ParamWin, win_name=None, win_id="ParamWin_Valve.Cycle Counter", parent=self, is_modal=False, paths=["Valve.Cycle Counter"], filter_param_paths=[], is_editblock_win=False, label_width=210)

    def on_clicked_valve_setting(self):
        WinManager().show_window(win_class=ParamWin, win_name=None, win_id="ParamWin_Valve.Option", parent=self, is_modal=False, paths=["Valve.Option"], filter_param_paths=[], is_editblock_win=False, label_width=210)

    def on_clicked_sens_zero(self):
        WinManager().show_window(win_class=ParamWin, win_name="Sensor.Zero", win_id="ParamWin_Sensor.Zero", parent=self, is_modal=False, paths=["Sensor.Basic","Sensor.Zero Adjust"], filter_param_paths=[], is_editblock_win=False, label_width=210)

    def on_clicked_sens_setting(self):
        WinManager().show_window(win_class=ParamWin, win_name="Sensor.Settings", win_id="ParamWin_Sensor.Settings", parent=self, is_modal=False, 
                                 paths=["Sensor.Sensor 1.Basic","Sensor.Sensor 2.Basic",
                                        "Sensor.Sensor 1.Range","Sensor.Sensor 2.Range",
                                        "Sensor.Sensor 1.Zero Adjust","Sensor.Sensor 2.Zero Adjust",
                                        "Sensor.Sensor 1.Filter","Sensor.Sensor 2.Filter",
                                        "Sensor.Sensor 1.Analog Sensor Input","Sensor.Sensor 2.Analog Sensor Input",
                                        "Sensor.Sensor 1.Digital Sensor Input","Sensor.Sensor 2.Digital Sensor Input",
                                        "Sensor.Crossover","Sensor.General Setting.Logarithmic Pressure"], 
                                filter_param_paths=[], is_editblock_win=False, label_width=210, folder_max_width=350)

    def on_clicked_posi_ctrl_setting(self):
        WinManager().show_window(win_class=ParamWin, win_name="Position Control", win_id="ParamWin_Position Control", parent=self, is_modal=False, paths=["Position Control"], filter_param_paths=[], is_editblock_win=False, label_width=210)

    def on_clicked_pres_ctrl_gen_setting(self):
        WinManager().show_window(win_class=ParamWin, win_name="Pressure Control", win_id="ParamWin_Pressure Control", parent=self, is_modal=False, paths=["Pressure Control.Basic", "Pressure Control.General Settings"], filter_param_paths=[], is_editblock_win=False, label_width=210)

    def on_clicked_pres_ctrl_controller_setting(self):
        show_not_ready(self)

    def on_clicked_learn(self):
        show_not_ready(self)

    def on_clicked_learn_bank1_setting(self):
        show_not_ready(self)

    def on_clicked_learn_bank2_setting(self):
        show_not_ready(self)

    def on_clicked_learn_bank3_setting(self):
        show_not_ready(self)

    def on_clicked_learn_bank4_setting(self):
        show_not_ready(self)

    def on_clicked_learn_list_setting(self):
        show_not_ready(self)

    def on_clicked_pfo_setting(self):
        show_not_ready(self)

    def on_clicked_iface_pwr_io(self):
        show_not_ready(self)

    def on_clicked_iface_dnet(self):
        show_not_ready(self)

    def on_clicked_iface_ethercat(self):
        show_not_ready(self)

    def on_clicked_iface_trace(self):
        show_not_ready(self)

    def on_clicked_cluster_master(self):
        show_not_ready(self)

    def on_clicked_cluster_monitor(self):
        show_not_ready(self)

    def on_clicked_compound_compound1(self):
        show_not_ready(self)

    def on_clicked_compound_compound2(self):
        show_not_ready(self)

    def on_clicked_compound_compound3(self):
        show_not_ready(self)

    def on_clicked_compound_compound4(self):
        show_not_ready(self)

    def on_clicked_advanced_backup(self):
        show_not_ready(self)

    def on_clicked_advanced_restore(self):
        show_not_ready(self)

    def on_clicked_advanced_legacy(self):
        show_not_ready(self)

    def on_clicked_analysis_sensor(self):
        show_not_ready(self)

    def on_clicked_analysis_chart(self):
        show_not_ready(self)

    def on_clicked_analysis_terminal(self):
        show_not_ready(self)

    def on_clicked_fac_adc_calib(self):
        show_not_ready(self)

    def on_clicked_fac_firmware_update(self):
        show_not_ready(self)

    def on_clicked_help_update(self):
        show_not_ready(self)

    def on_clicked_help_about(self):
        show_not_ready(self)

    '''
    시스템 시그널에 대한 슬롯
    '''
    def handle_changed_connection_info(self, info: str):
        # 공통 처리(상태바/refresh/param_worker 중지)는 믹스인 몫 —
        # MainWin 은 연결 끊김 시 compound 폴링 중지만 추가한다
        if not info:
            self.compound_worker.stop_polling()
        super().handle_changed_connection_info(info)

    def handle_finished_refresh(self):
        # refresh가 끝나면 compound는 다시 slot값을 쓰고 폴링 동작을 수행하면 된다.
        self.compound_worker.start_polling()

    # 재부팅 대기 다이얼로그(handle_started_reboot / handle_finished_reboot /
    # on_clicked_quit_app)는 ParamWorkerWinMixin 이 제공한다

    def handle_changed_acc_mode_param(self):
        if self.acc_mode_param.value is None:
            self.main_top_toolbar.local_btn.set_accent(False)
            self.main_top_toolbar.remote_btn.set_accent(False)
        elif self.acc_mode_param.value == p_enum.AccModeEnum.LOCAL.value:
            self.main_top_toolbar.local_btn.set_accent(True)
            self.main_top_toolbar.remote_btn.set_accent(False)
        else:
            self.main_top_toolbar.local_btn.set_accent(False)
            self.main_top_toolbar.remote_btn.set_accent(True)

    def handle_changed_ctrl_mode_param(self):
        self.ctrl_panel.set_ctrl_mode_value(self.ctrl_mode_param.value)

    def handle_changed_user_iface_param(self):
        pass

    def handle_compound_data(self):
        data_list = self.compound_worker.pop_all_data()
        if data_list:
            self.chart_panel.update_chart(data_list)

        if len(data_list) > 1:
            total_ms = data_list[-1].timestamp - data_list[0].timestamp
            self.statusbar.set_label_text(2, f"scan-rate: {int(total_ms / (len(data_list) - 1))}ms")
        else:
            self.statusbar.set_label_text(2, "scan-rate: -")
            