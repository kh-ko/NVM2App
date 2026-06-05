from c_ui.b_control_packet.param_container.param_folder_widget import ParamFolderWidget

class ParamFolderSensSens1RangeWidget(ParamFolderWidget):
    def __init__(self, parent=None):
        super().__init__(folder_name="Sensor 1 Range", param_path="Sensor.Sensor 1.Range", label_width = 210, parent=parent)