from c_ui.b_control_packet.param_container.param_folder_widget import ParamFolderWidget

class ParamFolderSensBasicWidget(ParamFolderWidget):
    def __init__(self, parent=None):
        super().__init__(folder_name="Basic", param_path="Sensor.Basic", label_width = 150, parent=parent)