from c_ui.b_control_packet.param_container.param_folder_widget import ParamFolderWidget

class ParamFolderIfaceDnetConnLossWidget(ParamFolderWidget):
    def __init__(self, parent=None):
        super().__init__(folder_name="Connection Loss Reaction", param_path="DeviceNet User Interface.Connection Loss Reaction", label_width = 210, parent=parent)