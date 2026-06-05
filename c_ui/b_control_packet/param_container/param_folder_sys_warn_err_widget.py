from c_ui.b_control_packet.param_container.param_folder_widget import ParamFolderWidget

class ParamFolderSysWarnErrWidget(ParamFolderWidget):
    def __init__(self, parent=None):
        super().__init__(folder_name="Warning & Error", param_path="System.Warning/Error", label_width = 150, parent=parent)