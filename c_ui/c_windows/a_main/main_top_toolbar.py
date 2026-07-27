from b_core.b_datatype.param_enum import SysUserInterfaceEnum
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
        self.refresh_btn = QToolButton(self)
        self.refresh_btn.setText("Refresh")
        self.refresh_btn.setProperty("menuBtn", "true")
        self.refresh_btn.clicked.connect(self.action_refresh.trigger)
        self.addWidget(self.refresh_btn)

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

        self.addSeparator()

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

        self.action_valve_basic       = QAction("Basic State"         , self)
        self.action_valve_cycle       = QAction("Cycle Counter"       , self)
        self.action_valve_setting     = QAction("Settings"             , self)

        self.valve_menu.addAction(self.action_valve_basic      )
        self.valve_menu.addAction(self.action_valve_cycle      )
        self.valve_menu.addAction(self.action_valve_setting    )

        self.valve_btn.setMenu(self.valve_menu)
        self.addWidget(self.valve_btn)   

        self.sens_btn = QToolButton(self)
        self.sens_btn.setText("Sensor")
        self.sens_btn.setProperty("menuBtn", "true") # 커스텀 CSS(마우스 오버 등) 적용
        self.sens_btn.setPopupMode(QToolButton.InstantPopup) # 클릭 시 즉시 메뉴 펼침

        self.sens_menu = QMenu(self.sens_btn)

        self.action_sens_zero    = QAction("Zero Adjust", self)
        self.action_sens_setting = QAction("Settings"   , self)

        self.sens_menu.addAction(self.action_sens_zero    )
        self.sens_menu.addAction(self.action_sens_setting )

        self.sens_btn.setMenu(self.sens_menu)
        self.addWidget(self.sens_btn) 

        self.posi_ctrl_btn = QToolButton(self)
        self.posi_ctrl_btn.setText("Position Control")
        self.posi_ctrl_btn.setProperty("menuBtn", "true") # 커스텀 CSS(마우스 오버 등) 적용
        self.posi_ctrl_btn.setPopupMode(QToolButton.InstantPopup) # 클릭 시 즉시 메뉴 펼침

        self.posi_ctrl_menu = QMenu(self.posi_ctrl_btn)

        self.action_posi_ctrl_setting = QAction("Settings", self)

        self.posi_ctrl_menu.addAction(self.action_posi_ctrl_setting)

        self.posi_ctrl_btn.setMenu(self.posi_ctrl_menu)
        self.addWidget(self.posi_ctrl_btn)   

        # Pressure Control
        self.pres_ctrl_btn = QToolButton(self)
        self.pres_ctrl_btn.setText("Pressure Control")
        self.pres_ctrl_btn.setProperty("menuBtn", "true") # 커스텀 CSS(마우스 오버 등) 적용
        self.pres_ctrl_btn.setPopupMode(QToolButton.InstantPopup) # 클릭 시 즉시 메뉴 펼침

        self.pres_ctrl_menu = QMenu(self.pres_ctrl_btn)

        self.action_pres_ctrl_gen_setting = QAction("General Settings", self)
        self.action_pres_ctrl_controller_setting = QAction("Controller Settings", self)

        self.pres_ctrl_menu.addAction(self.action_pres_ctrl_gen_setting)
        self.pres_ctrl_menu.addAction(self.action_pres_ctrl_controller_setting)

        self.pres_ctrl_btn.setMenu(self.pres_ctrl_menu)
        self.addWidget(self.pres_ctrl_btn)  

        # Learn
        self.learn_btn = QToolButton(self)
        self.learn_btn.setText("Learn")
        self.learn_btn.setProperty("menuBtn", "true") # 커스텀 CSS(마우스 오버 등) 적용
        self.learn_btn.setPopupMode(QToolButton.InstantPopup) # 클릭 시 즉시 메뉴 펼침

        self.learn_menu = QMenu(self.learn_btn)

        self.action_learn = QAction("Learn Execute", self)
        self.action_learn_bank1_setting = QAction("Learn Bank 1 Settings", self)
        self.action_learn_bank2_setting = QAction("Learn Bank 2 Settings", self)
        self.action_learn_bank3_setting = QAction("Learn Bank 3 Settings", self)
        self.action_learn_bank4_setting = QAction("Learn Bank 4 Settings", self)
        self.action_learn_list_setting  = QAction("Learn List Settings", self)

        self.learn_menu.addAction(self.action_learn)
        self.learn_menu.addAction(self.action_learn_bank1_setting)
        self.learn_menu.addAction(self.action_learn_bank2_setting)
        self.learn_menu.addAction(self.action_learn_bank3_setting)
        self.learn_menu.addAction(self.action_learn_bank4_setting)
        self.learn_menu.addAction(self.action_learn_list_setting)

        self.learn_btn.setMenu(self.learn_menu)
        self.addWidget(self.learn_btn) 

        # PFO
        self.pfo_btn = QToolButton(self)
        self.pfo_btn.setText("Power Fail Options")
        self.pfo_btn.setProperty("menuBtn", "true") # 커스텀 CSS(마우스 오버 등) 적용
        self.pfo_btn.setPopupMode(QToolButton.InstantPopup) # 클릭 시 즉시 메뉴 펼침

        self.pfo_menu = QMenu(self.pfo_btn)

        self.action_pfo_setting = QAction("Settings", self)

        self.pfo_menu.addAction(self.action_pfo_setting)

        self.pfo_btn.setMenu(self.pfo_menu)
        self.addWidget(self.pfo_btn) 

        # Interface
        self.iface_btn = QToolButton(self)
        self.iface_btn.setText("Interface")
        self.iface_btn.setProperty("menuBtn", "true") # 커스텀 CSS(마우스 오버 등) 적용
        self.iface_btn.setPopupMode(QToolButton.InstantPopup) # 클릭 시 즉시 메뉴 펼침

        self.iface_menu = QMenu(self.iface_btn)

        self.action_iface_pwr_io = QAction("Power Connector IO Settings", self)
        self.action_iface_dnet   = QAction("DeviceNet Settings", self)
        self.action_iface_trace  = QAction("Trace", self)

        self.iface_menu.addAction(self.action_iface_pwr_io)
        self.iface_menu.addAction(self.action_iface_trace)

        self.iface_btn.setMenu(self.iface_menu)
        self.addWidget(self.iface_btn)    

        # Cluster
        self.cluster_btn = QToolButton(self)
        self.cluster_btn.setText("Cluster")
        self.cluster_btn.setProperty("menuBtn", "true")
        self.cluster_btn.setPopupMode(QToolButton.InstantPopup)

        self.cluster_menu = QMenu(self.cluster_btn)

        self.action_cluster_master = QAction("Master Settings", self)
        self.action_cluster_monitor = QAction("Cluster Monitor", self)

        self.cluster_menu.addAction(self.action_cluster_master)
        self.cluster_menu.addAction(self.action_cluster_monitor)

        self.cluster_btn.setMenu(self.cluster_menu)
        self.addWidget(self.cluster_btn)        

        # Compound
        self.compound_btn = QToolButton(self)
        self.compound_btn.setText("Compound")
        self.compound_btn.setProperty("menuBtn", "true")
        self.compound_btn.setPopupMode(QToolButton.InstantPopup)

        self.compound_menu = QMenu(self.compound_btn)

        self.action_compound_compound1 = QAction("Compound 1 Settings", self)
        self.action_compound_compound2 = QAction("Compound 2 Settings", self)
        self.action_compound_compound3 = QAction("Compound 3 Settings", self)
        self.action_compound_compound4 = QAction("Compound 4 Settings", self)

        self.compound_menu.addAction(self.action_compound_compound1)
        self.compound_menu.addAction(self.action_compound_compound2)
        self.compound_menu.addAction(self.action_compound_compound3)
        self.compound_menu.addAction(self.action_compound_compound4)

        self.compound_btn.setMenu(self.compound_menu)
        self.addWidget(self.compound_btn)     

        # Advenced Setup
        self.advenced_btn = QToolButton(self)
        self.advenced_btn.setText("Advenced Setup")
        self.advenced_btn.setProperty("menuBtn", "true")
        self.advenced_btn.setPopupMode(QToolButton.InstantPopup)

        self.advenced_menu = QMenu(self.advenced_btn)

        self.action_advenced_backup    = QAction("Backup", self)
        self.action_advenced_restore   = QAction("Restore", self)
        self.action_advenced_lagacy    = QAction("Legacy Parameter Settings", self)

        self.advenced_menu.addAction(self.action_advenced_backup)
        self.advenced_menu.addAction(self.action_advenced_restore)
        self.advenced_menu.addAction(self.action_advenced_lagacy)

        self.advenced_btn.setMenu(self.advenced_menu)
        self.addWidget(self.advenced_btn)                   

        #Analysis
        self.analysis_btn = QToolButton(self)
        self.analysis_btn.setText("Analysis")
        self.analysis_btn.setProperty("menuBtn", "true") # 커스텀 CSS(마우스 오버 등) 적용
        self.analysis_btn.setPopupMode(QToolButton.InstantPopup) # 클릭 시 즉시 메뉴 펼침

        self.analysis_menu = QMenu(self.analysis_btn)

        self.action_analysis_sensor = QAction("Sensor Analysis", self)
        self.action_analysis_terminal = QAction("Terminal", self)

        self.analysis_menu.addAction(self.action_analysis_sensor)
        self.analysis_menu.addAction(self.action_analysis_terminal)

        self.analysis_btn.setMenu(self.analysis_menu)
        self.addWidget(self.analysis_btn) 

        #Factory
        self.factory_btn = QToolButton(self)
        self.factory_btn.setText("Factory")
        self.factory_btn.setProperty("menuBtn", "true") # 커스텀 CSS(마우스 오버 등) 적용
        self.factory_btn.setPopupMode(QToolButton.InstantPopup) # 클릭 시 즉시 메뉴 펼침

        self.factory_menu = QMenu(self.factory_btn)

        self.action_fac_adc_calib = QAction("ADC Calibration", self)
        self.action_fac_firmware_update = QAction("Firmware Update", self)

        self.factory_menu.addAction(self.action_fac_adc_calib)
        self.factory_menu.addAction(self.action_fac_firmware_update)

        self.factory_btn.setMenu(self.factory_menu)
        self.addWidget(self.factory_btn)       

        #Help
        self.help_btn = QToolButton(self)
        self.help_btn.setText("Help")
        self.help_btn.setProperty("menuBtn", "true") # 커스텀 CSS(마우스 오버 등) 적용
        self.help_btn.setPopupMode(QToolButton.InstantPopup) # 클릭 시 즉시 메뉴 펼침

        self.help_menu = QMenu(self.help_btn)

        self.action_help_update = QAction("Update", self)
        self.action_help_about = QAction("About", self)

        self.help_menu.addAction(self.action_help_update)
        self.help_menu.addAction(self.action_help_about)

        self.help_btn.setMenu(self.help_menu)
        self.addWidget(self.help_btn)           

    def set_iface(self, value):
        self.iface_menu.clear()
        self.iface_menu.addAction(self.action_iface_pwr_io)

        if value == SysUserInterfaceEnum.DEVICENET.value or value == SysUserInterfaceEnum.DEVICENET_LEGACY_MKS.value or value == SysUserInterfaceEnum.DEVICENET_APSYSTEM.value or value == SysUserInterfaceEnum.DEVICENET_NORCAL.value:
            self.iface_menu.addAction(self.action_iface_dnet)

        self.iface_menu.addAction(self.action_iface_trace)


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

    def reg_valve_cycle_counter_slot(self, slot):
        self.action_valve_cycle.triggered.connect(slot, Qt.QueuedConnection)

    def reg_valve_setting_slot(self, slot):
        self.action_valve_setting.triggered.connect(slot, Qt.QueuedConnection)   

    def reg_sens_zero_slot(self, slot):
        self.action_sens_zero.triggered.connect(slot, Qt.QueuedConnection)

    def reg_sens_setting_slot(self, slot):
        self.action_sens_setting.triggered.connect(slot, Qt.QueuedConnection) 

    def reg_posi_ctrl_setting_slot(self, slot):
        self.action_posi_ctrl_setting.triggered.connect(slot, Qt.QueuedConnection) 

    def reg_pres_ctrl_gen_setting_slot(self, slot):
        self.action_pres_ctrl_gen_setting.triggered.connect(slot, Qt.QueuedConnection)

    def reg_pres_ctrl_controller_setting_slot(self, slot):
        self.action_pres_ctrl_controller_setting.triggered.connect(slot, Qt.QueuedConnection)

    def reg_learn_slot(self, slot):
        self.action_learn.triggered.connect(slot, Qt.QueuedConnection)

    def reg_learn_bank1_setting_slot(self, slot):
        self.action_learn_bank1_setting.triggered.connect(slot, Qt.QueuedConnection)  

    def reg_learn_bank2_setting_slot(self, slot):
        self.action_learn_bank2_setting.triggered.connect(slot, Qt.QueuedConnection)  

    def reg_learn_bank3_setting_slot(self, slot):
        self.action_learn_bank3_setting.triggered.connect(slot, Qt.QueuedConnection)  

    def reg_learn_bank4_setting_slot(self, slot):
        self.action_learn_bank4_setting.triggered.connect(slot, Qt.QueuedConnection)  

    def reg_learn_list_setting_slot(self, slot):
        self.action_learn_list_setting.triggered.connect(slot, Qt.QueuedConnection)  

    def reg_pfo_setting_slot(self, slot):
        self.action_pfo_setting.triggered.connect(slot, Qt.QueuedConnection)  

    def reg_iface_pwr_io_slot(self, slot):
        self.action_iface_pwr_io.triggered.connect(slot, Qt.QueuedConnection)  

    def reg_iface_dnet_slot(self, slot):
        self.action_iface_dnet.triggered.connect(slot, Qt.QueuedConnection) 

    def reg_iface_trace_slot(self, slot):
        self.action_iface_trace.triggered.connect(slot, Qt.QueuedConnection) 

    def reg_cluster_master_setting_slot(self, slot):
        self.action_cluster_master.triggered.connect(slot, Qt.QueuedConnection)  

    def reg_cluster_monitor_slot(self, slot):
        self.action_cluster_monitor.triggered.connect(slot, Qt.QueuedConnection)          

    def reg_compound1_setting_slot(self, slot):
        self.action_compound_compound1.triggered.connect(slot, Qt.QueuedConnection)          

    def reg_compound2_setting_slot(self, slot):
        self.action_compound_compound2.triggered.connect(slot, Qt.QueuedConnection)    

    def reg_compound3_setting_slot(self, slot):
        self.action_compound_compound3.triggered.connect(slot, Qt.QueuedConnection)         

    def reg_compound4_setting_slot(self, slot):
        self.action_compound_compound4.triggered.connect(slot, Qt.QueuedConnection)                               

    def reg_advenced_backup_slot(self, slot):
        self.action_advenced_backup.triggered.connect(slot, Qt.QueuedConnection)  

    def reg_advenced_restore_slot(self, slot):
        self.action_advenced_restore.triggered.connect(slot, Qt.QueuedConnection)  

    def reg_advenced_lagacy_slot(self, slot):
        self.action_advenced_lagacy.triggered.connect(slot, Qt.QueuedConnection)  

    def reg_analysis_sensor_slot(self, slot):
        self.action_analysis_sensor.triggered.connect(slot, Qt.QueuedConnection)  

    def reg_analysis_terminal_slot(self, slot):
        self.action_analysis_terminal.triggered.connect(slot, Qt.QueuedConnection)  

    def reg_factory_adc_calib_slot(self, slot):
        self.action_fac_adc_calib.triggered.connect(slot, Qt.QueuedConnection)  

    def reg_factory_firmware_update_slot(self, slot):
        self.action_fac_firmware_update.triggered.connect(slot, Qt.QueuedConnection)  

    def reg_help_update_slot(self, slot):
        self.action_help_update.triggered.connect(slot, Qt.QueuedConnection)  

    def reg_help_about_slot(self, slot):
        self.action_help_about.triggered.connect(slot, Qt.QueuedConnection)  

    