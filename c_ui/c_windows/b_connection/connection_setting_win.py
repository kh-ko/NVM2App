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
from c_ui.b_components.a_custom.custom_line_edit import CustomLineEdit

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
        self.toolbar.add_action("Create", self.add_connection_info)
        self.toolbar.add_action("Save", self.save_connection_info)
        self.toolbar.add_action("Delete", self.delete_connection_info)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)

        # Splitter
        self.splitter = CustomSplitter(Qt.Horizontal)
        main_layout.addWidget(self.splitter)

        # Left: List Widget
        self.list_widget = CustomListWidget()
        self.list_widget.currentRowChanged.connect(self.on_change_item)
        self.splitter.addWidget(self.list_widget)

        # Right: Panel
        self.panel = CustomPanel("Detail")
        self.splitter.addWidget(self.panel)
        
        self.name_edit = CustomLineEdit("Name")
        self.panel.add_widget(self.name_edit)

        self.network_combo = CustomComboBox("Network")
        self.network_combo.addItem("RS232", 0)
        self.network_combo.addItem("RS485", 1)
        self.network_combo.addItem("TCP/IP", 2)
        self.network_combo.setEnabled(False)
        self.panel.add_widget(self.network_combo)

        self.address_edit = CustomLineEdit("Address")
        self.address_edit.setText("192.168.1.1")
        self.address_edit.setEnabled(False)
        self.panel.add_widget(self.address_edit)

        self.baudrate_combo = CustomComboBox("Baudrate")
        for br in [9600, 19200, 38400, 57600, 115200]:
            self.baudrate_combo.addItem(str(br), br)
        self.panel.add_widget(self.baudrate_combo)

        self.databits_combo = CustomComboBox("Data Bits")
        for db in [5, 6, 7, 8]:
            self.databits_combo.addItem(str(db), db)
        self.panel.add_widget(self.databits_combo)

        self.parity_combo = CustomComboBox("Parity")
        self.parity_combo.addItem("NoParity", 0)
        self.parity_combo.addItem("EvenParity", 2)
        self.parity_combo.addItem("OddParity", 3)
        self.parity_combo.addItem("SpaceParity", 4)
        self.parity_combo.addItem("MarkParity", 5)
        self.panel.add_widget(self.parity_combo)

        self.stopbits_combo = CustomComboBox("Stop Bits")
        self.stopbits_combo.addItem("OneStop", 1)
        self.stopbits_combo.addItem("TwoStop", 2)
        self.stopbits_combo.addItem("OneAndHalfStop", 3)
        self.panel.add_widget(self.stopbits_combo)

        self.termination_combo = CustomComboBox("Termination")
        self.termination_combo.addItem("CR+LF", 0)
        self.termination_combo.addItem("LF", 1)
        self.termination_combo.addItem("CR", 2)
        self.panel.add_widget(self.termination_combo)

        #self.is_select_check = QCheckBox()
        #self.form_layout.addRow("Is Select:", self.is_select_check)
        self.panel.add_stretch()

        self.splitter.setSizes([200, 550])

        self._load_connection_infos()

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