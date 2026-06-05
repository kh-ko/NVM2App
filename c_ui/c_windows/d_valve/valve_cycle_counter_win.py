from c_ui.b_control_packet.param_container.param_setting_win import ParamSettingWin
from c_ui.b_control_packet.param_container.param_folder_valve_cycle_widget import ParamFolderValveCycleWidget

class ValveCycleCounterWin(ParamSettingWin):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Valve >> Cycle Counter")
        
        self.add_param_folder_widget(ParamFolderValveCycleWidget())

        self.content_layout.addStretch()

        self.init_toolbar()
        self.init_end()