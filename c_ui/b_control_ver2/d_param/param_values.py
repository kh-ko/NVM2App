from b_core.b_datatype import param_enum as p_enum
from b_core.c_manager.parameter_manager import ParamManager
from b_core.f_helper.float_util import is_float_equal
from c_ui.a_converter.pressure_converter_manager import PresConverterManager
from c_ui.a_converter.position_converter_manager import PosiConverterManager
from c_ui.b_control_ver2.a_theme.tokens  import tokens
from c_ui.b_control_ver2.c_values.write_only_values import (WriteOnlyButtonValueWidget, WriteOnlyEnumValueWidget,
                                                            WriteOnlyFloatValueWidget)
from c_ui.b_control_ver2.c_values.read_only_values import (ReadOnlyBitmapValueWidget, ReadOnlyEnumValueWidget, ReadOnlyFloatValueWidget,
                                                           ReadOnlyIntValueWidget, ReadOnlyMultipleEnumValueWidget,
                                                           ReadOnlyTextValueWidget)
from c_ui.b_control_ver2.c_values.read_write_values import (ReadWriteBitmapValueWidget, ReadWriteEnumValueWidget, ReadWriteFloatValueSpinBoxWidget,
                                                            ReadWriteFloatValueWidget, ReadWriteHexValueWidget, ReadWriteIntValueWidget)

class ParamWidget:
    """param 바인딩 공통 동작 믹스인 — c_value 위젯과 다중상속으로 사용한다.

    사용 규칙 (서브클래스 __init__ 에서):
        1. label_text = self._resolve_param(param_full_path, force_label_text)
        2. super().__init__(...)   # 각자 베이스 위젯 인자 매핑 (enum_class 등)
        3. self._bind_param()      # 시그널 연결 + 초기 상태 동기화
    압력/위치 표시 위젯은 이 클래스를 확장한 PresDisplayMixin / PosiDisplayMixin 을 대신 쓴다 (아래).
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
        # 값 반영 후 commit 으로 dirty 기준(ori_value)까지 갱신한다.
        # 활성 여부는 set_value 안의 _sync_enabled 가 Not Support·값·enable 조건을 한꺼번에 본다 (8-d)
        self.set_value(self.param.value)
        self.commit()

    def handle_param_is_err_changed(self):
        if self.lbl_label is None:  # 라벨 없는 구성(label_text="")에서는 표시할 곳이 없다
            return

        if self.param.is_err:
            self.lbl_label.set_colors(text=tokens().danger)
        else:
            self.lbl_label.set_colors(text=tokens().text)

    def handle_param_is_not_support_changed(self):
        self.set_not_support(self.param.is_not_support)
        if not self.param.is_not_support:
            # Not Support 에서 정상으로 돌아왔는데 값이 같으면 sig_value_changed 가 오지 않는다 —
            # 마지막 값을 다시 표시해 "Not Support" 잔존을 없앤다 (F058)
            self.handle_param_value_changed()

    def import_backup_value(self, value, unit=None):
        # unit: 저장 당시 값의 단위 표식 — 단위 개념이 있는 위젯(pres)만 사용하고
        # 나머지는 무시한다 (None = 단위 정보 없음, 현재 표시 단위로 간주)
        self.set_value(value)

    def export_backup_value(self):
        return self.get_value()

    def export_backup_unit(self):
        # 저장 값에 함께 기록할 단위 표식. 단위 개념이 없는 위젯은 None — 파일에 unit 필드가 생략된다
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

        # 0 패딩 폭은 스키마 max 의 hex 자릿수 — 예: max 255(0xFF) -> 2자리,
        # 15 -> "0x0F". max 미지정이면 0(패딩 없음). _bind_param() 이 캐시 값을
        # 즉시 주입하므로 그 전에 계산해 둔다
        self._hex_digits = len(f"{int(self.param.max_value):X}") if self.param.max_value is not None else 0

        super().__init__(label_text=label_text, label_width=label_width, is_vertical_mode=is_vertical_mode, parent=parent)
        self._bind_param()

    def set_value(self, value):
        hex_str = None

        if value is not None:
            try:
                hex_str = f"0x{value:0{self._hex_digits}X}"
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
            # 0 패딩 폭은 max 의 hex 자릿수 — 예: max 255(0xFF) -> 2자리, 15 -> "0F"
            self.set_digits(len(f"{int(self.param.max_value):X}"))

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

class ParamReadOnlyScaleValueWidget(ParamWidget, ReadOnlyFloatValueWidget):
    """SCALE 표시 — 배율(×100 / ×10000)은 spec 의 ScaleCodec 이 적용해 param.value 가 이미 화면 기준 값이다. 위젯은 그대로 표시한다.
    본문은 ParamReadOnlyRealValueWidget 과 같다 — 표시 타입(SCALE / REAL)별 거울 클래스를 독립으로 두기 위한 의도된 동형 (N088)."""

    def __init__(self, param_full_path : str, force_label_text:str=None, label_width : int = 150, is_vertical_mode = False, parent = None):
        label_text = self._resolve_param(param_full_path, force_label_text)
        super().__init__(label_text=label_text, label_width=label_width, is_vertical_mode=is_vertical_mode, parent=parent)
        self._bind_param()

class ParamReadWriteScaleValueWidget(ParamWidget, ReadWriteFloatValueWidget):
    """SCALE 입력 — param.value 는 ScaleCodec 을 거친 화면 기준 값이고 스키마 min/max 도 표시 범위 기준(예: 0~100(%))이라 그대로 적용한다.
    본문은 ParamReadWriteRealValueWidget 과 같다 — 거울 클래스를 독립으로 두기 위한 의도된 동형 (N088)."""

    def __init__(self, param_full_path : str, force_label_text:str=None, label_width : int = 150, is_vertical_mode = False, parent = None):
        label_text = self._resolve_param(param_full_path, force_label_text)
        super().__init__(label_text=label_text, label_width=label_width, is_vertical_mode=is_vertical_mode, parent=parent)

        # [주의] 범위 설정은 _bind_param() 전에 — 창 생성 시점에 param 에 캐시된 값이 있으면 bind 가 즉시 값을 주입하는데,
        # 기본 범위로 클램프되면 안 된다
        if self.param.min_value is not None and self.param.max_value is not None:
            self.set_range(self.param.min_value, self.param.max_value)

        self._bind_param()

class ParamReadWriteIFaceGainValueWidget(ParamReadWriteScaleValueWidget):
    """IFACE_GAIN 입력 — ifgain param 도 ScaleCodec(nv2_spec.json codecs.scale10000) 을 거친 화면 기준 값이라 SCALE 입력과 같다.
    표시 타입별 이름(param_folder_widget 의 매핑)은 유지한다."""

# ============================================================================================ 컨버터 표시 믹스인 (Pres / Posi)
class PresDisplayMixin(ParamWidget):
    """압력 param 표시 — param.value 는 Torr(도메인), 위젯에는 LocalSetting 표시 단위로 환산한 값을 넣는다.
    어느 센서 기준으로 푸는가(auto / 1 / 2)는 param 의 codec 이 정하므로 위젯은 모른다.

    구체 클래스: class X(PresDisplayMixin, <c_values 위젯>). set_value / get_value 재정의는 이 믹스인에 둔다 — ParamWidget(MRO 상
    믹스인과 c_values 사이)에는 두지 않는다. import_backup_value / export_backup_value 의 super() 가 ParamWidget 을 지나 c_values
    위젯에 직행(변환 0회)하는 전제다 — 깨지면 Load 값에 표시 변환이 한 번 더 들어간다 (test_domain_step3 5절이 잡는다).
    _TEXT_VALUE = True 는 RO 라벨(ReadOnlyTextValueWidget) 구체 클래스가 둔다 — to_display_str / from_display_str, set_decimals 없음,
    is_dirty 는 c_values 의 False. False(기본)는 실수 편집기 — to_display / from_display, 자릿수는 set_decimals, 표시 기준 is_dirty.
    _UNIT_SUFFIX 는 라벨 단위 표기 뒤에 붙는다 — slope 가 "/sec".
    만압 문맥에는 의존하지 않으므로 표시 단위 / 자릿수 두 시그널만 받는다 (설계 7위). 백업 훅은 RW 편집기 전용이다 —
    Save/Load 는 acc == RW 위젯만 다루므로(param_win 의 widget_map) RO 라벨에서는 호출 경로가 없다."""

    _TEXT_VALUE = False
    _UNIT_SUFFIX = ""

    # ------------------------------------------------------------ 초기화 — 구체 클래스 __init__ 의 처음과 끝
    def _init_pres_display(self, param_full_path: str, force_label_text: str = None, is_visible_unit: bool = True) -> str:
        # super().__init__ 전에 — c_values __init__ 이 set_value(None)/commit 을 부르고 그것이 아래 set_value/get_value 를 지난다.
        # 라벨 문구를 돌려준다
        self.converter = PresConverterManager()
        self.is_visible_unit = is_visible_unit
        self.base_label_text = self._resolve_param(param_full_path, force_label_text)
        return self._make_label_text()

    def _bind_pres_display(self):
        # 자릿수·범위가 정해진 뒤 — bind 가 캐시 값을 주입하고, 그 다음 컨버터 변경을 받는다
        self._bind_param()
        self.converter.sig_display_unit_changed.connect(self.handle_pres_display_unit_changed)
        self.converter.sig_decimals_changed.connect(self.handle_pres_decimals_changed)

    # ------------------------------------------------------------ RO 라벨 / RW 편집기 차이를 흡수하는 훅
    def _to_widget(self, torr):
        return self.converter.to_display_str(torr) if self._TEXT_VALUE else self.converter.to_display(torr)

    def _from_widget(self, shown):
        return self.converter.from_display_str(shown) if self._TEXT_VALUE else self.converter.from_display(shown)

    def _apply_decimals(self):
        if not self._TEXT_VALUE:  # 라벨은 to_display_str 이 자릿수를 적용한다
            self.set_decimals(self.converter.pres_decimal_places)

    # ------------------------------------------------------------ 라벨
    def _make_label_text(self) -> str:
        # pres_unit 은 SensUnitEnum 의 int 값 — 표시 문자열은 get_desc 로 얻는다 (LocalSetting 핸들은 converter.local_setting 하나)
        if not self.is_visible_unit:
            return self.base_label_text
        unit = p_enum.SensUnitEnum.get_desc(self.converter.local_setting.pres_unit)
        return f"{self.base_label_text} ({unit}{self._UNIT_SUFFIX})"

    # ------------------------------------------------------------ 컨버터 시그널 슬롯 (1:1)
    def handle_pres_display_unit_changed(self):
        # 표시 단위가 바뀌면 라벨의 단위 표기와 표시값을 갱신한다
        if self.lbl_label is not None:
            self.lbl_label.setText(self._make_label_text())
        self.handle_pres_decimals_changed()

    def handle_pres_decimals_changed(self):
        self._apply_decimals()
        self.handle_param_value_changed()  # set_value(param.value) + commit — 변환은 set_value 안에서 1회 (N092 현행 동작 유지)

    # ------------------------------------------------------------ 값 (도메인 Torr ↔ 위젯 표시 단위)
    def set_value(self, value):
        super().set_value(self._to_widget(value))

    def get_value(self):
        # 표시 단위 → Torr (도메인). 쓰기 시 선로 문자열은 spec 의 codec 이 만든다
        return self._from_widget(super().get_value())

    def is_dirty(self):
        if self._TEXT_VALUE:
            return super().is_dirty()  # → ParamWidget(정의 없음) → ReadOnlyTextValueWidget.is_dirty = False
        # dirty 는 사용자에게 보이는 값(표시 단위) 기준 — get_value() 는 쓰기용 Torr 라 그대로
        # 비교하면 abs_tol(1e-9) 이 표시 단위와 어긋난다 (mTorr 표시에서 0 → 0.000001 이 clean)
        return not is_float_equal(self.converter.to_display(self.get_value()),
                                  self.converter.to_display(self.ori_value))

    # ------------------------------------------------------------ 백업 (Save/Load File — RW 만 호출된다)
    def import_backup_value(self, value, unit=None):
        # 저장 당시 표시 단위가 현재와 다르면 현재 표시 단위로 환산해 넣는다
        current_unit = self.converter.local_setting.pres_unit
        if unit is not None and unit != current_unit:  # value 없음(null)은 호출측(Load File)이 먼저 거른다
            value = self.converter.convert_pressure(value, unit, current_unit)
        super().set_value(value)  # 변환 없이 표시 단위 값 그대로 — ParamWidget 을 지나 c_values 위젯으로

    def export_backup_value(self):
        return super().get_value()  # 표시 단위 그대로 저장

    def export_backup_unit(self):
        return self.converter.local_setting.pres_unit


class PosiDisplayMixin(ParamWidget):
    """위치 param 표시 — param.value 는 이미 백분율(도메인)이다. 위젯은 LocalSetting 의 소수점 자릿수로 포맷만 한다.
    선로 ↔ 백분율 변환은 spec 의 PosiCodec 몫.

    구체 클래스: class X(PosiDisplayMixin, <c_values 위젯>). set_value / get_value 재정의는 이 믹스인에 둔다 — ParamWidget(MRO 상
    믹스인과 c_values 사이)에는 두지 않는다 (ParamWidget 기본 백업 훅의 self.set_value 가 변환 없는 항등을 지나는 전제).
    _TEXT_VALUE = True 는 RO 라벨(ReadOnlyTextValueWidget) 구체 클래스가 둔다 — format_dp / parse_dp_str 로 문자열을 만들고
    set_decimals 가 없다. False(기본)는 실수 편집기 — 값 변환이 없고 자릿수만 set_decimals.
    백업 훅과 is_dirty 는 ParamWidget / c_values 기본으로 충분하다 (표시값 = 도메인값)."""

    _TEXT_VALUE = False

    # ------------------------------------------------------------ 초기화 — 구체 클래스 __init__ 의 처음과 끝
    def _init_posi_display(self, param_full_path: str, force_label_text: str = None) -> str:
        # super().__init__ 전에 — c_values __init__ 이 set_value(None)/commit 을 부르고 그것이 아래 set_value/get_value 를 지난다
        self.converter = PosiConverterManager()
        return self._resolve_param(param_full_path, force_label_text)

    def _bind_posi_display(self):
        # 자릿수·범위가 정해진 뒤 — bind 가 캐시 값을 주입하고, 그 다음 자릿수 변경을 받는다
        # (sig_posi_range_changed 는 posi_decimal_places 변경에만 발화한다)
        self._bind_param()
        self.converter.sig_posi_range_changed.connect(self.handle_posi_range_changed)

    # ------------------------------------------------------------ RO 라벨 / RW 편집기 차이를 흡수하는 훅
    def _to_widget(self, percent):
        return self.converter.format_dp(percent) if self._TEXT_VALUE else percent

    def _from_widget(self, shown):
        return self.converter.parse_dp_str(shown) if self._TEXT_VALUE else shown

    def _apply_decimals(self):
        if not self._TEXT_VALUE:  # 라벨은 format_dp 가 자릿수를 적용한다
            self.set_decimals(self.converter.posi_decimal_places)

    # ------------------------------------------------------------ 컨버터 시그널 슬롯 (1:1)
    def handle_posi_range_changed(self):
        self._apply_decimals()
        self.handle_param_value_changed()  # set_value(param.value) + commit (N092 현행 동작 유지)

    # ------------------------------------------------------------ 값 (백분율 ↔ 위젯)
    def set_value(self, value):
        super().set_value(self._to_widget(value))

    def get_value(self):
        return self._from_widget(super().get_value())

# ============================================================================================ 구체 클래스 (이름·시그니처 불변)
class ParamReadOnlyPosiValueWidget(PosiDisplayMixin, ReadOnlyTextValueWidget):
    _TEXT_VALUE = True

    def __init__(self, param_full_path : str, force_label_text:str=None, label_width : int = 150, is_vertical_mode = False, parent = None):
        label_text = self._init_posi_display(param_full_path, force_label_text)
        super().__init__(label_text=label_text, label_width=label_width, is_vertical_mode=is_vertical_mode, parent=parent)
        self._bind_posi_display()

class ParamReadWritePosiValueWidget(PosiDisplayMixin, ReadWriteFloatValueWidget):
    """ReadWriteFloatValueWidget(라인에딧) 기반 posi 입력 — 스핀박스 버전과 달리 '값 없음'(Unknown placeholder) / Not Support 표시를
    지원한다. 스키마 min/max 는 표시 범위 기준이라 변환 없이 그대로 적용한다."""

    def __init__(self, param_full_path : str, force_label_text:str=None, label_width : int = 150, is_vertical_mode = False, parent = None):
        label_text = self._init_posi_display(param_full_path, force_label_text)
        super().__init__(label_text=label_text, label_width=label_width, is_vertical_mode=is_vertical_mode, parent=parent)

        # 자릿수/범위는 bind 전에 — bind 가 캐시된 값을 즉시 주입하므로 기본 범위(0~99.99)로 클램프되면 안 된다
        self._apply_decimals()
        if self.param.min_value is not None and self.param.max_value is not None:
            self.set_range(self.param.min_value, self.param.max_value)

        self._bind_posi_display()

class ParamWriteOnlyPosiValueWidget(PosiDisplayMixin, WriteOnlyFloatValueWidget):
    """위치(백분율) 쓰기 전용 입력 — 클러스터 장치 Target Position 처럼 읽기 값이 없는 명령형 param.
    입력은 백분율이며 자릿수는 LocalSetting, 범위는 스키마 min/max. Send 버튼 또는 Enter 로 쓴다 —
    선로 문자열(예: 030000)은 spec 의 codec 이 만든다. 창은 sig_edited_by_user 를 받아 get_value() 를 쓴다."""

    def __init__(self, param_full_path : str, force_label_text:str=None, label_width : int = 150, is_vertical_mode = False, parent = None):
        label_text = self._init_posi_display(param_full_path, force_label_text)
        super().__init__(btn_text="Send", label_text=label_text, label_width=label_width, is_vertical_mode=is_vertical_mode, parent=parent)

        self._apply_decimals()
        if self.param.min_value is not None and self.param.max_value is not None:
            self.set_range(self.param.min_value, self.param.max_value)

        self._bind_posi_display()

    def handle_posi_range_changed(self):
        self._apply_decimals()  # 읽기 값이 없는 WO 는 자릿수만 바꾼다

class ParamReadWritePosiValueSpinBoxWidget(PosiDisplayMixin, ReadWriteFloatValueSpinBoxWidget):
    def __init__(self, param_full_path : str, force_label_text:str=None, label_width : int = 150, is_vertical_mode = False, parent = None):
        label_text = self._init_posi_display(param_full_path, force_label_text)
        super().__init__(label_text=label_text, label_width=label_width, is_vertical_mode=is_vertical_mode, parent=parent)

        # 자릿수/범위는 bind 전에 — 스핀박스 기본 범위(0~99.99)로 클램프된 채 주입되지 않도록
        self._apply_decimals()
        if self.param.min_value is not None and self.param.max_value is not None:
            self.set_range(self.param.min_value, self.param.max_value)

        self._bind_posi_display()

class ParamReadOnlyPresValueWidget(PresDisplayMixin, ReadOnlyTextValueWidget):
    _TEXT_VALUE = True

    def __init__(self, param_full_path : str, force_label_text:str=None, label_width : int = 150, is_vertical_mode = False, is_visible_unit = True, parent = None):
        label_text = self._init_pres_display(param_full_path, force_label_text, is_visible_unit)
        super().__init__(label_text=label_text, label_width=label_width, is_vertical_mode=is_vertical_mode, parent=parent)
        self._bind_pres_display()

class ParamReadWritePresValueSpinBoxWidget(PresDisplayMixin, ReadWriteFloatValueSpinBoxWidget):
    def __init__(self, param_full_path : str, force_label_text:str=None, label_width : int = 150, is_vertical_mode = False, is_visible_unit = True, parent = None):
        label_text = self._init_pres_display(param_full_path, force_label_text, is_visible_unit)
        super().__init__(label_text=label_text, label_width=label_width, is_vertical_mode=is_vertical_mode, parent=parent)

        # 자릿수/범위는 bind 전에 — 스핀박스 기본 범위(0~99.99)로 클램프된 채 주입되지 않도록
        self._apply_decimals()
        if self.param.min_value is not None and self.param.max_value is not None:
            self.set_range(self.param.min_value, self.param.max_value)

        self._bind_pres_display()

class ParamReadWritePresValueWidget(PresDisplayMixin, ReadWriteFloatValueWidget):
    """ReadWriteFloatValueWidget(라인에딧) 기반 pres 입력 — 스핀박스 버전과 달리 '값 없음'(Unknown placeholder) / Not Support 표시를
    지원한다. 라벨 단위 표기(is_visible_unit)를 지원하고, 스키마 min/max 는 표시 범위 기준이라 변환 없이 그대로 적용한다."""

    def __init__(self, param_full_path : str, force_label_text:str=None, label_width : int = 150, is_vertical_mode = False, is_visible_unit = True, parent = None):
        label_text = self._init_pres_display(param_full_path, force_label_text, is_visible_unit)
        super().__init__(label_text=label_text, label_width=label_width, is_vertical_mode=is_vertical_mode, parent=parent)

        # 자릿수/범위는 bind 전에 — bind 가 캐시된 값을 즉시 주입하므로 기본 범위(0~99.99)로 클램프되면 안 된다
        self._apply_decimals()
        if self.param.min_value is not None and self.param.max_value is not None:
            self.set_range(self.param.min_value, self.param.max_value)

        self._bind_pres_display()

class ParamReadOnlyPresSlopeValueWidget(ParamReadOnlyPresValueWidget):
    """압력 변화율(slope) 표시 — ParamReadOnlyPresValueWidget 과 동일하되 라벨 단위 표기가 '(압력단위/sec)' 인 것만 다르다.

    값 변환은 압력과 완전히 같다 — psig 표시에서는 변화율에도 대기압 오프셋(-14.696)이 붙어
    물리적인 변화율과 다르게 보인다. 사용자가 환산해서 보도록 매뉴얼에 지침을 둔다
    (2026-09-30 사용자 결정, 결정 J 유지, N093)."""
    _UNIT_SUFFIX = "/sec"

class ParamReadWritePresSlopeValueWidget(ParamReadWritePresValueWidget):
    """압력 변화율(slope) 입력 — ParamReadWritePresValueWidget 과 동일하되 라벨 단위 표기가 '(압력단위/sec)' 인 것만 다르다.

    값 변환은 압력과 완전히 같다 — psig 표시에서는 입력값에도 대기압 오프셋이 적용되어
    Apply 되는 Torr/sec 가 화면의 psi/sec 와 물리적으로 다르다. 사용자가 환산해서 입력하도록
    매뉴얼에 지침을 둔다 (2026-09-30 사용자 결정, 결정 J 유지, N093)."""
    _UNIT_SUFFIX = "/sec"
