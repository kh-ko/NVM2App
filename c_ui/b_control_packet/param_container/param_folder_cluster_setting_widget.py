from c_ui.b_control_packet.param_container.param_folder_widget import ParamFolderWidget

class ParamFolderClusterSettingWidget(ParamFolderWidget):
    def __init__(self, parent=None):
        super().__init__(folder_name="Cluster Setting", param_path=None, label_width = 210, parent=parent)