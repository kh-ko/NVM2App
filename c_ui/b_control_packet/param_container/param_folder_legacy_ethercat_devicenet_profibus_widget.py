from c_ui.b_control_packet.param_container.param_folder_widget import ParamFolderWidget

class ParamFolderLegacyEtherCatDeviceNetProfibusWidget(ParamFolderWidget):
    def __init__(self, parent=None):
        super().__init__(folder_name="User Interface.EtherCAT/DeviceNet/Profibus", param_path="Legacy Parameters.Interface EtherCAT/DeviceNet/Profibus", label_width = 320, parent=parent)