from c_ui.b_control_packet.controls.my_lamptoolbutton import MyLampToolButton
from PySide6.QtWidgets import QToolButton, QMenu
from PySide6.QtGui import QAction
from PySide6.QtCore import Qt

from c_ui.b_control_packet.base.base_toolbar import BaseToolBar

class MainTopToolBar(BaseToolBar):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMovable(True)   
        self.setFloatable(True) 
        
        self.local_btn = MyLampToolButton(self)
        self.local_btn.setText("Local")
        self.local_btn.set_accent(False)
        self.addWidget(self.local_btn)

        self.remote_btn = MyLampToolButton(self)
        self.remote_btn.setText("Remote")
        self.remote_btn.set_accent(False)
        self.addWidget(self.remote_btn)

        self.addSeparator()

        self.action_refresh = QAction("Refresh", self)
        self.addAction(self.action_refresh)

        # 1. Connection 툴버튼 생성
        self.conn_btn = QToolButton(self)
        self.conn_btn.setText("Connection")
        self.conn_btn.setProperty("menuBtn", "true") # 커스텀 CSS(마우스 오버 등) 적용
        self.conn_btn.setPopupMode(QToolButton.InstantPopup) # 클릭 시 즉시 메뉴 펼침

        # 2. 하위 메뉴(QMenu) 생성
        self.conn_menu = QMenu(self.conn_btn)

        # 3. 메뉴에 들어갈 액션 생성 (외부 윈도우에서 이벤트를 연결할 수 있도록 self로 선언)
        self.action_connect = QAction("Connect", self)
        self.action_disconnect = QAction("Disconnect", self)
        self.action_settings = QAction("Settings", self)

        # 4. 메뉴에 액션 및 구분선 조립
        self.conn_menu.addAction(self.action_connect)
        self.conn_menu.addAction(self.action_disconnect)
        self.conn_menu.addSeparator() # Settings 전에 가로 구분선 추가
        self.conn_menu.addAction(self.action_settings)

        # 5. 완성된 메뉴를 툴버튼에 달고, 툴바에 위젯으로 추가
        self.conn_btn.setMenu(self.conn_menu)
        self.addWidget(self.conn_btn)

        self.sys_btn = QToolButton(self)
        self.sys_btn.setText("System")
        self.sys_btn.setProperty("menuBtn", "true") # 커스텀 CSS(마우스 오버 등) 적용
        self.sys_btn.setPopupMode(QToolButton.InstantPopup) # 클릭 시 즉시 메뉴 펼침

        # 2. 하위 메뉴(QMenu) 생성
        self.sys_menu = QMenu(self.sys_btn)

        # 3. 메뉴에 들어갈 액션 생성 (외부 윈도우에서 이벤트를 연결할 수 있도록 self로 선언)
        self.action_sys_identification = QAction("Identification", self)
        self.action_sys_statistics = QAction("Statistics", self)
        self.action_sys_warning_error = QAction("Warning/Error", self)
        self.action_sys_service = QAction("Service", self)

        # 4. 메뉴에 액션 및 구분선 조립
        self.sys_menu.addAction(self.action_sys_identification)
        self.sys_menu.addAction(self.action_sys_statistics)
        self.sys_menu.addAction(self.action_sys_warning_error)
        self.sys_menu.addAction(self.action_sys_service)

        # 5. 완성된 메뉴를 툴버튼에 달고, 툴바에 위젯으로 추가
        self.sys_btn.setMenu(self.sys_menu)
        self.addWidget(self.sys_btn)        

        self.valve_btn = QToolButton(self)
        self.valve_btn.setText("Valve")
        self.valve_btn.setProperty("menuBtn", "true") # 커스텀 CSS(마우스 오버 등) 적용
        self.valve_btn.setPopupMode(QToolButton.InstantPopup) # 클릭 시 즉시 메뉴 펼침

        self.valve_menu = QMenu(self.valve_btn)

        self.action_valve_basic       = QAction("Basic"               , self)
        self.action_valve_air         = QAction("Compressed Air"      , self)
        self.action_valve_cycle       = QAction("Cycle Counter"       , self)
        self.action_valve_homeing     = QAction("Homing"              , self)
        self.action_valve_restriction = QAction("Position Restriction", self)
        self.action_valve_adaption    = QAction("Position Adaption"   , self)

        self.valve_menu.addAction(self.action_valve_basic      )
        self.valve_menu.addAction(self.action_valve_air        )
        self.valve_menu.addAction(self.action_valve_cycle      )
        self.valve_menu.addAction(self.action_valve_homeing    )
        self.valve_menu.addAction(self.action_valve_restriction)
        self.valve_menu.addAction(self.action_valve_adaption   )

        self.valve_btn.setMenu(self.valve_menu)
        self.addWidget(self.valve_btn)   

    def reg_local_btn_slot(self, slot):
        self.local_btn.clicked.connect(slot, Qt.QueuedConnection)

    def reg_remote_btn_slot(self, slot):
        self.remote_btn.clicked.connect(slot, Qt.QueuedConnection)

    def reg_connection_refresh_slot(self, slot):
        self.action_refresh.triggered.connect(slot, Qt.QueuedConnection)

    def reg_connection_connect_slot(self, slot):
        self.action_connect.triggered.connect(slot, Qt.QueuedConnection)
    
    def reg_connection_disconnect_slot(self, slot):
        self.action_disconnect.triggered.connect(slot, Qt.QueuedConnection)
    
    def reg_connection_settings_slot(self, slot):
        self.action_settings.triggered.connect(slot, Qt.QueuedConnection)

    def reg_sys_identification_slot(self, slot):
        self.action_sys_identification.triggered.connect(slot, Qt.QueuedConnection)

    def reg_sys_statistics_slot(self, slot):
        self.action_sys_statistics.triggered.connect(slot, Qt.QueuedConnection)

    def reg_sys_warning_error_slot(self, slot):
        self.action_sys_warning_error.triggered.connect(slot, Qt.QueuedConnection)

    def reg_sys_service_slot(self, slot):
        self.action_sys_service.triggered.connect(slot, Qt.QueuedConnection)

    def reg_valve_basic_slot(self, slot):
        self.action_valve_basic.triggered.connect(slot, Qt.QueuedConnection)

    def reg_valve_comporessed_air_slot(self, slot):
        self.action_valve_air.triggered.connect(slot, Qt.QueuedConnection)

    def reg_valve_cycle_counter_slot(self, slot):
        self.action_valve_cycle.triggered.connect(slot, Qt.QueuedConnection)

    def reg_valve_homing_slot(self, slot):
        self.action_valve_homeing.triggered.connect(slot, Qt.QueuedConnection)        

    def reg_valve_posi_restriction_slot(self, slot):
        self.action_valve_restriction.triggered.connect(slot, Qt.QueuedConnection)      

    def reg_valve_posi_adaption_slot(self, slot):
        self.action_valve_adaption.triggered.connect(slot, Qt.QueuedConnection)                    