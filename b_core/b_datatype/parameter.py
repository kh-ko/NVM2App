from typing import List, Dict, Union, Type, Optional
from PySide6.QtCore import QObject, Signal

from b_core.b_datatype.general_enum import ParamDisplayType, ParamDataType, ParamAccType, ParamParseErrType
from b_core.b_datatype.param_enum import DescriptionEnum

from b_core.c_manager.log_manager import LogManager

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

    def __init__(self, path: str, name: str, id: str, index: int, display_type: ParamDisplayType, data_type: ParamDataType, acc: ParamAccType, is_only_local_acc:bool,is_nor_backup: bool, is_fu_backup: bool, unit: str, min_value: Union[int, float, None], max_value: Union[int, float, None], ref_list: Optional[Type[DescriptionEnum]], description: str):
        super().__init__()
        self.path : str = path
        self.name : str = name
        self.id : str = id
        self.index : int = index
        self.display_type : ParamDisplayType = display_type
        self.data_type : ParamDataType = data_type
        self.acc : ParamAccType = acc
        self.is_only_local_acc : bool = is_only_local_acc
        self.is_nor_backup : bool = is_nor_backup
        self.is_fu_backup : bool = is_fu_backup
        self.unit : str = unit
        self.min_value : Union[int, float, None] = min_value
        self.max_value : Union[int, float, None] = max_value
        self.ref_list : Optional[Type[DescriptionEnum]] = ref_list
        self.description : str = description
        
        self._value : Union[int, float, str, None] = None
        self.str_value : str = ""
        self._is_not_support : bool = False
        self._is_err : bool = False
        self.write_str_value : str | None = None

        if self.display_type == ParamDisplayType.ENUM and self.ref_list is not None:
            enum_values = [item.value for item in self.ref_list]
            if enum_values:
                self.min_value = min(enum_values)
                self.max_value = max(enum_values)

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