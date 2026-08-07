from PySide6.QtWidgets import QListWidgetItem, QMainWindow, QHBoxLayout, QWidget
from PySide6.QtCore import Qt

from b_core.e_worker_ver2.comport_scan_run_worker import ComportScanRunWorker
from b_core.d_dal.service_port import ServicePort
from b_core.c_manager.connection_setting_manager import ConnectionSettingManager

from c_ui.b_control_ver2.b_base.containers import BaseListWidget, BaseSplitter
from c_ui.b_control_ver2.b_base.toolbars import BaseToolBar
from c_ui.c_window_ver2.x_message.wait_message_box import show_wait_message_box

class ConnectionConnectWin(QMainWindow):
    """
    통신 설정 목록(ConnectionSettingManager)에서 선택된 설정 정보를 바탕으로
    마스터(PC)에서 사용 가능한 시리얼(Serial) 포트를 검색하여 연결을 수행하는 윈도우 클래스입니다.
    마스터-디테일(Master-Detail) 구조로 구현되어 있으며, 좌우 스플리터(Splitter)로 영역을 분할합니다.
    (통신 설정의 로드/저장/선택 상태 관리는 ConnectionSettingManager 가 전담합니다)

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

        self.conn_manager = ConnectionSettingManager()
        self._open_port_name = None  # 더블클릭으로 선택된 연결 대상 포트
        self._wait_box = None        # 스캔 종료 대기 안내 박스

        self.scan_worker = ComportScanRunWorker(self.handle_ports_found, self.handle_port_checked, self.handle_scan_stopped, parent=self)
        self.scan_worker.sig_wait_started.connect(self.handle_wait_started)
        self.scan_worker.sig_wait_finished.connect(self.handle_wait_finished)

        self._is_closing = False

        self._init_ui()
        self._load_connection_list()

        # 설정 윈도우 등에서 목록이 바뀌면 리스트 갱신
        self.conn_manager.sig_list_changed.connect(self._load_connection_list)

    def _init_ui(self):
        self.toolbar = BaseToolBar(self)
        self.addToolBar(Qt.TopToolBarArea, self.toolbar)
        self.toolbar.add_action("Scan", self.on_clicked_scan)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)

        # Splitter
        self.splitter = BaseSplitter(Qt.Horizontal)
        main_layout.addWidget(self.splitter)

        # Left: List Widget
        self.connection_list_widget = BaseListWidget()
        self.connection_list_widget.currentRowChanged.connect(self.on_change_connection_item)
        self.splitter.addWidget(self.connection_list_widget)

        # Right: Panel
        self.port_list_widget = BaseListWidget()
        self.port_list_widget.doubleClicked.connect(self.on_select_port_item)
        self.splitter.addWidget(self.port_list_widget)

        self.splitter.setSizes([200, 550])

    def _load_connection_list(self):
        self.connection_list_widget.clear()
        for name in self.conn_manager.names():
            self.connection_list_widget.addItem(name)

        # 선택 항목 복원 (setCurrentRow -> on_change_connection_item 에서 스캔 시작)
        self.connection_list_widget.setCurrentRow(self.conn_manager.selected_index())

    def on_clicked_scan(self):
        setting = self.conn_manager.selected()
        if setting is not None:
            self.scan_worker.start(setting)

    def on_change_connection_item(self, index):
        if index < 0 or index >= self.conn_manager.count():
            return

        self.conn_manager.select(index)
        self.scan_worker.start(self.conn_manager.get(index))

    def on_select_port_item(self, index):
        if self.conn_manager.selected() is None:
            return

        item = self.port_list_widget.item(index.row())
        if item is not None:
            self._open_port_name = item.data(Qt.UserRole)

            if self.scan_worker.stop():
                self.handle_scan_stopped()

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

    def handle_wait_started(self, title: str, message: str):
        self._wait_box = show_wait_message_box(self, title, message)

    def handle_wait_finished(self):
        if self._wait_box is not None:
            self._wait_box.accept()
            self._wait_box = None

    def handle_scan_stopped(self):
        self._execute_port_open()
        self._is_closing = True
        self.close()

    def _execute_port_open(self):
        if self._open_port_name is None:
            return

        setting = self.conn_manager.selected()
        if setting is None:
            return

        ServicePort().open(self._open_port_name,
                           setting["baudrate"],
                           setting["dataBits"],
                           setting["parity"],
                           setting["stopBits"],
                           setting["termination"])

    def closeEvent(self, event):
        if self._is_closing:
            event.accept()
            return

        if self.scan_worker.stop():
            event.accept()
        else:
            event.ignore()
