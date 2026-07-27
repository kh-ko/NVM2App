from PySide6.QtWidgets import QVBoxLayout
from PySide6.QtWidgets import QHBoxLayout
from c_ui.b_control_packet.param_container.param_setting_win import ParamSettingWin
from c_ui.b_control_packet.param_container.param_folder_pres_ctrl_basic_widget import ParamFolderPresCtrlBasicWidget
from c_ui.b_control_packet.param_container.param_folder_pres_ctrl_auto_sel_widget import ParamFolderPresCtrlAutoCtrlSelectorWidget
from c_ui.b_control_packet.param_container.param_folder_pres_ctrl_posi_restriction_widget import ParamFolderPresCtrlPosiRestrictionWidget
from c_ui.b_control_packet.param_container.param_folder_pres_ctrl_ramp_widget import ParamFolderPresCtrlRampWidget

class PresCtrlGenSettingWin(ParamSettingWin):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Pressure Control >> General Settings")
        self.resize(850, 450)

        columns_layout = QHBoxLayout()
        columns_layout.setSpacing(5)

        self.left_layout = QVBoxLayout()
        self.right_layout = QVBoxLayout()

        columns_layout.addLayout(self.left_layout)
        columns_layout.addLayout(self.right_layout)

        self.content_layout.addLayout(columns_layout)
        
        self.add_left_folder(ParamFolderPresCtrlBasicWidget())
        self.add_left_folder(ParamFolderPresCtrlPosiRestrictionWidget())
        self.left_layout.addStretch()

        self.add_right_folder(ParamFolderPresCtrlAutoCtrlSelectorWidget())
        self.right_layout.addStretch()

        self.add_param_folder_widget(ParamFolderPresCtrlRampWidget())

        self.content_layout.addStretch()

        self.init_toolbar()
        self.init_end()

    def add_left_folder(self, widget):
        self.left_layout.addWidget(widget)
        self.parameter_folder_widgets.append(widget)

    def add_right_folder(self, widget):
        self.right_layout.addWidget(widget)
        self.parameter_folder_widgets.append(widget)     