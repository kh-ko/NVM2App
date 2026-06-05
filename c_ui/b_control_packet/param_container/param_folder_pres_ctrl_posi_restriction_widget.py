from c_ui.b_control_packet.param_container.param_folder_widget import ParamFolderWidget

class ParamFolderPresCtrlPosiRestrictionWidget(ParamFolderWidget):
    def __init__(self, parent=None):
        super().__init__(folder_name="Position Restriction", param_path="Pressure Control.General Settings.Control Position Restriction", label_width = 210, parent=parent)