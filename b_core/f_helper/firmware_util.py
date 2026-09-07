"""펌웨어 버전 문자열 처리 유틸 (UI 무관 순수 함수 — f_helper 규칙).

장비 펌웨어 버전은 "x.y.z" 문자열로 통신되며, 버전 비교는 각 자리를
hex 한 자리로 이어 붙인 16진수 코드로 한다 (예: "6.5.5" -> 0x655).
"""


def to_version_code(version_str) -> int | None:
    """"x.y.z" 버전 문자열 -> 비교용 16진수 코드 (예: "6.5.5" -> 0x655).

    None 이나 형식 불량 문자열은 None 반환 — 호출측이 '버전 미확인' 으로
    처리한다 (예외 대신 None 을 쓰는 것은 float_util 과 같은 관례)."""
    if version_str is None:
        return None

    # 유효 형식은 숫자와 점 뿐 — 점을 제거한 결과가 전부 숫자가 아니면
    # 형식 불량이다 ("abc" 같은 문자열이 hex 로 오파싱되는 것을 막는다)
    digits = str(version_str).replace(".", "")
    if not digits.isdigit():
        return None

    return int(digits, 16)
