"""펌웨어 FTP 저장소 접근 (UI 무관 순수 함수 — f_helper 규칙).

ver1 은 FTP 호스트/계정/경로가 윈도우 클래스 상수와 메서드 본문에 두 벌로
하드코딩되어 있었다. ver2 는 이 모듈이 단일 출처다:
- 설정은 2_resource/config/ftp_connection.json 에서 읽는다. 파일에 없는 키는
  ver1 값(DEFAULT_SETTING)으로 채운다 — 현재 배포 파일에는 FTP_HOST/FTP_PORT
  만 있으므로 계정/경로를 바꾸려면 FTP_USER/FTP_PASS/FTP_PATH 키를 추가한다.
- 저장소 파일 규칙 (ver1 과 동일):
    {FTP_PATH}/version.txt                                   버전 목록 (한 줄에 하나)
    {FTP_PATH}/{ver}/VALVE_CPU1_{ver}_FLASH.txt              RS232 어댑터용 CPU1 앱
    {FTP_PATH}/{ver}/VALVE_CPU2_{ver}_FLASH.txt              RS232 어댑터용 CPU2 앱
    {FTP_PATH}/{ver}/VALVE_CPU1_{ver}_FLASH_NEW.txt          USB 어댑터용 CPU1 앱
    {FTP_PATH}/{ver}/VALVE_CPU2_{ver}_FLASH_NEW.txt          USB 어댑터용 CPU2 앱

모든 함수는 블로킹 네트워크 I/O 다 — 반드시 워커 스레드에서 호출한다
(ver1 은 UI 스레드에서 호출해 다운로드 동안 GUI 가 멈췄다).
실패는 예외(ftplib.all_errors / OSError)로 전파하며 호출측이 메시지로 바꾼다.
"""

import ftplib
import io
import json
import os
from typing import Callable, NamedTuple

from b_core.a_define import file_folder_path as path_def


class FtpSetting(NamedTuple):
    host: str
    port: int
    user: str
    password: str
    path: str


DEFAULT_SETTING = FtpSetting(
    host="121.175.173.236",
    port=10021,
    user="novasen",
    password="nova1002",
    path="/HDD1/FIRMWARE/VALVE/BASIC",
)

VERSION_FILE = "version.txt"
CONNECT_TIMEOUT_S = 10.0

# (다운로드 누적 바이트, 전체 바이트) — 전체를 알 수 없으면 0
ProgressCallback = Callable[[int, int], None]


def load_setting() -> FtpSetting:
    """ftp_connection.json 을 읽어 FtpSetting 반환. 파일이 없거나 형식이
    깨졌으면 DEFAULT_SETTING — 없는 키만 기본값으로 보충한다."""
    try:
        with open(path_def.RSRC_FTP_SETTING_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError):
        return DEFAULT_SETTING

    if not isinstance(data, dict):
        return DEFAULT_SETTING

    try:
        port = int(data.get("FTP_PORT", DEFAULT_SETTING.port))
    except (TypeError, ValueError):
        port = DEFAULT_SETTING.port

    return FtpSetting(
        host=str(data.get("FTP_HOST", DEFAULT_SETTING.host)),
        port=port,
        user=str(data.get("FTP_USER", DEFAULT_SETTING.user)),
        password=str(data.get("FTP_PASS", DEFAULT_SETTING.password)),
        path=str(data.get("FTP_PATH", DEFAULT_SETTING.path)),
    )


def _connect(setting: FtpSetting) -> ftplib.FTP:
    ftp = ftplib.FTP()
    ftp.connect(setting.host, setting.port, timeout=CONNECT_TIMEOUT_S)
    ftp.login(setting.user, setting.password)
    return ftp


def fetch_version_list(setting: FtpSetting) -> list[str]:
    """version.txt 의 버전 문자열 목록 (빈 줄 제외, 파일 순서 유지)."""
    buffer = io.BytesIO()
    with _connect(setting) as ftp:
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


def download_firmware_files(setting: FtpSetting, version: str, is_rs232_adapter: bool,
                            dest_cpu1: str, dest_cpu2: str,
                            progress_cb: ProgressCallback | None = None) -> None:
    """CPU1/CPU2 앱 파일을 dest 경로로 내려받는다.

    - 임시 파일(.part)에 받은 뒤 os.replace 로 교체한다 — 중간 실패 시
      기존(마지막 성공) 파일이 반쯤 덮어써진 채 남지 않게 하기 위함.
      (Local Files 모드가 이 파일을 그대로 쓰므로 중요)
    - progress_cb(done, total) 은 두 파일 합산 바이트로 호출된다. 서버가
      SIZE 를 지원하지 않으면 total=0.
    - progress_cb 가 예외를 던지면 그대로 전파된다 (중단 요청 전달 경로)."""
    remote_cpu1, remote_cpu2 = remote_firmware_paths(setting, version, is_rs232_adapter)
    targets = ((remote_cpu1, dest_cpu1), (remote_cpu2, dest_cpu2))

    for _, dest in targets:
        os.makedirs(os.path.dirname(dest), exist_ok=True)

    with _connect(setting) as ftp:
        ftp.voidcmd("TYPE I")  # SIZE/RETR 을 바이너리 모드로

        total = 0
        for remote, _ in targets:
            try:
                size = ftp.size(remote)
            except ftplib.all_errors:
                size = None
            if size is None:
                total = 0
                break
            total += size

        done = 0
        for remote, dest in targets:
            part_path = dest + ".part"
            try:
                with open(part_path, "wb") as f:
                    def write_chunk(chunk: bytes):
                        nonlocal done
                        f.write(chunk)
                        done += len(chunk)
                        if progress_cb is not None:
                            progress_cb(done, total)

                    ftp.retrbinary(f"RETR {remote}", write_chunk)

                os.replace(part_path, dest)
            finally:
                if os.path.exists(part_path):
                    try:
                        os.remove(part_path)
                    except OSError:
                        pass
