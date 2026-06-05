from c_ui.b_control_packet.param_container.param_folder_widget import ParamFolderWidget

class ParamFolderSensCrossoverWidget(ParamFolderWidget):
    def __init__(self, parent=None):
        super().__init__(folder_name="Crossover", param_path="Sensor.Crossover", label_width = 210, parent=parent)