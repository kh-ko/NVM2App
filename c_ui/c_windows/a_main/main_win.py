from PySide6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QLabel
from PySide6.QtCore import Qt

from b_core.a_define import app_info

from c_ui.c_windows.a_main.main_top_toolbar import MainTopToolBar

class MainWin(QMainWindow):
    """
    애플리케이션의 메인 윈도우 클래스입니다.
    """
    def __init__(self):
        super().__init__()

        # 1. 기본 윈도우 설정 (app_info에서 정의된 이름을 가져와 동적으로 설정)
        self.setWindowTitle(app_info.APP_DISPLAY_TITLE)
        self.resize(1024, 690)  # 초기 윈도우 크기 설정

        self.main_toolbar = MainTopToolBar("Main Toolbar")
        self.addToolBar(Qt.TopToolBarArea, self.main_toolbar)
        # 4. 상태바(Status Bar) 초기화
        self.statusBar().showMessage("준비 완료")

    def init_ui(self):
        """
        추가적인 UI 구성 요소 초기화가 필요할 경우 사용합니다.
        """
        pass
