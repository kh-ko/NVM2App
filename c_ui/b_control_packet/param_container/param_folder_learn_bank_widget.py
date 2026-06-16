from c_ui.b_control_packet.param_container.param_folder_widget import ParamFolderWidget

class ParamFolderLearnBankWidget(ParamFolderWidget):
    def __init__(self, bank_num, parent=None):
        super().__init__(folder_name=f"Learn Bank {bank_num}", param_path=f"Adaptive Learn.Learn Bank {bank_num}", label_width = 210, parent=parent)