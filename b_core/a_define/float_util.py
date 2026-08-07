"""실수 비교 공용 유틸 (앱 전역 정책).

장비와의 통신 값은 4byte float(유효숫자 6~7자리)로 주고받으므로, 앱 전역에서
실수 '같음' 판정은 보수적으로 유효숫자 6자리(rel_tol=1e-6) 기준으로 한다.
이보다 작은 차이는 장비가 표현할 수 없는 값이라 변경으로 볼 의미가 없다
(float32 양자화 오차를 변경으로 오판하는 것 방지). abs_tol 은 0 근처 전용
안전망이다 (상대 기준이 0 에 수렴하는 구간의 연산 잡음 흡수).

GUI(c_values 의 is_dirty)뿐 아니라 b_core 어디서든 이 함수를 사용한다.
장비 통신 정밀도가 바뀌면(예: double) 아래 상수만 조정하면 된다.
"""

import math

FLOAT_REL_TOL = 1e-6   # 유효숫자 6자리
FLOAT_ABS_TOL = 1e-9   # 0 근처 안전망


def is_float_equal(a: float | None, b: float | None) -> bool:
    """유효숫자 6자리 기준 실수 비교. None 은 둘 다 None 일 때만 같음."""
    if a is None or b is None:
        return a is None and b is None

    return math.isclose(a, b, rel_tol=FLOAT_REL_TOL, abs_tol=FLOAT_ABS_TOL)
