
from PySide6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QLabel, QMessageBox
from PySide6.QtCore import Qt, QTimer

from b_core.a_define import app_info

from b_core.b_datatype.compound_data import CompoundData
from b_core.c_manager.gv_manager import GvManager
from b_core.e_worker.compounds_run_worker import CompoundsRunWorker
from b_core.e_worker.parameter_worker import ParameterWorker
from b_core.d_dal.service_port import ServicePort
from c_ui.c_windows.win_manager import WinManager
from c_ui.c_windows.a_main.main_top_toolbar import MainTopToolBar
from c_ui.c_windows.b_connection.connection_setting_win import ConnectionSettingWin
from c_ui.c_windows.b_connection.connection_connect_win import ConnectionConnectWin
from c_ui.b_components.b_usercontrol.user_statusbar import UserStatusBar

class MainWin(QMainWindow):
    """
    애플리케이션의 메인 윈도우 클래스입니다.
    """
    def __init__(self):
        super().__init__()

        # 1. 기본 윈도우 설정 (app_info에서 정의된 이름을 가져와 동적으로 설정)
        self.setWindowTitle(app_info.APP_DISPLAY_TITLE)
        self.resize(1024, 690)  # 초기 윈도우 크기 설정

        self.main_toolbar = MainTopToolBar(self)
        self.addToolBar(Qt.TopToolBarArea, self.main_toolbar)

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
        self.param_worker.add_init_param("RS232 User interface.Scaling.Pressure.Pressure Unit")
        self.param_worker.add_init_param("RS232 User interface.Scaling.Pressure.Value Pressure 0")
        self.param_worker.add_init_param("RS232 User interface.Scaling.Pressure.Value Pressure Sensor Full Scale")
        self.param_worker.add_init_param("RS232 User interface.Scaling.Position.Position Unit")
        self.param_worker.add_init_param("RS232 User interface.Scaling.Position.Value Open Position")
        self.param_worker.add_init_param("RS232 User interface.Scaling.Position.Value Closest Position")

        self.param_worker.sig_progress_changed.connect(self.handle_progress_changed)

    def on_clicked_connection_setting(self):
        WinManager().show_window(win_class=ConnectionSettingWin, parent=self, is_modal=True)

    def on_clicked_connection_connect(self):
        WinManager().show_window(win_class=ConnectionConnectWin, parent=self, is_modal=True)

    def on_clicked_connection_disconnect(self):
        reply = QMessageBox.question(self, "Confirm Disconnect", "Are you sure you want to disconnect?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            ServicePort().close()

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

    
