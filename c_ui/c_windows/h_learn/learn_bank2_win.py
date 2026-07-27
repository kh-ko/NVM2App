from c_ui.b_control_packet.param_container.param_setting_win import ParamSettingWin
from c_ui.b_control_packet.param_container.param_folder_learn_bank_widget import ParamFolderLearnBankWidget
from c_ui.b_control_packet.param_container.param_folder_learn_bank_data_widget import ParamFolderLearnBankDataWidget

class LearnBank2Win(ParamSettingWin):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Learn >> Learn Bank 2 Settings")
        
        self.add_param_folder_widget(ParamFolderLearnBankWidget(bank_num = 2))
        self.add_param_folder_widget(ParamFolderLearnBankDataWidget(bank_num = 2))

        self.content_layout.addStretch()

        self.init_toolbar()
        self.init_end()