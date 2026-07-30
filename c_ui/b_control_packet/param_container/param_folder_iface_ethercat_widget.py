from c_ui.b_control_packet.param_container.param_folder_widget import ParamFolderWidget

class ParamFolderIfaceEtherCATWidget(ParamFolderWidget):
    def __init__(self, parent=None):
        super().__init__(folder_name="Interface EtherCAT", param_path="Interface EtherCAT", label_width = 300, parent=parent)