from PySide6.QtWidgets import QFileDialog
from PySide6.QtWidgets import QMessageBox

from b_core.a_define import file_folder_path as path_def
from b_core.b_datatype.general_enum import ParamAccType
from b_core.b_datatype.general_enum import EtherCATRangeSettingOptEnum
from b_core.b_datatype.param_enum import EtherCATDataTypeEnum
from b_core.c_manager.parameter_manager import ParamManager

from c_ui.b_control_packet.param_container.param_folder_iface_ethercat_range_setting_widget import ParamFolderIfaceEtherCATRangeSettingOptWidget
from c_ui.b_control_packet.param_container.param_folder_iface_ethercat_all_datatype_widget import ParamFolderIfaceEtherCATAllDataTypeWidget
from c_ui.b_control_packet.param_container.param_folder_iface_ethercat_scale_digi_sens1_in_widget import ParamFolderIfaceEtherCATScaleDigiSens1InWidget
from c_ui.b_control_packet.param_container.param_folder_iface_ethercat_scale_digi_sens2_in_widget import ParamFolderIfaceEtherCATScaleDigiSens2InWidget
from c_ui.b_control_packet.param_container.param_folder_iface_scale_pres_widget import ParamFolderIfaceScalePresWidget
from c_ui.b_control_packet.param_container.param_folder_iface_scale_posi_widget import ParamFolderIfaceScalePosiWidget
from c_ui.b_control_packet.param_container.param_folder_iface_ethercat_range import ParamFolderIfaceEtherCATRangeWidget
from c_ui.b_control_packet.param_container.param_folder_iface_ethercat_widget import ParamFolderIfaceEtherCATWidget
from c_ui.b_control_packet.param_container.param_folder_iface_ethercat_conn_loss_widget import ParamFolderIfaceEtherCATConnLossWidget
from c_ui.b_control_packet.param_container.param_setting_win import ParamSettingWin

XML_NAME_TO_DATATYPE_PARAM = {
    "<Name>Pressure</Name>"                               : "Interface EtherCAT.Range.Pressure.Data type",
    "<Name>Pressure sensor 1</Name>"                      : "Interface EtherCAT.Range.Pressure sensor 1.Data type",
    "<Name>Pressure sensor 2</Name>"                      : "Interface EtherCAT.Range.Pressure sensor 2.Data type",
    "<Name>Position</Name>"                               : "Interface EtherCAT.Range.Position.Data type",
    "<Name>Target position</Name>"                        : "Interface EtherCAT.Range.Target position.Data type",
    "<Name>Cluster valve position</Name>"                 : "Interface EtherCAT.Range.Cluster valve position.Data type",
    "<Name>Pressure setpoint</Name>"                      : "Interface EtherCAT.Range.Pressure setpoint.Data type",
    "<Name>Position setpoint</Name>"                      : "Interface EtherCAT.Range.Position setpoint.Data type",
    "<Name>Pressure alignment setpoint</Name>"            : "Interface EtherCAT.Range.Pressure alignment setpoint.Data type",
    "<Name>External digital pressure sensor 1</Name>"     : "Interface EtherCAT.Range.External digital sensor1.Data type",
    "<Name>External digital pressure sensor 2</Name>"     : "Interface EtherCAT.Range.External digital sensor2.Data type",
    "<Name>Cluster valve freeze position setpoint</Name>" : "Interface EtherCAT.Range.Cluster valve freeze position.Data type",
}

class IfaceEtherCATWin(ParamSettingWin):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.resize(900, 450)
        self.setWindowTitle("Interface >> EtherCAT Settings")

        self.folder_range_setting_opt   = ParamFolderIfaceEtherCATRangeSettingOptWidget()
        self.folder_all_datatype        = ParamFolderIfaceEtherCATAllDataTypeWidget()
        self.folder_scale_posi          = ParamFolderIfaceScalePosiWidget()
        self.folder_scale_pres          = ParamFolderIfaceScalePresWidget()
        self.folder_scale_digi_sens1_in = ParamFolderIfaceEtherCATScaleDigiSens1InWidget()
        self.folder_scale_digi_sens2_in = ParamFolderIfaceEtherCATScaleDigiSens2InWidget()
        self.folder_range               = ParamFolderIfaceEtherCATRangeWidget()
        
        self.add_param_folder_widget(ParamFolderIfaceEtherCATWidget())
        self.add_param_folder_widget(ParamFolderIfaceEtherCATConnLossWidget())
        self.add_param_folder_widget(self.folder_range_setting_opt)
        self.add_param_folder_widget(self.folder_all_datatype)
        self.add_param_folder_widget(self.folder_scale_posi)
        self.add_param_folder_widget(self.folder_scale_pres)
        self.add_param_folder_widget(self.folder_scale_digi_sens1_in)
        self.add_param_folder_widget(self.folder_scale_digi_sens2_in)
        self.add_param_folder_widget(self.folder_range)        

        self.folder_all_datatype.set_range_folder_widget(self.folder_range)
        self.folder_range.set_folder_all_datatype(self.folder_all_datatype)

        self.folder_range_setting_opt.sig_changed_opt.connect(self.on_changed_range_setting_opt)
        self.on_changed_range_setting_opt(EtherCATRangeSettingOptEnum.BASIC.value)
        
        self.content_layout.addStretch()

        self.init_toolbar()
        self.toolbar.add_action("Create XML", self.on_clicked_create_xml)
        self.init_end()

    def on_clicked_create_xml(self):
        file_path, _ = QFileDialog.getSaveFileName(self, "Save XML File", "", "XML Files (*.xml);;All Files (*)")

        if not file_path:
            return

        try:
            with open(path_def.RSRC_TEMPLATE_ETHERCAT_XML_FILE, 'r', encoding='utf-8') as f:
                lines = f.read().splitlines()

            contents = []
            idx = 0
            while idx < len(lines):
                line = lines[idx]
                contents.append(line)

                for marker, param_path in XML_NAME_TO_DATATYPE_PARAM.items():
                    if marker in line:
                        param = ParamManager().get_by_full_path(param_path)
                        datatype_str = "REAL" if param.value == EtherCATDataTypeEnum.FLOAT.value else "DINT"
                        idx += 1
                        contents.append(lines[idx].replace("%1", datatype_str))
                        break

                idx += 1

            with open(file_path, 'w', encoding='utf-8') as f_out:
                f_out.write("\n".join(contents) + "\n")

            QMessageBox.information(self, "Success", "XML file has been created successfully.")
        except Exception as e:
            print(f"[IfaceEtherCATWin] XML 파일 생성 중 오류 발생: {e}")
            QMessageBox.critical(self, "Error", f"Failed to create XML file.\nError details: {e}") 

    def on_changed_range_setting_opt(self, value):
        if EtherCATRangeSettingOptEnum.BASIC.value == value:
            self.restore_and_hide_folder(True , self.folder_scale_posi         )
            self.restore_and_hide_folder(True , self.folder_scale_pres         )
            self.restore_and_hide_folder(True , self.folder_scale_digi_sens1_in)
            self.restore_and_hide_folder(True , self.folder_scale_digi_sens2_in)
            self.restore_and_hide_folder(False, self.folder_range              )
            self.on_clicked_refresh()           
        else:
            self.restore_and_hide_folder(False, self.folder_scale_posi         )
            self.restore_and_hide_folder(False, self.folder_scale_pres         )
            self.restore_and_hide_folder(False, self.folder_scale_digi_sens1_in)
            self.restore_and_hide_folder(False, self.folder_scale_digi_sens2_in)
            self.restore_and_hide_folder(True , self.folder_range              )
            self.on_clicked_refresh()   

    def on_clicked_refresh(self):
        self.folder_all_datatype.reload_datatype()
        super().on_clicked_refresh()
            
    def restore_and_hide_folder(self, is_hide, folder_widget):
        if is_hide:
            folder_widget.hide()
            for param_component in folder_widget.param_components:
                if param_component.param.acc != ParamAccType.RO:
                    param_component.restore()
        else:
            folder_widget.show()