from c_ui.b_control_packet.param_container.param_folder_widget import ParamFolderWidget

class ParamFolderSensSens2FilterWidget(ParamFolderWidget):
    def __init__(self, parent=None):
        super().__init__(folder_name="Sensor 2 Filter", param_path="Sensor.Sensor 2.Filter", label_width = 210, parent=parent)