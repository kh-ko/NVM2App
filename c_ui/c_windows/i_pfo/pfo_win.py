from c_ui.b_control_packet.param_container.param_setting_win import ParamSettingWin
from c_ui.b_control_packet.param_container.param_folder_pfo_widget import ParamFolderPfoWidget

class PfoWin(ParamSettingWin):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Power Fail Options >> Settings")
        
        self.add_param_folder_widget(ParamFolderPfoWidget())

        self.content_layout.addStretch()

        self.init_toolbar()
        self.init_end()