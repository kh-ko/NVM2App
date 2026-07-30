from c_ui.b_control_packet.param_container.param_folder_widget import ParamFolderWidget

class ParamFolderIfaceEtherCATScaleDigiSens1InWidget(ParamFolderWidget):
    def __init__(self, parent=None):
        super().__init__(folder_name="Interface EtherCAT.Scaling.Digital Sensor 1 Input", param_path="Interface EtherCAT.Scaling.Digital Sensor 1 Input", label_width = 300, parent=parent)