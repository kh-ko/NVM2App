

import json
import os
from PySide6.QtWidgets import (
    QMainWindow, QVBoxLayout, QHBoxLayout, QListWidget, 
    QPushButton, QMessageBox, QWidget, QFormLayout, 
    QLineEdit, QCheckBox, QSplitter, QComboBox,
    QLabel, QFrame
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtSerialPort import QSerialPort 
from b_core.a_define import file_folder_path

from c_ui.b_components.a_custom.custom_list import CustomListWidget
from c_ui.b_components.a_custom.custom_splitter import CustomSplitter
from c_ui.b_components.a_custom.custom_combobox import CustomComboBox
from c_ui.b_components.a_custom.custom_toolbar import CustomToolBar
from c_ui.b_components.a_custom.custom_panel import CustomPanel

class ConnectionSettingWin(QMainWindow):
    """
    connections.json 파일의 내용을 CRUD 할 수 있는 설정 창입니다. (마스터-카드 디테일 구조)
    Spliiter 왼쪽은 CustomListWidget, 오른쪽은 CustomPanel로 구성한다.
    CustomListWidget는 json 파일의 "name" 항목을 리스트로 표현한다.
    CustomPanel의 항목은 아래와 같이 구성한다.
      * "name" - text 입력창으로 표현한다.
      * "network"(아직은 사용자 입력을 비활성화 해야됩니다. 구현 예정 기능) - CustomComboBox 로 표현한다.(0 : RS232, 1 : RS485, 2 : TCP/IP)
      * "address"(아직은 사용자 입력을 비활성화 해야됩니다. 구현 예정 기능) - text 입력 창으로 표현한다.
      * "baudrate", "dataBits", "parity", "stopBits" - QSerialPort의 값과 매칭되는 CustomComboBox로 표현한다.
      * "termination": CustomComboBox 로 표현한다.(0 : CR+LF, 1 : LF, 2 : CR)
      * "isSelect" : CheckBox 로 표현한다.,  
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Connection >> Settings")
        self.resize(750, 450)
        
        self.json_path = file_folder_path.RSRC_CONNECTIONS_JSON_FILE
        self.connection_data = []
        self.current_index = -1
        
        self.init_ui()

    def init_ui(self):
        self.toolbar = CustomToolBar(self) # 이전에 만든 Custom 툴바 클래스
        self.addToolBar(Qt.TopToolBarArea, self.toolbar)
        self.toolbar.add_action("추가", self.add_connection_info)
        self.toolbar.add_action("저장", self.save_connection_info)
        self.toolbar.add_action("삭제", self.delete_connection_info)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

    def _load_connection_infos(self):
        pass
    # 현재 CustomPanel의 내용으로 self.connection_data의 항목을 추가하고 self.connection_data를 다시 json파일로 덮어쓴다.
    # 단 항목을 추가할때 name은 적절한 값으로 변경해야된다.
    def add_connection_info(self):
        pass

    # 현재 CustomPanel의 내용으로 json 파일의 내용을 갱신한다.
    # self.connection_data의 해당 항목을 갱신하고 self.connection_data를 다시 json파일로 덮어쓴다.
    def save_connection_info(self):
        pass

    # 현재 선택된 item을 삭제하고 리스트의 첫번째 항목이 선택되도록 한다.
    # 단 item이 하나만 남아있을 경우 삭제 할수 없다는 알림창을 띄운다.
    def delete_connection_info(self):
        pass

    # CustomPanel의 값을 새로 선택된 item 값으로 갱신한다.
    def on_change_item(self):
        pass