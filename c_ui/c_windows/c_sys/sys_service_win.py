
from b_core.b_datatype.parameter import Parameter

from c_ui.b_control_packet.param_container.param_setting_win import ParamSettingWin
from c_ui.b_control_packet.param_container.param_folder_sys_svc_widget import ParamFolderSysSvcWidget

class SysServiceWin(ParamSettingWin):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("System >> Servcie")
        
        self.add_param_folder_widget(ParamFolderSysSvcWidget())

        self.content_layout.addStretch()

        self.init_toolbar()        
        self.init_end()

    def on_btn_widget_clicked(self, param : Parameter):
        # todo : restart 기능이 있는 버튼 처리가 필요하다.. parameter 속성에 restart 속성이 있는 것은 패킷 보낸 이후 10초 이후 재접속 시나리오를 거치고, 다시 refresh 하도록 해야된다.
        # 해당 기능은 ParamSettingWin 에서 구현하든 어디서 구현하든 중앙 집중식이 되어야겠다.
        pass