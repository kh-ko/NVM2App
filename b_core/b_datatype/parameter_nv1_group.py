
from typing import List, Dict, Union, Type
from PySide6.QtCore import QObject, Signal

from b_core.b_datatype.general_enum import ParamDisplayType, ParamDataType, ParamAccType
from b_core.b_datatype.param_enum import DescriptionEnum
from b_core.b_datatype.parameter import Parameter

class ParameterNv1Group(QObject):
    sig_value_changed = Signal()
    sig_is_not_support_changed = Signal()
    sig_is_err_changed = Signal()

    def __init__(self, group):
        super().__init__()
        self.path : str = group.path
        self.name : str = group.name
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
        self.btn_str_value : str = btn_str_value
        self.is_need_reconnect : bool = is_need_reconnect

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
        self.sub_items = []
