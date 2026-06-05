from c_ui.b_control_packet.param_container.param_setting_win import ParamSettingWin
from c_ui.b_control_packet.param_container.param_folder_posi_ctrl_ramp_widget import ParamFolderPosiCtrlRampWidget
from c_ui.b_control_packet.param_container.param_folder_posi_ctrl_basic_widget import ParamFolderPosiCtrlBasicWidget

class PosiCtrlSettingWin(ParamSettingWin):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Position Control >> Setting")
        
        self.add_param_folder_widget(ParamFolderPosiCtrlBasicWidget())
        self.add_param_folder_widget(ParamFolderPosiCtrlRampWidget())

        self.content_layout.addStretch()

        self.init_toolbar()
        self.init_end()