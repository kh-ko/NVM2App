from c_ui.b_control_packet.param_container.param_folder_widget import ParamFolderWidget

class ParamFolderIfaceScalePosiWidget(ParamFolderWidget):
    def __init__(self, parent=None):
        super().__init__(folder_name="Interface.Scaling.Position", param_path="Interface.Scaling.Position", label_width = 300, parent=parent)