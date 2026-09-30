"""압력 표시 보조 (도메인 = Torr, 3단계 도메인 중립화 이후).

압력은 세 단위가 있고 역할이 다르다:
- 선로 단위 : 장비의 Pressure Unit param (고정 단위 또는 USER_SPECIFIC 눈금)
- 도메인 단위: Torr 고정 — Parameter.value 와 차트 내부 버퍼의 단위 (codec.DOMAIN_PRES_UNIT)
- 표시 단위 : LocalSetting.pres_unit — 위젯·차트에 보이는 단위

선로 ↔ Torr 는 g_protocol 의 PresCodec 이 맡고 (센서 기준 auto/s1/s2 는 param 의 codec 종류),
이 관리자는 화면 쪽 일만 남았다:
- Torr ↔ 표시 단위 (to_display / from_display) 와 자릿수 포맷
- 설정점 sfs(만압 대비 비율) ↔ 표시 압력 — 만압은 Value Pressure Sensor Full Scale 을 auto codec 으로 푼 Torr.
  비율은 Torr 도메인에서 정의한다(설정점 Torr = 만압 Torr × sfs, sfs = 설정점 Torr ÷ 만압 Torr)
  — 표시 단위 만압에 곱하면 오프셋 단위(psig)에서 같은 sfs 가 다른 물리 압력이 된다 (F049, 2026-09-30 결정)
- 만압 구간(get_dp_full_range) — 차트 Full 범위용. 오프셋 단위에서는 하한(0 Torr 의 표시값)이 음수다
- 단위 환산표(get_unit_conversion / convert_pressure) — 차트 분석 창, 백업 값 단위 환산용
- 변경 알림은 원인별 시그널 셋(표시 단위 / 자릿수 / 만압 문맥)으로 낸다 — 구독처가 필요한 것만 받아
  자릿수 변경에 차트 이력을 지우는 일이 없게 (설계 7위). Parameter 값은 재디코드하지 않는다.

주의: 시그널 연결 기반이므로 UI 스레드 전용이다.
"""

import threading

from decimal import Decimal

from PySide6.QtCore import Signal, QObject

from b_core.c_manager.app_log_manager import AppLogManager
from b_core.c_manager.local_setting_manager import LocalSettingManager
from b_core.c_manager.parameter_manager import ParamManager
from b_core.f_helper.float_util import snap_float
from b_core.g_protocol import codec as codec_mod
from b_core.g_protocol.spec_registry import SpecRegistry


class PresConverterManager(QObject):
    _instance = None
    _creation_lock = threading.Lock()

    sig_display_unit_changed = Signal()  # LocalSetting.pres_unit — 라벨·표시값이 바뀌고 차트 이력은 무효
    sig_decimals_changed = Signal()      # LocalSetting.pres_decimal_places — 자릿수만
    sig_full_scale_changed = Signal()    # 만압 문맥 param(Pressure Unit / Min / Full Scale / 센서 구성) 값 — 만압·설정점 환산만

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

        # 만압(Full Scale) 해석과 문맥 param 은 auto codec 이 안다.
        # codec 은 ParamManager 가 스펙을 로드할 때 SpecRegistry 에 등록되므로,
        # 생성 순서와 무관하게 여기서 로드를 보장한다 (의존하는 쪽이 의존 대상을 생성 —
        # 구 PresConverterManager 도 ParamManager() 를 직접 호출했다)
        ParamManager()
        self.codec = SpecRegistry().get_codec("pres")
        if self.codec is None:
            self._log.error("pres codec 없음 — nv2_spec.json 의 codecs 절을 확인할 것")
        else:
            for param in self.codec.context_params:
                param.sig_value_changed.connect(self.handle_full_scale_changed)

        self.local_setting.sig_pres_unit_changed.connect(self.handle_display_unit_changed)
        self.local_setting.sig_pres_decimal_places_changed.connect(self.handle_decimals_changed)

        self.pres_decimal_places = self.local_setting.pres_decimal_places

    # ------------------------------------------------------------ 갱신 트리거 (원인별 1:1 슬롯)
    def handle_display_unit_changed(self):
        self.sig_display_unit_changed.emit()

    def handle_decimals_changed(self):
        self.pres_decimal_places = self.local_setting.pres_decimal_places
        self.sig_decimals_changed.emit()

    def handle_full_scale_changed(self):
        self.sig_full_scale_changed.emit()

    # ------------------------------------------------------------ Torr <-> 표시 단위
    def _display_coeff(self) -> tuple[float, float]:
        return codec_mod.pressure_unit_conversion(codec_mod.DOMAIN_PRES_UNIT, self.local_setting.pres_unit)

    def to_display(self, torr: float | None) -> float | None:
        if torr is None:
            return None
        gain, offset = self._display_coeff()
        # 선로 -> Torr -> 표시 단위 두 번의 곱셈이 남기는 1 ULP 잡음을 정리한다 —
        # 이 값이 표시 문자열, 차트 CSV, 로컬 설정점(sfs) 에 그대로 쓰인다
        return snap_float((torr * gain) + offset)

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
        """만압의 표시값. 오프셋 단위(psig)에서는 절대 상한이 아니라 게이지값이다 —
        범위가 필요하면 get_dp_full_range() 를 쓴다 (N079)."""
        return self.to_display(self.get_dp_max_torr())

    def get_dp_full_range(self) -> tuple[float, float] | None:
        """차트 Full 범위 — (0 Torr 의 표시값, 만압 Torr 의 표시값). 오프셋 단위(psig)에서는
        하한이 음수다. 만압 미준비면 None."""
        max_torr = self.get_dp_max_torr()
        if max_torr is None:
            return None
        return self.to_display(0.0), self.to_display(max_torr)

    def get_dp_max_pres_str(self) -> str | None:
        return self._format_dp(self.get_dp_max_pres())

    # ------------------------------------------------------------ 설정점 sfs (만압 대비 비율 — Torr 도메인에서 정의)
    def sfs_to_torr(self, sfs: float | None) -> float | None:
        """sfs → 설정점 Torr (= 설정 만압 Torr × sfs). 만압 미준비면 None. 설정점 버튼이 보내는 값."""
        max_torr = self.get_dp_max_torr()
        if max_torr is None or sfs is None:
            return None
        return max_torr * sfs

    def torr_to_sfs(self, torr: float | None) -> float | None:
        """설정점 Torr → sfs. 만압 미준비면 None, 만압이 0 이면 0.0."""
        max_torr = self.get_dp_max_torr()
        if max_torr is None or torr is None:
            return None
        if max_torr == 0:
            return 0.0
        return torr / max_torr

    def convert_sfs_to_dp_pres(self, value: float) -> float | None:
        """sfs → 표시 단위 압력 (Torr 로 만든 뒤 환산한다 — 표시 단위 만압에 곱하지 않는다)."""
        return self.to_display(self.sfs_to_torr(value))

    def convert_sfs_to_dp_pres_str(self, value: float) -> str | None:
        return self._format_dp(self.convert_sfs_to_dp_pres(value))

    def convert_dp_pres_to_sfs(self, value: float) -> float | None:
        """표시 단위 압력 → sfs (Torr 로 되돌린 뒤 만압 Torr 로 나눈다)."""
        return self.torr_to_sfs(self.from_display(value))

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
