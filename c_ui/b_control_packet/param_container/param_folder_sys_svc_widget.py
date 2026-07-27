from c_ui.b_control_packet.param_container.param_folder_widget import ParamFolderWidget

class ParamFolderSysSvcWidget(ParamFolderWidget):
    def __init__(self, parent=None):
        super().__init__(folder_name="Services", param_path="System.Services", label_width = 200, parent=parent)