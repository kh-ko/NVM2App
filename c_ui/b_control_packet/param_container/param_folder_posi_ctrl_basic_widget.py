from c_ui.b_control_packet.param_container.param_folder_widget import ParamFolderWidget

class ParamFolderPosiCtrlBasicWidget(ParamFolderWidget):
    def __init__(self, parent=None):
        super().__init__(folder_name="Basic", param_path="Position Control.Basic", label_width = 210, parent=parent)