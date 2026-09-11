"""압력 표시 보조 (도메인 = Torr, 3단계 도메인 중립화 이후).

압력은 세 단위가 있고 역할이 다르다:
- 선로 단위 : 장비의 Pressure Unit param (고정 단위 또는 USER_SPECIFIC 눈금)
- 도메인 단위: Torr 고정 — Parameter.value 와 차트 내부 버퍼의 단위 (codec.DOMAIN_PRES_UNIT)
- 표시 단위 : LocalSetting.pres_unit — 위젯·차트에 보이는 단위

선로 ↔ Torr 는 g_protocol 의 PresCodec 이 맡고 (센서 기준 auto/s1/s2 는 param 의 codec 종류),
이 관리자는 화면 쪽 일만 남았다:
- Torr ↔ 표시 단위 (to_display / from_display) 와 자릿수 포맷
- sfs(만압 대비 비율) ↔ 표시 압력 — 만압은 Value Pressure Sensor Full Scale 을 auto codec 으로 푼 값
- 단위 환산표(get_unit_conversion / convert_pressure) — 차트 분석 창, 백업 값 단위 환산용
- 문맥 param 이나 표시 단위·자릿수가 바뀌면 sig_pres_range_changed. Parameter 값은 재디코드하지 않는다.

주의: 시그널 연결 기반이므로 UI 스레드 전용이다.
"""

import threading

from decimal import Decimal

from PySide6.QtCore import Signal, QObject

from b_core.c_manager.app_log_manager import AppLogManager
from b_core.c_manager.local_setting_manager import LocalSettingManager
from b_core.f_helper.float_util import to_sig_str
from b_core.g_protocol import codec as codec_mod
from b_core.g_protocol.spec_registry import SpecRegistry


class PresConverterManager(QObject):
    _instance = None
    _creation_lock = threading.Lock()

    sig_pres_range_changed = Signal()

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
        self._log = AppLogManager().get_logger("PresConverterManager", is_global=True)
        self.local_setting = LocalSettingManager()
        self.pres_decimal_places = 6

        # 만압(Full Scale) 해석과 문맥 param 은 auto codec 이 안다
        self.codec = SpecRegistry().get_codec("pres")
        if self.codec is None:
            self._log.error("pres codec 없음 — nv2_spec.json 의 codecs 절을 확인할 것")
        else:
            for param in self.codec.context_params:
                param.sig_value_changed.connect(self.handle_sens_cfg_changed)

        self.local_setting.sig_pres_unit_changed.connect(self.handle_sens_cfg_changed)
        self.local_setting.sig_pres_decimal_places_changed.connect(self.handle_pres_decimal_places_changed)

        self.handle_pres_decimal_places_changed()

    # ------------------------------------------------------------ 갱신 트리거
    def handle_pres_decimal_places_changed(self):
        self.pres_decimal_places = self.local_setting.pres_decimal_places
        self.sig_pres_range_changed.emit()

    def handle_sens_cfg_changed(self):
        self.sig_pres_range_changed.emit()

    # ------------------------------------------------------------ Torr <-> 표시 단위
    def _display_coeff(self) -> tuple[float, float]:
        return codec_mod.pressure_unit_conversion(codec_mod.DOMAIN_PRES_UNIT, self.local_setting.pres_unit)

    def to_display(self, torr: float | None) -> float | None:
        if torr is None:
            return None
        gain, offset = self._display_coeff()
        return (torr * gain) + offset

    def to_display_str(self, torr: float | None) -> str | None:
        return self._format_dp(self.to_display(torr))

    def from_display(self, value: float | None) -> float | None:
        if value is None:
            return None
        gain, offset = self._display_coeff()
        if gain == 0:
            return None
        return (value - offset) / gain

    def from_display_str(self, display_value: str | None) -> float | None:
        if display_value is None:
            return None
        try:
            dp_value = float(display_value)
        except Exception:
            return None
        return self.from_display(dp_value)

    def convert_dp_str_to_domain_str(self, display_value: str | None) -> str | None:
        """화면 문자열(표시 단위) → 쓰기용 도메인 값 문자열(Torr, 유효숫자 6자리). 해석 불가는 None."""
        return to_sig_str(self.from_display_str(display_value))

    # ------------------------------------------------------------ 만압 (Full Scale)
    def get_dp_max_iface(self) -> float | None:
        return self.codec.iface_max.value if self.codec is not None and self.codec.iface_max is not None else None

    def get_dp_max_torr(self) -> float | None:
        """Value Pressure Sensor Full Scale(선로 눈금)을 auto codec 으로 푼 Torr. 미준비면 None."""
        iface_max = self.get_dp_max_iface()
        if iface_max is None or self.codec is None:
            return None
        return self.codec.from_line(iface_max)

    def get_dp_max_pres(self) -> float | None:
        return self.to_display(self.get_dp_max_torr())

    def get_dp_max_pres_str(self) -> str | None:
        return self._format_dp(self.get_dp_max_pres())

    # ------------------------------------------------------------ sfs <-> 표시 압력
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
        """표시 단위 값 -> 표시 문자열 (LocalSetting 의 소수점 자리수 적용)."""
        if value is None:
            return None
        fmt_spec = f".{self.pres_decimal_places}f"
        return format(Decimal(str(value)), fmt_spec)

    # ------------------------------------------------------------ 단위 환산 (공개 API)
    # 통신 상태와 무관한 정적 계산이므로 외부(차트 분석 윈도우 등)에서도 사용한다.
    def convert_pressure(self, value: float, from_unit_idx: int, to_unit_idx: int) -> float:
        return codec_mod.convert_pressure(value, from_unit_idx, to_unit_idx)

    def get_unit_conversion(self, from_unit_idx: int, to_unit_idx: int) -> tuple[float, float]:
        """단위 변환의 (gain, offset). Pa 경유 환산이며 PSIG 는 대기압 오프셋 보정."""
        return codec_mod.pressure_unit_conversion(from_unit_idx, to_unit_idx)
