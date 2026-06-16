from c_ui.b_control_packet.param_container.param_setting_win import ParamSettingWin
from c_ui.b_control_packet.param_container.param_folder_learn_exe_widget import ParamFolderLearnExeWidget

class LearnExeWin(ParamSettingWin):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Learn >> Execute")
        
        self.add_param_folder_widget(ParamFolderLearnExeWidget())

        self.content_layout.addStretch()

        self.init_toolbar()
        self.init_end()