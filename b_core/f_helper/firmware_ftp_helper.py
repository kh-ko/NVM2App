"""펌웨어 FTP 저장소 접근 (UI 무관 순수 함수 — f_helper 규칙).

ver1 은 FTP 호스트/계정/경로가 윈도우 클래스 상수와 메서드 본문에 두 벌로
하드코딩되어 있었다. ver2 는 접속 정보/설정 파일 읽기를 ftp_helper 가 맡고,
이 모듈은 펌웨어 저장소의 경로 규칙과 파일 전송만 안다:
- 저장소 경로는 ftp_connection.json 의 FTP_FIRMWARE_PATH 키 (없으면 DEFAULT_PATH).
- 저장소 파일 규칙 (ver1 과 동일):
    {FTP_PATH}/version.txt                                   버전 목록 (한 줄에 하나)
    {FTP_PATH}/{ver}/VALVE_CPU1_{ver}_FLASH.txt              RS232 어댑터용 CPU1 앱
    {FTP_PATH}/{ver}/VALVE_CPU2_{ver}_FLASH.txt              RS232 어댑터용 CPU2 앱
    {FTP_PATH}/{ver}/VALVE_CPU1_{ver}_FLASH_NEW.txt          USB 어댑터용 CPU1 앱
    {FTP_PATH}/{ver}/VALVE_CPU2_{ver}_FLASH_NEW.txt          USB 어댑터용 CPU2 앱

FTP 함수(fetch_version_list / download_firmware_files)는 블로킹 네트워크 I/O 다 — 반드시 워커 스레드에서
호출한다 (ver1 은 UI 스레드에서 호출해 다운로드 동안 GUI 가 멈췄다).
실패는 예외(ftplib.all_errors / OSError)로 전파하며 호출측이 메시지로 바꾼다.

다운로드 캐시 폴더(2_resource/temp)에는 어댑터별 '마지막으로 내려받은 버전' 기록 firmware_versions.json 도 둔다
(write_version_record / read_version_record — 로컬 파일 I/O 라 UI 스레드에서 읽어도 된다). 기록은 안내용이며
워커가 다운로드 성공 뒤 따로 쓴다 — 기록 실패가 업데이트를 막지 않는다 (N053).
"""

import io
import os
from datetime import datetime

from b_core.f_helper import ftp_helper
from b_core.f_helper.ftp_helper import FtpSetting, ProgressCallback
from b_core.f_helper.json_file_helper import JsonLoadError, load_json, save_json_atomic

PATH_KEY = "FTP_FIRMWARE_PATH"
DEFAULT_PATH = "/HDD1/FIRMWARE/VALVE/BASIC"

VERSION_FILE = "version.txt"

# 다운로드 캐시 폴더(2_resource/temp)의 어댑터별 '마지막으로 내려받은 버전' 기록 — Local Files 선택 결과 행에 보인다 (N053)
VERSION_RECORD_FILE = "firmware_versions.json"


def load_setting() -> FtpSetting:
    """펌웨어 저장소용 FtpSetting (접속 정보 공통 + FTP_FIRMWARE_PATH)."""
    return ftp_helper.load_setting(PATH_KEY, DEFAULT_PATH)


def fetch_version_list(setting: FtpSetting) -> list[str]:
    """version.txt 의 버전 문자열 목록 (빈 줄 제외, 파일 순서 유지)."""
    buffer = io.BytesIO()
    with ftp_helper.connect(setting) as ftp:
        ftp.cwd(setting.path)
        ftp.retrbinary(f"RETR {VERSION_FILE}", buffer.write)

    lines = buffer.getvalue().decode("utf-8", errors="ignore").splitlines()
    return [line.strip() for line in lines if line.strip()]


def remote_firmware_paths(setting: FtpSetting, version: str, is_rs232_adapter: bool) -> tuple[str, str]:
    """(CPU1 앱 원격 경로, CPU2 앱 원격 경로). 어댑터 종류에 따라 파일명이 다르다."""
    suffix = "FLASH" if is_rs232_adapter else "FLASH_NEW"
    base = f"{setting.path}/{version}"
    return (f"{base}/VALVE_CPU1_{version}_{suffix}.txt",
            f"{base}/VALVE_CPU2_{version}_{suffix}.txt")


def _adapter_key(is_rs232_adapter: bool) -> str:
    return "RS232" if is_rs232_adapter else "USB"


def write_version_record(cache_dir: str, is_rs232_adapter: bool, version: str) -> None:
    """캐시 폴더의 firmware_versions.json 에 어댑터별 {version, downloaded} 를 기록한다 (다른 어댑터의 기록은 유지).
    손상된 기록 파일은 새로 쓴다 — 기록은 안내용이지 다운로드의 조건이 아니다."""
    path = os.path.join(cache_dir, VERSION_RECORD_FILE)
    try:
        record = load_json(path, expect=dict) or {}
    except JsonLoadError:
        record = {}
    record[_adapter_key(is_rs232_adapter)] = {"version": version,
                                              "downloaded": datetime.now().strftime("%Y-%m-%d %H:%M")}
    save_json_atomic(path, record)


def read_version_record(cache_dir: str, is_rs232_adapter: bool) -> dict | None:
    """어댑터별 기록 {"version", "downloaded"} — 없거나 손상이면 None."""
    try:
        record = load_json(os.path.join(cache_dir, VERSION_RECORD_FILE), expect=dict)
    except JsonLoadError:
        return None
    entry = (record or {}).get(_adapter_key(is_rs232_adapter))
    if not isinstance(entry, dict) or "version" not in entry or "downloaded" not in entry:
        return None
    return entry


def download_firmware_files(setting: FtpSetting, version: str, is_rs232_adapter: bool,
                            dest_cpu1: str, dest_cpu2: str,
                            progress_cb: ProgressCallback | None = None) -> None:
    """CPU1/CPU2 앱 파일을 dest 경로로 내려받는다.

    - 두 파일을 모두 임시 파일(.part)로 받은 뒤에만 두 os.replace 를 연속 수행한다 — 전송이 하나라도 실패하면
      둘 다 폐기해 캐시에 '새 CPU1 + 옛 CPU2' 같은 버전 불일치 쌍이 남지 않게 한다 (Local Files 모드가 그 쌍을
      그대로 굽는다, N053). 두 번째 교체가 실패하면(백신 순간 잠금 등) 첫 번째를 되돌릴 수 없으므로 CPU1 을 지워
      반쪽 쌍 대신 '파일 없음' 상태로 둔다 — Local Files 사전 검사가 거부한다.
    - 버전 기록(write_version_record)은 호출측(워커)이 성공 뒤 따로 쓴다.
    - progress_cb(done, total) 은 두 파일 합산 바이트로 호출된다. 서버가
      SIZE 를 지원하지 않으면 total=0.
    - progress_cb 가 예외를 던지면 그대로 전파된다 (중단 요청 전달 경로)."""
    remote_cpu1, remote_cpu2 = remote_firmware_paths(setting, version, is_rs232_adapter)
    targets = ((remote_cpu1, dest_cpu1), (remote_cpu2, dest_cpu2))
    parts = [dest + ".part" for _, dest in targets]

    for _, dest in targets:
        os.makedirs(os.path.dirname(dest), exist_ok=True)

    try:
        with ftp_helper.connect(setting) as ftp:
            ftp.voidcmd("TYPE I")  # SIZE/RETR 을 바이너리 모드로

            # 두 파일 중 하나라도 크기를 모르면 전체 미상(0)
            sizes = [ftp_helper.remote_size(ftp, remote) for remote, _ in targets]
            total = sum(sizes) if all(sizes) else 0

            done = 0
            for (remote, _), part_path in zip(targets, parts):
                with open(part_path, "wb") as f:
                    def write_chunk(chunk: bytes):
                        nonlocal done
                        f.write(chunk)
                        done += len(chunk)
                        if progress_cb is not None:
                            progress_cb(done, total)

                    ftp.retrbinary(f"RETR {remote}", write_chunk)

        # 둘 다 받았을 때만 교체 — 연속 두 번. 두 번째가 실패하면 CPU1 을 지워 반쪽 쌍을 남기지 않는다
        os.replace(parts[0], dest_cpu1)
        try:
            os.replace(parts[1], dest_cpu2)
        except OSError:
            try:
                os.remove(dest_cpu1)
            except OSError:
                pass
            raise
    finally:
        for part_path in parts:
            if os.path.exists(part_path):
                try:
                    os.remove(part_path)
                except OSError:
                    pass
