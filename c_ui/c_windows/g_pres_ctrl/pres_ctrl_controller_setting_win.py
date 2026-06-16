
from c_ui.b_control_packet.layout.my_flow_layout import MyFlowLayout
from c_ui.b_control_packet.param_container.param_setting_win import ParamSettingWin
from c_ui.b_control_packet.param_container.param_folder_pres_ctrl_controller_widget import ParamFolderPresCtrlControllerWidget

class PresCtrlControllerSettingWin(ParamSettingWin):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Pressure Control >> Controller Setting")
        self.resize(850, 450)

        self.flow_layout = MyFlowLayout()
        self.content_layout.addLayout(self.flow_layout)
        
        self.add_folder(ParamFolderPresCtrlControllerWidget(1))
        self.add_folder(ParamFolderPresCtrlControllerWidget(2))
        self.add_folder(ParamFolderPresCtrlControllerWidget(3))
        self.add_folder(ParamFolderPresCtrlControllerWidget(4))

        self.content_layout.addStretch()

        self.init_toolbar()
        self.init_end()

    def add_folder(self, widget):
        self.flow_layout.addWidget(widget)
        self.parameter_folder_widgets.append(widget)