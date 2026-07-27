from c_ui.b_control_packet.param_container.param_setting_win import ParamSettingWin
from c_ui.b_control_packet.param_container.param_folder_valve_air_cmp_widget import ParamFolderValveAirCmpWidget
from c_ui.b_control_packet.param_container.param_folder_valve_homing_widget import ParamFolderValveHomingWidget
from c_ui.b_control_packet.param_container.param_folder_valve_restriction_widget import ParamFolderValveRestrictionWidget
from c_ui.b_control_packet.param_container.param_folder_valve_adap_widget import ParamFolderValveAdapWidget

class ValveSettingWin(ParamSettingWin):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Valve >> Settings")
        
        self.add_param_folder_widget(ParamFolderValveAirCmpWidget())
        self.add_param_folder_widget(ParamFolderValveHomingWidget())
        self.add_param_folder_widget(ParamFolderValveRestrictionWidget())
        self.add_param_folder_widget(ParamFolderValveAdapWidget())

        self.content_layout.addStretch()

        self.init_toolbar()
        self.init_end()