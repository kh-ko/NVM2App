from c_ui.b_control_packet.param_container.param_folder_widget import ParamFolderWidget

class ParamFolderIfaceEtherCATConnLossWidget(ParamFolderWidget):
    def __init__(self, parent=None):
        super().__init__(folder_name="Interface EtherCAT.Connection Loss Reaction", param_path="Interface EtherCAT.Connection Loss Reaction", label_width = 300, parent=parent)