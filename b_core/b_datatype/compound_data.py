from typing import NamedTuple

# 클래스 바깥이나 별도 파일에 정의
class CompoundData(NamedTuple):
    timestamp: int
    access_mode: int
    control_mode: int
    act_posi: float
    act_pres: float
    target_posi: float
    target_pres: float
    speed: float
    pres_contoller_selector: int
    warning_bitmap: int
    error_bitmap: int
    error_number: int
    error_code: int