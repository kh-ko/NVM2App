from c_ui.b_control_packet.param_container.param_folder_widget import ParamFolderWidget

class ParamFolderLegacyLogicWidget(ParamFolderWidget):
    def __init__(self, parent=None):
        super().__init__(folder_name="User Interface.Logic", param_path="Legacy Parameters.Logic", label_width = 320, parent=parent)