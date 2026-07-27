from c_ui.b_control_packet.param_container.param_folder_widget import ParamFolderWidget

class ParamFolderSensLogPresWidget(ParamFolderWidget):
    def __init__(self, parent=None):
        super().__init__(folder_name="Logarithmic Pressure", param_path="Sensor.General Setting.Logarithmic Pressure", label_width = 250, parent=parent)