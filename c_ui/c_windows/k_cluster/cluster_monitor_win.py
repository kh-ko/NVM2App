from c_ui.b_control_packet.param_container.param_setting_win import ParamSettingWin

class ClusterMonitorWin(ParamSettingWin):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.resize(750, 450)
        self.setWindowTitle("Cluster >> Monitor")
        
        