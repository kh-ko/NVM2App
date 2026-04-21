from typing import List, Dict, Union, Type, Optional
from PySide6.QtCore import QObject, Signal

from b_core.b_datatype.general_enum import ParamDisplayType, ParamDataType, ParamAccType
from b_core.b_datatype.param_enum import DescriptionEnum

class Parameter(QObject):
    # 값이 변경되었을 때 발생하는 시그널 (새로운 값을 문자열로 전달)
    sig_value_changed = Signal(str)
    sig_is_not_support_changed = Signal(bool)
    sig_is_err_changed = Signal(bool)

    def __init__(self, path: str, name: str, id: str, index: int, display_type: ParamDisplayType, data_type: ParamDataType, acc: ParamAccType, is_nor_backup: bool, is_fu_backup: bool, unit: str, min_value: Union[int, float, None], max_value: Union[int, float, None], ref_list: Optional[Type[DescriptionEnum]], description: str):
        super().__init__()
        self.path : str = path
        self.name : str = name
        self.id : str = id
        self.index : int = index
        self.display_type : ParamDisplayType = display_type
        self.data_type : ParamDataType = data_type
        self.acc : ParamAccType = acc
        self.is_nor_backup : bool = is_nor_backup
        self.is_fu_backup : bool = is_fu_backup
        self.unit : str = unit
        self.min_value : Union[int, float, None] = min_value
        self.max_value : Union[int, float, None] = max_value
        self.ref_list : Optional[Type[DescriptionEnum]] = ref_list
        self.description : str = description
        
        self._value : str = ""
        self._is_not_support : bool = False
        self._is_err : bool = False

        if self.display_type == ParamDisplayType.ENUM and self.ref_list is not None:
            enum_values = [item.value for item in self.ref_list]
            if enum_values:
                self.min_value = min(enum_values)
                self.max_value = max(enum_values)

    @property
    def value(self) -> str:
        return self._value

    @value.setter
    def value(self, new_val: str):
        if self._value != new_val:
            self._value = new_val
            # 값이 변경되면 시그널 발생
            self.sig_value_changed.emit(self._value)

    @property
    def is_not_support(self) -> bool:
        return self._is_not_support

    @is_not_support.setter
    def is_not_support(self, new_val: bool):
        if self._is_not_support != new_val:
            self._is_not_support = new_val
            self.sig_is_not_support_changed.emit(self._is_not_support)

    @property
    def is_err(self) -> bool:
        return self._is_err

    @is_err.setter
    def is_err(self, new_val: bool):
        if self._is_err != new_val:
            self._is_err = new_val
            self.sig_is_err_changed.emit(self._is_err)

    def set_force_value(self, new_val: str):
        self._value = new_val

    def set_read_response_packet(self, resp_msg: str) -> str | None:        
        err_msg = self.check_error(False, resp_msg)

        if err_msg is not None:
            return err_msg

        if len(resp_msg) > 16:
            self.value = resp_msg[16:]

    def set_write_response_packet(self, resp_msg: str) -> str | None:        
        return self.check_error(False, resp_msg)

    def check_error(self, is_read : bool, resp_msg: str) -> str | None: 
        if not is_read and self.acc != ParamAccType.WO:
            return None
        
        if not resp_msg:
            self.is_err = True
            return f"{self.path}.{self.name} : communication error"

        if len(resp_msg) < 4:
            self.is_err = True
            return f"{self.path}.{self.name} : wrong response message format"

        prefix = resp_msg[0:2]
        if prefix != "p:":
            self.is_err = True
            return f"{self.path}.{self.name} : wrong prefix"

        err_code = resp_msg[2:4]

        if err_code == "00":
            if len(resp_msg) < 16:
                self.is_err = True
                return f"{self.path}.{self.name} : wrong parameter length"

            svc_code = resp_msg[4:6]
            if (svc_code != "01" and not is_read) or (svc_code != "0B" and is_read):
                self.is_err = True
                return f"{self.path}.{self.name} : wrong service code"

            id_code = resp_msg[6:14]
            index = int(resp_msg[14:16], 16)
            
            if self.id == id_code and self.index == index:
                self.is_err = False
                self.is_not_support = False
                return None
            else:
                self.is_err = True
                return f"{self.path}.{self.name} : wrong parameter ID or index"

        error_map = {
            "0C": "wrong command length", "1C": "value too low", "1D": "value too high",
            "20": "resulting zero adjust offset value out of range", "21": "not valid because no sensor enabled",
            "50": "wrong access mode", "51": "timeout", "6D": "EEProm not ready",
            "6E": "wrong parameter ID", "6F": "set to default value not allowed",
            "70": "parameter not settable", "71": "parameter not readable", "72": "set to initial value not allowed",
            "73": "wrong parameter index", "74": "initial value out of range", "76": "wrong value",
            "77": "wrong value, only reset possible", "78": "not allowed in this state", "7A": "wrong service",
            "7B": "parameter not active", "7C": "parameter system error", "7D": "communication error",
            "7E": "unknown service", "7F": "unexpected character", "80": "no access rights",
            "81": "no adequately hardware", "82": "wrong object state", "84": "no slave command",
            "85": "command to unknown slave", "87": "command to master only", "88": "only G command allowed",
            "89": "not supported", "A0": "function is disabled", "A1": "already done"
        }

        not_support_codes = {"6E", "73", "7B", "7E", "89"}

        if err_code in error_map:
            if err_code in not_support_codes:
                self.is_not_support = True
            else:
                self.is_err = True
            return f"{self.path}.{self.name} : {error_map[err_code]}"
        else:
            self.is_err = True # 알 수 없는 에러일 때
            return f"{self.path}.{self.name} : unknown error"
