from c_ui.b_control_packet.param_container.param_folder_widget import ParamFolderWidget

class ParamFolderValveAdapWidget(ParamFolderWidget):
    def __init__(self, parent=None):
        super().__init__(folder_name="Position Adaption", param_path="Valve.Position Adaption", label_width = 150, parent=parent)