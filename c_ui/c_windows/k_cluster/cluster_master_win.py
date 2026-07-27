from c_ui.b_control_packet.param_container.param_setting_win import ParamSettingWin
from c_ui.b_control_packet.param_container.param_folder_cluster_master_setting_widget import ParamFolderClusterMasterSettingWidget

class ClusterMasterWin(ParamSettingWin):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Cluster >> Master Settings")
        
        self.add_param_folder_widget(ParamFolderClusterMasterSettingWidget())

        self.content_layout.addStretch()

        self.init_toolbar()
        self.init_end()