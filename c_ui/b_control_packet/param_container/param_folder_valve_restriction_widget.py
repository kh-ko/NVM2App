from c_ui.b_control_packet.param_container.param_folder_widget import ParamFolderWidget

class ParamFolderValveRestrictionWidget(ParamFolderWidget):
    def __init__(self, parent=None):
        super().__init__(folder_name="Position Restriction", param_path="Valve.Position Restriction", label_width = 150, parent=parent)