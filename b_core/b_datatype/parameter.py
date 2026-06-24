from typing import Tuple
from typing import List, Dict, Union, Type
from PySide6.QtCore import QObject, Signal

from b_core.b_datatype.general_enum import ParamDisplayType, ParamDataType, ParamAccType, ParamParseErrType, PARAM_DISPLAY_TYPE_MAP
from b_core.b_datatype import param_enum as p_enum

from b_core.c_manager.log_manager import LogManager

class ParamCondition(QObject):
    def __init__(self, parent:QObject):
        super().__init__(parent)

        self.ref_id = None
        self.ref_index = 0
        self.values : List[Union[int, float, str, None]] = []
        
        

class Parameter(QObject):
    # 값이 변경되었을 때 발생하는 시그널 (새로운 값을 문자열로 전달)
    sig_value_changed = Signal()
    sig_is_not_support_changed = Signal()
    sig_is_err_changed = Signal()

    ERR_CODE_MAP = {
        "0C" : ParamParseErrType.ERR_0C_WRONG_CMD_LEN                                   ,                                  
        "1C" : ParamParseErrType.ERR_1C_WRONG_CMD_LEN                                  ,
        "1D" : ParamParseErrType.ERR_1D_VALUE_TOO_LOW                                  ,
        "20" : ParamParseErrType.ERR_20_RESULTING_ZERO_ADJUST_OFFSET_VALUE_OUT_OF_RANGE,
        "21" : ParamParseErrType.ERR_21_NOT_VALID_BECAUSE_NO_SENSOR_ENABLED            ,
        "50" : ParamParseErrType.ERR_50_WRONG_ACCESS_MODE                              ,
        "51" : ParamParseErrType.ERR_51_TIMEOUT                                        ,
        "6D" : ParamParseErrType.ERR_6D_EEPROM_NOT_READY                               ,
        "6E" : ParamParseErrType.ERR_6E_WRONG_PARAMETER_ID                             ,
        "6F" : ParamParseErrType.ERR_6F_SET_TO_DEFAULT_VALUE_NOT_ALLOWED               ,
        "70" : ParamParseErrType.ERR_70_PARAMETER_NOT_SETTABLE                         ,
        "71" : ParamParseErrType.ERR_71_PARAMETER_NOT_READABLE                         ,
        "72" : ParamParseErrType.ERR_72_SET_TO_INITIAL_VALUE_NOT_ALLOWED               ,
        "73" : ParamParseErrType.ERR_73_WRONG_PARAMETER_INDEX                          ,
        "74" : ParamParseErrType.ERR_74_INITIAL_VALUE_OUT_OF_RANGE                     ,
        "76" : ParamParseErrType.ERR_76_WRONG_VALUE                                    ,
        "77" : ParamParseErrType.ERR_77_WRONG_VALUE_ONLY_RESET_POSSIBLE                ,
        "78" : ParamParseErrType.ERR_78_NOT_ALLOWED_IN_THIS_STATE                      ,
        "7A" : ParamParseErrType.ERR_7A_WRONG_SERVICE                                  ,
        "7B" : ParamParseErrType.ERR_7B_PARAMETER_NOT_ACTIVE                           ,
        "7C" : ParamParseErrType.ERR_7C_PARAMETER_SYSTEM_ERROR                         ,
        "7D" : ParamParseErrType.ERR_7D_COMMUNICATION_ERROR                            ,
        "7E" : ParamParseErrType.ERR_7E_UNKNOWN_SERVICE                                ,
        "7F" : ParamParseErrType.ERR_7F_UNEXPECTED_CHARACTER                           ,
        "80" : ParamParseErrType.ERR_80_NO_ACCESS_RIGHTS                               ,
        "81" : ParamParseErrType.ERR_81_NO_ADEQUATELY_HARDWARE                         ,
        "82" : ParamParseErrType.ERR_82_WRONG_OBJECT_STATE                             ,
        "84" : ParamParseErrType.ERR_84_NO_SLAVE_COMMAND                               ,
        "85" : ParamParseErrType.ERR_85_COMMAND_TO_UNKNOWN_SLAVE                       ,
        "87" : ParamParseErrType.ERR_87_COMMAND_TO_MASTER_ONLY                         ,
        "88" : ParamParseErrType.ERR_88_ONLY_G_COMMAND_ALLOWED                         ,
        "89" : ParamParseErrType.ERR_89_NOT_SUPPORTED                                  ,
        "A0" : ParamParseErrType.ERR_A0_FUNCTION_IS_DISABLED                           ,
        "A1" : ParamParseErrType.ERR_A1_ALREADY_DONE                                   
    }

    NOT_SUPPORT_CODES = frozenset({"6E", "73", "7B", "7E", "89"}) # 검색 속도가 빠른 frozenset 사용
    
    INT_TYPES = (ParamDataType.INT8, ParamDataType.INT16, ParamDataType.INT32, ParamDataType.UINT8, ParamDataType.UINT16, ParamDataType.UINT32)
    FLOAT_TYPES = (ParamDataType.FLOAT, ParamDataType.DOUBLE)
    STR_TYPES = (ParamDataType.STR,)

    def __init__(self, param_json, param_display_type: ParamDisplayType):
        super().__init__()

        full_path         = param_json.get("path", "")
        path, name        = full_path.rsplit(".", 1)
        id                = param_json.get("id", "")
        index             = param_json.get("idx", 0)
        proto_type        = param_json.get("proto_type", None)
        acc_str           = param_json.get("acc", "RO")
        acc               = getattr(ParamAccType, acc_str, ParamAccType.RO)
        local_acc         = param_json.get("local_acc", False)
        nor_backup        = param_json.get("nor_backup", False)
        fu_backup         = param_json.get("fu_backup", False)
        desc              = param_json.get("desc", None)
        enable_condition  = param_json.get("enable", None)
        visible_condition = param_json.get("visible", None)
        reconnect         = param_json.get("reconnect", False)

        if proto_type == "NV1":
            self.is_nv1_proto  = True
        else:
            self.is_nv1_proto  = False

        self.display_type      = param_display_type
        self.path              = path
        self.name              = name
        self.id                = id
        self.index             = index
        self.acc               = acc
        self.is_only_local_acc = local_acc
        self.is_nor_backup     = nor_backup
        self.is_fu_backup      = fu_backup
        self.description       = desc
        self.is_need_reconnect = reconnect

        if enable_condition is not None:
            self.enable_conditions = []
            for cond in enable_condition:
                param_cond = ParamCondition(self)
                param_cond.ref_id = cond.get("id")
                param_cond.values = cond.get("conditions", [])
                self.enable_conditions.append(param_cond)
        else:
            self.enable_conditions = None
        
        if visible_condition is not None:
            self.visible_conditions = []
            for cond in visible_condition:
                param_cond = ParamCondition(self)
                param_cond.ref_id = cond.get("id")
                param_cond.values = cond.get("conditions", [])
                self.visible_conditions.append(param_cond)
        else:
            self.visible_conditions = None

        
        self.data_type = ParamDataType.FLOAT
        self.min_value : Union[int, float, None] = None
        self.max_value : Union[int, float, None] = None
        self.ref_list  = None # Type[p_enum.DescriptionEnum] or List[Tuple[str, Type[DescriptionEnum]]] 
        self._value : Union[int, float, str, None] = None
        self.str_value : str = ""
        self._is_not_support : bool = False
        self._is_err : bool = False
        self.write_str_value : str | None = None
        self.nv1_read_req : str | None = None
        self.nv1_write_req : str | None = None
        self.nv1_read_res : str | None = None
        self.nv1_write_res : str | None = None
        
        if self.display_type == ParamDisplayType.ENUM:
            self._init_enum(param_json)
        elif self.display_type == ParamDisplayType.BTN:
            self._init_btn(param_json)
        elif self.display_type == ParamDisplayType.BITMAP:
            self._init_bitmap(param_json)
        elif self.display_type == ParamDisplayType.ERR_NUM:
            self._init_errnum(param_json)
        elif self.display_type == ParamDisplayType.TEXT:
            self._init_text(param_json)
        elif self.display_type == ParamDisplayType.HEX:
            self._init_hex(param_json)
        elif self.display_type == ParamDisplayType.NUMBER:
            self._init_number(param_json)
        elif self.display_type == ParamDisplayType.REAL:
            self._init_real(param_json)
        elif self.display_type == ParamDisplayType.SCALE:
            self._init_scale(param_json)
        elif self.display_type == ParamDisplayType.POSI:
            self._init_posi(param_json)
        elif self.display_type == ParamDisplayType.IFACE_GAIN:
            self._init_ifgain(param_json)
        elif self.display_type == ParamDisplayType.SENS_PRES:
            self._init_sens_pres(param_json)
        elif self.display_type == ParamDisplayType.SENS1_PRES:
            self._init_sens1_pres(param_json)
        elif self.display_type == ParamDisplayType.SENS2_PRES:
            self._init_sens2_pres(param_json)
        elif self.display_type == ParamDisplayType.PRESS_SLOPE:
            self._init_press_slope(param_json) 
        elif self.display_type == ParamDisplayType.NV1_GROUP:
            self._init_nv1_group(param_json) 

    def _init_enum(self, param_json):
        self.data_type = ParamDataType.UINT32; self.min_value = 0; self.max_value = 0xFFFFFFFF
        enum_str = param_json.get("enum"); enum_class = getattr(p_enum, enum_str, None); self.ref_list = enum_class

        if not self.description:
            items = [f"{item.value}: {item.description}" for item in self.ref_list]
            self.description = "<br>".join(items)

    def _init_btn(self, param_json):
        btn_value = param_json.get("value", ""); self.btn_str_value = btn_value

    def _init_bitmap(self, param_json):
        self.data_type = ParamDataType.UINT32; self.min_value = 0; self.max_value = 0xFFFFFFFF
        enum_str = param_json.get("enum"); enum_class = getattr(p_enum, enum_str, None); self.ref_list = enum_class

        if not self.description:
            items = [f"{item.value}: {item.description}" for item in self.ref_list]
            self.description = "<br>".join(items)

    def _init_text(self, param_json):
        self.data_type = ParamDataType.STR; #self.min_value = 0; self.max_value = 255

    def _init_hex(self, param_json):
        self.data_type = ParamDataType.UINT32; self.min_value, self.max_value = self._get_min_max_val(param_json)

    def _init_number(self, param_json):
        self.data_type = ParamDataType.UINT32; self.min_value, self.max_value = self._get_min_max_val(param_json)

    def _init_real(self, param_json):
        self.data_type = ParamDataType.FLOAT; self.min_value, self.max_value = self._get_min_max_val(param_json)

    def _init_scale(self, param_json):
        self.data_type = ParamDataType.FLOAT; self.min_value, self.max_value = self._get_min_max_val(param_json)

    def _init_posi(self, param_json):
        self.data_type = ParamDataType.FLOAT; self.min_value, self.max_value = self._get_min_max_val(param_json)

    def _init_ifgain(self, param_json):
        self.data_type = ParamDataType.FLOAT; self.min_value, self.max_value = self._get_min_max_val(param_json)

    def _init_sens_pres(self, param_json):
        self.data_type = ParamDataType.FLOAT; self.min_value = -3.4028235e+38; self.max_value = 3.4028235e+38

    def _init_sens1_pres(self, param_json):
        self.data_type = ParamDataType.FLOAT; self.min_value = -3.4028235e+38; self.max_value = 3.4028235e+38

    def _init_sens2_pres(self, param_json):
        self.data_type = ParamDataType.FLOAT; self.min_value = -3.4028235e+38; self.max_value = 3.4028235e+38

    def _init_press_slope(self, param_json):
        self.data_type = ParamDataType.FLOAT; self.min_value = -3.4028235e+38; self.max_value = 3.4028235e+38

    def _init_errnum(self, param_json):
        self.data_type = ParamDataType.UINT32; self.min_value = 0; self.max_value = 0xFFFFFFFF
        component_enum_str = param_json.get("component_enum",None)
        component_enum_class = getattr(p_enum, component_enum_str, None)
        mode_enum_str = param_json.get("mode_enum",None)
        mode_enum_class = getattr(p_enum, mode_enum_str, None)
        type_enum_str = param_json.get("type_enum",None)
        type_enum_class = getattr(p_enum, type_enum_str, None)

        self.ref_list : List[Tuple[str, Type[p_enum.DescriptionEnum]]] = []
        self.ref_list.append(("Component", component_enum_class))
        self.ref_list.append(("Mode", mode_enum_class))
        self.ref_list.append(("Type", type_enum_class))

        if not self.description:
            items1 = [f"{item.value}: {item.description}" for item in component_enum_class]
            items2 = [f"{item.value}: {item.description}" for item in mode_enum_class]
            items3 = [f"{item.value}: {item.description}" for item in type_enum_class]
            self.description = "<br>".join(items1 + items2 + items3)

    def _init_nv1_group(self, param_json):
        self.nv1_read_req = param_json.get("rreq","-").strip()
        self.nv1_write_req = param_json.get("wreq","-").strip()
        self.nv1_read_res = param_json.get("rres","-").strip()
        self.nv1_write_res = param_json.get("wres","-").strip()

        self.sub_items = []
        sub_item_list = param_json.get("sub_items",[])
        for sub_item in sub_item_list:
            param_type_str = sub_item.get("type", "")
            offset = sub_item.get("offset", 0)
            length = sub_item.get("len", 0)
            display_type = PARAM_DISPLAY_TYPE_MAP.get(param_type_str)
            sub_param = Parameter(sub_item, display_type)
            self.sub_items.append((offset, length, sub_param))

    def _get_min_max_val(self, param_json):
        min_str = param_json.get("min", "0")
        max_str = param_json.get("max", "0x7FFFFFFF")

        if self.display_type == ParamDisplayType.HEX or self.display_type == ParamDisplayType.NUMBER:
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

        return min, max
    
    @property
    def value(self) -> Union[int, float, str, None]:
        return self._value

    @value.setter
    def value(self, new_val: Union[int, float, str, None]):
        if self._value != new_val:
            self._value = new_val
            # 값이 변경되면 시그널 발생
            self.sig_value_changed.emit()

    @property
    def is_not_support(self) -> bool:
        return self._is_not_support

    @is_not_support.setter
    def is_not_support(self, new_val: bool):
        if self._is_not_support != new_val:
            self._is_not_support = new_val
            self.sig_is_not_support_changed.emit()

    @property
    def is_err(self) -> bool:
        return self._is_err

    @is_err.setter
    def is_err(self, new_val: bool):
        if self._is_err != new_val:
            self._is_err = new_val
            self.sig_is_err_changed.emit()

    def set_enable_condition(self, condition: ParamCondition | None):
        self.enable_condition = condition

    def set_visible_condition(self, condition: ParamCondition | None):
        self.visible_condition = condition
        
    def set_force_value(self, new_val: str):
        try:
            if self.data_type in self.INT_TYPES:
                self.str_value = new_val
                self.value = int(new_val)
            elif self.data_type in self.FLOAT_TYPES:
                self.str_value = new_val
                self.value = float(new_val)
            elif self.data_type in self.STR_TYPES:
                self.str_value = new_val
                self.value = new_val
                
            self.is_err = False
        except ValueError:
            print(f"[Parameter]set_force_value() : 설정 값이 잘못 되었습니다. {self.path}, {self.name}, {new_val}")
            pass

    def set_read_response_packet(self, resp_msg: str) -> tuple[ParamParseErrType | None, bool]:        
        parse_err_type : ParamParseErrType = ParamParseErrType.NONE

        parse_err_type, need_retry = self.check_error(True, resp_msg)

        if parse_err_type != ParamParseErrType.NONE:
            return parse_err_type, need_retry

        if len(resp_msg) > 16:
            new_val = resp_msg[16:]
            try:
                if self.data_type in self.INT_TYPES:
                    self.str_value = new_val
                    self.value = int(new_val)
                elif self.data_type in self.FLOAT_TYPES:
                    self.str_value = new_val
                    self.value = float(new_val)
                elif self.data_type in self.STR_TYPES:
                    self.str_value = new_val
                    self.value = new_val
            except ValueError:
                return ParamParseErrType.DATA_TYPE_ERROR, True
        else:
            if self.data_type is ParamDataType.STR and len(resp_msg) == 16:
                self.str_value = ""
                self.value = ""
            else:
                return ParamParseErrType.WRONG_PARAM_LENGTH, True

        return parse_err_type, False

    def set_read_response_nv1_group_packet(self, resp_msg: str) -> tuple[ParamParseErrType | None, bool]:        
        parse_err_type : ParamParseErrType = ParamParseErrType.NONE

        parse_err_type, need_retry = self.nv1_protocol_check_error(True, self.nv1_read_res, resp_msg)

        if parse_err_type != ParamParseErrType.NONE:
            return parse_err_type, need_retry

        
        for offset, data_len, sub_param in self.sub_items:
            if len(resp_msg) >= (offset+data_len):
                new_val = resp_msg[offset:offset+data_len]
                sub_param.set_force_value(new_val)
            else:
                print("WRONG_PARAM_LENGTH")
                return ParamParseErrType.WRONG_PARAM_LENGTH, True

        return parse_err_type, False        

    def set_write_response_packet(self, resp_msg: str) -> tuple[ParamParseErrType | None, bool]:        
        return self.check_error(False, resp_msg)

    def check_error(self, is_read : bool, resp_msg: str) -> tuple[ParamParseErrType | None, bool]: 
        if not is_read and self.acc != ParamAccType.WO:
            return ParamParseErrType.NONE, False
        
        if not resp_msg:
            self.is_err = True
            return ParamParseErrType.COMMUNICATION_ERR, True

        if len(resp_msg) < 4:
            self.is_err = True
            return ParamParseErrType.WRONG_FORMAT, True

        prefix = resp_msg[0:2]
        if prefix != "p:":
            self.is_err = True
            return ParamParseErrType.WRONG_PREFIX, True

        err_code = resp_msg[2:4]

        if err_code == "00":
            if len(resp_msg) < 16:
                self.is_err = True
                return ParamParseErrType.WRONG_PARAM_LENGTH, True

            svc_code = resp_msg[4:6]
            if (svc_code != "01" and not is_read) or (svc_code != "0B" and is_read):
                self.is_err = True
                return ParamParseErrType.WRONG_SVC_CODE, True

            id_code = resp_msg[6:14]
            index = int(resp_msg[14:16], 16)
            
            if self.id == id_code and self.index == index:
                self.is_err = False
                self.is_not_support = False
                return ParamParseErrType.NONE, False
            else:
                self.is_err = True
                return ParamParseErrType.WRONG_ID_OR_INDEX, True

        not_support_codes = {"6E", "73", "7B", "7E", "89"} 

        if err_code in self.ERR_CODE_MAP:
            if err_code in not_support_codes:
                self.is_not_support = True
            else:
                self.is_err = True

            mapped_enum = self.ERR_CODE_MAP[err_code]

            return mapped_enum, False
        else:
            self.is_err = True # 알 수 없는 에러일 때
            return ParamParseErrType.UNKNOWN_ERROR_CODE, True

    def nv1_protocol_check_error(self, is_read : bool, check_res_msg: str, resp_msg: str) -> tuple[ParamParseErrType | None, bool]: 
        if not is_read and self.acc != ParamAccType.WO:
            return ParamParseErrType.NONE, False
        
        if not resp_msg:
            self.is_err = True
            return ParamParseErrType.COMMUNICATION_ERR, True

        if len(resp_msg) < len(check_res_msg):
            self.is_err = True
            return ParamParseErrType.WRONG_FORMAT, True

        if resp_msg.startswith(check_res_msg) == False and resp_msg.startswith("E:") == False:
            self.is_err = True
            return ParamParseErrType.WRONG_PREFIX, True

        if resp_msg.startswith("E:"):
            self.is_err = True # 알 수 없는 에러일 때
            self.is_not_support = True
            return ParamParseErrType.UNKNOWN_ERROR_CODE, False
        else:
            self.is_err = False 
            self.is_not_support = False 
            return ParamParseErrType.NONE, False
