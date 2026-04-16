
from b_core.d_dal.service_port import ServicePort
import json
import os
from PySide6.QtWidgets import (QListWidgetItem, QMainWindow, QVBoxLayout, QHBoxLayout, QListWidget, QPushButton, QMessageBox, QWidget, QFormLayout, QLineEdit, QCheckBox, QSplitter, QComboBox, QLabel, QFrame)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtSerialPort import QSerialPort
from b_core.a_define import file_folder_path

from b_core.e_worker.comport_scan_worker import PortScanThread

from c_ui.b_components.a_custom.custom_list import CustomListWidget
from c_ui.b_components.a_custom.custom_splitter import CustomSplitter
from c_ui.b_components.a_custom.custom_combobox import CustomComboBox
from c_ui.b_components.a_custom.custom_toolbar import CustomToolBar
from c_ui.b_components.a_custom.custom_panel import CustomPanel
from c_ui.b_components.a_custom.custom_line_edit import CustomLineEdit

class ConnectionConnectWin(QMainWindow):      
    """
    통신 설정(connections.json) 데이터를 로드하고, 선택된 통신 설정 정보를 바탕으로 
    마스터(PC)에서 사용 가능한 시리얼(Serial) 포트를 검색하여 연결을 수행하는 윈도우 클래스입니다.
    마스터-디테일(Master-Detail) 구조로 구현되어 있으며, 좌우 스플리터(Splitter)로 영역을 분할합니다.

    [주요 구성 및 동작]
    1. 화면 구성:
       - 툴바(TopToolBar): 전체 포트를 다시 검색하는 'Scan' 기능을 제공합니다.
       - 좌측 리스트(왼쪽): 저장된 통신 설정 항목 목록을 표시합니다.
       - 우측 리스트(오른쪽): 현재 PC에서 검색된 COM Port 목록과 연결(Open) 테스트 결과를 표시합니다.

    2. 포트 스캔 과정(PortScanThread 활용):
       - 통신 설정 리스트에서 특정 항목이 선택되거나 'Scan' 버튼을 누르면, 백그라운드 스레드에서 포트 검색을 시작합니다.
       - 기존에 진행 중인 스캔/연결 작업이 있다면 안전하게 중지(Stop)시킨 후 새로운 작업을 수행합니다.
       - 검색된 모든 COM Port에 대해 "Checking..." 상태로 등록 후, 
         선택된 통신 설정값을 이용해 순차적으로 포트를 'Open > Send("i:83\\r\\n") > Read > Close' 해보며 유효성을 판단합니다.
       - 연결에 성공하여 응답(Response)을 받은 포트는 활성화 상태와 함께 수신된 데이터를 표시하고, 실패한 포트는 비활성화됩니다.

    3. 사용자 연결 및 종료 처리:
       - 사용자가 우측 리스트에서 특정 COM Port 항목을 더블 클릭하면, 즉시 스캔을 멈추고 해당 포트로 최종 연결(`ServicePort().open()`)을 수행한 뒤 창을 닫습니다.
       - 윈도우가 닫힐 때(closeEvent), 진행 중인 스레드가 있다면 UI 프리징 없이 안전하게 스레드를 종료시킨 후 창을 닫습니다.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Connection >> Connect")
        self.resize(750, 450)
        
        self.json_path = file_folder_path.RSRC_CONNECTIONS_JSON_FILE
        self.connection_data = []
        self.selected_index = -1
        self.scan_thread = None
        self._is_closing = False

        self._init_ui()
        self._load_connection_infos()
        
    def _init_ui(self):
        self.toolbar = CustomToolBar(self) # 이전에 만든 Custom 툴바 클래스
        self.addToolBar(Qt.TopToolBarArea, self.toolbar)
        self.toolbar.add_action("Scan", self.on_clicked_scan)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)

        # Splitter
        self.splitter = CustomSplitter(Qt.Horizontal)
        main_layout.addWidget(self.splitter)

        # Left: List Widget
        self.connection_list_widget = CustomListWidget()
        self.connection_list_widget.currentRowChanged.connect(self.on_change_connection_item)
        self.splitter.addWidget(self.connection_list_widget)

        # Right: Panel
        self.port_list_widget = CustomListWidget()
        self.port_list_widget.doubleClicked.connect(self.on_select_port_item)
        self.splitter.addWidget(self.port_list_widget)

        self.splitter.setSizes([200, 550])

    def _load_connection_infos(self):
        self.connection_data = []

        # 1. 파일 존재 여부 확인 후 JSON 읽기
        if os.path.exists(self.json_path):
            try:
                with open(self.json_path, 'r', encoding='utf-8') as f:
                    self.connection_data = json.load(f)
            except Exception as e:
                pass
        
        # 2. 파일이 없거나 읽기 실패 시, 기본 데이터 1개 추가
        if not self.connection_data:
            default_data = {
                "name": "defalut",
                "network": 0,      #네트워크 방식(0=RS232, 1=RS485, 2=TCP/IP) - 현재 0번만 사용 가능
                "address": "",     #연결 주소 - 현재 사용 안함
                "baudrate": 38400, #통신 속도(9600~115200)
                "dataBits": 7,     #데이터 비트(5~8)
                "parity": 2,       #패리티 비트(0=NoParity, 2=EvenParity, 3=OddParity, 4=SpaceParity, 5=MarkParity)
                "stopBits": 1,     #정지 비트(1=OneStop, 2=TwoStop, 3=OneAndHalfStop)
                "termination": 0,  #종료 문자(0=CR+LF, 1=LF, 2=CR)
                "isSelect": True
            }
            self.connection_data.append(default_data)


        # 2. 읽어온 데이터에서 'name' 항목을 추출하여 리스트 위젯에 추가
        for item in self.connection_data:
            name = item.get("name", "Unknown")
            self.connection_list_widget.addItem(name)
            # isSelect가 True인 항목을 찾아서 선택
            if item.get("isSelect", False):
                self.selected_index = self.connection_list_widget.count() - 1
                self.connection_list_widget.setCurrentRow(self.selected_index)

        # 3. 데이터가 있다면 첫 번째 항목을 선택하도록 설정
        if self.selected_index < 0:
            self.connection_list_widget.setCurrentRow(0)
        else:
            self.connection_list_widget.setCurrentRow(self.selected_index)

    def on_clicked_scan(self):
        if self.selected_index >= 0:
            self.start_port_scan(self.connection_data[self.selected_index])

    def on_change_connection_item(self, index):
        if index < 0 or index >= len(self.connection_data):
            return

        for item in self.connection_data:
            item["isSelect"] = False

        self.connection_data[index]["isSelect"] = True
        self.selected_index = index

        try:            
            with open(self.json_path, 'w', encoding='utf-8') as f:
                json.dump(self.connection_data, f, indent=4, ensure_ascii=False)
        except Exception as e:
            pass

        self.start_port_scan(self.connection_data[self.selected_index])            

    def start_port_scan(self, connection_setting):
        if self.scan_thread is not None and self.scan_thread.isRunning():
            self._next_setting = connection_setting
            self._stop_current_thread("Preparing to scan...", "Please wait for the previous scan to complete...", self._on_previous_scan_finished)
            return 

        self._run_new_scan_thread(connection_setting)

    def _on_previous_scan_finished(self):
        self._cleanup_after_thread_stop()
        if hasattr(self, '_next_setting'):
            self._run_new_scan_thread(self._next_setting)

    def handle_ports_found(self, port_names):
        self.port_list_widget.clear()
        
        for port in port_names:
            item = QListWidgetItem(f"{port} : Checking...")
            item.setData(Qt.UserRole, port) # 이후 포트 이름으로 찾기 위해 Data에 저장
            self.port_list_widget.addItem(item)

    def handle_port_checked(self, port_name, success, response):
        for i in range(self.port_list_widget.count()):
            item = self.port_list_widget.item(i)
            if item.data(Qt.UserRole) == port_name:
                if success:
                    display_text = response if response else "Open Success (No Read Data)"
                    item.setText(f"{port_name} : {display_text}")
                    item.setFlags(item.flags() | Qt.ItemIsEnabled) # 활성화
                else:
                    display_text = response if response else "Open Failed"
                    item.setText(f"{port_name} : {display_text}")
                    item.setFlags(item.flags() & ~Qt.ItemIsEnabled) # 비활성화
                break            

    def on_select_port_item(self, index):
        if self.selected_index < 0 or self.selected_index >= len(self.connection_data):
            return
        
        item = self.port_list_widget.item(index.row())
        if item is not None:
            selected_port_name = item.data(Qt.UserRole)

            if self.scan_thread is not None and self.scan_thread.isRunning():
                self._open_port_name = selected_port_name
                self._stop_current_thread("Opening...", "Please wait for the previous opening to complete...", self._on_open_thread_finished)
                return 
            else:
                self._execute_port_open(selected_port_name)

    def _on_open_thread_finished(self):
        self._cleanup_after_thread_stop()
        if hasattr(self, '_open_port_name'):
            self._execute_port_open(self._open_port_name)

    def _execute_port_open(self, port_name):
        setting = self.connection_data[self.selected_index]
        ServicePort().open(port_name,
                           setting["baudrate"],
                           setting["dataBits"],
                           setting["parity"],
                           setting["stopBits"],
                           setting["termination"])
        self.close()            

    def closeEvent(self, event):
        if self._is_closing:
            event.accept()
            return

        if self.scan_thread is not None and self.scan_thread.isRunning():
            event.ignore() 
            self._stop_current_thread("Closing", "Please wait for the previous scan to complete...", self._on_close_thread_finished)
        else:
            event.accept()

    def _on_close_thread_finished(self):
        self._cleanup_after_thread_stop()
        self._is_closing = True 
        self.close()

    def _run_new_scan_thread(self, connection_setting):
        self.scan_thread = PortScanThread(ServicePort().get_port_name(), connection_setting)
        self.scan_thread.ports_found.connect(self.handle_ports_found)
        self.scan_thread.port_checked.connect(self.handle_port_checked)
        self.scan_thread.start()

    def _stop_current_thread(self, title, message, finished_slot):
        self.setEnabled(False)

        self.wait_msg_box = QMessageBox(self)
        self.wait_msg_box.setWindowTitle(title)
        self.wait_msg_box.setText(message)
        self.wait_msg_box.setStandardButtons(QMessageBox.StandardButton.NoButton)
        self.wait_msg_box.show()

        # 기존 시그널 해제 (오작동 방지)
        try:
            self.scan_thread.ports_found.disconnect()
            self.scan_thread.port_checked.disconnect()
        except Exception:
            pass

        self.scan_thread.finished.connect(finished_slot)
        self.scan_thread.stop()

    def _cleanup_after_thread_stop(self):
        if hasattr(self, 'wait_msg_box') and self.wait_msg_box:
            self.wait_msg_box.accept()
            self.wait_msg_box = None
            
        self.setEnabled(True)

        if self.scan_thread:
            try:
                self.scan_thread.finished.disconnect()
            except Exception:
                pass
            self.scan_thread.deleteLater()
            self.scan_thread = None