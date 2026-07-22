from c_ui.b_control_packet.param_container.param_folder_legacy_rs232_rs485_logic_widget import ParamFolderLegacyRs232Rs485LogicWidget
from c_ui.b_control_packet.param_container.param_folder_legacy_rs232_rs485_widget import ParamFolderLegacyRs232Rs485Widget
from c_ui.b_control_packet.param_container.param_folder_legacy_ethercat_devicenet_profibus_widget import ParamFolderLegacyEtherCatDeviceNetProfibusWidget
from c_ui.b_control_packet.param_container.param_folder_legacy_profibus_widget import ParamFolderLegacyProfibusWidget
from c_ui.b_control_packet.param_container.param_folder_legacy_devicenet_widget import ParamFolderLegacyDeviceNetWidget
from c_ui.b_control_packet.param_container.param_folder_legacy_ethercat_widget import ParamFolderLegacyEtherCatWidget
from c_ui.b_control_packet.param_container.param_folder_legacy_logic_widget import ParamFolderLegacyLogicWidget
from c_ui.b_control_packet.param_container.param_folder_legacy_learn_widget import ParamFolderLegacyLearnWidget
from c_ui.b_control_packet.param_container.param_folder_legacy_pres_ctrl_widget import ParamFolderLegacyPresCtrlWidget
from c_ui.b_control_packet.param_container.param_folder_legacy_hw_adc_widget import ParamFolderLegacyHwAdcWidget
from c_ui.b_control_packet.param_container.param_folder_legacy_hw_link_widget import ParamFolderLegacyHwLinkWidget
from c_ui.b_control_packet.param_container.param_folder_legacy_hw_multi_posi_widget import ParamFolderLegacyHwMultiPosiWidget
from c_ui.b_control_packet.param_container.param_folder_legacy_hw_widget import ParamFolderLegacyHwWidget
from c_ui.b_control_packet.param_container.param_folder_legacy_hw_speed_widget import ParamFolderLegacyHwSpeedWidget
from c_ui.b_control_packet.param_container.param_folder_legacy_hw_encoder_widget import ParamFolderLegacyHwEncoderWidget
from c_ui.b_control_packet.param_container.param_folder_legacy_hw_torque_widget import ParamFolderLegacyHwTorqueWidget
from c_ui.b_control_packet.param_container.param_folder_compound_widget import ParamFolderCompoundWidget
from c_ui.b_control_packet.param_container.param_setting_win import ParamSettingWin
from c_ui.b_control_packet.param_container.param_folder_pfo_widget import ParamFolderPfoWidget

class AdvencedLegacyWin(ParamSettingWin):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Advenced >> Legacy Parameter")
        
        self.add_param_folder_widget(ParamFolderLegacyHwTorqueWidget())
        self.add_param_folder_widget(ParamFolderLegacyHwEncoderWidget())
        self.add_param_folder_widget(ParamFolderLegacyHwSpeedWidget())
        self.add_param_folder_widget(ParamFolderLegacyHwWidget())
        self.add_param_folder_widget(ParamFolderLegacyHwMultiPosiWidget())
        self.add_param_folder_widget(ParamFolderLegacyHwLinkWidget())
        self.add_param_folder_widget(ParamFolderLegacyHwAdcWidget())
        self.add_param_folder_widget(ParamFolderLegacyPresCtrlWidget())
        self.add_param_folder_widget(ParamFolderLegacyLearnWidget())
        self.add_param_folder_widget(ParamFolderLegacyLogicWidget())
        self.add_param_folder_widget(ParamFolderLegacyEtherCatWidget())
        self.add_param_folder_widget(ParamFolderLegacyDeviceNetWidget())
        self.add_param_folder_widget(ParamFolderLegacyProfibusWidget())
        self.add_param_folder_widget(ParamFolderLegacyEtherCatDeviceNetProfibusWidget())
        self.add_param_folder_widget(ParamFolderLegacyRs232Rs485Widget())
        self.add_param_folder_widget(ParamFolderLegacyRs232Rs485LogicWidget())

        self.content_layout.addStretch()

        self.init_toolbar()
        self.init_end()