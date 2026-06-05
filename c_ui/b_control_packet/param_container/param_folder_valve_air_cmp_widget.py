from c_ui.b_control_packet.param_container.param_folder_widget import ParamFolderWidget

class ParamFolderValveAirCmpWidget(ParamFolderWidget):
    def __init__(self, parent=None):
        super().__init__(folder_name="Compressed Air", param_path="Valve.Compressed Air", label_width = 150, parent=parent)