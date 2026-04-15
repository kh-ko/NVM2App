from PySide6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QLabel
from PySide6.QtCore import Qt

from b_core.a_define import app_info

from c_ui.c_windows.win_manager import WinManager
from c_ui.c_windows.a_main.main_top_toolbar import MainTopToolBar
from c_ui.c_windows.b_connection.connection_setting_win import ConnectionSettingWin

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
        # 4. 상태바(Status Bar) 초기화
        self.statusBar().showMessage("준비 완료")

    def open_connection_setting(self):
        WinManager().show_window(win_class=ConnectionSettingWin, parent=self, is_modal=True)
