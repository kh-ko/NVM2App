from b_core.b_datatype.param_enum import ControlModeEnum
from b_core.b_datatype.param_enum import AccModeEnum
from b_core.b_datatype.param_enum import ClusterUnfreezeFreezeEnum
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout
from PySide6.QtWidgets import QWidget, QScrollArea, QVBoxLayout

from b_core.c_manager.parameter_manager import ParamManager

from c_ui.b_control_packet.param_container.param_folder_cluster_monitor_control_widget import ParamFolderClusterMonitorControlWidget
from c_ui.b_control_packet.param_container.param_folder_cluster_monitor_setting_widget import ParamFolderClusterMonitorSettingWidget
from c_ui.b_control_packet.param_container.param_folder_cluster_monitor_status_widget import ParamFolderClusterMonitorStatusWidget

from c_ui.b_control_packet.param_container.param_folder_cluster_monitor_widget import ParamFolderClusterMonitorWidget
from c_ui.b_control_packet.param_container.param_setting_win import ParamSettingWin

class ClusterMonitorWin(ParamSettingWin):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.resize(900, 650)
        self.setWindowTitle("Cluster >> Monitor")

        old_central = self.takeCentralWidget()
        if old_central:
            old_central.deleteLater()       

        self.content_widget = QWidget()

        layout = QVBoxLayout(self.content_widget)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # 특수 GUI 이므로 툴바는 기본 툴바로 설정되게 하기 위해 ParamFolder를 붙이기 전에 init_toolbar()를 호출하도록 한다.
        self.init_toolbar()

        self.cluster_monitor_folder = ParamFolderClusterMonitorWidget()
        self.parameter_folder_widgets.append(self.cluster_monitor_folder)         
        layout.addWidget(self.cluster_monitor_folder)

        bottom_layout = QHBoxLayout()
        bottom_layout.setContentsMargins(0, 0, 0, 0)
        bottom_layout.setSpacing(10)
        layout.addLayout(bottom_layout)

        self.status_widget = ParamFolderClusterMonitorStatusWidget()
        self.status_widget.setFixedHeight(380)
        bottom_layout.addWidget(self.status_widget,60)

        self.setting_widget = ParamFolderClusterMonitorSettingWidget()
        self.setting_widget.setFixedHeight(380)
        bottom_layout.addWidget(self.setting_widget,110)

        self.control_widget = ParamFolderClusterMonitorControlWidget()
        self.control_widget.setFixedHeight(380)
        bottom_layout.addWidget(self.control_widget, 70)

        self.setCentralWidget(self.content_widget)
        
        self.num_device_param = ParamManager().get_by_full_path("Cluster.Settings.Number of Valves")
        self.num_device_param.sig_value_changed.connect(self.handle_num_device_changed, type=Qt.QueuedConnection)
        self.param_worker.add_read_param_ptr(self.num_device_param)

        self._is_init = False
        self.handle_num_device_changed()

        self.init_end()
        self.cluster_monitor_folder.sig_selected_addr.connect(self.on_selected_addr_changed)
        self.setting_widget.sig_apply_clicked.connect(self.on_option_apply_clicked)
        self.control_widget.sig_unfreeze_clicked.connect(self.on_unfreeze_clicked)
        self.control_widget.sig_freeze_clicked.connect(self.on_freeze_clicked)
        self.control_widget.sig_target_posi_edit_finished.connect(self.on_target_posi_edit_finished)
        self.control_widget.sig_open_clicked.connect(self.on_open_clicked)
        self.control_widget.sig_close_clicked.connect(self.on_close_clicked)
        self.control_widget.sig_restart_clicked.connect(self.on_restart_clicked)

        self._is_init = True
        
    def handle_num_device_changed(self):
        num_device = self.num_device_param.value
        self.param_worker.clear_monitor_param()
        self.param_worker.clear_write_param()

        print("[ClusterMonitorWin][handle_num_device_changed]")

        if num_device is not None:
            for num in range(0, num_device):
                print(f"[ClusterMonitorWin][handle_num_device_changed] add cluster num = {num}")
                self.param_worker.add_write_param(f"Cluster.Device {num}.Setting.Option")
                self.param_worker.add_write_param(f"Cluster.Device {num}.Setting.Position Control Speed (%)")
                self.param_worker.add_write_param(f"Cluster.Device {num}.Setting.Position Offset")
                self.param_worker.add_write_param(f"Cluster.Device {num}.Control.Freeze")
                self.param_worker.add_write_param(f"Cluster.Device {num}.Control.Target Position")
                self.param_worker.add_write_param(f"Cluster.Device {num}.Control.Control Mode Setpoint")
                self.param_worker.add_monitor_param(f"Cluster.Device {num}.Status")

        self.cluster_monitor_folder.set_cluster_num(num_device)

        # 초기화 과정에서는 'self.init_end()' 에서 refresh를 호출한다.
        if self._is_init:
            self.param_worker.refresh()

    # 사용자가 refresh 버튼을 눌렀을때는 입력하고 있던 값을 원복 해야되는데 특수한 GUI로 꾸몄으므로 해당 함수를 오버라이드해서 각 위젯의 특성에 맞게 처리해야 된다.
    def on_clicked_refresh(self):
        num_device = self.num_device_param.value
        self.cluster_monitor_folder.set_cluster_num(num_device)

        self.param_worker.refresh()

    def on_selected_addr_changed(self, addr):
        num_device = self.num_device_param.value

        if num_device is None:
            self.status_widget.set_addr(None)
            self.setting_widget.set_addr(None)
            self.control_widget.set_addr(None)
            return

        if addr == -1 or num_device <= addr:
            self.status_widget.set_addr(None)
            self.setting_widget.set_addr(None)
            self.control_widget.set_addr(None)
            return

        self.status_widget.set_addr(addr)
        self.setting_widget.set_addr(addr)
        self.control_widget.set_addr(addr)    

    def on_option_apply_clicked(self):
        for offset, data_len, param in self.setting_widget.opt_param.sub_items:
            if param.name == "End Position":
                end_posi_value = self.setting_widget.homing_end_posi.get_value()
            elif param.name == "Start Condition":
                start_condi_value = self.setting_widget.homing_start_cond.get_value()
            elif param.name == "Mode":
                mode_value = self.setting_widget.homing_mode.get_value()
            elif param.name == "Position Control Stroke Limitation":
                stroke_lim_value = self.setting_widget.stroke_limitation.get_value()
            elif param.name == "Power Failure Option":
                pwr_fail_value = self.setting_widget.power_failure_option.get_value()
            elif param.name == "Network Failure Option":
                net_fail_value = self.setting_widget.network_failure_option.get_value()

        self.setting_widget.opt_param.write_str_value = f"{self.setting_widget.opt_param.nv1_write_req}{end_posi_value}{pwr_fail_value}0{stroke_lim_value}{net_fail_value}0{start_condi_value}{mode_value}"        

        self.setting_widget.posi_speed_param.write_str_value = self.setting_widget.get_posi_speed_write_value()
        self.setting_widget.posi_offset_param.write_str_value = self.setting_widget.get_posi_offset_write_value()

        self.param_worker.write()

    def on_unfreeze_clicked(self):
        self.control_widget.freeze_param.write_str_value = f"{ClusterUnfreezeFreezeEnum.UNFREEZE.value}" 
        self.param_worker.write()

    def on_freeze_clicked(self):
        self.control_widget.freeze_param.write_str_value = f"{ClusterUnfreezeFreezeEnum.FREEZE.value}" 
        self.param_worker.write()
    
    def on_target_posi_edit_finished(self):
        self.control_widget.target_posi_param.write_str_value = self.control_widget.get_target_posi_write_value()
        self.param_worker.write()
        self.control_widget.target_posi.commit()
    
    def on_open_clicked(self):
        self.control_widget.ctrl_setpoint_param.write_str_value = f"{ControlModeEnum.OPEN.value}"
        self.param_worker.write()

    def on_close_clicked(self):
        self.control_widget.ctrl_setpoint_param.write_str_value = f"{ControlModeEnum.CLOSE.value}"
        self.param_worker.write()
    
    def on_restart_clicked(self):
        pass
            

                


        
        