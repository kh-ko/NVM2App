from c_ui.b_control_packet.param_container.param_folder_widget import ParamFolderWidget

class ParamFolderSensZeroWidget(ParamFolderWidget):
    def __init__(self, parent=None):
        super().__init__(folder_name="Zero Adjust", param_path="Sensor.Zero Adjust", label_width = 150, parent=parent)