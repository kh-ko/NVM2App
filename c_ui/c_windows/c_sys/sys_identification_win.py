from c_ui.b_control_packet.param_container.param_setting_win import ParamSettingWin
from c_ui.b_control_packet.param_container.param_folder_sys_id_widget import ParamFolderSysIdWidget
from c_ui.b_control_packet.param_container.param_folder_sys_id_cfg_widget import ParamFolderSysIdCfgWidget
from c_ui.b_control_packet.param_container.param_folder_sys_id_firmware_widget import ParamFolderSysIdFirmwareWidget

class SysIdentificationWin(ParamSettingWin):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("System >> Identification")
        
        self.add_param_folder_widget(ParamFolderSysIdWidget())
        self.add_param_folder_widget(ParamFolderSysIdCfgWidget())
        self.add_param_folder_widget(ParamFolderSysIdFirmwareWidget())

        self.content_layout.addStretch()

        self.init_toolbar()
        self.toolbar.add_action("Enable Edit", self.on_clicked_edit)
        self.toolbar.set_action_enabled("Load File", False)
        
        self.init_end()

    def on_clicked_edit(self):
        self.content_widget.setEnabled(True)
        self.toolbar.set_action_enabled("Load File", True)

    def handle_progress_changed(self, progress: int):
        self.statusbar.set_progress(progress)

        self.toolbar.set_action_enabled("Load File", False)

        if progress > 0:
            self.content_widget.setEnabled(False)
        else:
            self.content_widget.setEnabled(False)