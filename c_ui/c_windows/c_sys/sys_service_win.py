
from b_core.b_datatype.parameter import Parameter

from c_ui.b_control_packet.param_container.param_setting_win import ParamSettingWin
from c_ui.b_control_packet.param_container.param_folder_sys_svc_widget import ParamFolderSysSvcWidget

class SysServiceWin(ParamSettingWin):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("System >> Servcie")
        
        self.add_param_folder_widget(ParamFolderSysSvcWidget())

        self.content_layout.addStretch()

        self.init_toolbar()        
        self.init_end()