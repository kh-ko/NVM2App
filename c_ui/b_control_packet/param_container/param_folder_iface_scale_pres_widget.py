from c_ui.b_control_packet.param_container.param_folder_widget import ParamFolderWidget

class ParamFolderIfaceScalePresWidget(ParamFolderWidget):
    def __init__(self, parent=None):
        super().__init__(folder_name="Interface.Scaling.Pressure", param_path="Interface.Scaling.Pressure", label_width = 300, parent=parent)