"""FTP 서버 접속 공통 (UI 무관 순수 함수 — f_helper 규칙).

펌웨어 저장소(firmware_ftp_helper)와 앱 배포 저장소(app_update_helper)는 같은
FTP 서버/계정을 쓰고 저장소 경로만 다르다. 접속 정보와 설정 파일 읽기는 이
모듈이 단일 출처이고, 각 저장소 모듈은 자기 경로 키만 넘겨 load_setting() 을
호출한다:

    firmware : load_setting("FTP_PATH",     "/HDD1/FIRMWARE/VALVE/BASIC")
    app      : load_setting("FTP_APP_PATH", "/HDD1/NVM2App")

설정 파일 2_resource/config/ftp_connection.json 의 키:
    FTP_HOST / FTP_PORT / FTP_USER / FTP_PASS   접속 정보 (공통)
    FTP_PATH / FTP_APP_PATH ...                 저장소별 경로
파일에 없는 키는 ver1 하드코딩 값(DEFAULT_CONNECTION)으로 채운다 — 현재 배포
파일에는 FTP_HOST/FTP_PORT 만 있다.

connect() 는 블로킹 네트워크 I/O 다 — 워커 스레드에서 호출한다.
"""

import ftplib
import json
from typing import Callable, NamedTuple

from b_core.a_define import file_folder_path as path_def


class FtpSetting(NamedTuple):
    host: str
    port: int
    user: str
    password: str
    path: str  # 저장소 루트 경로 (호출한 모듈의 path_key 값)


# 접속 정보 기본값 (ver1 과 동일). path 는 저장소 모듈이 채운다
DEFAULT_CONNECTION = FtpSetting(
    host="121.175.173.236",
    port=10021,
    user="novasen",
    password="nova1002",
    path="/",
)

CONNECT_TIMEOUT_S = 10.0

# (누적 바이트, 전체 바이트) — 전체를 알 수 없으면 0
ProgressCallback = Callable[[int, int], None]


def load_setting(path_key: str, default_path: str) -> FtpSetting:
    """ftp_connection.json 을 읽어 FtpSetting 반환. path 는 path_key 의 값이고,
    파일이 없거나 형식이 깨졌거나 키가 없으면 기본값으로 보충한다."""
    default = DEFAULT_CONNECTION._replace(path=default_path)
    try:
        with open(path_def.RSRC_FTP_SETTING_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError):
        return default

    if not isinstance(data, dict):
        return default

    try:
        port = int(data.get("FTP_PORT", default.port))
    except (TypeError, ValueError):
        port = default.port

    return FtpSetting(
        host=str(data.get("FTP_HOST", default.host)),
        port=port,
        user=str(data.get("FTP_USER", default.user)),
        password=str(data.get("FTP_PASS", default.password)),
        path=str(data.get(path_key, default.path)),
    )


def connect(setting: FtpSetting) -> ftplib.FTP:
    """접속 + 로그인된 FTP 객체. with 문으로 쓰면 블록 종료 시 quit 된다."""
    ftp = ftplib.FTP()
    ftp.connect(setting.host, setting.port, timeout=CONNECT_TIMEOUT_S)
    ftp.login(setting.user, setting.password)
    return ftp


def remote_size(ftp: ftplib.FTP, remote_path: str) -> int:
    """SIZE 응답 바이트 수. 서버가 지원하지 않으면 0 (진행률 미상)."""
    try:
        return ftp.size(remote_path) or 0
    except ftplib.all_errors:
        return 0
