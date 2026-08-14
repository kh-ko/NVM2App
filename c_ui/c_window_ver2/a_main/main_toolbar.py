"""메인 윈도우 상단 툴바 (기존 main_top_toolbar.py 의 MainTopToolBar 대응).

ver1 에서 달라진 점:
- QToolButton + setProperty("menuBtn", "true") 매직 프로퍼티 대신
  자기 스타일을 소유하는 BaseToolButton / LampToolButton 을 사용한다.
- 드롭다운 버튼마다 반복되던 [버튼 생성 -> 메뉴 생성 -> 액션 조립 -> 장착]
  보일러플레이트를 _add_menu_button() 헬퍼로 통합.
- reg_*_slot 래퍼 메서드(45개)를 제거. 액션(action_*)과 버튼(*_btn)이 모두
  공개 속성이므로 호출측에서 직접 연결한다:
      toolbar.action_connection_connect.triggered.connect(slot, Qt.QueuedConnection)
      toolbar.local_btn.clicked.connect(slot, Qt.QueuedConnection)
- 오타 수정: advenced -> advanced, lagacy -> legacy (속성명 / UI 텍스트)
"""

from b_core.b_datatype.param_enum import SysUserInterfaceEnum
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QMenu, QToolButton

from c_ui.b_control_ver2.b_base.toolbars import (BaseToolBar, BaseToolButton,
                                                 LampToolButton)


class MainToolBar(BaseToolBar):

    # Interface 메뉴에서 DeviceNet 항목을 노출할 인터페이스 종류
    _DNET_IFACES = (
        SysUserInterfaceEnum.DEVICENET.value,
        SysUserInterfaceEnum.DEVICENET_LEGACY_MKS.value,
        SysUserInterfaceEnum.DEVICENET_APSYSTEM.value,
        SysUserInterfaceEnum.DEVICENET_NORCAL.value,
    )

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMovable(True)
        self.setFloatable(True)

        # Local / Remote 상태 램프 버튼
        self.local_btn = LampToolButton(self)
        self.local_btn.setText("Local")
        self.local_btn.set_accent(False)
        self.addWidget(self.local_btn)

        self.remote_btn = LampToolButton(self)
        self.remote_btn.setText("Remote")
        self.remote_btn.set_accent(False)
        self.addWidget(self.remote_btn)

        self.addSeparator()

        # Refresh (메뉴 없는 단일 버튼 — 외부 연결용 액션을 함께 노출)
        self.action_refresh = QAction("Refresh", self)
        self.refresh_btn = BaseToolButton(self)
        self.refresh_btn.setText("Refresh")
        self.refresh_btn.clicked.connect(self.action_refresh.trigger)
        self.addWidget(self.refresh_btn)

        # Connection
        self.action_connection_connect = QAction("Connect", self)
        self.action_connection_disconnect = QAction("Disconnect", self)
        self.action_connection_settings = QAction("Settings", self)
        self.conn_btn, self.conn_menu = self._add_menu_button("Connection", [
            self.action_connection_connect,
            self.action_connection_disconnect,
            None,
            self.action_connection_settings,
        ])

        self.addSeparator()

        # System
        self.action_sys_identification = QAction("Identification", self)
        self.action_sys_statistics = QAction("Statistics", self)
        self.action_sys_warning_error = QAction("Warning/Error", self)
        self.action_sys_service = QAction("Service", self)
        self.sys_btn, self.sys_menu = self._add_menu_button("System", [
            self.action_sys_identification,
            self.action_sys_statistics,
            self.action_sys_warning_error,
            self.action_sys_service,
        ])

        # Valve
        self.action_valve_basic = QAction("Basic State", self)
        self.action_valve_cycle = QAction("Cycle Counter", self)
        self.action_valve_setting = QAction("Settings", self)
        self.valve_btn, self.valve_menu = self._add_menu_button("Valve", [
            self.action_valve_basic,
            self.action_valve_cycle,
            self.action_valve_setting,
        ])

        # Sensor
        self.action_sens_zero = QAction("Zero Adjust", self)
        self.action_sens_setting = QAction("Settings", self)
        self.sens_btn, self.sens_menu = self._add_menu_button("Sensor", [
            self.action_sens_zero,
            self.action_sens_setting,
        ])

        # Position Control
        self.action_posi_ctrl_setting = QAction("Settings", self)
        self.posi_ctrl_btn, self.posi_ctrl_menu = self._add_menu_button(
            "Position Control", [
                self.action_posi_ctrl_setting,
            ])

        # Pressure Control
        self.action_pres_ctrl_gen_setting = QAction("General Settings", self)
        self.action_pres_ctrl_controller_setting = QAction("Controller Settings", self)
        self.pres_ctrl_btn, self.pres_ctrl_menu = self._add_menu_button(
            "Pressure Control", [
                self.action_pres_ctrl_gen_setting,
                self.action_pres_ctrl_controller_setting,
            ])

        # Learn
        self.action_learn = QAction("Learn Execute", self)
        self.action_learn_bank1_setting = QAction("Learn Bank 1 Settings", self)
        self.action_learn_bank2_setting = QAction("Learn Bank 2 Settings", self)
        self.action_learn_bank3_setting = QAction("Learn Bank 3 Settings", self)
        self.action_learn_bank4_setting = QAction("Learn Bank 4 Settings", self)
        self.action_learn_list_setting = QAction("Learn List Settings", self)
        self.learn_btn, self.learn_menu = self._add_menu_button("Learn", [
            self.action_learn,
            self.action_learn_bank1_setting,
            self.action_learn_bank2_setting,
            self.action_learn_bank3_setting,
            self.action_learn_bank4_setting,
            self.action_learn_list_setting,
        ])

        # Power Fail Options
        self.action_pfo_setting = QAction("Settings", self)
        self.pfo_btn, self.pfo_menu = self._add_menu_button("Power Fail Options", [
            self.action_pfo_setting,
        ])

        # Interface — dnet / ethercat 액션은 set_iface() 가 조건부로 노출한다
        self.action_iface_pwr_io = QAction("Power Connector IO Settings", self)
        self.action_iface_dnet = QAction("DeviceNet Settings", self)
        self.action_iface_ethercat = QAction("EtherCAT Settings", self)
        self.action_iface_trace = QAction("Trace", self)
        self.iface_btn, self.iface_menu = self._add_menu_button("Interface", [
            self.action_iface_pwr_io,
            self.action_iface_trace,
        ])

        # Cluster
        self.action_cluster_master = QAction("Master Settings", self)
        self.action_cluster_monitor = QAction("Cluster Monitor", self)
        self.cluster_btn, self.cluster_menu = self._add_menu_button("Cluster", [
            self.action_cluster_master,
            self.action_cluster_monitor,
        ])

        # Compound
        self.action_compound_compound1 = QAction("Compound 1 Settings", self)
        self.action_compound_compound2 = QAction("Compound 2 Settings", self)
        self.action_compound_compound3 = QAction("Compound 3 Settings", self)
        self.action_compound_compound4 = QAction("Compound 4 Settings", self)
        self.compound_btn, self.compound_menu = self._add_menu_button("Compound", [
            self.action_compound_compound1,
            self.action_compound_compound2,
            self.action_compound_compound3,
            self.action_compound_compound4,
        ])

        # Advanced Setup
        self.action_advanced_backup = QAction("Backup", self)
        self.action_advanced_restore = QAction("Restore", self)
        self.action_advanced_legacy = QAction("Legacy Parameter Settings", self)
        self.advanced_btn, self.advanced_menu = self._add_menu_button(
            "Advanced Setup", [
                self.action_advanced_backup,
                self.action_advanced_restore,
                self.action_advanced_legacy,
            ])

        # Analysis
        self.action_analysis_sensor = QAction("Sensor Analysis", self)
        self.action_analysis_chart = QAction("Chart Analysis", self)
        self.action_analysis_terminal = QAction("Terminal", self)
        self.analysis_btn, self.analysis_menu = self._add_menu_button("Analysis", [
            self.action_analysis_sensor,
            self.action_analysis_chart,
            self.action_analysis_terminal,
        ])

        # Factory
        self.action_fac_adc_calib = QAction("ADC Calibration", self)
        self.action_fac_firmware_update = QAction("Firmware Update", self)
        self.factory_btn, self.factory_menu = self._add_menu_button("Factory", [
            self.action_fac_adc_calib,
            self.action_fac_firmware_update,
        ])

        # Help
        self.action_help_update = QAction("Update", self)
        self.action_help_about = QAction("About", self)
        self.help_btn, self.help_menu = self._add_menu_button("Help", [
            self.action_help_update,
            self.action_help_about,
        ])

    def _add_menu_button(self, text: str, actions) -> tuple[BaseToolButton, QMenu]:
        """드롭다운 메뉴 툴버튼을 만들어 툴바에 장착한다. actions 의 None 은 구분선."""
        btn = BaseToolButton(self)
        btn.setText(text)
        btn.setPopupMode(QToolButton.InstantPopup)  # 클릭 시 즉시 메뉴 펼침

        menu = QMenu(btn)
        for action in actions:
            if action is None:
                menu.addSeparator()
            else:
                menu.addAction(action)

        btn.setMenu(menu)
        self.addWidget(btn)
        return btn, menu

    def set_iface(self, value) -> None:
        """인터페이스 종류에 따라 Interface 메뉴의 항목 구성을 갱신한다."""
        self.iface_menu.clear()
        self.iface_menu.addAction(self.action_iface_pwr_io)

        if value in self._DNET_IFACES:
            self.iface_menu.addAction(self.action_iface_dnet)
        elif value == SysUserInterfaceEnum.ETHERCAT.value:
            self.iface_menu.addAction(self.action_iface_ethercat)

        self.iface_menu.addAction(self.action_iface_trace)
