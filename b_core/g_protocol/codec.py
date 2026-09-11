"""Codec — 선로 문자열 ↔ 도메인 값 변환 (PacketSpec 3단계, 도메인 중립화).

Parameter.value 는 프로토콜과 무관한 "도메인 값" 이다 (2026-09-11 결정 E, F):
    위치  = 백분율 float (0 닫힘 ~ 100 열림)
    압력  = Torr 절대압 float
    배율  = 화면 기준 값 (예: 선로 0.5 → 50 %)
    그 외 = 형 변환만 (int / float / str / base36)

선로에 실리는 숫자의 뜻은 프로토콜과 장비 설정(문맥 param)에 따라 다르므로,
그 변환은 spec 에 붙는 Codec 이 맡는다. 어떤 param 이 어떤 codec 을 쓰는지는
nv2_spec.json 의 "as" 가, codec 이 읽는 문맥 param 은 같은 파일의 "codecs" 절이
선언한다 (결정 G, H). 이 모듈은 스키마 경로를 모른다.

    Codec
      ├ decode(text)    선로 문자열 → 도메인 값. 형식 불량이면 ValueError,
      │                 문맥 미준비면 None (화면은 Unknown)
      ├ encode(value)   도메인 값(숫자 또는 숫자 문자열) → 선로 문자열. 문맥 미준비면 None
      ├ from_line(v)    숫자 선로값 → 도메인 값 (Compound 폴링처럼 이미 숫자인 경로)
      ├ to_line(v)      도메인 값 → 숫자 선로값
      └ context_params  decode/encode 가 읽는 문맥 param. 워커는 refresh 큐 맨 앞에 이들을
                        한 번 읽어 decode 시점의 문맥이 최신임을 보장한다

재디코드는 하지 않는다 (결정 E 논의): 옛 선로 원문을 새 문맥으로 다시 풀면 물리적으로
없는 값이 나온다. 도메인 값은 물리량이므로 문맥이 바뀌어도 그대로 두고 다음 읽기가 갱신한다.

압력 단위 환산표(PA_FACTORS 등)는 UI 의 표시 단위 변환도 같은 표를 써야 하므로
여기(모듈 함수)에 둔다 — 구 PresConverterManager 에서 이사.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from b_core.b_datatype import param_enum as p_enum
from b_core.b_datatype.general_enum import ParamDataType
from b_core.f_helper.float_util import to_sig_str

if TYPE_CHECKING:
    from b_core.b_datatype.parameter import Parameter

DOMAIN_PRES_UNIT = p_enum.SensUnitEnum.TORR.value  # 압력 도메인 단위 (결정 F)


# ================================================================== 압력 단위 환산 (공용 표)
# 단위 -> Pa 환산 계수 (구 PresConverterManager 와 동일)
PA_FACTORS = {
    p_enum.SensUnitEnum.PA.value:    1.0,
    p_enum.SensUnitEnum.KPA.value:   1000.0,
    p_enum.SensUnitEnum.BAR.value:   100000.0,
    p_enum.SensUnitEnum.MBAR.value:  100.0,
    p_enum.SensUnitEnum.TORR.value:  133.322368,
    p_enum.SensUnitEnum.MTORR.value: 0.133322368,
    p_enum.SensUnitEnum.PSIA.value:  6894.757,
    p_enum.SensUnitEnum.PSIG.value:  6894.757,
}

ATM_PA = 101325.0  # 표준 대기압 (PSIG <-> 절대압 변환 오프셋)

# 인터페이스 압력 단위 -> 센서 압력 단위 대응
IFACE_TO_SENS_UNIT = {
    p_enum.RS232PressureUnitEnum.PA.value:    p_enum.SensUnitEnum.PA.value,
    p_enum.RS232PressureUnitEnum.KPA.value:   p_enum.SensUnitEnum.KPA.value,
    p_enum.RS232PressureUnitEnum.BAR.value:   p_enum.SensUnitEnum.BAR.value,
    p_enum.RS232PressureUnitEnum.MBAR.value:  p_enum.SensUnitEnum.MBAR.value,
    p_enum.RS232PressureUnitEnum.TORR.value:  p_enum.SensUnitEnum.TORR.value,
    p_enum.RS232PressureUnitEnum.MTORR.value: p_enum.SensUnitEnum.MTORR.value,
    p_enum.RS232PressureUnitEnum.PSI.value:   p_enum.SensUnitEnum.PSIA.value,
}


def pressure_unit_conversion(from_unit: int, to_unit: int) -> tuple[float, float]:
    """단위 변환의 (gain, offset). Pa 경유 환산이며 PSIG 는 대기압 오프셋 보정.
    변환식: to = from * gain + offset"""
    from_factor = PA_FACTORS.get(from_unit, 1.0)
    to_factor = PA_FACTORS.get(to_unit, 1.0)

    gain = from_factor / to_factor
    offset = 0.0

    psig = p_enum.SensUnitEnum.PSIG.value
    if from_unit == psig and to_unit != psig:
        offset = ATM_PA / to_factor
    elif from_unit != psig and to_unit == psig:
        offset = -ATM_PA / to_factor

    return gain, offset


def convert_pressure(value: float, from_unit: int, to_unit: int) -> float:
    gain, offset = pressure_unit_conversion(from_unit, to_unit)
    return (value * gain) + offset


# ================================================================== 위치 단위 범위표
POSI_UNIT_RANGE = {
    p_enum.RS232PositionUnitEnum.ZERO_TO_1.value:      (0.0, 1.0),
    p_enum.RS232PositionUnitEnum.ZERO_TO_10.value:     (0.0, 10.0),
    p_enum.RS232PositionUnitEnum.ZERO_TO_90.value:     (0.0, 90.0),
    p_enum.RS232PositionUnitEnum.ZERO_TO_100.value:    (0.0, 100.0),
    p_enum.RS232PositionUnitEnum.ZERO_TO_1000.value:   (0.0, 1000.0),
    p_enum.RS232PositionUnitEnum.ZERO_TO_10000.value:  (0.0, 10000.0),
    p_enum.RS232PositionUnitEnum.ZERO_TO_100000.value: (0.0, 100000.0),
}


# ================================================================== 공통
def _as_float(value) -> float:
    """encode 입력은 도메인 값(숫자) 또는 그 문자열 — 둘 다 받는다 (ValueError 전파)."""
    if isinstance(value, bool):
        raise ValueError(f"bool is not a numeric value: {value!r}")
    return float(value)


def _ready(*params: "Parameter") -> bool:
    return all(p is not None and p.value is not None for p in params)


class Codec(ABC):
    name: str = "?"
    context_params: tuple = ()

    @property
    def is_ready(self) -> bool:
        return True

    @abstractmethod
    def decode(self, text: str):
        """선로 문자열 → 도메인 값. 형식 불량 ValueError, 문맥 미준비 None."""

    @abstractmethod
    def encode(self, value) -> str | None:
        """도메인 값 → 선로 문자열. 문맥 미준비 None."""

    def from_line(self, line_value: float) -> float | None:
        raise TypeError(f"{self.name}: numeric line value is not supported")

    def to_line(self, value) -> float | None:
        raise TypeError(f"{self.name}: numeric line value is not supported")

    def describe(self) -> str:
        return self.name


# ================================================================== 형 변환만
class TextCodec(Codec):
    """선로 문자열을 data_type 규칙으로 형 변환만 한다 — 구 Parameter.set_text_value 로직.
    encode: 문자열은 그대로(호출측이 만든 선로 문자열 — enum 값, 버튼 값 등), 실수는
    유효숫자 6자리(to_sig_str), 정수는 str."""

    INT_TYPES = (ParamDataType.INT8, ParamDataType.INT16, ParamDataType.INT32,
                 ParamDataType.UINT8, ParamDataType.UINT16, ParamDataType.UINT32)
    FLOAT_TYPES = (ParamDataType.FLOAT, ParamDataType.DOUBLE)

    _cache: dict = {}

    def __init__(self, data_type: ParamDataType):
        self.data_type = data_type
        self.name = f"text:{data_type.name.lower()}"

    @classmethod
    def of(cls, data_type: ParamDataType) -> "TextCodec":
        codec = cls._cache.get(data_type)
        if codec is None:
            codec = cls._cache[data_type] = cls(data_type)
        return codec

    def decode(self, text: str):
        if self.data_type in self.INT_TYPES:
            return int(text)
        if self.data_type in self.FLOAT_TYPES:
            return float(text)
        if self.data_type is ParamDataType.STR:
            return text
        if self.data_type is ParamDataType.BASE_36:
            return int(text, 36)
        raise ValueError(f"unsupported data type: {self.data_type}")

    def encode(self, value) -> str | None:
        if value is None:
            return None
        if isinstance(value, str):
            return value
        if isinstance(value, float):
            return to_sig_str(value)
        return str(value)


# ================================================================== 배율
class ScaleCodec(Codec):
    """선로값 × factor = 도메인 값 (예: factor 100 → 선로 0.5 = 50 %). 문맥 없음."""

    def __init__(self, name: str, factor: float):
        self.name = name
        self.factor = float(factor)

    def from_line(self, line_value: float) -> float | None:
        return None if line_value is None else line_value * self.factor

    def to_line(self, value) -> float | None:
        return None if value is None else _as_float(value) / self.factor

    def decode(self, text: str):
        return self.from_line(float(text))

    def encode(self, value) -> str | None:
        line = self.to_line(value)
        return None if line is None else to_sig_str(line)


# ================================================================== 위치
class PosiCodec(Codec):
    """선로 위치값 ↔ 백분율. 범위는 Position Unit 이 정하고, USER_SPECIFIC 이면
    Value Closest Position / Value Open Position 이 (min, max) 다 (구 PosiConverterManager)."""

    def __init__(self, name: str, unit_param: "Parameter", min_param: "Parameter", max_param: "Parameter"):
        self.name = name
        self.unit_param = unit_param
        self.min_param = min_param
        self.max_param = max_param
        self.context_params = tuple(p for p in (unit_param, min_param, max_param) if p is not None)

    def range(self) -> tuple[float, float] | None:
        """(min, max) — 문맥 미준비/알 수 없는 단위면 None."""
        if not _ready(self.unit_param):
            return None
        unit = self.unit_param.value
        if unit == p_enum.RS232PositionUnitEnum.USER_SPECIFIC.value:
            if not _ready(self.min_param, self.max_param):
                return None
            return float(self.min_param.value), float(self.max_param.value)
        return POSI_UNIT_RANGE.get(unit)

    @property
    def is_ready(self) -> bool:
        return self.range() is not None

    def from_line(self, line_value: float) -> float | None:
        rng = self.range()
        if rng is None or line_value is None:
            return None
        lo, hi = rng
        span = hi - lo
        if span == 0:
            return 0.0
        return (line_value - lo) / span * 100.0

    def to_line(self, value) -> float | None:
        rng = self.range()
        if rng is None or value is None:
            return None
        lo, hi = rng
        span = hi - lo
        if span == 0:
            return lo
        return (_as_float(value) / 100.0) * span + lo

    def decode(self, text: str):
        return self.from_line(float(text))

    def encode(self, value) -> str | None:
        line = self.to_line(value)
        return None if line is None else to_sig_str(line)


# ================================================================== 압력
class PresCodec(Codec):
    """선로 압력값 ↔ Torr.

    인터페이스 단위가 고정 단위면 그 단위의 절대값 → 단위 환산만.
    USER_SPECIFIC 이면 Value Pressure Min ~ Full Scale 눈금을 센서(mode: auto / s1 / s2)의
    Lower ~ Upper 범위(센서 Data Unit)로 선형 대응한 뒤 Torr 로 환산.
    계수 계산은 구 PresConverterManager 와 동일하되 목표 단위가 표시 단위가 아니라 Torr.
    slope(변화율) param 도 같은 변환을 쓴다 (결정 J: 현행 유지)."""

    MODE_AUTO = "auto"
    MODE_S1 = "s1"
    MODE_S2 = "s2"

    def __init__(self, name: str, mode: str,
                 iface_unit: "Parameter", iface_min: "Parameter", iface_max: "Parameter",
                 sens1: dict, sens2: dict):
        """sens1 / sens2: {"avail", "enable", "unit", "min", "max"} → Parameter | None"""
        if mode not in (self.MODE_AUTO, self.MODE_S1, self.MODE_S2):
            raise ValueError(f"pres codec mode: {mode}")
        self.name = name
        self.mode = mode
        self.iface_unit = iface_unit
        self.iface_min = iface_min
        self.iface_max = iface_max
        self.sens1 = sens1
        self.sens2 = sens2

        iface = [iface_unit, iface_min, iface_max]
        if mode == self.MODE_S1:
            ctx = iface + [sens1.get(k) for k in ("unit", "min", "max")]
        elif mode == self.MODE_S2:
            ctx = iface + [sens2.get(k) for k in ("unit", "min", "max")]
        else:
            ctx = iface + [sens1.get(k) for k in ("avail", "enable", "unit", "min", "max")] \
                        + [sens2.get(k) for k in ("avail", "enable", "unit", "min", "max")]
        self.context_params = tuple(p for p in ctx if p is not None)

    # ------------------------------------------------------------ 계수
    def coeff(self) -> tuple[float, float, float, float] | None:
        """(slope, intercept, unit_gain, unit_offset): 선로 → 센서단위 실압 → Torr. 미준비 None."""
        if not _ready(self.iface_unit, self.iface_min, self.iface_max):
            return None

        if self.iface_unit.value != p_enum.RS232PressureUnitEnum.USER_SPECIFIC.value:
            sens_unit = IFACE_TO_SENS_UNIT.get(self.iface_unit.value, p_enum.SensUnitEnum.PA.value)
            gain, offset = pressure_unit_conversion(sens_unit, DOMAIN_PRES_UNIT)
            return (1.0, 0.0, gain, offset)

        if self.mode == self.MODE_S1:
            return self._sensor_coeff(self.sens1)
        if self.mode == self.MODE_S2:
            return self._sensor_coeff(self.sens2)
        return self._auto_coeff()

    def _sensor_coeff(self, sens: dict):
        unit, lo, hi = sens.get("unit"), sens.get("min"), sens.get("max")
        if not _ready(unit, lo, hi):
            return None
        return self._make_coeff(unit.value, lo.value, hi.value)

    def _auto_coeff(self):
        flags = [self.sens1.get("avail"), self.sens1.get("enable"), self.sens2.get("avail"), self.sens2.get("enable")]
        if not _ready(*flags):
            return None

        s1_active = bool(self.sens1["avail"].value and self.sens1["enable"].value)
        s2_active = bool(self.sens2["avail"].value and self.sens2["enable"].value)

        s1 = (self.sens1.get("unit"), self.sens1.get("min"), self.sens1.get("max"))
        s2 = (self.sens2.get("unit"), self.sens2.get("min"), self.sens2.get("max"))
        if s1_active and not _ready(*s1):
            return None
        if s2_active and not _ready(*s2):
            return None

        if s1_active and s2_active:
            s1_max_pa = convert_pressure(s1[2].value, s1[0].value, p_enum.SensUnitEnum.PA.value)
            s2_max_pa = convert_pressure(s2[2].value, s2[0].value, p_enum.SensUnitEnum.PA.value)
            use_s1 = s1_max_pa >= s2_max_pa
        elif s1_active:
            use_s1 = True
        elif s2_active:
            use_s1 = False
        else:
            return self._make_coeff(p_enum.SensUnitEnum.TORR.value, 0.0, 1.0)

        sel = s1 if use_s1 else s2
        return self._make_coeff(sel[0].value, sel[1].value, sel[2].value)

    def _make_coeff(self, sens_unit, sens_min, sens_max):
        iface_min = self.iface_min.value
        iface_max = self.iface_max.value

        if iface_max == iface_min or sens_max == sens_min:
            return (1.0, 0.0, 0.0, 0.0)  # 퇴화 구성 — 기존 동작 유지

        slope = (sens_max - sens_min) / (iface_max - iface_min)
        intercept = sens_min - (slope * iface_min)
        gain, offset = pressure_unit_conversion(sens_unit, DOMAIN_PRES_UNIT)
        return (slope, intercept, gain, offset)

    @property
    def is_ready(self) -> bool:
        return self.coeff() is not None

    # ------------------------------------------------------------ 변환
    def from_line(self, line_value: float) -> float | None:
        coeff = self.coeff()
        if coeff is None or line_value is None:
            return None
        slope, intercept, gain, offset = coeff
        real = (line_value * slope) + intercept
        return (real * gain) + offset

    def to_line(self, value) -> float | None:
        coeff = self.coeff()
        if coeff is None or value is None:
            return None
        slope, intercept, gain, offset = coeff
        if slope == 0 or gain == 0:
            return None
        real = (_as_float(value) - offset) / gain
        return (real - intercept) / slope

    def decode(self, text: str):
        return self.from_line(float(text))

    def encode(self, value) -> str | None:
        line = self.to_line(value)
        return None if line is None else to_sig_str(line)
