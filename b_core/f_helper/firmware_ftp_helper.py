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

모든 함수는 블로킹 네트워크 I/O 다 — 반드시 워커 스레드에서 호출한다
(ver1 은 UI 스레드에서 호출해 다운로드 동안 GUI 가 멈췄다).
실패는 예외(ftplib.all_errors / OSError)로 전파하며 호출측이 메시지로 바꾼다.
"""

import io
import os

from b_core.f_helper import ftp_helper
from b_core.f_helper.ftp_helper import FtpSetting, ProgressCallback

PATH_KEY = "FTP_FIRMWARE_PATH"
DEFAULT_PATH = "/HDD1/FIRMWARE/VALVE/BASIC"

VERSION_FILE = "version.txt"


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

    with ftp_helper.connect(setting) as ftp:
        ftp.voidcmd("TYPE I")  # SIZE/RETR 을 바이너리 모드로

        # 두 파일 중 하나라도 크기를 모르면 전체 미상(0)
        sizes = [ftp_helper.remote_size(ftp, remote) for remote, _ in targets]
        total = sum(sizes) if all(sizes) else 0

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
