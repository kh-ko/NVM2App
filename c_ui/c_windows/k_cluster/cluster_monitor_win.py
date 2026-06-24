from b_core.c_manager.parameter_manager import ParamManager
from c_ui.b_control_packet.param_container.param_folder_cluster_monitor_widget import ParamFolderClusterMonitorWidget
from c_ui.b_control_packet.param_container.param_setting_win import ParamSettingWin

class ClusterMonitorWin(ParamSettingWin):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.resize(750, 650)
        self.setWindowTitle("Cluster >> Monitor")

        self.cluster_monitor_folder = ParamFolderClusterMonitorWidget()
        self.add_param_folder_widget(self.cluster_monitor_folder)

        self.content_layout.addStretch()

        self.init_toolbar()
        
        self.num_device_param = ParamManager().get_by_full_path("Cluster.Settings.Number of Valves")
        self.num_device_param.sig_value_changed.connect(self.handle_num_device_changed)
        self.param_worker.add_read_param_ptr(self.num_device_param)

        self._is_init = False
        self.handle_num_device_changed()
        self.init_end()
        self._is_init = True
        
    def handle_num_device_changed(self):
        num_device = self.num_device_param.value
        self.param_worker.clear_monitor_param()

        if num_device is not None:
            for num in range(0, num_device):
                status_param = ParamManager().get_by_full_path(f"Cluster.Device {num}.Status")
                self.param_worker.add_monitor_param_ptr(status_param)

        self.cluster_monitor_folder.set_cluster_num(num_device)

        if self._is_init:
            self.param_worker.refresh()
            

                


        
        