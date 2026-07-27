
from c_ui.b_control_packet.param_container.param_setting_win import ParamSettingWin
from c_ui.b_control_packet.param_container.param_folder_valve_basic_widget import ParamFolderValveBasicWidget

class ValveBasicWin(ParamSettingWin):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Valve >> Basic State")
        
        self.add_param_folder_widget(ParamFolderValveBasicWidget())

        self.content_layout.addStretch()

        self.init_toolbar()
        self.init_end()