from c_ui.b_control_packet.param_container.param_folder_widget import ParamFolderWidget

class ParamFolderPresCtrlBasicWidget(ParamFolderWidget):
    def __init__(self, parent=None):
        super().__init__(folder_name="Basic", param_path="Pressure Control.Basic", label_width = 210, parent=parent)