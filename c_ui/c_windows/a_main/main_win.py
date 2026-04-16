from b_core.d_dal.service_port import ServicePort
from PySide6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QLabel, QMessageBox
from PySide6.QtCore import Qt

from b_core.a_define import app_info

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

        self.main_toolbar.reg_connection_settings_slot(self.open_connection_setting)
        self.main_toolbar.reg_connection_connect_slot(self.open_connection_connect)
        self.main_toolbar.reg_connection_disconnect_slot(self.disconnect)
        # 4. 상태바(Status Bar) 초기화
        self.custom_statusbar = UserStatusBar(self)
        self.setStatusBar(self.custom_statusbar)

    def open_connection_setting(self):
        WinManager().show_window(win_class=ConnectionSettingWin, parent=self, is_modal=True)

    def open_connection_connect(self):
        WinManager().show_window(win_class=ConnectionConnectWin, parent=self, is_modal=True)

    def disconnect(self):
        reply = QMessageBox.question(self, "Confirm Disconnect", "Are you sure you want to disconnect?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            ServicePort().close()
