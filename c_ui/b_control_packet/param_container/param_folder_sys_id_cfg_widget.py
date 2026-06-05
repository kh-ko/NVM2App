from c_ui.b_control_packet.param_container.param_folder_widget import ParamFolderWidget

class ParamFolderSysIdCfgWidget(ParamFolderWidget):
    def __init__(self, parent=None):
        super().__init__(folder_name="Configuration", param_path="System.Identification.Configuration", label_width = 150, parent=parent)