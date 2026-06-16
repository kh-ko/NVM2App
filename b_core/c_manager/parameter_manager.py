
import os
import json
import threading

from typing import Union, List, Dict, Optional
from PySide6.QtCore import QFile, QIODevice

from b_core.a_define import file_folder_path as path_def
from b_core.b_datatype import param_enum as p_enum
from b_core.b_datatype.general_enum import LogType, ParamDataType, ParamAccType, ParamDisplayType
from b_core.c_manager.log_manager import LogManager
from b_core.b_datatype.parameter_errnum import ParameterErrNum 
from b_core.b_datatype.parameter import Parameter


class ParamManager:
    _instance = None
    _creation_lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        # 멀티스레드 환경에서 동시에 생성되는 것을 방지
        with cls._creation_lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        # 중복 초기화 방어
        if self._initialized:
            return

        self._initialized = True
        self._init_manager()     

    def _init_manager(self):
        f_min = -3.4028235e+38
        f_max = 3.4028235e+38
        n_min = -2147483648
        n_max = 2147483647
        un_min = 0
        un_max = 4294967295

        self._param_map: Dict[tuple, Parameter] = {}  # (path, name) 검색용
        self._parameters: List[Parameter] = []         # 전체 리스트 보관용

        if os.path.exists(path_def.RSRC_PARAM_SCHEMA_JSON_FILE):
            try:
                with open(path_def.RSRC_PARAM_SCHEMA_JSON_FILE, 'r', encoding='utf-8') as f:
                    param_list = json.load(f)
            except Exception as e:
                print(f"[ParamManager] 로드 실패: {e}")

        for param in param_list:
            param_type = param["type"]
            param_path = param["path"]
            param_id = param["id"]
            param_index = param["idx"]
            param_acc_str = param["acc"]
            param_acc = getattr(ParamAccType, param_acc_str, ParamAccType.RO)
            param_local_acc = param["local_acc"]
            param_nor_backup = param["nor_backup"]
            param_fu_backup = param["fu_backup"]
            param_desc = param["desc"]

            param_enable_condition = param.get("enable")
            param_visible_condition = param.get("visible")
    


            try:
                param_reconnect = param["reconnect"]
            except Exception:
                param_reconnect = False

            if param_type == "enum":
                enum_str = param["enum"]
                enum_class = getattr(p_enum, enum_str, None)
                self._add_param_enum(param_path, param_id,  param_index, param_acc, enum_class, param_local_acc, param_nor_backup, param_fu_backup, param_enable_condition, param_visible_condition, param_desc)
            elif param_type == "errnum":
                component_enum_str = param["component_enum"]
                component_enum_class = getattr(p_enum, component_enum_str, None)
                mode_enum_str = param["mode_enum"]
                mode_enum_class = getattr(p_enum, mode_enum_str, None)
                type_enum_str = param["mode_enum"]
                type_enum_class = getattr(p_enum, type_enum_str, None)
                self._add_param_errnum(param_path, param_id,  param_index, param_acc, component_enum_class, "Component", mode_enum_class, "Mode", type_enum_class, "Type", param_local_acc, param_nor_backup, param_fu_backup, param_enable_condition, param_visible_condition, param_desc)
            elif param_type == "bitmap":
                enum_str = param["enum"]
                enum_class = getattr(p_enum, enum_str, None)
                self._add_param_bitmap(param_path, param_id,  param_index, param_acc, enum_class, param_local_acc, param_nor_backup, param_fu_backup, param_enable_condition, param_visible_condition, param_desc)
            elif param_type == "text":
                self._add_param_text(param_path, param_id,  param_index, param_acc, param_local_acc, param_nor_backup, param_fu_backup, param_enable_condition, param_visible_condition, param_desc)
            elif param_type == "hex" or param_type == "num" or param_type == "real" or param_type == "scale" or param_type == "posi" or param_type == "ifgain":
                try:
                    min_str = param["min"]
                    max_str = param["max"]
                except Exception:
                    min_str = "0"
                    max_str = "0"

                if param_type == "hex" or param_type == "num":
                    if min_str.startswith("0x"):
                        min = int(min_str, 16)
                    else:
                        min = int(min_str)
                    
                    if max_str.startswith("0x"):
                        max = int(max_str, 16)
                    else:
                        max = int(max_str)
                else:
                    min = float(min_str)
                    max = float(max_str)
                
                if param_type == "hex":
                    self._add_param_hex(param_path, param_id, param_index, param_acc, min, max, param_local_acc, param_nor_backup, param_fu_backup, param_enable_condition, param_visible_condition, param_desc)
                elif param_type == "num":
                    self._add_param_num(param_path, param_id, param_index, param_acc, min, max, param_local_acc, param_nor_backup, param_fu_backup, param_enable_condition, param_visible_condition, param_desc)
                elif param_type == "real":
                    self._add_param_real(param_path, param_id, param_index, param_acc, min, max, param_local_acc, param_nor_backup, param_fu_backup, param_enable_condition, param_visible_condition, param_desc)
                elif param_type == "scale":
                    self._add_param_scale(param_path, param_id, param_index, param_acc, min, max, param_local_acc, param_nor_backup, param_fu_backup, param_enable_condition, param_visible_condition, param_desc)
                elif param_type == "posi":
                    self._add_param_posi(param_path, param_id, param_index, param_acc, min, max, param_local_acc, param_nor_backup, param_fu_backup, param_enable_condition, param_visible_condition, param_desc)
                elif param_type == "ifgain":
                    self._add_param_ifgain(param_path, param_id, param_index, param_acc, min, max, param_local_acc, param_nor_backup, param_fu_backup, param_enable_condition, param_visible_condition, param_desc)
            elif param_type == "pres" or param_type == "s1pres" or param_type == "s2pres" or param_type == "presslope":
                self._add_param_pres(param_type, param_path, param_id, param_index, param_acc, f_min, f_max, param_local_acc, param_nor_backup, param_fu_backup, param_enable_condition, param_visible_condition, param_desc)
            elif param_type == "btn":
                write_value = param["value"]
                self._add_param_btn(param_path, param_id,  param_index, param_acc, write_value, param_local_acc, param_nor_backup, param_fu_backup, param_reconnect, param_enable_condition, param_visible_condition, param_desc)
            elif param_type == "compound":
                self._add_param_compound(param_path, param_id, param_index)

        '''              
        PFO            
        
        self._add_param_real  ("Power Fail Option.Battery Voltage [V]"                                                   , "22050000",  0, ParamAccType.RO, f_min, f_max, ""            , False, False, False, "Shows state of charge")
        self._add_param_real  ("Power Fail Option.Delay [sec]"                                                           , "22040000",  0, ParamAccType.RW, f_min, f_max, ""            , False, True , True , "In seconds After this delay,<br>the power failure reaction starts after the power failed.<br>Helps to bridge a short power interruption.")
        self._add_param_enum  ("Power Fail Option.Enable"                                                                , "22010000",  0, ParamAccType.RW, p_enum.DisableEnableEnum    , False, True , True , None)
        self._add_param_enum  ("Power Fail Option.Functionality"                                                         , "22030000",  0, ParamAccType.RW, p_enum.PfoFuncEnum          , False, True , True , None)
        self._add_param_num   ("Power Fail Option.Power Fail Cycles"                                                     , "22060000",  0, ParamAccType.RW, un_min, un_max, ""          , False, False, False, "Counts Power Failure")
        self._add_param_enum  ("Power Fail Option.State"                                                                 , "22020000",  0, ParamAccType.RO, p_enum.PfoStateEnum         , False, False, False, None)
        ''' 

        '''              
        Power Connector IO            
        
        self._add_param_enum  ("Power Connector IO.Drive Power Enable"                                                   , "37500000",  0, ParamAccType.RO, p_enum.DisableEnableEnum    , False, False, False, None)

        self._add_param_enum  ("Power Connector IO.Digital Input 1.Enable"                                               , "37010100",  0, ParamAccType.RW, p_enum.DisableEnableEnum    , False, True , True , None)
        self._add_param_enum  ("Power Connector IO.Digital Input 1.Functionality"                                        , "37010300",  0, ParamAccType.RW, p_enum.DigitalInFuncEnum    , False, True , True , None)
        self._add_param_enum  ("Power Connector IO.Digital Input 1.Inverted"                                             , "37010400",  0, ParamAccType.RW, p_enum.DigitalIOInvertEnum  , False, True , True , None)
        self._add_param_enum  ("Power Connector IO.Digital Input 1.State"                                                , "37010200",  0, ParamAccType.RO, p_enum.OffOnEnum            , False, False, False, None)
        self._add_param_enum  ("Power Connector IO.Digital Input 2.Enable"                                               , "37020100",  0, ParamAccType.RW, p_enum.DisableEnableEnum    , False, True , True , None)
        self._add_param_enum  ("Power Connector IO.Digital Input 2.Functionality"                                        , "37020300",  0, ParamAccType.RW, p_enum.DigitalInFuncEnum    , False, True , True , None)
        self._add_param_enum  ("Power Connector IO.Digital Input 2.Inverted"                                             , "37020400",  0, ParamAccType.RW, p_enum.DigitalIOInvertEnum  , False, True , True , None)
        self._add_param_enum  ("Power Connector IO.Digital Input 2.State"                                                , "37020200",  0, ParamAccType.RO, p_enum.OffOnEnum            , False, False, False, None)
        self._add_param_enum  ("Power Connector IO.Digital Output 1.Enable"                                              , "37030100",  0, ParamAccType.RW, p_enum.DisableEnableEnum    , False, True , True , None)
        self._add_param_enum  ("Power Connector IO.Digital Output 1.Functionality"                                       , "37030300",  0, ParamAccType.RW, p_enum.DigitalOutFuncEnum   , False, True , True , None)
        self._add_param_enum  ("Power Connector IO.Digital Output 1.Inverted"                                            , "37030400",  0, ParamAccType.RW, p_enum.DigitalIOInvertEnum  , False, True , True , None)
        self._add_param_enum  ("Power Connector IO.Digital Output 1.State"                                               , "37030200",  0, ParamAccType.RO, p_enum.OffOnEnum            , False, False, False, None)
        self._add_param_enum  ("Power Connector IO.Digital Output 2.Enable"                                              , "37040100",  0, ParamAccType.RW, p_enum.DisableEnableEnum    , False, True , True , None)
        self._add_param_enum  ("Power Connector IO.Digital Output 2.Functionality"                                       , "37040300",  0, ParamAccType.RW, p_enum.DigitalOutFuncEnum   , False, True , True , None)
        self._add_param_enum  ("Power Connector IO.Digital Output 2.Inverted"                                            , "37040400",  0, ParamAccType.RW, p_enum.DigitalIOInvertEnum  , False, True , True , None)
        self._add_param_enum  ("Power Connector IO.Digital Output 2.State"                                               , "37040200",  0, ParamAccType.RO, p_enum.OffOnEnum            , False, False, False, None)
        ''' 

        '''              
        DeviceNet User interface            
        
        self._add_param_hex ("Interface DeviceNet.Identity Object.Instance.Vendor ID"                                    , "A4010101", 0, ParamAccType.RW,                                False, True , True , "")
        self._add_param_enum("Interface DeviceNet.Identity Object.Instance.Device Type"                                  , "A4010102", 0, ParamAccType.RW, p_enum.DeviceNetDevTypeEnum  , False, True , True , None)
        self._add_param_hex ("Interface DeviceNet.Identity Object.Instance.Product Code"                                 , "A4010103", 0, ParamAccType.RW,                                False, True , True , "")
        self._add_param_hex ("Interface DeviceNet.Identity Object.Instance.Revision"                                     , "A4010104", 0, ParamAccType.RO,                                False, False, False, "")
        self._add_param_hex ("Interface DeviceNet.Identity Object.Instance.Serial Number"                                , "A4010104", 0, ParamAccType.RO,                                False, False, False, "")
        self._add_param_text("Interface DeviceNet.Identity Object.Instance.Product Name"                                 , "A4010107", 0, ParamAccType.RO,                                False, False, False, "")
        self._add_param_btn ("Interface DeviceNet.Identity Object.Services.Reset"                                        , "A401F005", 0, ParamAccType.WO, "1"                          , False, False, False, "")
        self._add_param_num ("Interface DeviceNet.DeviceNet Object.MAC ID"                                               , "A4030100", 0, ParamAccType.RW, 0, 63, ""                    , False, True , True , "")
        self._add_param_num ("Interface DeviceNet.DeviceNet Object.MAC ID Switch"                                        , "A4030300", 0, ParamAccType.RW, 0, 63, ""                    , False, True , True , "")
        self._add_param_enum("Interface DeviceNet.DeviceNet Object.Baud Rate"                                            , "A4030200", 0, ParamAccType.RW, p_enum.DeviceNetBaudRateEnum , False, True , True , None)
        self._add_param_enum("Interface DeviceNet.DeviceNet Object.Profile.Profile"                                      , "A4056600", 0, ParamAccType.RW, p_enum.DeviceNetProfileTypeEnum, False, True , True , None)
        ''' 

    def _add_param_btn(self, full_path: str, id: str, index: int, param_acc : ParamAccType, write_str: str, is_only_local_acc:bool, is_nor_backup: bool, is_fu_backup: bool, is_need_reconnect:bool, param_enable_condition, param_visible_condition, description: str | None):
        path, name = full_path.rsplit(".", 1)

        self._add_param(Parameter(path, name, id, index, ParamDisplayType.BTN, ParamDataType.UINT32, param_acc, is_only_local_acc, is_nor_backup, is_fu_backup, "", int(0), int(0), None, param_enable_condition, param_visible_condition, description, write_str, is_need_reconnect))


    def _add_param_enum(self, full_path: str, id: str, index: int, param_acc : ParamAccType, enum_class: type, is_only_local_acc:bool, is_nor_backup: bool, is_fu_backup: bool, param_enable_condition, param_visible_condition, description: str | None):
        path, name = full_path.rsplit(".", 1)

        if not description:
            items = [f"{item.value}: {item.description}" for item in enum_class]
            description = "<br>".join(items)

        self._add_param(Parameter(path, name, id, index, ParamDisplayType.ENUM, ParamDataType.UINT32, param_acc, is_only_local_acc, is_nor_backup, is_fu_backup, "", int(0), int(0), enum_class, param_enable_condition, param_visible_condition, description))


    def _add_param_bitmap(self, full_path: str, id: str, index: int, param_acc : ParamAccType, enum_class: type, is_only_local_acc:bool, is_nor_backup: bool, is_fu_backup: bool, param_enable_condition, param_visible_condition, description: str | None):
        path, name = full_path.rsplit(".", 1)

        if not description:
            items = [f"{item.value}: {item.description}" for item in enum_class]
            description = "<br>".join(items)

        self._add_param(Parameter(path, name, id, index, ParamDisplayType.BITMAP, ParamDataType.UINT32, param_acc, is_only_local_acc, is_nor_backup, is_fu_backup, "", int(0), int(4294967295), enum_class, param_enable_condition, param_visible_condition, description))


    def _add_param_errnum(self, full_path: str, id: str, index: int, param_acc : ParamAccType, enum_class1: type, name1: str, enum_class2: type, name2: str, enum_class3: type, name3: str, is_only_local_acc:bool, is_nor_backup: bool, is_fu_backup: bool, param_enable_condition, param_visible_condition, description: str | None):
        path, name = full_path.rsplit(".", 1)

        if not description:
            items1 = [f"{item.value}: {item.description}" for item in enum_class1]
            items2 = [f"{item.value}: {item.description}" for item in enum_class2]
            items3 = [f"{item.value}: {item.description}" for item in enum_class3]
            description = "<br>".join(items1 + items2 + items3)

        errnumparam = ParameterErrNum(path, name, id, index, ParamDisplayType.ERR_NUM , ParamDataType.UINT32, param_acc, is_only_local_acc, is_nor_backup, is_fu_backup, "", int(0), int(4294967295), param_enable_condition, param_visible_condition, description)
        errnumparam.add_ref_list(name1, enum_class1) 
        errnumparam.add_ref_list(name2, enum_class2) 
        errnumparam.add_ref_list(name3, enum_class3) 

        self._add_param(errnumparam)        


    def _add_param_text(self, full_path: str, id: str, index: int, param_acc : ParamAccType, is_only_local_acc:bool, is_nor_backup: bool, is_fu_backup: bool, param_enable_condition, param_visible_condition, description: str):
        path, name = full_path.rsplit(".", 1)
        self._add_param(Parameter(path, name, id, index, ParamDisplayType.TEXT, ParamDataType.STR, param_acc, is_only_local_acc, is_nor_backup, is_fu_backup, None, int(0), int(0), None, param_enable_condition, param_visible_condition, description))

    def _add_param_hex(self, full_path: str, id: str, index: int, param_acc : ParamAccType, min_value: int, max_value: int, is_only_local_acc:bool, is_nor_backup: bool, is_fu_backup: bool, param_enable_condition, param_visible_condition, description: str):
        path, name = full_path.rsplit(".", 1)
        self._add_param(Parameter(path, name, id, index, ParamDisplayType.HEX, ParamDataType.UINT32, param_acc, is_only_local_acc, is_nor_backup, is_fu_backup, None, min_value, max_value, None, param_enable_condition, param_visible_condition, description))


    def _add_param_num(self, full_path: str, id: str, index: int, param_acc : ParamAccType, min_value: int, max_value: int, is_only_local_acc:bool, is_nor_backup: bool, is_fu_backup: bool, param_enable_condition, param_visible_condition, description: str):
        path, name = full_path.rsplit(".", 1)
        self._add_param(Parameter(path, name, id, index, ParamDisplayType.NUMBER, ParamDataType.UINT32, param_acc, is_only_local_acc, is_nor_backup, is_fu_backup, None, min_value, max_value, None, param_enable_condition, param_visible_condition, description))

    def _add_param_pres(self, display_type:str, full_path: str, id: str, index: int, param_acc : ParamAccType, min_value: float, max_value: float, is_only_local_acc:bool, is_nor_backup: bool, is_fu_backup: bool, param_enable_condition, param_visible_condition, description: str):
        path, name = full_path.rsplit(".", 1)

        if display_type == "s1pres":
            display_type = ParamDisplayType.SENS1_PRES
        elif display_type == "s2pres":
            display_type = ParamDisplayType.SENS2_PRES
        elif display_type == "presslope":
            display_type = ParamDisplayType.PRESS_SLOPE
        else:
            display_type = ParamDisplayType.SENS_PRES

        self._add_param(Parameter(path, name, id, index, display_type, ParamDataType.FLOAT, param_acc, is_only_local_acc, is_nor_backup, is_fu_backup, None, min_value, max_value, None, param_enable_condition, param_visible_condition, description))

    def _add_param_posi(self, full_path: str, id: str, index: int, param_acc : ParamAccType, min_value: float, max_value: float, is_only_local_acc:bool, is_nor_backup: bool, is_fu_backup: bool, param_enable_condition, param_visible_condition, description: str):
        path, name = full_path.rsplit(".", 1)
        self._add_param(Parameter(path, name, id, index, ParamDisplayType.POSI, ParamDataType.FLOAT, param_acc, is_only_local_acc, is_nor_backup, is_fu_backup, None, min_value, max_value, None, param_enable_condition, param_visible_condition, description))

    def _add_param_real(self, full_path: str, id: str, index: int, param_acc : ParamAccType, min_value: float, max_value: float, is_only_local_acc:bool, is_nor_backup: bool, is_fu_backup: bool, param_enable_condition, param_visible_condition, description: str):
        path, name = full_path.rsplit(".", 1)
        self._add_param(Parameter(path, name, id, index, ParamDisplayType.REAL, ParamDataType.FLOAT, param_acc, is_only_local_acc, is_nor_backup, is_fu_backup, None, min_value, max_value, None, param_enable_condition, param_visible_condition, description))   

    def _add_param_ifgain(self, full_path: str, id: str, index: int, param_acc : ParamAccType, min_value: float, max_value: float, is_only_local_acc:bool, is_nor_backup: bool, is_fu_backup: bool, param_enable_condition, param_visible_condition, description: str):
        path, name = full_path.rsplit(".", 1)
        self._add_param(Parameter(path, name, id, index, ParamDisplayType.IFACE_GAIN, ParamDataType.FLOAT, param_acc, is_only_local_acc, is_nor_backup, is_fu_backup, None, min_value, max_value, None, param_enable_condition, param_visible_condition, description))   

    def _add_param_scale(self, full_path: str, id: str, index: int, param_acc : ParamAccType, min_value: float, max_value: float, is_only_local_acc:bool, is_nor_backup: bool, is_fu_backup: bool, param_enable_condition, param_visible_condition, description: str):
        path, name = full_path.rsplit(".", 1)
        self._add_param(Parameter(path, name, id, index, ParamDisplayType.SCALE, ParamDataType.FLOAT, param_acc, is_only_local_acc, is_nor_backup, is_fu_backup, None, min_value, max_value, None, param_enable_condition, param_visible_condition, description)) 

    def _add_param_compound(self, full_path: str, id: str, index: int):
        path, name = full_path.rsplit(".", 1)
        self._add_param(Parameter(path, name, id, index, ParamDisplayType.HEX, ParamDataType.UINT32, ParamAccType.RW, False, False, False, "", int(0), int(4294967295), None, None, None, ""))

    def _add_param(self, param: Parameter):
        self._parameters.append(param)
        self._param_map[(param.path, param.name)] = param

    def get_by_full_path(self, full_path: str) -> Optional[Parameter]:
        path, name = full_path.rsplit(".", 1)
        ret_param = self._param_map.get((path, name))
        if ret_param is None:
            LogManager().log(LogType.ERROR, f"[ParameterManager] 파라미터를 찾을 수 없습니다: {full_path}")
        return ret_param

    def get(self, path: str, name: str) -> Optional[Parameter]:
        ret_param = self._param_map.get((path, name))
        if ret_param is None:
            LogManager().log(LogType.ERROR, f"[ParameterManager] 파라미터를 찾을 수 없습니다: {path}, {name}")
        return ret_param

    def get_params_in_folder(self, folder_path: str) -> List[Parameter]:
        ret_params: List[Parameter] = []
        for param in self._parameters:
            if param.path == folder_path:
                ret_params.append(param)
        return ret_params

    def get_all(self) -> List[Parameter]:
        """전체 파라미터 리스트를 가져옵니다."""
        return self._parameters
        
