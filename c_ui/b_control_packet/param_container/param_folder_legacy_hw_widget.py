from c_ui.b_control_packet.param_container.param_folder_widget import ParamFolderWidget

class ParamFolderLegacyHwWidget(ParamFolderWidget):
    def __init__(self, parent=None):
        super().__init__(folder_name="Hardware", param_path="Legacy Parameters.Hardware", label_width = 320, parent=parent)