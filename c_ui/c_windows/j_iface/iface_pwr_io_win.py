
from PySide6.QtWidgets import QVBoxLayout
from PySide6.QtWidgets import QHBoxLayout
from c_ui.b_control_packet.param_container.param_setting_win import ParamSettingWin
from c_ui.b_control_packet.param_container.param_folder_pwr_io_widget import ParamFolderPwrIoWidget
from c_ui.b_control_packet.param_container.param_folder_pwr_io_in2_widget import ParamFolderPwrIoIn2Widget
from c_ui.b_control_packet.param_container.param_folder_pwr_io_in1_widget import ParamFolderPwrIoIn1Widget
from c_ui.b_control_packet.param_container.param_folder_pwr_io_out2_widget import ParamFolderPwrIoOut2Widget
from c_ui.b_control_packet.param_container.param_folder_pwr_io_out1_widget import ParamFolderPwrIoOut1Widget

class IfacePwrIoWin(ParamSettingWin):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.resize(800, 450)
        self.setWindowTitle("Interface >> Power Connector IO")

        self.add_param_folder_widget(ParamFolderPwrIoWidget())

        columns_layout = QHBoxLayout()
        columns_layout.setSpacing(5)

        self.in_layout = QVBoxLayout()
        self.out_layout = QVBoxLayout()

        columns_layout.addLayout(self.in_layout)
        columns_layout.addLayout(self.out_layout)

        self.content_layout.addLayout(columns_layout)
        
        self.add_in_folder(ParamFolderPwrIoIn1Widget())
        self.add_in_folder(ParamFolderPwrIoIn2Widget())
        self.in_layout.addStretch()

        self.add_out_folder(ParamFolderPwrIoOut1Widget())
        self.add_out_folder(ParamFolderPwrIoOut2Widget())
        self.out_layout.addStretch()

        self.content_layout.addStretch()

        self.init_toolbar()
        self.init_end()

    def add_in_folder(self, widget):
        self.in_layout.addWidget(widget)
        self.parameter_folder_widgets.append(widget)

    def add_out_folder(self, widget):
        self.out_layout.addWidget(widget)
        self.parameter_folder_widgets.append(widget)        