
from typing import List, Dict, Union, Type, Optional
from PySide6.QtCore import QObject, Signal

from b_core.b_datatype.general_enum import ParamDisplayType, ParamDataType, ParamAccType
from b_core.b_datatype.param_enum import DescriptionEnum

class Parameter(QObject):
    # 값이 변경되었을 때 발생하는 시그널 (새로운 값을 문자열로 전달)
    valueChanged = Signal(str)
    notSupportChanged = Signal(bool)
    editedChanged = Signal(bool)
    syncingChanged = Signal(bool)

    def __init__(self, path: str, name: str, id: str, index: int, display_type: ParamDisplayType, data_type: ParamDataType, acc: ParamAccType, is_nor_backup: bool, is_fu_backup: bool, unit: str, min: Union[int, float, None], max: Union[int, float, None], ref_list: Optional[Type[DescriptionEnum]], description: str):
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
        self.min : Union[int, float, None] = min
        self.max : Union[int, float, None] = max
        self.ref_list : Optional[Type[DescriptionEnum]] = ref_list
        self.description : str = description
        
        self._value : str = ""
        self._is_not_support : bool = False
        self._is_edited : bool = False
        self._is_syncing : bool = False

        if self.display_type == ParamDisplayType.ENUM and self.ref_list is not None:
            enum_values = [item.value for item in self.ref_list]
            if enum_values:
                self.min = min(enum_values)
                self.max = max(enum_values)

    @property
    def value(self) -> str:
        return self._value

    @value.setter
    def value(self, new_val: str):
        if self._value != new_val:
            self._value = new_val
            # 값이 변경되면 시그널 발생
            self.valueChanged.emit(self._value)

    @property
    def is_not_support(self) -> bool:
        return self._is_not_support

    @is_not_support.setter
    def is_not_support(self, new_val: bool):
        if self._is_not_support != new_val:
            self._is_not_support = new_val
            self.notSupportChanged.emit(self._is_not_support)

    @property
    def is_edited(self) -> bool:
        return self._is_edited

    @is_edited.setter
    def is_edited(self, new_val: bool):
        if self._is_edited != new_val:
            self._is_edited = new_val
            self.editedChanged.emit(self._is_edited)

    @property
    def is_syncing(self) -> bool:
        return self._is_syncing

    @is_syncing.setter
    def is_syncing(self, new_val: bool):
        if self._is_syncing != new_val:
            self._is_syncing = new_val
            self.syncingChanged.emit(self._is_syncing)

    def edit_value(self, new_val: str):
        self.value = new_val
        self.is_edited = True