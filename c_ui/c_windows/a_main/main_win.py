from typing import List, Tuple
from PySide6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QLabel, QMessageBox, QFrame, QHBoxLayout
from PySide6.QtCore import Qt, QTimer

from b_core.a_define import app_info

from b_core.b_datatype import param_enum as p_enum
from b_core.b_datatype.compound_data import CompoundData
from b_core.e_worker.compounds_run_worker import CompoundsRunWorker
from b_core.e_worker.parameter_worker import ParameterWorker
from b_core.d_dal.service_port import ServicePort
from b_core.c_manager.parameter_manager import ParamManager
from c_ui.c_windows.win_manager import WinManager
from c_ui.c_windows.a_main.main_top_toolbar import MainTopToolBar
from c_ui.c_windows.b_connection.connection_setting_win import ConnectionSettingWin
from c_ui.c_windows.b_connection.connection_connect_win import ConnectionConnectWin
from c_ui.b_components.b_usercontrol.user_statusbar import UserStatusBar
from c_ui.b_components.a_custom.custom_panel import CustomPanel
from c_ui.b_components.a_custom.custom_icon_button import CustomIconButton
from c_ui.b_components.a_custom.custom_icon_label_button import CustomIconLabelButton
from c_ui.b_components.a_custom.custom_button import CustomButton

from c_ui.c_windows.a_main.main_status import MainStatus
from c_ui.c_windows.a_main.main_control import MainControl
from c_ui.c_windows.a_main.main_position import MainPosition
from c_ui.c_windows.a_main.main_pressure import MainPressure

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

        self.top_area = QFrame()
        self.top_area.setStyleSheet("background-color: lightgray;") # 시각적 확인을 위한 색상
        main_layout.addWidget(self.top_area)

        self.bottom_area = QWidget()
        self.bottom_area.setFixedHeight(290)

        bottom_layout = QHBoxLayout(self.bottom_area)
        bottom_layout.setContentsMargins(0, 0, 0, 0) # 영역 간 마진 없애기
        bottom_layout.setSpacing(0)

        section = MainStatus("System.Control Mode", "Position Control.Basic.Position Control Speed", "Pressure Control.Basic.Controller Selector Used", "System.Warning/Error.Warning Bitmap", "System.Warning/Error.Error Bitmap")
        bottom_layout.addWidget(section, 26)

        self.ctrl_panel = MainControl(); self.ctrl_panel.open_btn.clicked.connect(self.on_clicked_open_btn, Qt.QueuedConnection); self.ctrl_panel.close_btn.clicked.connect(self.on_clicked_close_btn, Qt.QueuedConnection); self.ctrl_panel.hold_btn.clicked.connect(self.on_clicked_hold_btn, Qt.QueuedConnection); self.ctrl_panel.learn_btn.clicked.connect(self.on_clicked_learn_btn, Qt.QueuedConnection)
        bottom_layout.addWidget(self.ctrl_panel, 10)
            
        self.posi_panel = MainPosition()
        bottom_layout.addWidget(self.posi_panel, 20)
        self.posi_panel.posi_input.editingFinished.connect(self.on_posi_input_finished, Qt.QueuedConnection)
        self.posi_panel.sig_btn_clicked.connect(self.on_clicked_posi_btn, Qt.QueuedConnection)
        self.posi_panel.btn_edit.clicked.connect(self.on_clicked_posi_edit_btn, Qt.QueuedConnection)

        self.pres_panel = MainPressure()
        bottom_layout.addWidget(self.pres_panel, 20)
        self.pres_panel.pres_input.editingFinished.connect(self.on_pres_input_finished, Qt.QueuedConnection)
        self.pres_panel.sig_btn_clicked.connect(self.on_clicked_pres_btn, Qt.QueuedConnection)
        self.pres_panel.btn_edit.clicked.connect(self.on_clicked_pres_edit_btn, Qt.QueuedConnection)

        # 메인 레이아웃에 하단 영역 추가
        main_layout.addWidget(self.bottom_area)

        self.main_toolbar = MainTopToolBar(self)
        self.addToolBar(Qt.TopToolBarArea, self.main_toolbar)

        self.main_toolbar.reg_local_btn_slot(self.on_clicked_local_btn)
        self.main_toolbar.reg_remote_btn_slot(self.on_clicked_remote_btn)
        self.main_toolbar.reg_connection_refresh_slot(self.on_clicked_refresh)
        self.main_toolbar.reg_connection_settings_slot(self.on_clicked_connection_setting)
        self.main_toolbar.reg_connection_connect_slot(self.on_clicked_connection_connect)
        self.main_toolbar.reg_connection_disconnect_slot(self.on_clicked_connection_disconnect)
        # 4. 상태바(Status Bar) 초기화
        self.custom_statusbar = UserStatusBar(self)
        self.setStatusBar(self.custom_statusbar)

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

    def on_clicked_warn_err_button(self):
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
        write_value_str = self.posi_panel.posi_input.getParamWriteValue()
        print(f"posi_value : {write_value_str}")
        self.ctrl_mode_param.write_str_value = f"{p_enum.ControlModeEnum.POSITION.value}"
        self.posi_target_param.write_str_value = write_value_str
        self.param_worker.write()
        
    def on_clicked_posi_btn(self, write_str_value=""):
        self.ctrl_mode_param.write_str_value = f"{p_enum.ControlModeEnum.POSITION.value}"
        self.posi_target_param.write_str_value = write_str_value
        print(f"click posi_value : {write_str_value}")
        self.param_worker.write()

    def on_clicked_posi_edit_btn(self):
        pass
        
    def on_pres_input_finished(self):
        write_value_str = self.pres_panel.pres_input.getParamWriteValue()
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
        pass

    def handle_changed_connection_info(self, info: str):
        if info:
            self.param_worker.refresh()
        else:
            pass

    def handle_progress_changed(self, progress: int):
        self.custom_statusbar.set_progress(progress)

    def handle_compounds_data(self):
        data_list = self.compounds_worker.pop_all_data()

        if data_list:
            if len(data_list) > 1:
                last_data = data_list[-1]

                compound_data : CompoundData = last_data

                total_time_diff = last_data.timestamp - data_list[0].timestamp
                avg_interval = total_time_diff / (len(data_list) - 1)
                self.custom_statusbar.set_scan_rate(int(avg_interval))
            else:
                self.custom_statusbar.set_scan_rate(-1)
        else:
            self.custom_statusbar.set_scan_rate(-1)

    def handle_access_mode_changed(self):
        if not self.acc_mode_param.str_value:
            self.main_toolbar.local_btn.set_accent(False)
            self.main_toolbar.remote_btn.set_accent(False)
            return

        int_value = self.acc_mode_param.value

        if int_value == p_enum.AccModeEnum.LOCAL.value:
            self.main_toolbar.local_btn.set_accent(True)
            self.main_toolbar.remote_btn.set_accent(False)
        elif int_value == p_enum.AccModeEnum.REMOTE.value:
            self.main_toolbar.local_btn.set_accent(False)
            self.main_toolbar.remote_btn.set_accent(True)
        else:
            self.main_toolbar.local_btn.set_accent(False)
            self.main_toolbar.remote_btn.set_accent(False)


    def handle_ctrl_mode_changed(self):
        if not self.ctrl_mode_param.str_value:
            self.ctrl_panel.set_ctrl_mode_value(p_enum.ControlModeEnum.INIT.value)
            return

        self.ctrl_panel.set_ctrl_mode_value(self.ctrl_mode_param.value)