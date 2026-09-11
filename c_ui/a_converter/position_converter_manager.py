"""위치 표시 보조 (도메인 = 백분율, 3단계 도메인 중립화 이후).

선로값 ↔ 백분율 변환은 g_protocol 의 PosiCodec 이 맡고 Parameter.value 는 이미 백분율이다.
이 관리자는 화면 쪽 일만 남았다:
- 소수점 자릿수(LocalSetting.posi_decimal_places) 표시 포맷
- 로컬 설정점(pfs) ↔ 백분율 변환. pfs 는 "백분율 ÷ 100" (0 닫힘 ~ 1 열림) 으로 정의한다 —
  인터페이스 단위와 무관한 물리 비율이라 저장과 표시가 서로 역함수다 (2026-09-11 사용자 결정).
  [구 코드는 저장 dp ÷ Open값, 표시 codec(Open값 × pfs) 로 식이 어긋나 0-100 외 단위에서 왕복이
  틀렸다 — 3단계에서 수정]. 설정점 버튼이 눌리면 백분율이 그대로 쓰기 값이 되고, 현재 인터페이스
  단위의 선로값(예: 0-100000 에서 100 % → 100000)은 spec 의 PosiCodec 이 만든다.
- 자릿수가 바뀌면 sig_posi_range_changed — 설정점 버튼처럼 다시 그려야 하는 화면용.
  Parameter 값은 재디코드하지 않는다.

주의: 시그널 연결 기반이므로 UI 스레드 전용이다.
"""

import threading

from decimal import Decimal
from PySide6.QtCore import Signal, QObject

from b_core.c_manager.local_setting_manager import LocalSettingManager
from b_core.f_helper.float_util import to_sig_str


class PosiConverterManager(QObject):
    _instance = None
    _creation_lock = threading.Lock()

    sig_posi_range_changed = Signal()

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
        self.posi_decimal_places = 2

        self.local_setting.sig_posi_decimal_places_changed.connect(self.handle_posi_decimal_places_changed)
        self.handle_posi_decimal_places_changed()

    # ------------------------------------------------------------ 갱신 트리거
    def handle_posi_decimal_places_changed(self):
        self.posi_decimal_places = self.local_setting.posi_decimal_places
        self.sig_posi_range_changed.emit()

    # ------------------------------------------------------------ 표시 포맷
    def format_dp(self, value: float | None) -> str | None:
        """백분율 → 고정 자릿수 문자열. None 은 None."""
        if value is None:
            return None
        fmt_spec = f".{self.posi_decimal_places}f"
        return format(Decimal(str(value)), fmt_spec)

    def parse_dp_str(self, text: str | None) -> float | None:
        if text is None:
            return None
        try:
            return float(text)
        except Exception:
            return None

    def normalize_dp_str(self, text: str | None) -> str | None:
        """화면의 백분율 문자열 → 쓰기용 도메인 값 문자열 (유효숫자 6자리). 해석 불가는 None."""
        return to_sig_str(self.parse_dp_str(text))

    # ------------------------------------------------------------ 로컬 설정점 (pfs = 백분율 ÷ 100)
    def convert_dp_to_pfs(self, display_value: float) -> float | None:
        if display_value is None:
            return None
        return display_value / 100.0

    def convert_pfs_to_dp(self, value):
        if value is None:
            return None
        return value * 100.0

    def convert_pfs_to_dp_str(self, value):
        if value is None:
            return ""
        return self.format_dp(self.convert_pfs_to_dp(value))
