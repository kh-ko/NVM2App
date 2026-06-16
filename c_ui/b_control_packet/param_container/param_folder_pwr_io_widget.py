from c_ui.b_control_packet.param_container.param_folder_widget import ParamFolderWidget
class ParamFolderPwrIoWidget(ParamFolderWidget):
    def __init__(self, parent=None):
        super().__init__(folder_name="Power Connector IO", param_path="Power Connector IO", label_width = 210, parent=parent)