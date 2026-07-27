import time

from PySide6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QMessageBox, QHBoxLayout
from PySide6.QtCore import Qt, QTimer

from b_core.a_define import app_info

from b_core.b_datatype import param_enum as p_enum
from b_core.b_datatype.compound_data import CompoundData
from b_core.e_worker.compounds_run_worker import CompoundsRunWorker
from b_core.e_worker.parameter_worker import ParameterWorker
from b_core.d_dal.service_port import ServicePort

from c_ui.c_windows.win_manager import WinManager
from c_ui.c_windows.a_main.main_top_toolbar import MainTopToolBar
from c_ui.c_windows.a_main.main_foot_statusbar import MainFootStatusBar
from c_ui.c_windows.a_main.main_chart import MainChart
from c_ui.c_windows.a_main.main_valve_status import MainValveStatus
from c_ui.c_windows.a_main.main_valve_control import MainValveControl
from c_ui.c_windows.a_main.main_valve_position import MainValvePosition
from c_ui.c_windows.a_main.main_setpoint_posi_edit_win import MainSetpointPosiEditWin
from c_ui.c_windows.a_main.main_valve_pressure import MainValvePressure
from c_ui.c_windows.a_main.main_setpoint_pres_edit_win import MainSetpointPresEditWin

from c_ui.c_windows.b_connection.connection_setting_win import ConnectionSettingWin
from c_ui.c_windows.b_connection.connection_connect_win import ConnectionConnectWin
from c_ui.c_windows.c_sys.sys_identification_win import SysIdentificationWin
from c_ui.c_windows.c_sys.sys_warn_err_win import SysWarnErrWin
from c_ui.c_windows.c_sys.sys_statistics_win import SysStatisticsWin
from c_ui.c_windows.c_sys.sys_service_win import SysServiceWin
from c_ui.c_windows.d_valve.valve_basic_win import ValveBasicWin
from c_ui.c_windows.d_valve.valve_cycle_counter_win import ValveCycleCounterWin
from c_ui.c_windows.d_valve.valve_setting_win import ValveSettingWin
from c_ui.c_windows.e_sensor.sensor_zero_win import SensorZeroWin
from c_ui.c_windows.e_sensor.sensor_setting_win import SensorSettingWin
from c_ui.c_windows.f_posi_ctrl.posi_ctrl_setting_win import PosiCtrlSettingWin
from c_ui.c_windows.g_pres_ctrl.pres_ctrl_gen_setting_win import PresCtrlGenSettingWin
from c_ui.c_windows.g_pres_ctrl.pres_ctrl_controller_setting_win import PresCtrlControllerSettingWin
from c_ui.c_windows.h_learn.learn_exe_win import LearnExeWin
from c_ui.c_windows.h_learn.learn_bank1_win import LearnBank1Win
from c_ui.c_windows.h_learn.learn_bank2_win import LearnBank2Win
from c_ui.c_windows.h_learn.learn_bank3_win import LearnBank3Win
from c_ui.c_windows.h_learn.learn_bank4_win import LearnBank4Win
from c_ui.c_windows.i_pfo.pfo_win import PfoWin
from c_ui.c_windows.j_iface.iface_pwr_io_win import IfacePwrIoWin
from c_ui.c_windows.j_iface.iface_dnet_win import IfaceDnetWin
from c_ui.c_windows.j_iface.iface_trace_win import IfaceTraceWin
from c_ui.c_windows.l_compound.compound_4_win import Compound04Win
from c_ui.c_windows.l_compound.compound_3_win import Compound03Win
from c_ui.c_windows.l_compound.compound_2_win import Compound02Win
from c_ui.c_windows.l_compound.compound_1_win import Compound01Win
from c_ui.c_windows.k_cluster.cluster_master_win import ClusterMasterWin
from c_ui.c_windows.k_cluster.cluster_monitor_win import ClusterMonitorWin
from c_ui.c_windows.o_factory.factory_firmware_update_win import FactoryFirmwareUpdateWin
from c_ui.c_windows.m_advenced.advenced_lagacy_win import AdvencedLegacyWin
from c_ui.c_windows.m_advenced.advenced_backup_win import AdvencedBackupWin
from c_ui.c_windows.m_advenced.advenced_restore_win import AdvencedRestoreWin
from c_ui.c_windows.p_help.help_nvm_update_win import HelpNvmUpdateWin

class MainWin(QMainWindow):
    """
    애플리케이션의 메인 윈도우 클래스입니다.
    """
    def __init__(self):
        super().__init__()

        # 1. 기본 윈도우 설정 (app_info에서 정의된 이름을 가져와 동적으로 설정)
        self.setWindowTitle(app_info.APP_DISPLAY_TITLE)
        self.resize(1024, 690)  # 초기 윈도우 크기 설정

        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self.chart = MainChart()
        main_layout.addWidget(self.chart)

        self.bottom_area = QWidget()
        self.bottom_area.setFixedHeight(290)

        bottom_layout = QHBoxLayout(self.bottom_area)
        bottom_layout.setContentsMargins(0, 0, 0, 0) # 영역 간 마진 없애기
        bottom_layout.setSpacing(0)

        section = MainValveStatus("System.Control Mode", "Position Control.Basic.Position Control Speed Used (%)", "Pressure Control.Basic.Controller Selector Used", "System.Warning/Error.Warning Bitmap", "System.Warning/Error.Error Bitmap")
        section.sig_warn_err_clicked.connect(self.on_clicked_sys_warning_error)
        bottom_layout.addWidget(section, 27)

        self.ctrl_panel = MainValveControl(); 
        self.ctrl_panel.open_btn.clicked.connect(self.on_clicked_open_btn, Qt.QueuedConnection); 
        self.ctrl_panel.close_btn.clicked.connect(self.on_clicked_close_btn, Qt.QueuedConnection); 
        self.ctrl_panel.hold_btn.clicked.connect(self.on_clicked_hold_btn, Qt.QueuedConnection); 
        self.ctrl_panel.learn_btn.clicked.connect(self.on_clicked_learn, Qt.QueuedConnection)
        bottom_layout.addWidget(self.ctrl_panel, 10)
            
        self.posi_panel = MainValvePosition()
        bottom_layout.addWidget(self.posi_panel, 19)
        self.posi_panel.posi_input.sig_value_changed.connect(self.on_posi_input_finished, Qt.QueuedConnection)
        self.posi_panel.sig_btn_clicked.connect(self.on_clicked_posi_btn, Qt.QueuedConnection)
        self.posi_panel.btn_edit.clicked.connect(self.on_clicked_posi_edit_btn, Qt.QueuedConnection)

        self.pres_panel = MainValvePressure()
        bottom_layout.addWidget(self.pres_panel, 20)
        self.pres_panel.pres_input.sig_value_changed.connect(self.on_pres_input_finished, Qt.QueuedConnection)
        self.pres_panel.sig_btn_clicked.connect(self.on_clicked_pres_btn, Qt.QueuedConnection)
        self.pres_panel.btn_edit.clicked.connect(self.on_clicked_pres_edit_btn, Qt.QueuedConnection)

        # 메인 레이아웃에 하단 영역 추가
        main_layout.addWidget(self.bottom_area)

        self.main_top_toolbar = MainTopToolBar(self)
        self.addToolBar(Qt.TopToolBarArea, self.main_top_toolbar)

        self.main_top_toolbar.reg_local_btn_slot(self.on_clicked_local_btn)
        self.main_top_toolbar.reg_remote_btn_slot(self.on_clicked_remote_btn)
        self.main_top_toolbar.reg_connection_refresh_slot(self.on_clicked_refresh)
        self.main_top_toolbar.reg_connection_settings_slot(self.on_clicked_connection_setting)
        self.main_top_toolbar.reg_connection_connect_slot(self.on_clicked_connection_connect)
        self.main_top_toolbar.reg_connection_disconnect_slot(self.on_clicked_connection_disconnect)
        self.main_top_toolbar.reg_sys_identification_slot(self.on_clicked_sys_identification)
        self.main_top_toolbar.reg_sys_statistics_slot(self.on_clicked_sys_statistics)
        self.main_top_toolbar.reg_sys_warning_error_slot(self.on_clicked_sys_warning_error)
        self.main_top_toolbar.reg_sys_service_slot(self.on_clicked_sys_service)
        self.main_top_toolbar.reg_valve_basic_slot(self.on_clicked_valve_basic)
        self.main_top_toolbar.reg_valve_cycle_counter_slot(self.on_clicked_valve_cycle_counter)
        self.main_top_toolbar.reg_valve_setting_slot(self.on_clicked_valve_setting)
        self.main_top_toolbar.reg_sens_zero_slot(self.on_clicked_sens_zero)
        self.main_top_toolbar.reg_sens_setting_slot(self.on_clicked_sens_setting)
        self.main_top_toolbar.reg_posi_ctrl_setting_slot(self.on_clicked_posi_ctrl_setting)
        self.main_top_toolbar.reg_pres_ctrl_gen_setting_slot(self.on_clicked_pres_ctrl_gen_setting)
        self.main_top_toolbar.reg_pres_ctrl_controller_setting_slot(self.on_clicked_pres_ctrl_controller_setting)
        self.main_top_toolbar.reg_learn_slot(self.on_clicked_learn)
        self.main_top_toolbar.reg_learn_bank1_setting_slot(self.on_clicked_learn_bank1_setting)
        self.main_top_toolbar.reg_learn_bank2_setting_slot(self.on_clicked_learn_bank2_setting)
        self.main_top_toolbar.reg_learn_bank3_setting_slot(self.on_clicked_learn_bank3_setting)
        self.main_top_toolbar.reg_learn_bank4_setting_slot(self.on_clicked_learn_bank4_setting)
        self.main_top_toolbar.reg_learn_list_setting_slot(self.on_clicked_learn_list_setting)
        self.main_top_toolbar.reg_pfo_setting_slot(self.on_clicked_pfo_setting)
        self.main_top_toolbar.reg_iface_pwr_io_slot(self.on_clicked_iface_pwr_io)
        self.main_top_toolbar.reg_iface_dnet_slot(self.on_clicked_iface_dnet)
        self.main_top_toolbar.reg_iface_trace_slot(self.on_clicked_iface_trace)
        self.main_top_toolbar.reg_cluster_master_setting_slot(self.on_clicked_cluster_master_setting)
        self.main_top_toolbar.reg_cluster_monitor_slot(self.on_clicked_cluster_monitor)
        self.main_top_toolbar.reg_compound1_setting_slot(self.on_clicked_compound1_setting)
        self.main_top_toolbar.reg_compound2_setting_slot(self.on_clicked_compound2_setting)
        self.main_top_toolbar.reg_compound3_setting_slot(self.on_clicked_compound3_setting)
        self.main_top_toolbar.reg_compound4_setting_slot(self.on_clicked_compound4_setting)
        self.main_top_toolbar.reg_advenced_backup_slot(self.on_clicked_advenced_backup)
        self.main_top_toolbar.reg_advenced_restore_slot(self.on_clicked_advenced_restore)
        self.main_top_toolbar.reg_advenced_lagacy_slot(self.on_clicked_advenced_lagacy)
        self.main_top_toolbar.reg_analysis_sensor_slot(self.on_clicked_analysis_sensor)
        self.main_top_toolbar.reg_analysis_terminal_slot(self.on_clicked_analysis_terminal)
        self.main_top_toolbar.reg_factory_adc_calib_slot(self.on_clicked_factory_adc_calib)
        self.main_top_toolbar.reg_factory_firmware_update_slot(self.on_clicked_factory_firmware_update)
        self.main_top_toolbar.reg_help_update_slot(self.on_clicked_help_update)
        self.main_top_toolbar.reg_help_about_slot(self.on_clicked_help_about)
        
        # 4. 상태바(Status Bar) 초기화
        self.main_foot_statusbar = MainFootStatusBar(self)
        self.setStatusBar(self.main_foot_statusbar)

        ServicePort().connect_info_changed.connect(self.handle_changed_connection_info)

        self.compounds_worker = CompoundsRunWorker(self)
        self.compounds_worker.start()

        self.compounds_timer = QTimer(self)
        self.compounds_timer.setInterval(200)  # 100ms = 0.1초
        self.compounds_timer.timeout.connect(self.handle_compounds_data)

        self.compounds_timer.start()

        self.param_worker = ParameterWorker(parent=self, win_name="Main Win")   
        self.param_worker.add_init_param("System.Identification.Serial Number")    
        self.param_worker.add_init_param("System.Identification.Configuration.Valve Type") 
        self.param_worker.add_init_param("System.Identification.Configuration.Contract Method")
        self.param_worker.add_init_param("System.Identification.Configuration.User Interface")    
        self.param_worker.add_init_param("System.Identification.Configuration.Revision 1")
        self.param_worker.add_init_param("System.Identification.Configuration.Revision 2")
        self.param_worker.add_init_param("System.Identification.Configuration.Revision 3")
        self.param_worker.add_init_param("System.Identification.Firmware.Firmware Version")
        self.param_worker.add_init_param("Sensor.Sensor 1.Basic.Available")  
        self.param_worker.add_init_param("Sensor.Sensor 1.Basic.Enable")
        self.param_worker.add_init_param("Sensor.Sensor 1.Range.Data Unit")
        self.param_worker.add_init_param("Sensor.Sensor 1.Basic.Scale")
        self.param_worker.add_init_param("Sensor.Sensor 1.Range.Upper Limit Data Value")
        self.param_worker.add_init_param("Sensor.Sensor 1.Range.Lower Limit Data Value")
        self.param_worker.add_init_param("Sensor.Sensor 1.Range.Voltage Per Decade [V]")
        self.param_worker.add_init_param("Sensor.Sensor 2.Basic.Available")  
        self.param_worker.add_init_param("Sensor.Sensor 2.Basic.Enable")
        self.param_worker.add_init_param("Sensor.Sensor 2.Range.Data Unit")
        self.param_worker.add_init_param("Sensor.Sensor 2.Basic.Scale")
        self.param_worker.add_init_param("Sensor.Sensor 2.Range.Upper Limit Data Value")
        self.param_worker.add_init_param("Sensor.Sensor 2.Range.Lower Limit Data Value")
        self.param_worker.add_init_param("Sensor.Sensor 2.Range.Voltage Per Decade [V]")
        self.param_worker.add_init_param("Interface RS232/RS485.Scaling.Pressure.Pressure Unit")
        self.param_worker.add_init_param("Interface RS232/RS485.Scaling.Pressure.Value Pressure Min")
        self.param_worker.add_init_param("Interface RS232/RS485.Scaling.Pressure.Value Pressure Sensor Full Scale")
        self.param_worker.add_init_param("Interface RS232/RS485.Scaling.Position.Position Unit")
        self.param_worker.add_init_param("Interface RS232/RS485.Scaling.Position.Value Open Position")
        self.param_worker.add_init_param("Interface RS232/RS485.Scaling.Position.Value Closest Position")

        self.pre_ctrl_mode = p_enum.ControlModeEnum.INIT.value

        self.acc_mode_param = self.param_worker.add_write_param("System.Access Mode")    

        if self.acc_mode_param:
            self.acc_mode_param.sig_value_changed.connect(self.handle_access_mode_changed)
            self.handle_access_mode_changed()

        self.ctrl_mode_param = self.param_worker.add_write_param("System.Control Mode")    

        if self.ctrl_mode_param:
            self.ctrl_mode_param.sig_value_changed.connect(self.handle_ctrl_mode_changed)
            self.handle_ctrl_mode_changed()

        self.user_iface_param = self.param_worker.add_write_param("System.Identification.Configuration.User Interface")    

        if self.user_iface_param:
            self.user_iface_param.sig_value_changed.connect(self.handle_user_iface_changed)
            self.handle_user_iface_changed()    

        self.param_worker.sig_progress_changed.connect(self.handle_progress_changed)

        self.posi_target_param = self.param_worker.add_write_param("Position Control.Basic.Target.Target Position")    
        self.pres_target_param = self.param_worker.add_write_param("Pressure Control.Basic.Target.Target Pressure")

    def on_clicked_local_btn(self):
        self.acc_mode_param.write_str_value = f"{p_enum.AccModeEnum.LOCAL.value}"
        self.param_worker.write()

    def on_clicked_remote_btn(self):
        self.acc_mode_param.write_str_value = f"{p_enum.AccModeEnum.REMOTE.value}"
        self.param_worker.write()

    def on_clicked_refresh(self):
        self.param_worker.refresh()

    def on_clicked_connection_setting(self):
        WinManager().show_window(win_class=ConnectionSettingWin, parent=self, is_modal=True)

    def on_clicked_connection_connect(self):
        WinManager().show_window(win_class=ConnectionConnectWin, parent=self, is_modal=True)

    def on_clicked_connection_disconnect(self):
        reply = QMessageBox.question(self, "Confirm Disconnect", "Are you sure you want to disconnect?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            ServicePort().close()
        else:
            pass

    def on_clicked_sys_identification(self):
        WinManager().show_param_window(win_class=SysIdentificationWin, parent=self, is_modal=False)

    def on_clicked_sys_statistics(self):
        WinManager().show_param_window(win_class=SysStatisticsWin, parent=self, is_modal=False)

    def on_clicked_sys_warning_error(self):
        WinManager().show_param_window(win_class=SysWarnErrWin, parent=self, is_modal=False)

    def on_clicked_sys_service(self):
        WinManager().show_param_window(win_class=SysServiceWin, parent=self, is_modal=False)

    def on_clicked_valve_basic(self):
        WinManager().show_param_window(win_class=ValveBasicWin, parent=self, is_modal=False)

    def on_clicked_valve_cycle_counter(self):
        WinManager().show_param_window(win_class=ValveCycleCounterWin, parent=self, is_modal=False)

    def on_clicked_valve_setting(self):
        WinManager().show_param_window(win_class=ValveSettingWin, parent=self, is_modal=False)

    def on_clicked_sens_zero(self):
        WinManager().show_param_window(win_class=SensorZeroWin, parent=self, is_modal=False)

    def on_clicked_sens_setting(self):
        WinManager().show_param_window(win_class=SensorSettingWin, parent=self, is_modal=False)

    def on_clicked_posi_ctrl_setting(self):
        WinManager().show_param_window(win_class=PosiCtrlSettingWin, parent=self, is_modal=False)

    def on_clicked_pres_ctrl_gen_setting(self):
        WinManager().show_param_window(win_class=PresCtrlGenSettingWin, parent=self, is_modal=False)

    def on_clicked_pres_ctrl_controller_setting(self):
        WinManager().show_param_window(win_class=PresCtrlControllerSettingWin, parent=self, is_modal=False)

    def on_clicked_learn(self):
        WinManager().show_param_window(win_class=LearnExeWin, parent=self, is_modal=False)

    def on_clicked_learn_bank1_setting(self):
        WinManager().show_param_window(win_class=LearnBank1Win, parent=self, is_modal=False)

    def on_clicked_learn_bank2_setting(self):
        WinManager().show_param_window(win_class=LearnBank2Win, parent=self, is_modal=False)

    def on_clicked_learn_bank3_setting(self):
        WinManager().show_param_window(win_class=LearnBank3Win, parent=self, is_modal=False)

    def on_clicked_learn_bank4_setting(self):
        WinManager().show_param_window(win_class=LearnBank4Win, parent=self, is_modal=False)

    def on_clicked_learn_list_setting(self):
        #WinManager().show_param_window(win_class=LearnListWin, parent=self, is_modal=False)
        pass

    def on_clicked_pfo_setting(self):
        WinManager().show_param_window(win_class=PfoWin, parent=self, is_modal=False)

    def on_clicked_iface_pwr_io(self):
        WinManager().show_param_window(win_class=IfacePwrIoWin, parent=self, is_modal=False)

    def on_clicked_iface_dnet(self):
        WinManager().show_param_window(win_class=IfaceDnetWin, parent=self, is_modal=False)

    def on_clicked_iface_trace(self):
        WinManager().show_param_window(win_class=IfaceTraceWin, parent=self, is_modal=False)

    def on_clicked_cluster_master_setting(self):
        WinManager().show_param_window(win_class=ClusterMasterWin, parent=self, is_modal=False)

    def on_clicked_cluster_monitor(self):
        WinManager().show_param_window(win_class=ClusterMonitorWin, parent=self, is_modal=False) 

    def on_clicked_compound1_setting(self):
        WinManager().show_param_window(win_class=Compound01Win, parent=self, is_modal=False)

    def on_clicked_compound2_setting(self):
        WinManager().show_param_window(win_class=Compound02Win, parent=self, is_modal=False)

    def on_clicked_compound3_setting(self):
        WinManager().show_param_window(win_class=Compound03Win, parent=self, is_modal=False)

    def on_clicked_compound4_setting(self):
        WinManager().show_param_window(win_class=Compound04Win, parent=self, is_modal=False)

    def on_clicked_advenced_backup(self):
        WinManager().show_param_window(win_class=AdvencedBackupWin, parent=self, is_modal=False)
        
    def on_clicked_advenced_restore(self):
        WinManager().show_param_window(win_class=AdvencedRestoreWin, parent=self, is_modal=False)

    def on_clicked_advenced_lagacy(self):
        WinManager().show_param_window(win_class=AdvencedLegacyWin, parent=self, is_modal=False)
        pass

    def on_clicked_analysis_sensor(self):
        #WinManager().show_param_window(win_class=AnalysisSensorWin, parent=self, is_modal=False)
        pass

    def on_clicked_analysis_terminal(self):
        #WinManager().show_param_window(win_class=AnalysisTerminalWin, parent=self, is_modal=False)
        pass

    def on_clicked_factory_adc_calib(self):
        #WinManager().show_param_window(win_class=FactoryAdcCalibWin, parent=self, is_modal=False)
        pass

    def on_clicked_factory_firmware_update(self):
        msg_box = QMessageBox(self)  
        msg_box.setWindowTitle("Select Backup Option")
        msg_box.setText("Please select whether to perform a backup.")
        
        if ServicePort().connect_info:
            btn_backup = msg_box.addButton("Backup", QMessageBox.AcceptRole)
            btn_skip = msg_box.addButton("Skip", QMessageBox.AcceptRole)
            msg_box.exec()
        
            clicked = msg_box.clickedButton()
            if clicked == btn_backup:
                win = WinManager().show_param_window(win_class=AdvencedBackupWin, parent=self, is_modal=False) 
                win.set_firmware_update_backup(True)
                win.destroyed.connect(self.on_finished_backup_for_firmware_update)
                return
        win = WinManager().show_param_window(win_class=FactoryFirmwareUpdateWin, parent=self, is_modal=False)
        win.sig_finished_firmware_update.connect(self.on_clicked_connection_connect)

    def on_finished_backup_for_firmware_update(self):
        win = WinManager().show_param_window(win_class=FactoryFirmwareUpdateWin, parent=self, is_modal=False)
        win.sig_finished_firmware_update.connect(self.on_clicked_connection_connect)

    def on_clicked_help_update(self):
        WinManager().show_param_window(win_class=HelpNvmUpdateWin, parent=self, is_modal=False)
        pass

    def on_clicked_help_about(self):
        #WinManager().show_param_window(win_class=HelpAboutWin, parent=self, is_modal=False)
        pass

    def on_clicked_open_btn(self):
        self.ctrl_mode_param.write_str_value = f"{p_enum.ControlModeEnum.OPEN.value}"
        self.param_worker.write()

    def on_clicked_close_btn(self):
        self.ctrl_mode_param.write_str_value = f"{p_enum.ControlModeEnum.CLOSE.value}"
        self.param_worker.write()

    def on_clicked_hold_btn(self):
        self.ctrl_mode_param.write_str_value = f"{p_enum.ControlModeEnum.HOLD.value}"
        self.param_worker.write()

    def on_posi_input_finished(self):
        write_value_str = self.posi_panel.posi_input.get_param_write_value()
        print(f"posi_value : {write_value_str}")
        self.ctrl_mode_param.write_str_value = f"{p_enum.ControlModeEnum.POSITION.value}"
        self.posi_target_param.write_str_value = write_value_str
        self.param_worker.write()
        
    def on_clicked_posi_btn(self, write_str_value=""):
        self.ctrl_mode_param.write_str_value = f"{p_enum.ControlModeEnum.POSITION.value}"
        self.posi_target_param.write_str_value = write_str_value
        self.param_worker.write()

    def on_clicked_posi_edit_btn(self):
        WinManager().show_window(win_class=MainSetpointPosiEditWin, parent=self, is_modal=True)
        
    def on_pres_input_finished(self):
        write_value_str = self.pres_panel.pres_input.get_param_write_value()
        print(f"input pres_value : {write_value_str}")
        self.ctrl_mode_param.write_str_value = f"{p_enum.ControlModeEnum.PRESSURE.value}"
        self.pres_target_param.write_str_value = write_value_str
        self.param_worker.write()

    def on_clicked_pres_btn(self, write_str_value=""):
        self.ctrl_mode_param.write_str_value = f"{p_enum.ControlModeEnum.PRESSURE.value}"
        print(f"click pres_value : {write_str_value}")
        self.pres_target_param.write_str_value = write_str_value
        self.param_worker.write()

    def on_clicked_pres_edit_btn(self):
        WinManager().show_window(win_class=MainSetpointPresEditWin, parent=self, is_modal=True)

    def handle_changed_connection_info(self, info: str):
        if info:
            self.compounds_worker.refresh()
            self.param_worker.refresh()
        else:
            pass

    def handle_progress_changed(self, progress: int):
        self.main_foot_statusbar.set_progress(progress)

    def handle_compounds_data(self):
        data_list = self.compounds_worker.pop_all_data()
        
        if data_list:
            self.chart.update_chart(data_list)
        
            if len(data_list) > 1:
                last_data = data_list[-1]
        
                compound_data : CompoundData = last_data
        
                total_time_diff = last_data.timestamp - data_list[0].timestamp
                avg_interval = total_time_diff / (len(data_list) - 1)
                self.main_foot_statusbar.set_scan_rate(int(avg_interval))
            else:
                self.main_foot_statusbar.set_scan_rate(-1)
        else:
            self.main_foot_statusbar.set_scan_rate(-1)

    def handle_access_mode_changed(self):
        if self.acc_mode_param.value is None:
            self.main_top_toolbar.local_btn.set_accent(False)
            self.main_top_toolbar.remote_btn.set_accent(False)
            return
        
        int_value = self.acc_mode_param.value
        
        if int_value == p_enum.AccModeEnum.LOCAL.value:
            self.main_top_toolbar.local_btn.set_accent(True)
            self.main_top_toolbar.remote_btn.set_accent(False)
        elif int_value == p_enum.AccModeEnum.REMOTE.value:
            self.main_top_toolbar.local_btn.set_accent(False)
            self.main_top_toolbar.remote_btn.set_accent(True)
        else:
            self.main_top_toolbar.local_btn.set_accent(False)
            self.main_top_toolbar.remote_btn.set_accent(False)

    def handle_ctrl_mode_changed(self):
        if self.ctrl_mode_param.value is None:
            self.ctrl_panel.set_ctrl_mode_value(p_enum.ControlModeEnum.INIT.value)
            return

        if self.pre_ctrl_mode == p_enum.ControlModeEnum.INIT.value and self.ctrl_mode_param.value != p_enum.ControlModeEnum.INIT.value:
            self.param_worker.refresh()

        self.pre_ctrl_mode = self.ctrl_mode_param.value
        self.ctrl_panel.set_ctrl_mode_value(self.ctrl_mode_param.value)

    def handle_user_iface_changed(self):
        if self.user_iface_param.value is None:
            return
        
        self.main_top_toolbar.set_iface(self.user_iface_param.value)