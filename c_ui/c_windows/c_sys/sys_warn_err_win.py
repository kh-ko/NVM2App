from c_ui.b_control_packet.param_container.param_setting_win import ParamSettingWin
from c_ui.b_control_packet.param_container.param_folder_sys_warn_err_widget import ParamFolderSysWarnErrWidget

class SysWarnErrWin(ParamSettingWin):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("System >> Warning & Error")
        
        self.add_param_folder_widget(ParamFolderSysWarnErrWidget())

        self.content_layout.addStretch()

        self.init_toolbar()        
        self.init_end()