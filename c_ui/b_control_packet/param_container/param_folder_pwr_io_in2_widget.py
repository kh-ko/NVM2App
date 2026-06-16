from c_ui.b_control_packet.param_container.param_folder_widget import ParamFolderWidget
class ParamFolderPwrIoIn2Widget(ParamFolderWidget):
    def __init__(self, parent=None):
        super().__init__(folder_name="Digital Input 2", param_path="Power Connector IO.Digital Input 2", label_width = 210, parent=parent)