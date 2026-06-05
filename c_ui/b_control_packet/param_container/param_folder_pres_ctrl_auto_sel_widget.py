from c_ui.b_control_packet.param_container.param_folder_widget import ParamFolderWidget

class ParamFolderPresCtrlAutoCtrlSelectorWidget(ParamFolderWidget):
    def __init__(self, parent=None):
        super().__init__(folder_name="Automated Controller Selector", param_path="Pressure Control.General Settings.Automated Controller Selector", label_width = 210, parent=parent)