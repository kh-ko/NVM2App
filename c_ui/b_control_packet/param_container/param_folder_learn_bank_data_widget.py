from c_ui.b_control_packet.param_container.param_folder_widget import ParamFolderWidget

class ParamFolderLearnBankDataWidget(ParamFolderWidget):
    def __init__(self, bank_num, parent=None):
        super().__init__(folder_name=f"Learn Bank {bank_num} Data", param_path=f"Adaptive Learn.Learn Bank {bank_num}.Data", label_width = 210, parent=parent)