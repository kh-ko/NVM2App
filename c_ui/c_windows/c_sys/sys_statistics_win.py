
from c_ui.b_control_packet.param_container.param_setting_win import ParamSettingWin
from c_ui.b_control_packet.param_container.param_folder_sys_statistics_widget import ParamFolderSysStatisticsWidget

class SysStatisticsWin(ParamSettingWin):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("System >> Statistics")
        
        self.add_param_folder_widget(ParamFolderSysStatisticsWidget())

        self.content_layout.addStretch()

        self.init_toolbar()        
        self.init_end()