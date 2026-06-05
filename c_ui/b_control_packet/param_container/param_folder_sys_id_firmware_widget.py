from c_ui.b_control_packet.param_container.param_folder_widget import ParamFolderWidget

class ParamFolderSysIdFirmwareWidget(ParamFolderWidget):
    def __init__(self, parent=None):
        super().__init__(folder_name="Firmware", param_path="System.Identification.Firmware", label_width = 150, parent=parent)