from c_ui.b_control_packet.param_container.param_setting_win import ParamSettingWin
from c_ui.b_control_packet.param_container.param_folder_pfo_widget import ParamFolderPfoWidget
from c_ui.b_control_packet.param_container.param_folder_compound_widget import ParamFolderCompoundWidget

class Compound03Win(ParamSettingWin):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Compound >> Compound 3")
        
        self.add_param_folder_widget(ParamFolderCompoundWidget(3))

        self.content_layout.addStretch()

        self.init_toolbar()
        self.init_end()