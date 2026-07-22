from c_ui.b_control_packet.param_container.param_folder_widget import ParamFolderWidget

class ParamFolderCompoundWidget(ParamFolderWidget):
    def __init__(self, num, parent=None):
        super().__init__(folder_name=f"Compound {num}", param_path=f"Compound Commands.User Interface.Compound Commands {num}", label_width = 210, parent=parent)