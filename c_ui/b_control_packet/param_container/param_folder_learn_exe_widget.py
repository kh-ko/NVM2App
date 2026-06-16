from c_ui.b_control_packet.param_container.param_folder_widget import ParamFolderWidget

class ParamFolderLearnExeWidget(ParamFolderWidget):
    def __init__(self, parent=None):
        super().__init__(folder_name="Learn", param_path="Adaptive Learn.Basic", label_width = 210, parent=parent)