from c_ui.b_control_packet.param_container.param_setting_win import ParamSettingWin
from c_ui.b_control_packet.param_container.param_folder_pfo_widget import ParamFolderPfoWidget
from c_ui.b_control_packet.param_container.param_folder_compound_widget import ParamFolderCompoundWidget

class Compound02Win(ParamSettingWin):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Compound >> Compound 2 Settings")
        
        self.add_param_folder_widget(ParamFolderCompoundWidget(2))

        self.content_layout.addStretch()

        self.init_toolbar()
        self.init_end()