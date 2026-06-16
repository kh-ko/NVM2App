from c_ui.b_control_packet.param_container.param_folder_widget import ParamFolderWidget
class ParamFolderPwrIoIn1Widget(ParamFolderWidget):
    def __init__(self, parent=None):
        super().__init__(folder_name="Digital Input 1", param_path="Power Connector IO.Digital Input 1", label_width = 210, parent=parent)