from c_ui.b_control_packet.param_container.param_folder_widget import ParamFolderWidget

class ParamFolderLegacyRs232Rs485LogicWidget(ParamFolderWidget):
    def __init__(self, parent=None):
        super().__init__(folder_name="User Interface.RS232/RS485/Logic", param_path="Legacy Parameters.Interface RS232/RS485/Logic", label_width = 320, parent=parent)