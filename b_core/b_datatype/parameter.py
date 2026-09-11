from typing import Tuple
from typing import List, Dict, Union, Type
from PySide6.QtCore import QObject, Signal

from b_core.b_datatype.general_enum import ParamDisplayType, ParamDataType, ParamAccType, PARAM_DISPLAY_TYPE_MAP
from b_core.b_datatype import param_enum as p_enum
from b_core.c_manager.app_log_manager import AppLogManager

# Parameter 인스턴스가 수백 개라 인스턴스별 로거 대신 모듈 로거를 공유한다
_log = AppLogManager().get_logger("Parameter", is_global=True)

"""값(Parameter) 계층.

Parameter 는 값의 정의와 상태만 갖는다: 경로/이름, 표시 타입, 데이터 타입, 범위,
enum 참조, 현재 값, 오류 플래그, 변경 시그널. 전송 규약(요청 문자열, 응답 해석,
NV2 의 id/idx, NV1 의 자리/폭)은 b_core/g_protocol 의 PacketSpec 이 맡는다.
어떤 param 이 어떤 spec 을 쓰는지는 SpecRegistry(g_protocol/spec_registry) 가
path 기준으로 보유한다 — Parameter 는 spec 객체를 참조하지 않는다 (결정 A, 2026-09-11).

2026-09-11 (PacketSpec 도입 1단계) 에서 옮겨간 것:
- check_error / set_read_response_packet / set_write_response_packet / ERR_CODE_MAP
  -> g_protocol/nv2_spec.py (로직 동일)
- id / index 필드 -> nv2_spec.json + SpecRegistry.get_nv2_key() (백업 파일/Compound
  프로토콜이 NV2 식별자를 쓰므로 역조회만 남긴다)
- 미사용 필드 len / rreq / rres / wreq / wres / proto_type 제거
- enable / visible 조건의 참조가 NV2 id 에서 전체 경로(ref_path)로 바뀌었다
값 형 변환은 set_text_value() 하나로 모았다 (spec 과 set_force_value 가 공유).
"""


class ParamCondition(QObject):
    def __init__(self, parent: QObject):
        super().__init__(parent)

        self.ref_path = None  # 참조 param 의 전체 경로 ("path.name")
        self.values: List[Union[int, float, str, None]] = []


class Parameter(QObject):
    # 값이 변경되었을 때 발생하는 시그널 (새로운 값을 문자열로 전달)
    sig_value_changed = Signal()
    sig_is_not_support_changed = Signal()
    sig_is_err_changed = Signal()
    # 장비 값으로 동기화가 확정되었을 때 발생하는 시그널.
    # sig_value_changed 와 달리 값이 변하지 않아도 발생한다 — refresh 시퀀스에서
    # UI 측 dirty 상태를 클리어하기 위한 용도. (write 후 read-back 이나 모니터링에서는
    # 발생시키지 않는다 — 쓰기 미반영/사용자 편집 중 dirty 는 유지되어야 하므로)
    sig_synced = Signal()

    INT_TYPES = (ParamDataType.INT8, ParamDataType.INT16, ParamDataType.INT32, ParamDataType.UINT8, ParamDataType.UINT16, ParamDataType.UINT32)
    FLOAT_TYPES = (ParamDataType.FLOAT, ParamDataType.DOUBLE)
    STR_TYPES = (ParamDataType.STR,)
    BASE36_TYPES = (ParamDataType.BASE_36,)

    def __init__(self, param_json, param_display_type: ParamDisplayType):
        super().__init__()

        full_path         = param_json.get("path", "")
        path, name        = full_path.rsplit(".", 1)
        acc_str           = param_json.get("acc", "RO")
        acc               = getattr(ParamAccType, acc_str, ParamAccType.RO)
        local_acc         = param_json.get("local_acc", False)
        nor_backup        = param_json.get("nor_backup", False)
        fu_backup         = param_json.get("fu_backup", False)
        desc              = param_json.get("desc", None)
        enable_condition  = param_json.get("enable", None)
        visible_condition = param_json.get("visible", None)
        reconnect         = param_json.get("reconnect", False)

        self.display_type      = param_display_type
        self.path              = path
        self.name              = name
        self.acc               = acc
        self.is_only_local_acc = local_acc
        self.is_nor_backup     = nor_backup
        self.is_fu_backup      = fu_backup
        self.description       = desc
        self.is_need_reconnect = reconnect

        self.enable_conditions = self._build_conditions(enable_condition)
        self.visible_conditions = self._build_conditions(visible_condition)

        self.data_type = ParamDataType.FLOAT
        self.min_value : Union[int, float, None] = None
        self.max_value : Union[int, float, None] = None
        self.ref_list  = None # Type[p_enum.DescriptionEnum] or List[Tuple[str, Type[DescriptionEnum]]]
        self._value : Union[int, float, str, None] = None
        self.str_value : str = ""
        self._is_not_support : bool = False
        self._is_err : bool = False
        self.write_str_value : str | None = None

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
        elif self.display_type == ParamDisplayType.ENUM_36:
            self._init_enum(param_json)
            self.display_type = ParamDisplayType.ENUM
            self.data_type = ParamDataType.BASE_36

    def _build_conditions(self, condition_json):
        """enable / visible 조건 목록 -> ParamCondition 목록 (없으면 None)."""
        if condition_json is None:
            return None
        conditions = []
        for cond in condition_json:
            param_cond = ParamCondition(self)
            param_cond.ref_path = cond.get("path")
            param_cond.values = cond.get("conditions", [])
            conditions.append(param_cond)
        return conditions

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
    def full_path(self) -> str:
        return f"{self.path}.{self.name}"

    @property
    def value(self) -> Union[int, float, str, None]:
        return self._value

    @value.setter
    def value(self, new_val: Union[int, float, str, None]):
        if self._value != new_val:
            self._value = new_val
            # 값이 변경되면 시그널 발생
            self.sig_value_changed.emit()

    def notify_synced(self):
        # 호출 주체는 워커 — refresh 시퀀스의 읽기 성공 시점에만 호출한다
        self.sig_synced.emit()

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

    def set_text_value(self, text: str) -> bool:
        """전송 문자열을 data_type 규칙으로 변환해 값으로 확정한다. 변환 실패면 False.
        spec 의 응답 반영과 set_force_value 가 공유한다.

        [기존 동작 유지] str_value 는 변환 전에 대입되므로 실패해도 그 문자열이 남는다
        (구 set_read_response_packet / set_force_value 와 동일). 실패 시 되돌리는 쪽이
        맞아 보이지만 1단계는 동작 변화 없음이 원칙이라 그대로 둔다 — 정리 후보."""
        self.str_value = text
        try:
            if self.data_type in self.INT_TYPES:
                self.value = int(text)
            elif self.data_type in self.FLOAT_TYPES:
                self.value = float(text)
            elif self.data_type in self.STR_TYPES:
                self.value = text
            elif self.data_type in self.BASE36_TYPES:
                self.value = int(text, 36)
            else:
                return False
        except ValueError:
            return False
        return True

    def set_force_value(self, new_val: str):
        if self.set_text_value(new_val):
            self.is_err = False
        else:
            _log.error(f"set_force_value() 설정 값이 잘못 되었습니다: {self.path}, {self.name}, {new_val}")
