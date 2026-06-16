from c_ui.b_control_packet.param_container.param_folder_widget import ParamFolderWidget

class ParamFolderPfoWidget(ParamFolderWidget):
    def __init__(self, parent=None):
        super().__init__(folder_name="Power Fail Option", param_path="Power Fail Option", label_width = 210, parent=parent)