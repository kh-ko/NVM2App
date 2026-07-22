from c_ui.b_control_packet.param_container.param_folder_widget import ParamFolderWidget

class ParamFolderLegacyPresCtrlWidget(ParamFolderWidget):
    def __init__(self, parent=None):
        super().__init__(folder_name="Pressure Control", param_path="Legacy Parameters.Pressure Control", label_width = 320, parent=parent)