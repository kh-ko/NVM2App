from c_ui.b_control_packet.param_container.param_setting_win import ParamSettingWin

from c_ui.b_control_packet.param_container.param_folder_sens_zero_widget import ParamFolderSensZeroWidget
from c_ui.b_control_packet.param_container.param_folder_sens_basic_widget import ParamFolderSensBasicWidget

class SensorZeroWin(ParamSettingWin):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Sensor >> Zero Adjust")
        
        self.add_param_folder_widget(ParamFolderSensBasicWidget())
        self.add_param_folder_widget(ParamFolderSensZeroWidget())

        self.content_layout.addStretch()

        self.init_toolbar()
        self.init_end()