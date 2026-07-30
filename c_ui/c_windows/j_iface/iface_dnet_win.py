from b_core.b_datatype.param_enum import DeviceNetDataTypeEnum
from b_core.a_define import file_folder_path
import re
import os
from datetime import datetime

from PySide6.QtWidgets import QMessageBox
from PySide6.QtWidgets import QFileDialog
from PySide6.QtWidgets import QVBoxLayout
from PySide6.QtWidgets import QHBoxLayout

from b_core.a_define import file_folder_path as path_def
from b_core.b_datatype.param_enum import DeviceNetDevTypeEnum
from b_core.b_datatype.param_enum import DeviceNetProfileTypeEnum
from b_core.c_manager.parameter_manager import ParamManager

from c_ui.b_control_packet.param_container.param_setting_win import ParamSettingWin
from c_ui.b_control_packet.param_container.param_folder_iface_dnet_io_in_widget import ParamFolderIfaceDnetIoInWidget
from c_ui.b_control_packet.param_container.param_folder_iface_dnet_scale_out_widget import ParamFolderIfaceDnetScaleOutWidget
from c_ui.b_control_packet.param_container.param_folder_iface_dnet_scale_int_widget import ParamFolderIfaceDnetScaleInWidget
from c_ui.b_control_packet.param_container.param_folder_iface_dnet_io_out_widget import ParamFolderIfaceDnetIoOutWidget
from c_ui.b_control_packet.param_container.param_folder_iface_dnet_connloss_widget import ParamFolderIfaceDnetConnLossWidget
from c_ui.b_control_packet.param_container.param_folder_iface_dnet_basic_widget import ParamFolderIfaceDnetBasicWidget

RE_NAME_LENGTH = re.compile(r"(.*?)\((\d+)\)")
RE_BITMAP_LENGTH = re.compile(r"(.*?)\[Length:\s*(\d+)\]")

class IfaceDnetWin(ParamSettingWin):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.resize(900, 450)
        self.setWindowTitle("Interface >> DeviceNet Settings")

        self.add_param_folder_widget(ParamFolderIfaceDnetBasicWidget())
        self.add_param_folder_widget(ParamFolderIfaceDnetConnLossWidget())

        columns_layout = QHBoxLayout()
        columns_layout.setSpacing(5)

        self.out_layout = QVBoxLayout()
        self.in_layout = QVBoxLayout()
        
        columns_layout.addLayout(self.out_layout, 1)
        columns_layout.addLayout(self.in_layout, 1)        

        self.content_layout.addLayout(columns_layout)
        
        self.add_in_folder(ParamFolderIfaceDnetIoOutWidget())
        self.add_in_folder(ParamFolderIfaceDnetScaleOutWidget())
        self.in_layout.addStretch()

        self.add_out_folder(ParamFolderIfaceDnetIoInWidget())
        self.add_out_folder(ParamFolderIfaceDnetScaleInWidget())
        self.out_layout.addStretch()

        self.content_layout.addStretch()

        self.init_toolbar()
        self.toolbar.add_action("Create EDS", self.on_clicked_create_eds)

        self.number_of_valves_param = ParamManager().get_by_full_path("Cluster.Settings.Number of Valves")
        self.param_worker.add_read_param_ptr(self.number_of_valves_param)
        
        self.init_end()

    def add_in_folder(self, widget):
        self.in_layout.addWidget(widget)
        self.parameter_folder_widgets.append(widget)

    def add_out_folder(self, widget):
        self.out_layout.addWidget(widget)
        self.parameter_folder_widgets.append(widget)        

    def on_clicked_create_eds(self):
        file_path, _ = QFileDialog.getSaveFileName(self, "Save EDS File", "", "EDS Files (*.eds);;All Files (*)")

        if not file_path:
            return 

        try:
            with open(path_def.RSRC_TEMPLATE_EDS_FILE, 'r', encoding='utf-8') as f:
                eds_template = f.read()
                vendor_id_param      = ParamManager().get_by_full_path("Interface DeviceNet.Identity Object.Instance.Vendor ID"                   )
                device_type_param    = ParamManager().get_by_full_path("Interface DeviceNet.Identity Object.Instance.Device Type"                 )
                product_code_param   = ParamManager().get_by_full_path("Interface DeviceNet.Identity Object.Instance.Product Code"                )
                product_name_param   = ParamManager().get_by_full_path("Interface DeviceNet.Identity Object.Instance.Product Name"                )
                revision_param       = ParamManager().get_by_full_path("Interface DeviceNet.Identity Object.Instance.Revision"                    )
                profile_param        = ParamManager().get_by_full_path("Interface DeviceNet.Connection Object.Profile.Profile"                    )
                data_type_param      = ParamManager().get_by_full_path("Interface DeviceNet.Connection Object.Profile.Data type"                  )
                output_name_param    = ParamManager().get_by_full_path("Interface DeviceNet.Connection Object.Output.Output Name"                 )
                input_name_param     = ParamManager().get_by_full_path("Interface DeviceNet.Connection Object.Input.Input Name"                   )
                output_sel_old_param = ParamManager().get_by_full_path("Interface DeviceNet.Connection Object.Output.Output Selector Bitmap (old)")
                input_sel_old_param  = ParamManager().get_by_full_path("Interface DeviceNet.Connection Object.Input.Input Selector Bitmap (old)"  )

                is_int16_data_type = data_type_param.value == DeviceNetDataTypeEnum.INT16.value
                slave_count = self.number_of_valves_param.value
                
                vender_id:int = vendor_id_param.value
                prod_type_str:str = DeviceNetDevTypeEnum.get_desc(device_type_param.value)
                prod_code:int = product_code_param.value
                prod_name :str = product_name_param.value
                maj_rev:int = revision_param.value // 256
                min_rev:int = revision_param.value % 256
                output_assembly_name = "Output Assembly 1"
                output_epath = "20 04 24 96 30 03"
                output_obj_names: str = ""
                outputLength:int = 0
                input_assembly_name = "Input Assembly 1"
                input_epath = "20 04 24 64 30 03"
                input_obj_names:str = ""
                inputLength:int = 0

                if profile_param.value == DeviceNetProfileTypeEnum.GENERIC_DEVICE_B.value:
                    outputLength, output_obj_names = self.make_names(output_sel_old_param)
                    inputLength, input_obj_names = self.make_names(input_sel_old_param)
                else:
                    outputLength, output_obj_names = self.parse_names(output_name_param)
                    inputLength, input_obj_names = self.parse_names(input_name_param)

                now = datetime.now()
                date_str = now.strftime("%m-%d-%Y")
                time_str = now.strftime("%H:%M:%S")

                eds_content = eds_template

                eds_content = re.sub(r"CreateDate[ \t]*=[ \t]*.*", f"CreateDate = {date_str};", eds_content)
                eds_content = re.sub(r"CreateTime[ \t]*=[ \t]*.*", f"CreateTime = {time_str};", eds_content)
                eds_content = re.sub(r"ModDate[ \t]*=[ \t]*.*", f"ModDate = {date_str};", eds_content)
                eds_content = re.sub(r"ModTime[ \t]*=[ \t]*.*", f"ModTime = {time_str};", eds_content)

                eds_content = re.sub(r"VendCode[ \t]*=[ \t]*.*", f"VendCode = {vender_id};", eds_content)
                eds_content = re.sub(r"ProdType[ \t]*=[ \t]*.*", f"ProdType = {device_type_param.value};", eds_content)
                eds_content = re.sub(r"ProdTypeStr[ \t]*=[ \t]*.*", f'ProdTypeStr = "{prod_type_str}";', eds_content)
                eds_content = re.sub(r"ProdCode[ \t]*=[ \t]*.*", f"ProdCode = {prod_code};", eds_content)
                eds_content = re.sub(r"MajRev[ \t]*=[ \t]*.*", f"MajRev = {maj_rev};", eds_content)
                eds_content = re.sub(r"MinRev[ \t]*=[ \t]*.*", f"MinRev = {min_rev};", eds_content)
                eds_content = re.sub(r"ProdName[ \t]*=[ \t]*.*", f'ProdName = "{prod_name}";', eds_content)

                eds_content = re.sub(r"Input1[ \t]*=[ \t]*.*", f'Input1 = {inputLength},0,0x000F,"{input_assembly_name}",6,"{input_epath}","{input_obj_names}";', eds_content)
                eds_content = re.sub(r"Output1[ \t]*=[ \t]*.*", f'Output1 = {outputLength},0,0x000F,"{output_assembly_name}",6,"{output_epath}","{output_obj_names}";', eds_content)

                lines = eds_content.splitlines()
                new_lines = []

                for line in lines:
                    if any(p in line for p in ["Param3 =", "Param5 =", "Param8 =", "Param9 =", "Param10 =", "Param11 =", "Param12 =", "Param13 =", "Param30 ="]):
                        if is_int16_data_type:
                            byteSize = "2"; min_val = "-32768"  ; max_val = "32767"  ; fixedN = "0"
                            line = line.replace("%1", "195")
                        else:
                            byteSize = "4"; min_val = "-3.0E+38"; max_val = "3.0E+38"; fixedN = "4"
                            line = line.replace("%1", "202")    
                        
                        line = line.replace("%2", byteSize)
                        line = line.replace("%3", min_val)
                        line = line.replace("%4", max_val)
                        line = line.replace("%5", fixedN)
                    elif "Param16 =" in line:
                        if slave_count > 0:
                            line = line.replace("%1", str(slave_count))
                            line = line.replace("%2", "Cluster information")
                        else:
                            line = line.replace("%1", "1")
                            line = line.replace("%2", "Reserved")
                    elif "Param28 =" in line:
                        if is_int16_data_type:
                            byteSize = "2"; fixedN = "0"
                            line = line.replace("%1", "195")
                        else:
                            byteSize = "4"; fixedN = "4"
                            line = line.replace("%1", "202") 
                            
                        line = line.replace("%2", byteSize)
                        line = line.replace("%3", fixedN)

                    new_lines.append(line)
                
                eds_content = "\n".join(new_lines)
            
                with open(file_path, 'w', encoding='utf-8') as f_out:
                    f_out.write(eds_content)
            
                QMessageBox.information(self, "Success", "EDS file has been created successfully.")
        except Exception as e:
            print(f"[IfaceDnetWin] EDS 파일 생성 중 오류 발생: {e}") 
            QMessageBox.critical(self, "Error", f"Failed to create EDS file.\nError details: {e}")

    def parse_names(self, p_names_obj):
        total_length = 0
        names_list = []
        
        if p_names_obj and p_names_obj.value:
            items = p_names_obj.value.split('/')
            for item in items:
                match = RE_NAME_LENGTH.search(item.strip())
                if match:
                    length = int(match.group(2))
                    total_length += length
                    names_list.append(f"{match.group(1).strip()}({length})")
                
        return total_length, ",".join(names_list)

    def make_names(self, param):
        bitmap = param.value
        total_length = 0
        names_list = []
        
        if param and hasattr(param, 'ref_list'):
            for item in param.ref_list:
                if (bitmap & (1 << item.value)) != 0:
                    description = item.description.strip()
                    match = RE_BITMAP_LENGTH.search(description)
                    
                    if match:
                        name = match.group(1).strip()
                        length = int(match.group(2))
                        
                        total_length += length
                        
                        names_list.append(f"{name}({length})")
                    else:
                        names_list.append(description)
                    
        return total_length, ",".join(names_list)