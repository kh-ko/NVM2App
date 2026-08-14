from b_core.b_datatype import param_enum as p_enum
from b_core.c_manager.local_setting_manager import LocalSettingManager
from b_core.c_manager.parameter_manager import ParamManager
from b_core.f_helper.float_util import to_sig_str
from c_ui.a_converter.pressure_converter_manager import PresConverterManager
from c_ui.a_converter.position_converter_manager import PosiConverterManager
from c_ui.b_control_ver2.a_theme.tokens  import tokens
from c_ui.b_control_ver2.c_values.write_only_values import (WriteOnlyButtonValueWidget, WriteOnlyEnumValueWidget)
from c_ui.b_control_ver2.c_values.read_only_values import (ReadOnlyBitmapValueWidget, ReadOnlyEnumValueWidget, ReadOnlyFloatValueWidget,
                                                           ReadOnlyIntValueWidget, ReadOnlyMultipleEnumValueWidget,
                                                           ReadOnlyScaleValueWidget, ReadOnlyTextValueWidget)
from c_ui.b_control_ver2.c_values.read_write_values import (ReadWriteBitmapValueWidget, ReadWriteEnumValueWidget, ReadWriteFloatValueSpinBoxWidget,
                                                            ReadWriteFloatValueWidget, ReadWriteHexValueWidget, ReadWriteIntValueWidget,
                                                            ReadWriteScaleValueWidget)

class ParamWidget:
    """param 바인딩 공통 동작 믹스인 — c_value 위젯과 다중상속으로 사용한다.

    사용 규칙 (서브클래스 __init__ 에서):
        1. label_text = self._resolve_param(param_full_path, force_label_text)
        2. super().__init__(...)   # 각자 베이스 위젯 인자 매핑 (enum_class 등)
        3. self._bind_param()      # 시그널 연결 + 초기 상태 동기화
    """

    def _resolve_param(self, param_full_path: str, force_label_text: str = None) -> str:
        self.param = ParamManager().get_by_full_path(param_full_path)
        if self.param is None:
            # ParamManager 가 오류 로그를 남긴 뒤 None 을 주므로, 여기서 명확히 실패시킨다
            raise ValueError(f"param not found: {param_full_path}")

        return force_label_text if force_label_text else self.param.name

    def _bind_param(self):
        self.param.sig_value_changed.connect(self.handle_param_value_changed)
        # refresh 동기화 확정 통지 — 값이 안 변해도 set_value+commit 으로 dirty 를 클리어한다
        self.param.sig_synced.connect(self.handle_param_value_changed)
        self.param.sig_is_err_changed.connect(self.handle_param_is_err_changed)
        self.param.sig_is_not_support_changed.connect(self.handle_param_is_not_support_changed)
        self.handle_param_value_changed()
        self.handle_param_is_err_changed()
        self.handle_param_is_not_support_changed()

    def handle_param_value_changed(self):
        # 값 반영 후 commit 으로 dirty 기준(ori_value)까지 갱신한다
        self.set_value(self.param.value)
        self.commit()

        # set_value 가 setEnabled(True) 로 복구하므로, enable 조건이 걸린
        # 위젯은 값 갱신 후 조건을 다시 평가한다 (조건 없는 위젯은 건드리지
        # 않는다 — RO 위젯의 '값 없음 = 비활성' 표시를 되살리지 않기 위함)
        if self._enable_conditions:
            self.on_enable_condition_changed()

    def handle_param_is_err_changed(self):
        if self.lbl_label is None:  # 라벨 없는 구성(label_text="")에서는 표시할 곳이 없다
            return

        if self.param.is_err:
            self.lbl_label.set_colors(text=tokens().danger)
        else:
            self.lbl_label.set_colors(text=tokens().text)

    def handle_param_is_not_support_changed(self):
        self.set_not_support(self.param.is_not_support)

    def import_backup_value(self, value, unit=None):
        # unit: 저장 당시 값의 단위 표식 — 단위 개념이 있는 위젯(pres)만 사용하고
        # 나머지는 무시한다 (None = 단위 정보 없음, 현재 표시 단위로 간주)
        self.set_value(value)

    def export_backup_value(self):
        return self.get_value()

    def export_backup_unit(self):
        # 저장 값에 함께 기록할 단위 표식. 단위 개념이 없는 위젯은 None —
        # 파일에 unit 필드가 생략된다 (ver1 파일 스키마와 호환)
        return None

class ParamWriteOnlyButtonValueWidget(ParamWidget,WriteOnlyButtonValueWidget):
    def __init__(self, param_full_path : str, force_label_text:str=None, label_width : int = 150, is_vertical_mode = False, parent = None):
        label_text = self._resolve_param(param_full_path, force_label_text)
        super().__init__(label_text=label_text, label_width=label_width, is_vertical_mode=is_vertical_mode, parent=parent)
        self._bind_param()

class ParamReadOnlyTextValueWidget(ParamWidget,ReadOnlyTextValueWidget):
    def __init__(self, param_full_path : str, force_label_text:str=None, label_width : int = 150, is_vertical_mode = False, parent = None):
        label_text = self._resolve_param(param_full_path, force_label_text)
        super().__init__(label_text=label_text, label_width=label_width, is_vertical_mode=is_vertical_mode, parent=parent)
        self._bind_param()

class ParamReadOnlyEnumValueWidget(ParamWidget,ReadOnlyEnumValueWidget):
    def __init__(self, param_full_path : str, force_label_text:str=None, label_width : int = 150, is_vertical_mode = False, parent = None):
        label_text = self._resolve_param(param_full_path, force_label_text)
        super().__init__(enum_class=self.param.ref_list, label_text=label_text, label_width=label_width, is_vertical_mode=is_vertical_mode, parent=parent)
        self._bind_param()

class ParamReadWriteEnumValueWidget(ParamWidget, ReadWriteEnumValueWidget):
    def __init__(self, param_full_path : str, force_label_text:str=None, label_width : int = 150, is_vertical_mode = False, parent = None):
        label_text = self._resolve_param(param_full_path, force_label_text)
        super().__init__(enum_class=self.param.ref_list, label_text=label_text, label_width=label_width, is_vertical_mode=is_vertical_mode, parent=parent)
        self._bind_param()

class ParamWriteOnlyEnumValueWidget(ParamWidget, WriteOnlyEnumValueWidget):
    def __init__(self, param_full_path : str, force_label_text:str=None, label_width : int = 150, is_vertical_mode = False, parent = None):
        label_text = self._resolve_param(param_full_path, force_label_text)
        super().__init__(enum_class=self.param.ref_list, label_text=label_text, label_width=label_width, is_vertical_mode=is_vertical_mode, parent=parent)
        self._bind_param()

class ParamReadOnlyBitmapValueWidget(ParamWidget, ReadOnlyBitmapValueWidget):
    def __init__(self, param_full_path : str, force_label_text:str=None, label_width : int = 150, is_vertical_mode = False, parent = None):
        label_text = self._resolve_param(param_full_path, force_label_text)
        super().__init__(enum_class=self.param.ref_list, label_text=label_text, label_width=label_width, is_vertical_mode=is_vertical_mode, parent=parent)
        self._bind_param()

class ParamReadWriteBitmapValueWidget(ParamWidget, ReadWriteBitmapValueWidget):
    def __init__(self, param_full_path : str, force_label_text:str=None, label_width : int = 150, is_vertical_mode = False, parent = None):
        label_text = self._resolve_param(param_full_path, force_label_text)
        super().__init__(enum_class=self.param.ref_list, label_text=label_text, label_width=label_width, is_vertical_mode=is_vertical_mode, parent=parent)
        self._bind_param()

class ParamReadOnlyMultipleEnumValueWidget(ParamWidget, ReadOnlyMultipleEnumValueWidget):
    def __init__(self, param_full_path : str, force_label_text:str=None, label_width : int = 150, is_vertical_mode = False, parent = None):
        label_text = self._resolve_param(param_full_path, force_label_text)
        # ERR_NUM param 의 ref_list 는 [(이름, DescriptionEnum), ...] — enum_items 와 동일 형태
        super().__init__(enum_items=self.param.ref_list, label_text=label_text, label_width=label_width, is_vertical_mode=is_vertical_mode, parent=parent)
        self._bind_param()

class ParamReadOnlyHexValueWidget(ParamWidget, ReadOnlyTextValueWidget):
    def __init__(self, param_full_path : str, force_label_text:str=None, label_width : int = 150, is_vertical_mode = False, parent = None):
        label_text = self._resolve_param(param_full_path, force_label_text)
        super().__init__(label_text=label_text, label_width=label_width, is_vertical_mode=is_vertical_mode, parent=parent)
        self._bind_param() 

    def set_value(self, value):
        hex_str = None

        if value is not None:
            try:
                hex_str = f"0x{value:X}"
            except Exception:
                pass

        super().set_value(hex_str)

    def get_value(self):
        int_value = None
        hex_str = super().get_value()

        if hex_str is not None:
            try:
                int_value = int(hex_str, 16)
            except Exception:
                pass

        return int_value

class ParamReadWriteHexValueWidget(ParamWidget, ReadWriteHexValueWidget):
    def __init__(self, param_full_path : str, force_label_text:str=None, label_width : int = 150, is_vertical_mode = False, parent = None):
        label_text = self._resolve_param(param_full_path, force_label_text)
        super().__init__(label_text=label_text, label_width=label_width, is_vertical_mode=is_vertical_mode, parent=parent)

        # HEX param 은 UINT32 — 스키마에 좁은 범위가 지정된 경우만 반영한다
        # (None 이면 BaseHexLineEdit 기본 범위 0~0xFFFFFFFF 유지).
        # [주의] 범위 설정은 _bind_param() 전에 — 창 생성 시점에 param 에 캐시된
        # 값이 있으면 bind 가 즉시 값을 주입하는데, 기본 범위로 클램프되면 안 된다
        if self.param.min_value is not None and self.param.max_value is not None:
            self.set_range(self.param.min_value, self.param.max_value)

        self._bind_param()

class ParamReadOnlyNumValueWidget(ParamWidget, ReadOnlyIntValueWidget):
    def __init__(self, param_full_path : str, force_label_text:str=None, label_width : int = 150, is_vertical_mode = False, parent = None):
        label_text = self._resolve_param(param_full_path, force_label_text)
        super().__init__(label_text=label_text, label_width=label_width, is_vertical_mode=is_vertical_mode, parent=parent)
        self._bind_param()

class ParamReadWriteNumValueWidget(ParamWidget, ReadWriteIntValueWidget):
    def __init__(self, param_full_path : str, force_label_text:str=None, label_width : int = 150, is_vertical_mode = False, parent = None):
        label_text = self._resolve_param(param_full_path, force_label_text)
        super().__init__(label_text=label_text, label_width=label_width, is_vertical_mode=is_vertical_mode, parent=parent)

        # NUM param 은 스키마에 min/max 가 지정된 정수 — 입력 범위로 반영한다.
        # [주의] 범위 설정은 _bind_param() 전에 — 창 생성 시점에 param 에 캐시된
        # 값이 있으면 bind 가 즉시 값을 주입하는데, 기본 범위(0~99.99)로
        # 클램프되면 안 된다
        if self.param.min_value is not None and self.param.max_value is not None:
            self.set_range(self.param.min_value, self.param.max_value)

        self._bind_param()

class ParamReadOnlyRealValueWidget(ParamWidget, ReadOnlyFloatValueWidget):
    def __init__(self, param_full_path : str, force_label_text:str=None, label_width : int = 150, is_vertical_mode = False, parent = None):
        label_text = self._resolve_param(param_full_path, force_label_text)
        super().__init__(label_text=label_text, label_width=label_width, is_vertical_mode=is_vertical_mode, parent=parent)
        self._bind_param()

class ParamReadWriteRealValueWidget(ParamWidget, ReadWriteFloatValueWidget):
    def __init__(self, param_full_path : str, force_label_text:str=None, label_width : int = 150, is_vertical_mode = False, parent = None):
        label_text = self._resolve_param(param_full_path, force_label_text)
        super().__init__(label_text=label_text, label_width=label_width, is_vertical_mode=is_vertical_mode, parent=parent)

        # REAL param 은 스키마에 min/max 가 지정된 float — 입력 범위로 반영한다.
        # 자릿수는 지정하지 않는다 — BaseFloatLineEdit 기본인 유효숫자 6자리
        # 모드를 그대로 쓴다 (RO 쪽 to_str 의 전역 정책과 표기 일치).
        # [주의] 범위 설정은 _bind_param() 전에 — 창 생성 시점에 param 에
        # 캐시된 값이 있으면 bind 가 즉시 값을 주입하는데, 기본 범위(0~99.99)로
        # 클램프되면 안 된다
        if self.param.min_value is not None and self.param.max_value is not None:
            self.set_range(self.param.min_value, self.param.max_value)

        self._bind_param()

class ParamReadOnlyScaleValueWidget(ParamWidget, ReadOnlyScaleValueWidget):
    def __init__(self, param_full_path : str, force_label_text:str=None, label_width : int = 150, is_vertical_mode = False, parent = None):
        label_text = self._resolve_param(param_full_path, force_label_text)
        super().__init__(label_text=label_text, scale=100.0, label_width=label_width, is_vertical_mode=is_vertical_mode, parent=parent)
        self._bind_param()

class ParamReadWriteScaleValueWidget(ParamWidget, ReadWriteScaleValueWidget):
    def __init__(self, param_full_path : str, force_label_text:str=None, label_width : int = 150, is_vertical_mode = False, parent = None):
        label_text = self._resolve_param(param_full_path, force_label_text)
        super().__init__(label_text=label_text, scale=100.0, label_width=label_width, is_vertical_mode=is_vertical_mode, parent=parent)

        # SCALE param 의 스키마 min/max 는 표시 범위 기준(예: 0~100(%)) —
        # set_range 계약도 표시값이므로 그대로 적용한다.
        # [주의] 범위 설정은 _bind_param() 전에 — 창 생성 시점에 param 에 캐시된
        # 값이 있으면 bind 가 즉시 값을 주입하는데, 기본 범위로 클램프되면 안 된다
        if self.param.min_value is not None and self.param.max_value is not None:
            self.set_range(self.param.min_value, self.param.max_value)

        self._bind_param()

class ParamReadOnlyPosiValueWidget(ParamWidget, ReadOnlyTextValueWidget):
    def __init__(self, param_full_path : str, force_label_text:str=None, label_width : int = 150, is_vertical_mode = False, parent = None):
        self.converter = PosiConverterManager()
        label_text = self._resolve_param(param_full_path, force_label_text)
        super().__init__(label_text=label_text, label_width=label_width, is_vertical_mode=is_vertical_mode, parent=parent)
        self._bind_param() 

        self.converter.sig_posi_range_changed.connect(self.handle_posi_range_changed)
        self.handle_posi_range_changed()

    def handle_posi_range_changed(self):
        self.set_value(self.param.value)
        self.commit()

    def set_value(self, value):
        converted_value = self.converter.convert_posi_to_dp_str(value)
        super().set_value(converted_value)

    def get_value(self):
        value = super().get_value()
        converted_value = self.converter.convert_dp_str_to_posi(value)
        return converted_value

    def import_backup_value(self, value, unit=None):
        # posi 표시값은 단위 설정과 무관하게 항상 백분율 — unit 은 사용하지 않는다
        super().set_value(value)

    def export_backup_value(self):
        return super().get_value()

class ParamReadWritePosiValueWidget(ParamWidget, ReadWriteFloatValueWidget):
    """ReadWriteFloatValueWidget(라인에딧) 기반 posi 입력 — 스핀박스 버전과 달리
    '값 없음'(Unknown placeholder) / Not Support 표시를 지원한다.

    스키마 min/max 는 표시 범위 기준이라 변환 없이 그대로 적용한다 (스펙)."""

    def __init__(self, param_full_path : str, force_label_text:str=None, label_width : int = 150, is_vertical_mode = False, parent = None):
        self.converter = PosiConverterManager()
        label_text = self._resolve_param(param_full_path, force_label_text)
        super().__init__(label_text=label_text, label_width=label_width, is_vertical_mode=is_vertical_mode, parent=parent)

        # 범위/자릿수는 _bind_param() 전에 — bind 가 캐시된 값을 즉시 주입하므로
        # 기본 범위(0~99.99)로 클램프되면 안 된다
        self.converter.sig_posi_range_changed.connect(self.handle_posi_range_changed)
        self.set_decimals(self.converter.posi_decimal_places)
        if self.param.min_value is not None and self.param.max_value is not None:
            self.set_range(self.param.min_value, self.param.max_value)

        self._bind_param()

    def handle_posi_range_changed(self):
        self.set_decimals(self.converter.posi_decimal_places)
        self.set_value(self.param.value)
        self.commit()

    def set_value(self, value):
        converted_value = self.converter.convert_posi_to_dp(value)
        super().set_value(converted_value)

    def get_value(self):
        value = super().get_value()
        converted_value = self.converter.convert_dp_to_posi(value)
        return converted_value

    def import_backup_value(self, value, unit=None):
        # posi 표시값은 단위 설정과 무관하게 항상 백분율 — unit 은 사용하지 않는다
        super().set_value(value)

    def export_backup_value(self):
        return super().get_value()

class ParamReadWritePosiValueSpinBoxWidget(ParamWidget, ReadWriteFloatValueSpinBoxWidget):
    def __init__(self, param_full_path : str, force_label_text:str=None, label_width : int = 150, is_vertical_mode = False, parent = None):
        self.converter = PosiConverterManager()
        label_text = self._resolve_param(param_full_path, force_label_text)
        super().__init__(label_text=label_text, label_width=label_width, is_vertical_mode=is_vertical_mode, parent=parent)
        self._bind_param()  
      
        self.converter.sig_posi_range_changed.connect(self.handle_posi_range_changed)
        self.set_range(self.param.min_value, self.param.max_value)
        self.handle_posi_range_changed()

    def handle_posi_range_changed(self):
        self.set_decimals(self.converter.posi_decimal_places)
        self.set_value(self.param.value)
        self.commit()

    def set_value(self, value):
        converted_value = self.converter.convert_posi_to_dp(value)
        super().set_value(converted_value)

    def get_value(self):
        value = super().get_value()
        converted_value = self.converter.convert_dp_to_posi(value)
        return converted_value

    def import_backup_value(self, value, unit=None):
        # posi 표시값은 단위 설정과 무관하게 항상 백분율 — unit 은 사용하지 않는다
        super().set_value(value)

    def export_backup_value(self):
        return super().get_value()

class ParamReadOnlyPresValueWidget(ParamWidget, ReadOnlyTextValueWidget):
    def __init__(self, param_full_path : str, force_label_text:str=None, label_width : int = 150, is_vertical_mode = False, is_visible_unit = True, convert_type = None, parent = None):
        self.converter = PresConverterManager()
        self.local_setting_manager = LocalSettingManager()
        self.convert_type = convert_type
        self.is_visible_unit = is_visible_unit
        self.base_label_text = self._resolve_param(param_full_path, force_label_text)

        super().__init__(label_text=self._make_label_text(), label_width=label_width, is_vertical_mode=is_vertical_mode, parent=parent)
        self._bind_param()

        self.converter.sig_pres_range_changed.connect(self.handle_pres_range_changed)
        self.handle_pres_range_changed()

    def _make_label_text(self) -> str:
        # pres_unit 은 SensUnitEnum 의 int 값 — 표시 문자열은 get_desc 로 얻는다
        if not self.is_visible_unit:
            return self.base_label_text
        return f"{self.base_label_text} ({p_enum.SensUnitEnum.get_desc(self.local_setting_manager.pres_unit)})"

    def handle_pres_range_changed(self):
        # 표시 단위가 바뀌면 라벨의 단위 표기도 함께 갱신한다
        if self.lbl_label is not None:
            self.lbl_label.setText(self._make_label_text())

        self.set_value(self.param.value)
        self.commit()

    def set_value(self, value):
        converted_value = self.converter.convert_iface_pres_to_dp_pres_str(value, self.convert_type)
        super().set_value(converted_value)

    def get_value(self):
        value = super().get_value()
        converted_value = self.converter.convert_dp_pres_str_to_iface_pres(value, self.convert_type)
        return converted_value

    def import_backup_value(self, value, unit=None):
        # 저장 당시 표시 단위가 현재와 다르면 현재 표시 단위로 환산해 넣는다
        current_unit = self.converter.local_setting.pres_unit
        if value is not None and unit is not None and unit != current_unit:
            try:
                converted = self.converter.convert_pressure(float(value), unit, current_unit)
                value = to_sig_str(converted)
            except (TypeError, ValueError):
                pass  # 해석 불가 값은 환산 없이 그대로 (표시 전용 위젯이라 무해)
        super().set_value(value)

    def export_backup_value(self):
        return super().get_value()

    def export_backup_unit(self):
        return self.converter.local_setting.pres_unit

class ParamReadWritePresValueSpinBoxWidget(ParamWidget, ReadWriteFloatValueSpinBoxWidget):
    def __init__(self, param_full_path : str, force_label_text:str=None, label_width : int = 150, is_vertical_mode = False, is_visible_unit = True, convert_type = None, parent = None):
        self.converter = PresConverterManager()
        self.local_setting_manager = LocalSettingManager()
        self.convert_type = convert_type
        self.is_visible_unit = is_visible_unit
        self.base_label_text = self._resolve_param(param_full_path, force_label_text)
        super().__init__(label_text=self._make_label_text(), label_width=label_width, is_vertical_mode=is_vertical_mode, parent=parent)
        self._bind_param()  

        self.converter.sig_pres_range_changed.connect(self.handle_pres_range_changed)
        self.set_range(self.param.min_value, self.param.max_value)
        self.handle_pres_range_changed()

    def _make_label_text(self) -> str:
        # pres_unit 은 SensUnitEnum 의 int 값 — 표시 문자열은 get_desc 로 얻는다
        if not self.is_visible_unit:
            return self.base_label_text
        return f"{self.base_label_text} ({p_enum.SensUnitEnum.get_desc(self.local_setting_manager.pres_unit)})"

    def handle_pres_range_changed(self):
        # 표시 단위가 바뀌면 라벨의 단위 표기도 함께 갱신한다
        if self.lbl_label is not None:
            self.lbl_label.setText(self._make_label_text())
        
        self.set_decimals(self.converter.pres_decimal_places)
        self.set_value(self.param.value)
        self.commit()

    def set_value(self, value):
        converted_value = self.converter.convert_iface_pres_to_dp_pres(value, self.convert_type)
        super().set_value(converted_value)

    def get_value(self):
        value = super().get_value()
        converted_value = self.converter.convert_dp_pres_to_iface_pres(value, self.convert_type)
        return converted_value

    def import_backup_value(self, value, unit=None):
        # 저장 당시 표시 단위가 현재와 다르면 현재 표시 단위로 환산해 넣는다
        current_unit = self.converter.local_setting.pres_unit
        if value is not None and unit is not None and unit != current_unit:
            value = self.converter.convert_pressure(value, unit, current_unit)
        super().set_value(value)

    def export_backup_value(self):
        return super().get_value()

    def export_backup_unit(self):
        return self.converter.local_setting.pres_unit

class ParamReadWritePresValueWidget(ParamWidget, ReadWriteFloatValueWidget):
    """ReadWriteFloatValueWidget(라인에딧) 기반 pres 입력 — 스핀박스 버전과 달리
    '값 없음'(Unknown placeholder) / Not Support 표시를 지원한다.

    스핀박스 버전과 동일하게 convert_type(센서 기준 선택)과 라벨 단위 표기
    (is_visible_unit)를 지원하고, 스키마 min/max 는 표시 범위 기준이라 변환
    없이 그대로 적용한다."""

    def __init__(self, param_full_path : str, force_label_text:str=None, label_width : int = 150, is_vertical_mode = False, is_visible_unit = True, convert_type = None, parent = None):
        self.converter = PresConverterManager()
        self.local_setting_manager = LocalSettingManager()
        self.convert_type = convert_type
        self.is_visible_unit = is_visible_unit
        self.base_label_text = self._resolve_param(param_full_path, force_label_text)
        super().__init__(label_text=self._make_label_text(), label_width=label_width, is_vertical_mode=is_vertical_mode, parent=parent)

        # 범위/자릿수는 _bind_param() 전에 — bind 가 캐시된 값을 즉시 주입하므로
        # 기본 범위(0~99.99)로 클램프되면 안 된다
        self.converter.sig_pres_range_changed.connect(self.handle_pres_range_changed)
        self.set_decimals(self.converter.pres_decimal_places)
        if self.param.min_value is not None and self.param.max_value is not None:
            self.set_range(self.param.min_value, self.param.max_value)

        self._bind_param()

    def _make_label_text(self) -> str:
        # pres_unit 은 SensUnitEnum 의 int 값 — 표시 문자열은 get_desc 로 얻는다
        if not self.is_visible_unit:
            return self.base_label_text
        return f"{self.base_label_text} ({p_enum.SensUnitEnum.get_desc(self.local_setting_manager.pres_unit)})"

    def handle_pres_range_changed(self):
        # 표시 단위가 바뀌면 라벨의 단위 표기도 함께 갱신한다
        if self.lbl_label is not None:
            self.lbl_label.setText(self._make_label_text())

        self.set_decimals(self.converter.pres_decimal_places)
        self.set_value(self.param.value)
        self.commit()

    def set_value(self, value):
        converted_value = self.converter.convert_iface_pres_to_dp_pres(value, self.convert_type)
        super().set_value(converted_value)

    def get_value(self):
        value = super().get_value()
        converted_value = self.converter.convert_dp_pres_to_iface_pres(value, self.convert_type)
        return converted_value

    def import_backup_value(self, value, unit=None):
        # 저장 당시 표시 단위가 현재와 다르면 현재 표시 단위로 환산해 넣는다
        current_unit = self.converter.local_setting.pres_unit
        if value is not None and unit is not None and unit != current_unit:
            value = self.converter.convert_pressure(value, unit, current_unit)
        super().set_value(value)

    def export_backup_value(self):
        return super().get_value()

    def export_backup_unit(self):
        return self.converter.local_setting.pres_unit

class ParamReadOnlyPresSlopeValueWidget(ParamReadOnlyPresValueWidget):
    """압력 변화율(slope) 표시 — ParamReadOnlyPresValueWidget 과 동일하되
    라벨 단위 표기가 '(압력단위/sec)' 인 것만 다르다."""

    def _make_label_text(self) -> str:
        if not self.is_visible_unit:
            return self.base_label_text
        return f"{self.base_label_text} ({p_enum.SensUnitEnum.get_desc(self.local_setting_manager.pres_unit)}/sec)"

class ParamReadWritePresSlopeValueWidget(ParamReadWritePresValueWidget):
    """압력 변화율(slope) 입력 — ParamReadWritePresValueWidget 과 동일하되
    라벨 단위 표기가 '(압력단위/sec)' 인 것만 다르다."""

    def _make_label_text(self) -> str:
        if not self.is_visible_unit:
            return self.base_label_text
        return f"{self.base_label_text} ({p_enum.SensUnitEnum.get_desc(self.local_setting_manager.pres_unit)}/sec)"
