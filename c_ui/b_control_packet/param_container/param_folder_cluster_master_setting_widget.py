from c_ui.b_control_packet.param_container.param_folder_widget import ParamFolderWidget

class ParamFolderClusterMasterSettingWidget(ParamFolderWidget):
    def __init__(self, parent=None):
        super().__init__(folder_name="Master Setting", param_path="Cluster.Settings", label_width = 210, parent=parent)