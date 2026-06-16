from c_ui.b_control_packet.param_container.param_folder_widget import ParamFolderWidget

class ParamFolderIfaceDnetScaleInWidget(ParamFolderWidget):
    def __init__(self, parent=None):
        super().__init__(folder_name="Scaling.Input", param_path="Interface DeviceNet.Scaling.Input", label_width = 210, parent=parent)