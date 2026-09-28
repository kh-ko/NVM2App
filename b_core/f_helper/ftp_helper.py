"""FTP 서버 접속 공통 (UI 무관 순수 함수 — f_helper 규칙).

펌웨어 저장소(firmware_ftp_helper)와 앱 배포 저장소(app_update_helper)는 같은
FTP 서버/계정을 쓰고 저장소 경로만 다르다. 접속 정보와 설정 파일 읽기는 이
모듈이 단일 출처이고, 각 저장소 모듈은 자기 경로 키만 넘겨 load_setting() 을
호출한다:

    firmware : load_setting("FTP_FIRMWARE_PATH", "/HDD1/FIRMWARE/VALVE/BASIC")
    app      : load_setting("FTP_APP_PATH",      "/HDD1/NVM2App")

설정 파일 2_resource/config/ftp_connection.json 의 키:
    FTP_HOST / FTP_PORT / FTP_USER / FTP_PASS   접속 정보 (공통)
    FTP_FIRMWARE_PATH / FTP_APP_PATH            저장소별 경로
파일이 없거나 키가 없으면 기본값(DEFAULT_CONNECTION)으로 채운다 — 현재 배포 파일에는
FTP_HOST/FTP_PORT 만 있다. 파일이 있는데 깨졌거나 객체가 아니면 JsonLoadError 를 올린다:
잘못된 서버로 조용히 접속하지 않도록 호출한 워커가 실패로 보고한다(호출부는 모두 try 안).

connect() 는 블로킹 네트워크 I/O 다 — 워커 스레드에서 호출한다.
"""

import ftplib
from typing import Callable, NamedTuple

from b_core.a_define import file_folder_path as path_def
from b_core.f_helper.json_file_helper import JsonLoadError, load_json


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
    파일이 없거나 키가 없으면 기본값으로 보충한다(BOM 수용).
    파일이 깨졌거나 객체가 아니면 JsonLoadError (호출한 워커가 실패로 보고)."""
    default = DEFAULT_CONNECTION._replace(path=default_path)
    data = load_json(path_def.RSRC_FTP_SETTING_FILE, expect=dict)  # 없으면 None, 깨지면 JsonLoadError
    if data is None:
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
