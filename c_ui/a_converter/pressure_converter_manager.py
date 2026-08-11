"""압력 값 변환 관리자.

압력은 세 가지 표현이 있고, 이 관리자가 상호 변환을 담당한다:
- iface : 통신(장비 인터페이스)에서 사용하는 압력 값
- dp    : GUI 에 표시하는 압력 값 (LocalSetting 의 표시 단위/소수점 자리수 적용)
- sfs   : Full Scale 비율 (0.0 ~ 1.0, 1.0 = 압력 센서 Max)

변환 파이프라인:
    iface --(slope, intercept)--> 센서 단위의 실제 압력 --(unit_gain, unit_offset)--> dp

slope/intercept/unit_gain/unit_offset 은 관련 param(인터페이스 스케일링,
센서 1/2 구성)과 로컬 설정(표시 단위)이 바뀔 때마다 재계산되고,
재계산 시 sig_pres_range_changed 가 발화된다 (UI 갱신 트리거).

주의: 시그널 연결 기반이므로 UI 스레드 전용이다.
"""

import threading

from decimal import Decimal

from PySide6.QtCore import Signal, QObject

from b_core.b_datatype import param_enum as p_enum
from b_core.c_manager.parameter_manager import ParamManager
from b_core.c_manager.local_setting_manager import LocalSettingManager

from c_ui.a_converter.float_converter_manager import FloatConverterManager


class PresConverterManager(QObject):
    _instance = None
    _creation_lock = threading.Lock()

    sig_pres_range_changed = Signal()

    # 단위 -> Pa 환산 계수
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

    def __new__(cls, *args, **kwargs):
        # 멀티스레드 환경에서 동시에 생성되는 것을 방지
        with cls._creation_lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        # 중복 초기화 방어
        if self._initialized:
            return

        super().__init__()

        self._initialized = True
        self.local_setting = LocalSettingManager()
        self.float_converter = FloatConverterManager()

        self.slope = 1.0
        self.intercept = 0.0
        self.unit_gain = 0.0
        self.unit_offset = 0.0
        self.pres_decimal_places = 6

        pm = ParamManager()
        self.iface_unit_param      = pm.get_by_full_path("Interface.Scaling.Pressure.Pressure Unit")
        self.iface_min_param       = pm.get_by_full_path("Interface.Scaling.Pressure.Value Pressure Min")
        self.iface_max_param       = pm.get_by_full_path("Interface.Scaling.Pressure.Value Pressure Sensor Full Scale")

        self.sens1_avail_param     = pm.get_by_full_path("Sensor.Sensor 1.Basic.Available")
        self.sens1_enable_param    = pm.get_by_full_path("Sensor.Sensor 1.Basic.Enable")
        self.sens1_unit_param      = pm.get_by_full_path("Sensor.Sensor 1.Range.Data Unit")
        self.sens1_min_value_param = pm.get_by_full_path("Sensor.Sensor 1.Range.Lower Limit Data Value")
        self.sens1_max_value_param = pm.get_by_full_path("Sensor.Sensor 1.Range.Upper Limit Data Value")

        self.sens2_avail_param     = pm.get_by_full_path("Sensor.Sensor 2.Basic.Available")
        self.sens2_enable_param    = pm.get_by_full_path("Sensor.Sensor 2.Basic.Enable")
        self.sens2_unit_param      = pm.get_by_full_path("Sensor.Sensor 2.Range.Data Unit")
        self.sens2_min_value_param = pm.get_by_full_path("Sensor.Sensor 2.Range.Lower Limit Data Value")
        self.sens2_max_value_param = pm.get_by_full_path("Sensor.Sensor 2.Range.Upper Limit Data Value")

        # 재계산 조건이 되는 param 목록 — 준비 검사는 실제 필요 관계에 따라 분기별로 한다:
        #   iface 3종: 항상 필요
        #   센서 활성 플래그: USER_SPECIFIC 모드에서만 필요
        #   센서 상세(단위/min/max): USER_SPECIFIC + 해당 센서가 활성일 때만 필요
        #   (미장착/비활성 센서의 상세 param 은 장비가 지원하지 않아 None 일 수 있음)
        self._iface_params = [self.iface_unit_param, self.iface_min_param, self.iface_max_param]
        self._sens_flag_params = [self.sens1_avail_param, self.sens1_enable_param,
                                  self.sens2_avail_param, self.sens2_enable_param]
        self._sens1_detail_params = [self.sens1_unit_param, self.sens1_min_value_param, self.sens1_max_value_param]
        self._sens2_detail_params = [self.sens2_unit_param, self.sens2_min_value_param, self.sens2_max_value_param]

        # 스키마에 없는 param 은 ParamManager 가 오류 로그를 남기고 None 을 반환한다.
        # 크래시 대신 해당 param 만 제외하고 동작한다 (준비 검사에서 미준비로 취급됨).
        all_params = (self._iface_params + self._sens_flag_params
                      + self._sens1_detail_params + self._sens2_detail_params)
        for param in all_params:
            if param is not None:
                param.sig_value_changed.connect(self.handle_sens_cfg_changed)

        self.local_setting.sig_pres_unit_changed.connect(self.handle_sens_cfg_changed)
        self.local_setting.sig_pres_decimal_places_changed.connect(self.handle_pres_decimal_places_changed)

        self.handle_pres_decimal_places_changed()
        self.handle_sens_cfg_changed()

    # ------------------------------------------------------------ 재계산
    def handle_pres_decimal_places_changed(self):
        self.pres_decimal_places = self.local_setting.pres_decimal_places
        self.sig_pres_range_changed.emit()

    def handle_sens_cfg_changed(self):
        # 항상 필요한 인터페이스 param 준비 검사
        if any(p is None or p.value is None for p in self._iface_params):
            return

        if self.iface_unit_param.value == p_enum.RS232PressureUnitEnum.USER_SPECIFIC.value:
            # USER_SPECIFIC 모드는 센서 구성이 필요 — 활성 플래그부터 확인
            if any(p is None or p.value is None for p in self._sens_flag_params):
                return

            s1_active = bool(self.sens1_avail_param.value and self.sens1_enable_param.value)
            s2_active = bool(self.sens2_avail_param.value and self.sens2_enable_param.value)

            # 활성 센서의 상세 param 만 준비되면 된다 (비활성 센서는 None 이어도 무관)
            if s1_active and any(p is None or p.value is None for p in self._sens1_detail_params):
                return
            if s2_active and any(p is None or p.value is None for p in self._sens2_detail_params):
                return

            iface_min = self.iface_min_param.value
            iface_max = self.iface_max_param.value
            sens_unit, sens_min, sens_max = self._select_active_sensor(s1_active, s2_active)

            if iface_max == iface_min or sens_max == sens_min:
                self.slope = 1.0
                self.intercept = 0.0
                self.unit_gain = 0.0
                self.unit_offset = 0.0
            else:
                self.slope = (sens_max - sens_min) / (iface_max - iface_min)
                self.intercept = sens_min - (self.slope * iface_min)
                self.unit_gain, self.unit_offset = self.get_unit_conversion(sens_unit, self.local_setting.pres_unit)
        else:
            self.slope = 1.0
            self.intercept = 0.0
            iface_unit = self.IFACE_TO_SENS_UNIT.get(self.iface_unit_param.value, p_enum.SensUnitEnum.PA.value)
            self.unit_gain, self.unit_offset = self.get_unit_conversion(iface_unit, self.local_setting.pres_unit)

        # UI 갱신 등을 위한 시그널 발생
        self.sig_pres_range_changed.emit()

    def _select_active_sensor(self, s1_active: bool, s2_active: bool) -> tuple[int, float, float]:
        """활성 센서의 (단위, min, max) 선택. 둘 다 활성이면 Max 압력(Pa 환산)이 큰 쪽."""
        if s1_active and s2_active:
            s1_max_pa = self.convert_pressure(self.sens1_max_value_param.value, self.sens1_unit_param.value, p_enum.SensUnitEnum.PA.value)
            s2_max_pa = self.convert_pressure(self.sens2_max_value_param.value, self.sens2_unit_param.value, p_enum.SensUnitEnum.PA.value)
            use_sens1 = s1_max_pa >= s2_max_pa
        elif s1_active:
            use_sens1 = True
        elif s2_active:
            use_sens1 = False
        else:
            return p_enum.SensUnitEnum.TORR.value, 0.0, 1.0

        if use_sens1:
            return (self.sens1_unit_param.value,
                    self.sens1_min_value_param.value,
                    self.sens1_max_value_param.value)

        return (self.sens2_unit_param.value,
                self.sens2_min_value_param.value,
                self.sens2_max_value_param.value)

    def get_dp_max_iface(self) -> float | None:
        return self.iface_max_param.value

    # ------------------------------------------------------------ 변환 (iface <-> dp)
    def get_dp_max_pres(self) -> float | None:
        return self.convert_iface_pres_to_dp_pres(self.iface_max_param.value)

    def get_dp_max_pres_str(self) -> str | None:
        return self._format_dp(self.get_dp_max_pres())

    def convert_iface_pres_to_dp_pres(self, ori_value: float) -> float | None:
        if ori_value is None:
            return None

        real_pres_in_sens_unit = (ori_value * self.slope) + self.intercept
        return (real_pres_in_sens_unit * self.unit_gain) + self.unit_offset

    def convert_iface_pres_to_dp_pres_str(self, ori_value: float) -> str | None:
        return self._format_dp(self.convert_iface_pres_to_dp_pres(ori_value))

    def convert_dp_pres_str_to_iface_pres(self, display_value: str) -> float | None:
        if display_value is None:
            return None

        try:
            dp_value = float(display_value)
        except Exception:
            return None

        return self.convert_dp_pres_to_iface_pres(dp_value)

    def convert_dp_pres_str_to_iface_pres_str(self, display_value: str) -> str | None:
        if display_value is None:
            return None

        try:
            dp_value = float(display_value)
        except Exception:
            return None

        return self.convert_dp_pres_to_iface_pres_str(dp_value)

    def convert_dp_pres_to_iface_pres(self, value: float) -> float | None:
        if self.slope == 0 or self.unit_gain == 0 or value is None:
            return None

        real_pres_in_sens_unit = (value - self.unit_offset) / self.unit_gain
        return (real_pres_in_sens_unit - self.intercept) / self.slope

    def convert_dp_pres_to_iface_pres_str(self, value: float) -> str | None:
        result_value = self.convert_dp_pres_to_iface_pres(value)

        if result_value is None:
            return None

        return self.float_converter.to_str(result_value)

    # ------------------------------------------------------------ 변환 (sfs <-> dp)
    def convert_sfs_to_dp_pres(self, value: float) -> float | None:
        pres_max = self.get_dp_max_pres()

        if pres_max is None or value is None:
            return None

        return pres_max * value

    def convert_sfs_to_dp_pres_str(self, value: float) -> str | None:
        return self._format_dp(self.convert_sfs_to_dp_pres(value))

    def convert_dp_pres_to_sfs(self, value: float) -> float | None:
        pres_max = self.get_dp_max_pres()

        if pres_max is None or value is None:
            return None

        if pres_max == 0:
            return 0.0
        return value / pres_max

    def convert_dp_pres_str_to_sfs(self, value: str) -> float | None:
        try:
            float_value = float(value)
        except Exception:
            return None

        return self.convert_dp_pres_to_sfs(float_value)

    # ------------------------------------------------------------ 내부 공통
    def _format_dp(self, value: float | None) -> str | None:
        """dp 값 -> 표시 문자열 (LocalSetting 의 소수점 자리수 적용)."""
        if value is None:
            return None

        fmt_spec = f".{self.pres_decimal_places}f"
        return format(Decimal(str(value)), fmt_spec)

    # ------------------------------------------------------------ 단위 환산 (공개 API)
    # 통신 상태와 무관한 정적 계산이므로 외부(차트 분석 윈도우 등)에서도 사용한다.
    def convert_pressure(self, value: float, from_unit_idx: int, to_unit_idx: int) -> float:
        gain, offset = self.get_unit_conversion(from_unit_idx, to_unit_idx)
        return (value * gain) + offset

    def get_unit_conversion(self, from_unit_idx: int, to_unit_idx: int) -> tuple[float, float]:
        """단위 변환의 (gain, offset). Pa 경유 환산이며 PSIG 는 대기압 오프셋 보정."""
        from_factor = self.PA_FACTORS.get(from_unit_idx, 1.0)
        to_factor = self.PA_FACTORS.get(to_unit_idx, 1.0)

        gain = from_factor / to_factor
        offset = 0.0

        if from_unit_idx == p_enum.SensUnitEnum.PSIG.value and to_unit_idx != p_enum.SensUnitEnum.PSIG.value:
            offset = self.ATM_PA / to_factor
        elif from_unit_idx != p_enum.SensUnitEnum.PSIG.value and to_unit_idx == p_enum.SensUnitEnum.PSIG.value:
            offset = -self.ATM_PA / to_factor

        return gain, offset
