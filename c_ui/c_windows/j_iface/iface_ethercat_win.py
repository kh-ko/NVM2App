from c_ui.b_control_packet.param_container.param_folder_iface_ethercat_all_datatype_widget import ParamFolderIfaceEtherCATAllDataTypeWidget
from c_ui.b_control_packet.param_container.param_folder_iface_ethercat_scale_digi_sens1_in_widget import ParamFolderIfaceEtherCATScaleDigiSens1InWidget
from c_ui.b_control_packet.param_container.param_folder_iface_ethercat_scale_digi_sens2_in_widget import ParamFolderIfaceEtherCATScaleDigiSens2InWidget
from c_ui.b_control_packet.param_container.param_folder_iface_scale_pres_widget import ParamFolderIfaceScalePresWidget
from c_ui.b_control_packet.param_container.param_folder_iface_scale_posi_widget import ParamFolderIfaceScalePosiWidget
from c_ui.b_control_packet.param_container.param_folder_iface_ethercat_range import ParamFolderIfaceEtherCATRangeWidget
from c_ui.b_control_packet.param_container.param_folder_iface_ethercat_widget import ParamFolderIfaceEtherCATWidget
from c_ui.b_control_packet.param_container.param_setting_win import ParamSettingWin

class IfaceEtherCATWin(ParamSettingWin):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.resize(900, 450)
        self.setWindowTitle("Interface >> EtherCAT Settings")

        folder_all_datatype = ParamFolderIfaceEtherCATAllDataTypeWidget()
        folder_range = ParamFolderIfaceEtherCATRangeWidget()
        self.add_param_folder_widget(ParamFolderIfaceEtherCATWidget())
        self.add_param_folder_widget(folder_all_datatype)
        self.add_param_folder_widget(ParamFolderIfaceScalePosiWidget())
        self.add_param_folder_widget(ParamFolderIfaceScalePresWidget())
        self.add_param_folder_widget(ParamFolderIfaceEtherCATScaleDigiSens1InWidget())
        self.add_param_folder_widget(ParamFolderIfaceEtherCATScaleDigiSens2InWidget())
        self.add_param_folder_widget(folder_range)
        #self.add_param_folder_widget(ParamFolderIfaceEtherCATConnLossWidget())

        folder_all_datatype.set_range_folder_widget(folder_range)
        folder_range.set_folder_all_datatype(folder_all_datatype)
        self.content_layout.addStretch()

        self.init_toolbar()
        self.init_end()