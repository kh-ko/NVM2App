from c_ui.b_control_packet.param_container.param_folder_widget import ParamFolderWidget

class ParamFolderIfaceDnetScaleOutWidget(ParamFolderWidget):
    def __init__(self, parent=None):
        super().__init__(folder_name="Scaling.Output", param_path="Interface DeviceNet.Scaling.Output", label_width = 210, parent=parent)