from typing import List, Tuple
from PySide6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QLabel, QMessageBox, QFrame, QHBoxLayout
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

from c_ui.c_windows.b_connection.connection_setting_win import ConnectionSettingWin
from c_ui.c_windows.b_connection.connection_connect_win import ConnectionConnectWin

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

        section = MainValveStatus("System.Control Mode", "Position Control.Basic.Position Control Speed", "Pressure Control.Basic.Controller Selector Used", "System.Warning/Error.Warning Bitmap", "System.Warning/Error.Error Bitmap")
        bottom_layout.addWidget(section, 26)

        self.ctrl_panel = MainValveControl(); 
        self.ctrl_panel.open_btn.clicked.connect(self.on_clicked_open_btn, Qt.QueuedConnection); 
        self.ctrl_panel.close_btn.clicked.connect(self.on_clicked_close_btn, Qt.QueuedConnection); 
        self.ctrl_panel.hold_btn.clicked.connect(self.on_clicked_hold_btn, Qt.QueuedConnection); 
        self.ctrl_panel.learn_btn.clicked.connect(self.on_clicked_learn_btn, Qt.QueuedConnection)
        bottom_layout.addWidget(self.ctrl_panel, 10)
            
        self.posi_panel = MainValvePosition()
        bottom_layout.addWidget(self.posi_panel, 20)
        self.posi_panel.posi_input.sig_value_changed.connect(self.on_posi_input_finished, Qt.QueuedConnection)
        #self.posi_panel.sig_btn_clicked.connect(self.on_clicked_posi_btn, Qt.QueuedConnection)
        #self.posi_panel.btn_edit.clicked.connect(self.on_clicked_posi_edit_btn, Qt.QueuedConnection)

        self.pres_panel = QWidget() #MainPressure()
        bottom_layout.addWidget(self.pres_panel, 20)
        #self.pres_panel.pres_input.sig_value_changed.connect(self.on_pres_input_finished, Qt.QueuedConnection)
        #self.pres_panel.sig_btn_clicked.connect(self.on_clicked_pres_btn, Qt.QueuedConnection)
        #self.pres_panel.btn_edit.clicked.connect(self.on_clicked_pres_edit_btn, Qt.QueuedConnection)

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
        self.main_top_toolbar.reg_valve_comporessed_air_slot(self.on_clicked_valve_comporessed_air)
        self.main_top_toolbar.reg_valve_cycle_counter_slot(self.on_clicked_valve_cycle_counter)
        self.main_top_toolbar.reg_valve_homing_slot(self.on_clicked_valve_homing)
        self.main_top_toolbar.reg_valve_posi_restriction_slot(self.on_clicked_valve_posi_restriction)
        self.main_top_toolbar.reg_valve_posi_adaption_slot(self.on_clicked_valve_posi_adaption)

        # 4. 상태바(Status Bar) 초기화
        self.main_foot_statusbar = MainFootStatusBar(self)
        self.setStatusBar(self.main_foot_statusbar)

        ServicePort().connect_info_changed.connect(self.handle_changed_connection_info)

        self.compounds_worker = CompoundsRunWorker(self)
        self.compounds_worker.start()

        self.compounds_timer = QTimer(self)
        self.compounds_timer.setInterval(100)  # 100ms = 0.1초
        self.compounds_timer.timeout.connect(self.handle_compounds_data)
        self.compounds_timer.start()

        self.param_worker = ParameterWorker(self)   
        self.param_worker.add_init_param("System.Identification.Serial Number")    
        self.param_worker.add_init_param("System.Identification.Configuration.Valve Type") 
        self.param_worker.add_init_param("System.Identification.Configuration.Contract Method")
        self.param_worker.add_init_param("System.Identification.Configuration.User Interface")    
        self.param_worker.add_init_param("System.Identification.Configuration.Revision 1")
        self.param_worker.add_init_param("System.Identification.Configuration.Revision 2")
        self.param_worker.add_init_param("System.Identification.Configuration.Revision 3")
        self.param_worker.add_init_param("Sensor.Sensor 1.Basic.Available")  
        self.param_worker.add_init_param("Sensor.Sensor 1.Basic.Enable")
        self.param_worker.add_init_param("Sensor.Sensor 1.Range.Data Unit")
        self.param_worker.add_init_param("Sensor.Sensor 1.Basic.Scale")
        self.param_worker.add_init_param("Sensor.Sensor 1.Range.Upper Limit Data Value")
        self.param_worker.add_init_param("Sensor.Sensor 1.Range.Lower Limit Data Value")
        self.param_worker.add_init_param("Sensor.Sensor 1.Range.Voltage Per Decade")
        self.param_worker.add_init_param("Sensor.Sensor 2.Basic.Available")  
        self.param_worker.add_init_param("Sensor.Sensor 2.Basic.Enable")
        self.param_worker.add_init_param("Sensor.Sensor 2.Range.Data Unit")
        self.param_worker.add_init_param("Sensor.Sensor 2.Basic.Scale")
        self.param_worker.add_init_param("Sensor.Sensor 2.Range.Upper Limit Data Value")
        self.param_worker.add_init_param("Sensor.Sensor 2.Range.Lower Limit Data Value")
        self.param_worker.add_init_param("Sensor.Sensor 2.Range.Voltage Per Decade")
        self.param_worker.add_init_param("RS232/RS485 User interface.Scaling.Pressure.Pressure Unit")
        self.param_worker.add_init_param("RS232/RS485 User interface.Scaling.Pressure.Value Pressure 0")
        self.param_worker.add_init_param("RS232/RS485 User interface.Scaling.Pressure.Value Pressure Sensor Full Scale")
        self.param_worker.add_init_param("RS232/RS485 User interface.Scaling.Position.Position Unit")
        self.param_worker.add_init_param("RS232/RS485 User interface.Scaling.Position.Value Open Position")
        self.param_worker.add_init_param("RS232/RS485 User interface.Scaling.Position.Value Closest Position")

        self.acc_mode_param = self.param_worker.add_write_param("System.Access Mode")    

        if self.acc_mode_param:
            self.acc_mode_param.sig_value_changed.connect(self.handle_access_mode_changed)
            self.handle_access_mode_changed()

        self.ctrl_mode_param = self.param_worker.add_write_param("System.Control Mode")    

        if self.ctrl_mode_param:
            self.ctrl_mode_param.sig_value_changed.connect(self.handle_ctrl_mode_changed)
            self.handle_ctrl_mode_changed()

        self.param_worker.sig_progress_changed.connect(self.handle_progress_changed)

        self.posi_target_param = self.param_worker.add_write_param("Position Control.Basic.Target Position")    
        self.pres_target_param = self.param_worker.add_write_param("Pressure Control.Basic.Target Pressure")

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
        #WinManager().show_param_window(win_class=SysIdentificationWin, parent=self, is_modal=False)
        pass

    def on_clicked_sys_statistics(self):
        #WinManager().show_param_window(win_class=SysStatisticsWin, parent=self, is_modal=False)
        pass

    def on_clicked_sys_warning_error(self):
        #WinManager().show_param_window(win_class=SysWarnErrWin, parent=self, is_modal=False)
        pass

    def on_clicked_sys_service(self):
        #WinManager().show_param_window(win_class=SysServiceWin, parent=self, is_modal=False)
        pass

    def on_clicked_valve_basic(self):
        #WinManager().show_param_window(win_class=ValveBasicWin, parent=self, is_modal=False)
        pass

    def on_clicked_valve_comporessed_air(self):
        #WinManager().show_param_window(win_class=ValveCompressedAirWin, parent=self, is_modal=False)
        pass

    def on_clicked_valve_cycle_counter(self):
        #WinManager().show_param_window(win_class=ValveCycleCounterWin, parent=self, is_modal=False)
        pass

    def on_clicked_valve_homing(self):
        pass

    def on_clicked_valve_posi_restriction(self):
        pass

    def on_clicked_valve_posi_adaption(self):
        pass

    def on_clicked_sys_warn_err_button(self):
        #WinManager().show_param_window(win_class=SysWarnErrWin, parent=self, is_modal=False)
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

    def on_clicked_learn_btn(self):
        pass

    def on_posi_input_finished(self):
        write_value_str = self.posi_panel.posi_input.get_param_write_value()
        print(f"posi_value : {write_value_str}")
        self.ctrl_mode_param.write_str_value = f"{p_enum.ControlModeEnum.POSITION.value}"
        self.posi_target_param.write_str_value = write_value_str
        self.param_worker.write()
        
    def on_clicked_posi_btn(self, write_str_value=""):
        #self.ctrl_mode_param.write_str_value = f"{p_enum.ControlModeEnum.POSITION.value}"
        #self.posi_target_param.write_str_value = write_str_value
        #print(f"click posi_value : {write_str_value}")
        #self.param_worker.write()
        pass

    def on_clicked_posi_edit_btn(self):
        #WinManager().show_window(win_class=MainPosiEditWin, parent=self, is_modal=True)
        pass
        
    def on_pres_input_finished(self):
        #write_value_str = self.pres_panel.pres_input.getParamWriteValue()
        #print(f"input pres_value : {write_value_str}")
        #self.ctrl_mode_param.write_str_value = f"{p_enum.ControlModeEnum.PRESSURE.value}"
        #self.pres_target_param.write_str_value = write_value_str
        #self.param_worker.write()
        pass

    def on_clicked_pres_btn(self, write_str_value=""):
        #self.ctrl_mode_param.write_str_value = f"{p_enum.ControlModeEnum.PRESSURE.value}"
        #print(f"click pres_value : {write_str_value}")
        #self.pres_target_param.write_str_value = write_str_value
        #self.param_worker.write()
        pass

    def on_clicked_pres_edit_btn(self):
        #WinManager().show_window(win_class=MainPresEditWin, parent=self, is_modal=True)
        pass

    def handle_changed_connection_info(self, info: str):
        if info:
            self.param_worker.refresh()
        else:
            pass

    def handle_progress_changed(self, progress: int):
        self.main_foot_statusbar.set_progress(progress)
        pass

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
        
        self.ctrl_panel.set_ctrl_mode_value(self.ctrl_mode_param.value)