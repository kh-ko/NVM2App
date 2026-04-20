
from typing import List, Dict, Union, Type, Optional
from PySide6.QtCore import QObject, Signal

from b_core.b_datatype.general_enum import ParamDisplayType, ParamDataType, ParamAccType
from b_core.b_datatype.param_enum import DescriptionEnum

class Parameter(QObject):
    # 값이 변경되었을 때 발생하는 시그널 (새로운 값을 문자열로 전달)
    sig_value_changed = Signal(str)
    sig_not_support_changed = Signal(bool)
    sig_edited_changed = Signal(bool)
    sig_syncing_changed = Signal(bool)
    sig_err_changed = Signal(bool)

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
        self._is_edited : bool = False
        self._is_syncing : bool = False
        self._err :  bool = False

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
            self.sig_not_support_changed.emit(self._is_not_support)

    @property
    def is_edited(self) -> bool:
        return self._is_edited

    @is_edited.setter
    def is_edited(self, new_val: bool):
        if self._is_edited != new_val:
            self._is_edited = new_val
            self.sig_edited_changed.emit(self._is_edited)

    @property
    def is_syncing(self) -> bool:
        return self._is_syncing

    @is_syncing.setter
    def is_syncing(self, new_val: bool):
        if self._is_syncing != new_val:
            self._is_syncing = new_val
            self.sig_syncing_changed.emit(self._is_syncing)

    @property
    def err(self) -> bool:
        return self._err

    @err.setter
    def err(self, new_val: bool):
        if self._err != new_val:
            self._err = new_val
            self.sig_err_changed.emit(self._err)

    def edit_value(self, new_val: str):
        self.value = new_val
        self.is_edited = True

    def set_read_response_packet(self, resp_msg: str) -> str | None:
        self.is_syncing = False
        self.is_edited = False
        
        if resp_msg and len(resp_msg) >= 4:
            prefix     = resp_msg[0:2]   # 인덱스 0~1 (2자리) -> "p:"
            err_code   = resp_msg[2:4]   # 인덱스 2~3 (2자리) -> "00"

            if prefix != "p:":
                self.err = True
                return f"{self.path}.{self.name} : wrong prefix"

            if err_code == "00" and len(resp_msg) >= 16:
                svc_code   = resp_msg[4:6]   # 인덱스 4~5 (2자리) -> "0B"

                if svc_code != "0B":
                    self.err = True
                    return f"{self.path}.{self.name} : wrong service code"

                id_code    = resp_msg[6:14]  # 인덱스 6~13 (8자리) -> "12345678"
                index      = int(resp_msg[14:16], 16) # 인덱스 14~15 (2자리) -> "ab"
                if self.id == id_code and self.index == index:
                    self.is_not_support = False
                    self.value = resp_msg[16:]   # 인덱스 16부터 끝까지 -> "xxx..." (나머지 모두)
                    self.err = False
                    return None
                else:
                    self.err = True
                    return f"{self.path}.{self.name} : wrong parameter ID or index"
            elif err_code == "00" and len(resp_msg) < 16:
                self.err = True
                return f"{self.path}.{self.name} : wrong parameter length"
            else:
                if   err_code == "0C": self.err = True;            return f"{self.path}.{self.name} : wrong command length"
                elif err_code == "1C": self.err = True;            return f"{self.path}.{self.name} : value too low"
                elif err_code == "1D": self.err = True;            return f"{self.path}.{self.name} : value too high"
                elif err_code == "20": self.err = True;            return f"{self.path}.{self.name} : resulting zero adjust offset value out of range"
                elif err_code == "21": self.err = True;            return f"{self.path}.{self.name} : not valid because no sensor enabled"
                elif err_code == "50": self.err = True;            return f"{self.path}.{self.name} : wrong access mode"
                elif err_code == "51": self.err = True;            return f"{self.path}.{self.name} : timeout"
                elif err_code == "6D": self.err = True;            return f"{self.path}.{self.name} : EEProm not ready"
                elif err_code == "6E": self.is_not_support = True; return f"{self.path}.{self.name} : wrong parameter ID"
                elif err_code == "6F": self.err = True;            return f"{self.path}.{self.name} : set to default value not allowed"
                elif err_code == "70": self.err = True;            return f"{self.path}.{self.name} : parameter not settable"
                elif err_code == "71": self.err = True;            return f"{self.path}.{self.name} : parameter not readable"
                elif err_code == "72": self.err = True;            return f"{self.path}.{self.name} : set to initial value not allowed"
                elif err_code == "73": self.is_not_support = True; return f"{self.path}.{self.name} : wrong parameter index"
                elif err_code == "74": self.err = True;            return f"{self.path}.{self.name} : initial value out of range"
                elif err_code == "76": self.err = True;            return f"{self.path}.{self.name} : wrong value"
                elif err_code == "77": self.err = True;            return f"{self.path}.{self.name} : wrong value, only reset possible"
                elif err_code == "78": self.err = True;            return f"{self.path}.{self.name} : not allowed in this state"
                elif err_code == "7A": self.err = True;            return f"{self.path}.{self.name} : wrong service"
                elif err_code == "7B": self.is_not_support = True; return f"{self.path}.{self.name} : parameter not active"
                elif err_code == "7C": self.err = True;            return f"{self.path}.{self.name} : parameter system error"
                elif err_code == "7D": self.err = True;            return f"{self.path}.{self.name} : communication error"
                elif err_code == "7E": self.is_not_support = True; return f"{self.path}.{self.name} : unknown service"
                elif err_code == "7F": self.err = True;            return f"{self.path}.{self.name} : unexpected character"
                elif err_code == "80": self.err = True;            return f"{self.path}.{self.name} : no access rights"
                elif err_code == "81": self.err = True;            return f"{self.path}.{self.name} : no adequately hardware"
                elif err_code == "82": self.err = True;            return f"{self.path}.{self.name} : wrong object state"
                elif err_code == "84": self.err = True;            return f"{self.path}.{self.name} : no slave command"
                elif err_code == "85": self.err = True;            return f"{self.path}.{self.name} : command to unknown slave"
                elif err_code == "87": self.err = True;            return f"{self.path}.{self.name} : command to master only"
                elif err_code == "88": self.err = True;            return f"{self.path}.{self.name} : only G command allowed"
                elif err_code == "89": self.is_not_support = True; return f"{self.path}.{self.name} : not supported"
                elif err_code == "A0": self.err = True;            return f"{self.path}.{self.name} : function is disabled"
                elif err_code == "A1": self.err = True;            return f"{self.path}.{self.name} : already done"   
                else:                                              return f"{self.path}.{self.name} : unknown error"
        elif resp_msg is None:
            self.err = True
            return f"{self.path}.{self.name} : communication error"
        else:
            self.err = True
            return f"{self.path}.{self.name} : wrong response message format"

    def set_write_response_packet(self, resp_msg: str) -> str | None:        
        if resp_msg and len(resp_msg) >= 4:
            prefix     = resp_msg[0:2]   # 인덱스 0~1 (2자리) -> "p:"
            err_code   = resp_msg[2:4]   # 인덱스 2~3 (2자리) -> "00"

            if prefix != "p:":
                self.err = True
                return f"{self.path}.{self.name} : wrong prefix"

            if err_code == "00" and len(resp_msg) >= 16:
                svc_code   = resp_msg[4:6]   # 인덱스 4~5 (2자리) -> "01"

                if svc_code != "01":
                    self.err = True
                    return f"{self.path}.{self.name} : wrong service code"

                id_code    = resp_msg[6:14]  # 인덱스 6~13 (8자리) -> "12345678"
                index      = int(resp_msg[14:16], 16) # 인덱스 14~15 (2자리) -> "ab"
                if self.id == id_code and self.index == index and self.acc == ParamAccType.WO:
                    self.is_not_support = False
                    self.err = False
                    return None
                else:
                    self.err = True
                    return f"{self.path}.{self.name} : wrong parameter ID or index"
            elif err_code == "00" and len(resp_msg) < 16:
                self.err = True
                return f"{self.path}.{self.name} : wrong parameter length"
            else:
                if   err_code == "0C": self.err = True;            return f"{self.path}.{self.name} : wrong command length"
                elif err_code == "1C": self.err = True;            return f"{self.path}.{self.name} : value too low"
                elif err_code == "1D": self.err = True;            return f"{self.path}.{self.name} : value too high"
                elif err_code == "20": self.err = True;            return f"{self.path}.{self.name} : resulting zero adjust offset value out of range"
                elif err_code == "21": self.err = True;            return f"{self.path}.{self.name} : not valid because no sensor enabled"
                elif err_code == "50": self.err = True;            return f"{self.path}.{self.name} : wrong access mode"
                elif err_code == "51": self.err = True;            return f"{self.path}.{self.name} : timeout"
                elif err_code == "6D": self.err = True;            return f"{self.path}.{self.name} : EEProm not ready"
                elif err_code == "6E": self.is_not_support = True; return f"{self.path}.{self.name} : wrong parameter ID"
                elif err_code == "6F": self.err = True;            return f"{self.path}.{self.name} : set to default value not allowed"
                elif err_code == "70": self.err = True;            return f"{self.path}.{self.name} : parameter not settable"
                elif err_code == "71": self.err = True;            return f"{self.path}.{self.name} : parameter not readable"
                elif err_code == "72": self.err = True;            return f"{self.path}.{self.name} : set to initial value not allowed"
                elif err_code == "73": self.is_not_support = True; return f"{self.path}.{self.name} : wrong parameter index"
                elif err_code == "74": self.err = True;            return f"{self.path}.{self.name} : initial value out of range"
                elif err_code == "76": self.err = True;            return f"{self.path}.{self.name} : wrong value"
                elif err_code == "77": self.err = True;            return f"{self.path}.{self.name} : wrong value, only reset possible"
                elif err_code == "78": self.err = True;            return f"{self.path}.{self.name} : not allowed in this state"
                elif err_code == "7A": self.err = True;            return f"{self.path}.{self.name} : wrong service"
                elif err_code == "7B": self.is_not_support = True; return f"{self.path}.{self.name} : parameter not active"
                elif err_code == "7C": self.err = True;            return f"{self.path}.{self.name} : parameter system error"
                elif err_code == "7D": self.err = True;            return f"{self.path}.{self.name} : communication error"
                elif err_code == "7E": self.is_not_support = True; return f"{self.path}.{self.name} : unknown service"
                elif err_code == "7F": self.err = True;            return f"{self.path}.{self.name} : unexpected character"
                elif err_code == "80": self.err = True;            return f"{self.path}.{self.name} : no access rights"
                elif err_code == "81": self.err = True;            return f"{self.path}.{self.name} : no adequately hardware"
                elif err_code == "82": self.err = True;            return f"{self.path}.{self.name} : wrong object state"
                elif err_code == "84": self.err = True;            return f"{self.path}.{self.name} : no slave command"
                elif err_code == "85": self.err = True;            return f"{self.path}.{self.name} : command to unknown slave"
                elif err_code == "87": self.err = True;            return f"{self.path}.{self.name} : command to master only"
                elif err_code == "88": self.err = True;            return f"{self.path}.{self.name} : only G command allowed"
                elif err_code == "89": self.is_not_support = True; return f"{self.path}.{self.name} : not supported"
                elif err_code == "A0": self.err = True;            return f"{self.path}.{self.name} : function is disabled"
                elif err_code == "A1": self.err = True;            return f"{self.path}.{self.name} : already done"   
                else:                                              return f"{self.path}.{self.name} : unknown error"
        elif resp_msg is None:
            self.err = True
            return f"{self.path}.{self.name} : communication error"
        else:
            self.err = True
            return f"{self.path}.{self.name} : wrong response message format"