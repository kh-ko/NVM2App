"""백업 파일 형식 헬퍼 (UI 무관 순수 함수 — f_helper 규칙).

형식:
  1행(헤더, 선택적): # NVM2App Backup | fw=<펌웨어 버전> | iface=<User Interface 값> | date=<일시>
  이후 각 행:        <path>.<name>, p:01<id 8자리><index hex 2자리><값>

각 행의 뒷부분은 그대로 전송 가능한 쓰기 패킷이다. 헤더 없는(구버전) 파일도
허용한다 — 복원측은 헤더가 있을 때만 장비 정보 비교를 수행한다.
"""

from datetime import datetime
from typing import Optional

HEADER_PREFIX = "# NVM2App Backup"
UNKNOWN_VALUE = "-"  # 저장 시점에 값 미확인이었음을 표시


def build_header(firmware_version, user_iface_value) -> str:
    """저장 시점의 장비 정보로 헤더 행 생성. 미확인 값은 '-' 로 기록한다."""
    fw = UNKNOWN_VALUE if firmware_version is None else str(firmware_version)
    iface = UNKNOWN_VALUE if user_iface_value is None else str(user_iface_value)
    return f"{HEADER_PREFIX} | fw={fw} | iface={iface} | date={datetime.now():%Y-%m-%d %H:%M:%S}"


def parse_header(line: str) -> Optional[dict]:
    """헤더 행 -> {"fw": ..., "iface": ..., "date": ...}. 헤더 행이 아니면 None."""
    line = line.strip()
    if not line.startswith(HEADER_PREFIX):
        return None

    info = {}
    for token in line[len(HEADER_PREFIX):].split(" | "):
        key, sep, value = token.partition("=")
        if sep:
            info[key.strip()] = value.strip()
    return info


def parse_item_line(line: str) -> Optional[tuple[str, str]]:
    """백업 항목 행 -> (표시 이름 '<path>.<name>', 쓰기 패킷). 형식 불량이면 None.

    빈 행과 주석('#') 행도 None 을 반환한다 — 호출측은 형식 불량과 구분이
    필요하면 먼저 걸러낼 것. 패킷 내용은 해석하지 않는다 (프로토콜 무관)."""
    line = line.strip()
    if not line or line.startswith("#"):
        return None

    name, separator, packet = line.rpartition(", ")
    if not separator or not name or not packet:
        return None

    return name, packet


def expected_write_response_prefix(packet: str) -> Optional[str]:
    """쓰기 요청 패킷의 성공 응답 접두어. 판정 규칙이 정의된 프로토콜만 —
    'p:01' 요청은 'p:0001' + id(8) + index(2) 로 응답한다.
    그 외 형식은 None (응답 내용 판정 안 함, 통신 오류만 확인)."""
    if packet.startswith("p:01") and len(packet) >= 14:
        return "p:0001" + packet[4:14]
    return None
