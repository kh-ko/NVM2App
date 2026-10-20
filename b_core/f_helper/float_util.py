"""실수 비교/표시 공용 유틸 (앱 전역 정책).

장비와의 통신 값은 4byte float(유효숫자 6~7자리)로 주고받으므로, 앱 전역에서
실수 '같음' 판정은 보수적으로 유효숫자 6자리(rel_tol=1e-6) 기준으로 한다.
이보다 작은 차이는 장비가 표현할 수 없는 값이라 변경으로 볼 의미가 없다
(float32 양자화 오차를 변경으로 오판하는 것 방지). abs_tol 은 0 근처 전용
안전망이다 (상대 기준이 0 에 수렴하는 구간의 연산 잡음 흡수).

표시 문자열도 같은 정책을 따른다 — to_sig_str() 이 유효숫자 6자리 포맷의
단일 구현이고(BaseFloatLineEdit 유효숫자 모드 / codec 의 encode / RO 실수 라벨 표시 등이
쓴다), 고정 자릿수 표시는 to_str_with_decimal_places() 가 단일 구현이다(압력·위치 컨버터의
라벨·버튼 문자열 / BaseFloatLineEdit 고정 자릿수 모드 / BaseDoubleSpinBox 할당값의 사전 반올림 / RO 실수 라벨의
자릿수 모드가 쓴다 — 유효숫자 15자리로 정리한 십진값을 ROUND_HALF_UP 으로 자른다, F048).

GUI(c_values 의 is_dirty)뿐 아니라 b_core 어디서든 이 함수를 사용한다.
장비 통신 정밀도가 바뀌면(예: double) 아래 상수만 조정하면 된다.
"""

import math

from decimal import Decimal, ROUND_HALF_UP, localcontext

FLOAT_REL_TOL = 1e-6   # 유효숫자 6자리 (비교)
FLOAT_ABS_TOL = 1e-9   # 0 근처 안전망
SIG_DIGITS = 6         # 유효숫자 6자리 (표시)
SNAP_SIG_DIGITS = 15   # 단위 환산 곱셈의 마지막 비트 잡음 제거용 — float64 유효숫자(~16) 바로 아래.
                       # 더 줄이면(예: 12) 실제 자릿수를 깎고 인위적인 .5 동점을 만들어 표시 반올림이 흔들린다


def is_float_equal(a: float | None, b: float | None) -> bool:
    """유효숫자 6자리 기준 실수 비교. None 은 둘 다 None 일 때만 같음."""
    if a is None or b is None:
        return a is None and b is None

    return math.isclose(a, b, rel_tol=FLOAT_REL_TOL, abs_tol=FLOAT_ABS_TOL)


def to_sig_str(value: float | None) -> str | None:
    """유효숫자 6자리 표시 문자열 — 후행 0 없음, 지수 표기는 풀어쓴다.

    예: 0.00000123456789 -> "0.00000123457", 1234567.0 -> "1234570".
    None/해석 불가 입력은 None 을 반환한다."""
    if value is None:
        return None

    try:
        text = f"{value:.{SIG_DIGITS}g}"
        return f"{Decimal(text):f}" if "e" in text or "E" in text else text
    except Exception:
        return None


def snap_float(value: float | None) -> float | None:
    """유효숫자 15자리로 되묶어 1 ULP 잡음을 없앤다 (예: 749.9999999999999 -> 750.0).

    선로 단위 -> Torr(도메인) -> 표시 단위처럼 환산 계수를 두 번 곱하면 곱이 정확히
    1 이나 10^n 이 되지 않아 마지막 비트가 흔들린다. 그 값이 CSV/설정 파일에 그대로
    기록되거나 반올림 경계에서 표시 마지막 자리를 바꾸므로 표시 직전에 정리한다.
    None/해석 불가 입력은 None."""
    if value is None:
        return None

    try:
        return float(f"{value:.{SNAP_SIG_DIGITS}g}")
    except Exception:
        return None


def to_str_with_decimal_places(value: float | None, decimal_places: int) -> str | None:
    """고정 자릿수 표시 문자열 — 앱의 단일 구현(압력·위치 컨버터, BaseFloatLineEdit, BaseDoubleSpinBox, RO 실수 라벨이 위임).

    값을 유효숫자 15자리(SNAP_SIG_DIGITS)로 정리한 십진수로 읽고 ROUND_HALF_UP 으로 자른다 —
    장비가 보낸 십진 ASCII(위치 카운트·압력 문자열)가 기준이고, 이진 표현 잡음(2.675 → 2.67499…)이
    .5 동점의 마지막 자리를 정하지 않는다 (F048). 예: 2.675 → "2.68", 2.665 → "2.67", 0자리 2.5 → "3".
    15자리를 넘는 자릿수는 0 이 된다(예: 1234567890.123456 → "1234567890.123460") — 장비 float32 정밀도 밖이라 무해.
    반올림 결과가 0 이면 부호를 뗀다 ("-0.000" → "0.000", N081/N005). None/해석 불가 입력은 None."""
    if value is None:
        return None

    try:
        with localcontext() as ctx:
            ctx.rounding = ROUND_HALF_UP
            # quantize 는 3.4e38 같은 큰 값에서 정밀도 예외 — format 경로는 자릿수 제한이 없다
            text = format(Decimal(f"{value:.{SNAP_SIG_DIGITS}g}"), f".{decimal_places}f")
    except Exception:
        return None

    return text[1:] if text.startswith("-") and Decimal(text) == 0 else text
