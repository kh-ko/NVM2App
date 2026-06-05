from c_ui.b_control_packet.param_container.param_folder_widget import ParamFolderWidget

class ParamFolderSensSens2RangeWidget(ParamFolderWidget):
    def __init__(self, parent=None):
        super().__init__(folder_name="Sensor 2 Range", param_path="Sensor.Sensor 2.Range", label_width = 210, parent=parent)