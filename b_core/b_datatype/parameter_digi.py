
from typing import List, Dict, Union, Type
from PySide6.QtCore import QObject, Signal

from b_core.b_datatype.general_enum import ParamDisplayType, ParamDataType, ParamAccType
from b_core.b_datatype.param_enum import DescriptionEnum
from b_core.b_datatype.parameter import Parameter

class ParameterDigi(Parameter):
    def __init__(self, path: str, name: str, id: str, index: int, display_type: ParamDisplayType, data_type: ParamDataType, acc: ParamAccType, is_only_local_acc:bool, is_nor_backup: bool, is_fu_backup: bool, unit: str, min_value: Union[int, float, None], max_value: Union[int, float, None], description: str):
        super().__init__(path=path, name=name, id=id, index=index, display_type=display_type, data_type=data_type, acc=acc, is_only_local_acc=is_only_local_acc, is_nor_backup=is_nor_backup, is_fu_backup=is_fu_backup, unit=unit, min_value=min_value, max_value=max_value, ref_list=None, description=description)
        self.ref_list: List[Type[DescriptionEnum]] = []

    def add_ref_list(self, ref: Type[DescriptionEnum]):
        self.ref_list.append(ref)