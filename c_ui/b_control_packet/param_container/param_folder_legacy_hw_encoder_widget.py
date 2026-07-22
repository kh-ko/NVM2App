from c_ui.b_control_packet.param_container.param_folder_widget import ParamFolderWidget

class ParamFolderLegacyHwEncoderWidget(ParamFolderWidget):
    def __init__(self, parent=None):
        super().__init__(folder_name="Hardware.Encoder", param_path="Legacy Parameters.Hardware.Encoder", label_width = 320, parent=parent)