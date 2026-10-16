"""앱 임시 폴더 정리 (UI 무관 순수 함수 — f_helper 규칙).

앱의 임시 파일은 path_def.APP_TEMP_PATH(%TEMP%\\NVM2App) 아래에 둔다 — 가치가 없어진 뒤 지워도 되는 것만.
지금은 앱 업데이트의 zip·압축 해제본·설치 스크립트(APP_TEMP_UPDATE_PATH)가 전부다. 차트 기록은 사용자 데이터라
여기 두지 않는다 (path_def.CHART_RECORD_PATH, 앱 폴더).

설치가 끝까지 가면 설치 스크립트가 패키지와 자기 자신을 지우지만, 다운로드 뒤 설치로 못 간 경로(창이 닫기를 거부 등),
스크립트의 실패 종료, 전원 차단은 잔재를 남긴다. 그래서 앱이 켜질 때 한 번 오래된 것을 지운다 (main.py).

STALE_AFTER_SEC 를 넘긴 항목만 지우는 이유: 업데이트 직후 재실행된 새 앱이 켜지는 순간, 설치 스크립트가 아직 자기
패키지·스크립트 파일을 지우는 중일 수 있다. 방금 만들어진 것은 건드리지 않으면 그 겹침이 없다.
"""

import os
import shutil
import time

from b_core.a_define import file_folder_path as path_def

STALE_AFTER_SEC = 3600   # 지난 실행의 잔재로 보는 기준 — 설치 스크립트의 재실행 대기(5초)·정리보다 넉넉히


def sweep_stale_update_files(now: float | None = None) -> tuple[int, int]:
    """APP_TEMP_UPDATE_PATH 바로 아래 항목 중 수정 시각이 STALE_AFTER_SEC 를 넘긴 것을 지운다 (폴더는 통째로).

    (지운 수, 실패 수) 를 돌려준다. 폴더가 없으면 (0, 0). 예외는 밖으로 내지 않는다 — 기동을 막지 않는다.
    경로는 호출 시점에 path_def 에서 읽는다 (하네스 isolate_runtime 이 바꿔 끼운다)."""
    root = path_def.APP_TEMP_UPDATE_PATH
    try:
        entries = os.listdir(root)
    except OSError:
        return 0, 0

    now = time.time() if now is None else now
    removed = failed = 0
    for name in entries:
        path = os.path.join(root, name)
        try:
            if now - os.path.getmtime(path) <= STALE_AFTER_SEC:
                continue
            if os.path.isdir(path):
                shutil.rmtree(path)
            else:
                os.remove(path)
            removed += 1
        except OSError:
            failed += 1
    return removed, failed
