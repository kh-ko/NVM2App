"""JSON 설정 파일 읽기/쓰기 공통 (UI 무관 순수 함수 — f_helper 규칙).

local_setting.json / connections.json 처럼 값이 바뀔 때마다 통째로 다시 쓰는 작은
설정 파일용이다. 로거·시그널 없음 — 실패는 예외로 올리고 로그/기본값 처리는 호출자 몫.

- save_json_atomic(): 같은 폴더의 임시 파일에 쓰고 flush + fsync 한 뒤 os.replace 로
  바꿔 넣는다. 기록 도중 정전·강제 종료가 나도 파일은 '이전 내용 전체' 아니면
  '새 내용 전체' 둘 중 하나다. (제자리 'w' 쓰기는 0바이트/반쪽 JSON 을 남겨 다음 기동에서
  기본값이 확정된다 — 2차 보고서 F010) Windows 에서 백신/동기화 폴더가 파일을 순간
  잠그면 os.replace 가 PermissionError 를 내므로 짧게 세 번(50/100/200ms) 더 시도한다.
- load_json(): 파일이 없으면 None. BOM(utf-8-sig)은 수용한다. 깨졌거나 최상위 형태가
  expect 와 다르면 JsonLoadError(사유).
- quarantine_corrupt(): 손상 파일을 '<이름>.corrupt-YYYYMMDD-HHMMSS' 로 옮겨 증거를
  남기고, 다음 저장이 깨끗한 파일로 시작하게 한다. 옮긴 경로를 돌려준다(실패 시 None).
"""

import json
import os
import tempfile
import time
from datetime import datetime


class JsonLoadError(Exception):
    """파일이 있는데 읽을 수 없거나(깨진 JSON, 인코딩) 최상위 형태가 기대와 다르다."""


def load_json(path: str, expect: type = dict):
    """path 의 JSON 을 읽어 돌려준다. 파일이 없으면 None.

    깨졌거나 최상위가 expect 타입이 아니면 JsonLoadError."""
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8-sig") as f:
            data = json.load(f)
    except (OSError, ValueError, RecursionError) as e:  # JSONDecodeError/UnicodeDecodeError 는 ValueError, 과도한 중첩은 RecursionError
        raise JsonLoadError(f"{os.path.basename(path)}: {e}") from e
    if not isinstance(data, expect):
        raise JsonLoadError(f"{os.path.basename(path)}: top-level must be "
                            f"{expect.__name__}, got {type(data).__name__}")
    return data


def save_json_atomic(path: str, data, *, indent: int = 4, ensure_ascii: bool = True) -> None:
    """data 를 path 에 원자적으로 저장한다. 실패는 예외로 올린다(임시 파일은 정리)."""
    folder = os.path.dirname(path) or "."
    os.makedirs(folder, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=os.path.basename(path) + ".", suffix=".tmp", dir=folder)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=indent, ensure_ascii=ensure_ascii)
            f.flush()
            os.fsync(f.fileno())
        for delay in (0.05, 0.1, 0.2, None):
            try:
                os.replace(tmp, path)
                break
            except PermissionError:
                if delay is None:
                    raise
                time.sleep(delay)
    except BaseException:
        try:
            os.remove(tmp)
        except OSError:
            pass
        raise


def quarantine_corrupt(path: str) -> str | None:
    """손상 파일을 옆으로 옮겨 보관하고 그 경로를 돌려준다. 없거나 옮기지 못하면 None."""
    if not os.path.exists(path):
        return None
    target = f"{path}.corrupt-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    try:
        os.replace(path, target)
        return target
    except OSError:
        return None
