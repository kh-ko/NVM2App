from c_ui.b_control_packet.param_container.param_folder_widget import ParamFolderWidget

class ParamFolderLegacyProfibusWidget(ParamFolderWidget):
    def __init__(self, parent=None):
        super().__init__(folder_name="User Interface.Profibus", param_path="Legacy Parameters.Profibus", label_width = 320, parent=parent)