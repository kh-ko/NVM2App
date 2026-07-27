from c_ui.b_control_packet.param_container.param_folder_widget import ParamFolderWidget

class ParamFolderSysIdWidget(ParamFolderWidget):
    def __init__(self, parent=None):
        super().__init__(folder_name="Identification", param_path="System.Identification", label_width = 200, parent=parent)