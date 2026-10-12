"""앱(NVM2App) 자체 업데이트 헬퍼 (UI 무관 순수 함수 — f_helper 규칙).

ver1 HelpNvmUpdateWin 은 FTP 접속 상수, version_info.txt 파싱, zip 다운로드,
압축 해제, 교체 배치 스크립트 생성이 모두 윈도우 클래스 안에 있었다. ver2 는
이 모듈이 단일 출처다.

저장소 (접속 정보는 ftp_helper 공통, 경로는 ftp_connection.json 의 FTP_APP_PATH):
    {FTP_APP_PATH}/version_info.txt        릴리스 노트 (아래 형식)
    {FTP_APP_PATH}/binary/{version}.zip    배포 zip — build.bat 산출물 NVM2App 폴더의
                                           내용물 (NVM2App.exe + _internal + 2_resource).
                                           폴더째 압축한 zip(루트에 폴더 하나)도 허용한다.
version_info.txt 형식 (ver1 과 동일, 최신이 위):
    [VER : 20260616-v0.0.2]
    1. 수정 내용 ...
    -------------------------------------------------------------------
    [VER : 20260610-v0.0.1]
    ...
  '[VER : x]' 의 x 가 버전 이름이자 zip 파일 이름(확장자 제외)이다.

설치 절차 — 실행 중인 exe 는 스스로 덮어쓸 수 없으므로 배치 스크립트에 위임한다:
    (워커)  download_package -> extract_package (실패·중단은 discard_package 로 정리)
    (UI)    write_install_script -> 다른 창 닫기 -> 앱 종료 (aboutToQuit 에서 start_install_script)
    (스크립트, 2026-10-12 트랜잭션 — F036/N063)
      쓰기 권한 검사(잠금 대기보다 먼저 — 권한 없음이 '앱 미종료' 로 보이지 않게) -> exe 잠금 해제 대기(=앱 종료 확인)
      -> 지난 실행이 남긴 .update_old: 저널에 committed 가 있으면 확정된 뒤 삭제가 덜 끝난 것이라 그냥 지우고, 없으면
         교체 도중 끊긴 것이라 먼저 되돌림
      -> 준비: 패키지를 앱 폴더 옆 .update_new 에 전부 복사 (실패하면 앱 무변경)
      -> 교체: 패키지 최상위 항목마다 앱 폴더의 것을 .update_old 로, .update_new 의 것을 제자리로 이름 바꾸기 (같은 볼륨, 매 단계 검사)
         -> 보존 폴더(2_resource/temp)는 옛 트리에서 되돌려 놓음
         -> 확정: 저널에 committed 를 적은 뒤 .update_old/.update_new 삭제, .update_old 가 없어지면 저널도 삭제
         -> 실패: 되돌리기 — .update_old 의 내용만 보고 하므로 어디서 끊겼든 같은 절차. 항목마다 새 것을 치운 뒤 옛 것을
            옮기고 결과를 검사한다: 치우지 못한 항목에서 멈추고 .update_old 를 그대로 둔다 (옛 파일은 잃지 않고, 다음 실행이
            먼저 되돌린다). 저널(.update_journal)은 앱 폴더에 남김
      -> 앱 재실행 -> 임시 정리. 종료 코드 1 직접 실행 / 2 권한 없음 / 3 앱 미종료 / 4 준비 복사 실패 / 5 교체 실패(되돌림) /
         6 되돌리기 미완(.update_old 유지).
    _internal(PyInstaller one-folder 라이브러리)은 통째로 교체되므로 구버전에만 있던 DLL/모듈이 남지 않는다.

ver1 에서 달라진 점:
- PRESERVED_RELATIVE_DIRS(3_log, 2_resource/temp) 는 패키지에 들어 있어도 배포하지 않는다.
  그 외(2_resource 의 나머지 포함)는 배포본으로 바뀐다 (사용자 결정 2026-09-09) — 패키지의 최상위 항목이 통째로 교체되므로
  그 안에 있던 로컬 파일은 보존 폴더 외에는 남지 않는다 (ver1 의 xcopy 덮어쓰기와 다른 점).
- 배치 스크립트는 순수 ASCII 로 저장하고 경로(앱 폴더/exe 이름/패키지)는 환경변수
  NVM2APP_* 로 넘긴다 — 코드페이지와 무관하고 & % ! 같은 cmd 특수문자도 재해석되지 않는다
  (ver1 은 UTF-8 한글 + chcp 65001 — cmd 의 UTF-8 배치 해석은 불안정하다. build.bat 주석 참고).
  잠금 검사는 'exe 를 쓰기 모드로 열기' 로 한다 — ver1 의 ren 은 실행 중인
  exe 도 이름이 바뀔 수 있어 잠금 검사가 되지 않는다.
- 소스 실행(python main.py) 상태에서는 설치를 거부한다 — ver1 은 sys.argv[0]
  폴더(= 프로젝트 소스 폴더)에 배포본을 덮어썼다.

네트워크/파일 I/O 함수는 블로킹이다 — 워커 스레드에서 호출한다.
실패는 예외로 전파하며 호출측이 메시지로 바꾼다.
"""

import io
import os
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from typing import NamedTuple

from b_core.a_define import app_info
from b_core.a_define import file_folder_path as path_def
from b_core.f_helper import ftp_helper
from b_core.f_helper.ftp_helper import FtpSetting, ProgressCallback

PATH_KEY = "FTP_APP_PATH"
DEFAULT_PATH = "/HDD1/NVM2App"

RELEASE_NOTES_FILE = "version_info.txt"
BINARY_DIR = "binary"

APP_EXE_NAME = "NVM2App.exe"  # build.bat 의 --name NVM2App

# 로컬 작업 폴더 — 다운로드 zip / 압축 해제본 / 설치 스크립트
WORK_DIR = os.path.join(tempfile.gettempdir(), "NVM2App_update")
INSTALL_SCRIPT_NAME = "nvm2app_update.bat"

# 업데이트가 건드리지 않는 앱 폴더 내 상대 경로 — 패키지에 들어 있어도 배포하지 않는다.
# 사용자 결정(2026-09-09): 로그는 유지하고 2_resource 는 배포본으로 덮어쓴다.
# 예외 2_resource/temp (N046): 펌웨어 다운로드 캐시 = Local Files 모드의 원본 — 현장의 마지막 다운로드본을
# 빌드 시점 파일로 되돌리지 않는다 (build.bat 도 이 폴더를 싣지 않는다)
PRESERVED_RELATIVE_DIRS = ("3_log", "2_resource/temp")

LOCK_WAIT_RETRY = 30    # 앱 종료(exe 잠금 해제) 대기 상한 — 1초 간격
RESTART_DELAY_S = 5     # 복사 후 재실행까지 대기 (백신 스캔/디스크 동기화 — ver1 현장 조치)


class ReleaseNote(NamedTuple):
    version: str  # '[VER : x]' 의 x = zip 파일 이름(확장자 제외)
    notes: str    # 수정 내용 본문 (구분선 제외, 앞뒤 공백 제거)


# ============================================================================
#  설정 / 버전
# ============================================================================
def load_setting() -> FtpSetting:
    """앱 배포 저장소용 FtpSetting (접속 정보 공통 + FTP_APP_PATH)."""
    return ftp_helper.load_setting(PATH_KEY, DEFAULT_PATH)


def is_deployed_exe() -> bool:
    """PyInstaller 로 빌드된 exe 로 실행 중인가 (소스 실행이면 False)."""
    return bool(getattr(sys, "frozen", False))


def installed_app_dir() -> str:
    return path_def.EXE_BASE


def installed_exe_name() -> str:
    return os.path.basename(sys.executable) if is_deployed_exe() else APP_EXE_NAME


_RELEASE_NAME = re.compile(r"^(?:(?P<date>\d{8})-)?[vV]?(?P<version>.+)$")
_VERSION_NAME = re.compile(r"^[A-Za-z0-9._-]+\Z")   # \Z — '$' 는 끝의 개행을 허용한다


def is_installed_version(version: str) -> bool:
    """릴리스 이름이 현재 실행 중인 앱 빌드인가. 이름 = [YYYYMMDD-][v]<버전> ('20260616-v0.0.2', 'v0.0.2', '0.0.2',
    '20260616-v1.0.0-rc1'). 버전이 APP_VERSION 과 같고, 이름에 날짜가 있고 빌드 날짜(APP_BUILD_DATE — 배포 exe)도 있으면
    날짜까지 같아야 한다 — 같은 번호의 다른 날짜 빌드는 '설치됨' 이 아니다 (F034/N060)."""
    match = _RELEASE_NAME.match(version.strip())
    if match is None or match.group("version") != app_info.APP_VERSION:
        return False
    date = match.group("date")
    build_date = app_info.APP_BUILD_DATE.replace("-", "")
    return date is None or not build_date or date == build_date


def is_valid_version_name(version: str) -> bool:
    """릴리스 이름이 로컬 경로 조각(zip 이름·압축 해제 폴더)으로 안전한가 — 영숫자·점·밑줄·하이픈만, '.'/'..' 제외.
    서버의 이름을 검증 없이 경로에 쓰면 '..' 로 작업 폴더 밖을 지울 수 있다 (N061)."""
    return bool(_VERSION_NAME.match(version)) and version not in (".", "..")


# ============================================================================
#  릴리스 노트
# ============================================================================
_VERSION_HEADER = re.compile(r"^\[\s*VER\s*:\s*(?P<version>.+?)\s*\]$")
_SEPARATOR_PREFIX = "-----"


def parse_release_notes(text: str) -> list[ReleaseNote]:
    """version_info.txt 본문을 ReleaseNote 목록으로 (파일 순서 유지).

    '[VER : x]' 로 항목이 시작하고 다음 헤더 또는 '-----' 구분선에서 끝난다.
    헤더 밖의 줄은 무시한다."""
    notes: list[ReleaseNote] = []
    version: str | None = None
    lines: list[str] = []

    def flush():
        if version is not None:
            notes.append(ReleaseNote(version, "\n".join(lines).strip()))

    for raw_line in text.splitlines():
        line = raw_line.strip()
        match = _VERSION_HEADER.match(line)
        if match is not None:
            flush()
            version = match.group("version")
            lines = []
        elif line.startswith(_SEPARATOR_PREFIX):
            flush()
            version = None
            lines = []
        elif version is not None:
            lines.append(raw_line.rstrip())

    flush()
    return notes


def _decode_text(raw: bytes) -> str:
    # 서버 파일이 UTF-8(BOM 가능) 또는 CP949 — ver1 과 같은 순서로 시도
    try:
        return raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        return raw.decode("cp949", errors="replace")


def fetch_release_notes(setting: FtpSetting) -> list[ReleaseNote]:
    """FTP 의 version_info.txt 를 받아 파싱한 목록."""
    buffer = io.BytesIO()
    with ftp_helper.connect(setting) as ftp:
        ftp.cwd(setting.path)
        ftp.retrbinary(f"RETR {RELEASE_NOTES_FILE}", buffer.write)
    return parse_release_notes(_decode_text(buffer.getvalue()))


# ============================================================================
#  패키지 다운로드 / 압축 해제
# ============================================================================
def remote_package_path(setting: FtpSetting, version: str) -> str:
    return f"{setting.path}/{BINARY_DIR}/{version}.zip"


def local_package_path(version: str) -> str:
    return os.path.join(WORK_DIR, f"{version}.zip")


def local_extract_dir(version: str) -> str:
    return os.path.join(WORK_DIR, version)


def download_package(setting: FtpSetting, version: str,
                     progress_cb: ProgressCallback | None = None) -> str:
    """배포 zip 을 WORK_DIR 로 내려받고 로컬 경로를 반환한다.

    - .part 에 받은 뒤 os.replace — 중단/실패 시 반쯤 받은 zip 이 남지 않는다.
    - progress_cb(done, total): 서버가 SIZE 를 지원하지 않으면 total=0.
    - progress_cb 가 예외를 던지면 그대로 전파된다 (중단 요청 전달 경로)."""
    remote = remote_package_path(setting, version)
    dest = local_package_path(version)
    os.makedirs(WORK_DIR, exist_ok=True)

    part_path = dest + ".part"
    try:
        with ftp_helper.connect(setting) as ftp:
            ftp.voidcmd("TYPE I")  # SIZE/RETR 을 바이너리 모드로
            total = ftp_helper.remote_size(ftp, remote)

            done = 0
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
    return dest


def extract_package(zip_path: str, version: str) -> str:
    """zip 을 WORK_DIR/{version}/ 에 풀고 교체 원본 폴더(= 그 폴더)를 반환한다.

    zip 루트에 exe 가 없고 폴더 하나만 있으면(폴더째 압축) 그 안의 내용을 한 단계 올린다 — 패키지 루트가 늘 압축 해제 폴더
    자신이라 설치 스크립트의 정리(rd SRC_DIR)가 전부를 지운다 (F037). exe 를 찾지 못하거나 풀다 실패하면 압축 해제 폴더를 지우고
    예외 — 잘못된 패키지로 앱 폴더를 덮어쓰지 않기 위함. zip 은 풀고 나면 지운다."""
    extract_dir = local_extract_dir(version)
    if os.path.isdir(extract_dir):
        shutil.rmtree(extract_dir)

    try:
        with zipfile.ZipFile(zip_path) as zf:
            zf.extractall(extract_dir)

        exe_name = installed_exe_name()
        root = _find_package_root(extract_dir, exe_name)
        if root is None:
            raise RuntimeError(f"'{exe_name}' was not found in the package '{version}.zip'.")
        if root != extract_dir:
            _lift_folder(root, extract_dir)
    except Exception:
        shutil.rmtree(extract_dir, ignore_errors=True)
        raise

    os.remove(zip_path)
    return extract_dir


def _lift_folder(inner: str, extract_dir: str) -> None:
    """폴더째 압축한 zip: inner 의 내용을 extract_dir 로 올리고 빈 inner 를 지운다."""
    for name in os.listdir(inner):
        os.replace(os.path.join(inner, name), os.path.join(extract_dir, name))
    os.rmdir(inner)


def discard_package(version: str) -> None:
    """실패·중단한 준비의 잔재를 지운다 — 압축 해제 폴더와 zip(.part 포함). 없으면 아무것도 하지 않는다 (F037).
    version 은 is_valid_version_name 을 통과한 이름이어야 한다 (경로 조각으로 쓴다)."""
    shutil.rmtree(local_extract_dir(version), ignore_errors=True)
    for path in (local_package_path(version), local_package_path(version) + ".part"):
        try:
            os.remove(path)
        except OSError:
            pass


def _find_package_root(extract_dir: str, exe_name: str) -> str | None:
    if os.path.isfile(os.path.join(extract_dir, exe_name)):
        return extract_dir

    entries = os.listdir(extract_dir)
    if len(entries) == 1:
        inner = os.path.join(extract_dir, entries[0])
        if os.path.isdir(inner) and os.path.isfile(os.path.join(inner, exe_name)):
            return inner
    return None


# ============================================================================
#  설치 (교체 스크립트)
# ============================================================================
def write_install_script(package_root: str) -> str:
    """교체 배치 스크립트 파일을 만들고 그 경로를 반환한다 (기동은 start_install_script).

    배포 exe 에서만 동작한다 (소스 실행이면 예외). 앱 종료 전에 호출해 실패를
    대화상자로 보일 수 있게 한다."""
    if not is_deployed_exe():
        raise RuntimeError("Application update works only in the deployed executable "
                           f"({APP_EXE_NAME}), not when running from source.")

    _drop_preserved_dirs(package_root)

    script_path = os.path.join(WORK_DIR, INSTALL_SCRIPT_NAME)
    with open(script_path, "w", encoding="ascii", newline="\r\n") as f:  # 경로는 환경변수로 — 본문은 순수 ASCII
        f.write(_build_install_script())
    return script_path


def start_install_script(script_path: str, package_root: str) -> None:
    """교체 스크립트를 새 콘솔로 기동한다. 경로 세 개는 환경변수 NVM2APP_* 로 넘긴다.

    앱 종료가 확정된 뒤(aboutToQuit)에 호출한다 — 스크립트는 exe 잠금 해제(=앱 종료)를
    기다리므로, 어떤 창이 종료를 거부한 채 스크립트만 뜨면 30초 뒤 실패한다 (F094)."""
    # PyInstaller 부트로더 환경변수는 넘기지 않는다 — 재실행되는 새 exe 가
    # 이미 종료된 부모의 임시 폴더를 자기 것으로 오인하지 않게
    env = {key: value for key, value in os.environ.items()
           if not key.startswith(("_MEIPASS", "_PYI", "PYI_"))}
    # 경로는 배치 본문이 아니라 환경변수로 — 환경 블록은 유니코드라 배치 파일의 코드페이지와 무관하고,
    # 배치의 %NVM2APP_*% 확장 결과는 다시 해석되지 않아 & % ! 같은 문자도 그대로 전달된다 (N062 검토)
    env["NVM2APP_APP_DIR"] = installed_app_dir()
    env["NVM2APP_EXE_NAME"] = installed_exe_name()
    env["NVM2APP_SRC_DIR"] = package_root

    # 문자열 명령줄 + /s — cmd 는 바깥 따옴표 한 쌍만 벗기고 안쪽 "경로" 를 그대로 실행한다.
    # 리스트 인자(["cmd.exe", "/c", path])는 %TEMP% 경로에 & ^ ( ) = , ; 가 있으면 cmd 의
    # /c 따옴표 규칙에 걸려 실행되지 않는다 (N062, 실측). 배치를 직접 넘기는 형태도 같은 이유로 실패.
    subprocess.Popen(f'cmd.exe /s /c ""{script_path}""', cwd=WORK_DIR, env=env,
                     creationflags=subprocess.CREATE_NEW_CONSOLE)


def _drop_preserved_dirs(package_root: str) -> None:
    """보존 폴더를 패키지에서 지운다. 최상위 항목(3_log)은 패키지에 없으면 교체 루프에 들어가지 않아 앱 폴더의 것이 그대로
    남고, 교체되는 폴더 안의 항목(2_resource/temp)은 교체 뒤 _preserve_lines 의 줄이 .update_old 에서 되돌려 놓는다."""
    for relative in PRESERVED_RELATIVE_DIRS:
        packaged_dir = os.path.join(package_root, *relative.split("/"))
        if os.path.isdir(packaged_dir):
            shutil.rmtree(packaged_dir)


def _preserve_lines() -> tuple[str, str]:
    """교체되는 폴더 안에 있는 보존 폴더(PRESERVED_RELATIVE_DIRS 중 '/' 가 있는 항목)의 배치 줄 —
    (교체 뒤 옛 트리에서 되돌려 놓는 줄, 되돌리기 앞에 옛 트리로 되돌려 보내는 줄).
    최상위 보존 폴더(3_log)는 패키지에 없어 교체 자체가 일어나지 않으므로 줄이 필요 없다."""
    after, before_rollback = [], []
    for relative in PRESERVED_RELATIVE_DIRS:
        if "/" not in relative:
            continue
        win = relative.replace("/", "\\")
        parent = win.split("\\")[0]
        after.append(
            f'if exist "%OLD_DIR%\\{win}" (\n'
            f'    if exist "%APP_DIR%\\{win}" rd /s /q "%APP_DIR%\\{win}" >nul 2>&1\n'
            f'    move /y "%OLD_DIR%\\{win}" "%APP_DIR%\\{win}" >nul || goto swap_failed\n'
            f'    >>"%JOURNAL%" echo preserved {win}\n'
            f')\n')
        before_rollback.append(
            f'if exist "%APP_DIR%\\{win}" if exist "%OLD_DIR%\\{parent}" if not exist "%OLD_DIR%\\{win}" '
            f'move /y "%APP_DIR%\\{win}" "%OLD_DIR%\\{win}" >nul 2>&1\n')
    return "".join(after), "".join(before_rollback)


def _build_install_script() -> str:
    """교체 배치 스크립트 본문 (순수 ASCII — 경로는 환경변수 NVM2APP_APP_DIR / NVM2APP_EXE_NAME /
    NVM2APP_SRC_DIR 로 받는다. start_install_script 가 넣어 준다). 절차는 모듈 docstring '설치 절차'.

    - 잠금 검사: 실행 중인 exe 는 쓰기 모드로 열 수 없다 (>> 리다이렉션 실패).
    - 권한 검사: 앱 폴더에 파일을 하나 만들어 본다 — 권한 없음을 '아직 실행 중' 으로 오인하지 않는다 (N063).
    - 교체는 move(이름 바꾸기)만 — 같은 볼륨이라 즉시 끝나고, 실패해도 반쯤 복사된 파일이 생기지 않는다. 매 move 의
      결과를 검사(||)하고 저널에 적는다. 되돌리기는 .update_old 의 내용만 보고 하므로 어디서 끊겼든 같은 절차다.
    - 되돌리기의 항목 처리는 서브루틴(:restore_entry)이고 결과는 'if errorlevel 1' 로 본다 — 'call :x || ...' 는
      서브루틴이 괄호 블록 안에서 exit /b 한 경우 동작이 불안정하다. for 블록 안의 exit /b 는 루프와 서브루틴을 함께 끝낸다 (실측).
    - 확정 표식은 저널의 'committed' 한 줄 — .update_old 삭제가 덜 끝나도 다음 실행이 되돌리지 않는다.
    - 저널에 경로를 적는 줄도 따옴표 안에 둔다 — 따옴표 밖의 %변수% 확장 결과는 cmd 가 다시 해석해 & 가 명령 구분자가 된다.
    - 괄호 블록 안에서 %변수% 를 갱신하지 않는다 (지연 확장 문제 회피). for 변수(%%~nxD)는 블록 안에서도 안전하다.
    - 시스템 도구는 절대 경로로 부른다 — PATH 에 동명의 다른 도구(Git 의 GNU timeout 등)가 앞서 있어도 영향받지 않게.
    - 대기는 'ping -n (초+1) 127.0.0.1' 로 한다 — timeout.exe 는 stdin 이 콘솔이 아니면(리다이렉션) 즉시 종료한다.
    - 마지막 줄에서 자기 자신을 지운다 ((goto) 2>nul & del 관용구).
    - 경로를 본문에 박지 않으므로 코드페이지(한글·ë 등)와 % 이스케이프 문제가 없다 (N062 검토).
    - 지연 확장은 명시적으로 끈다 — 레지스트리로 기본 켜진 PC 에서는 경로의 ! 가 확장 표시로 먹혀 사라진다 (실측).
    - 환경변수 없이(남은 파일을 직접 실행) 시작되면 아무것도 하지 않는다 — 빈 경로로 move/rd 가 돌지 않게.
    - NVM2APP_SKIP_RESTART 가 정의돼 있으면 재실행만 건너뛴다 — 헤드리스 테스트(tools/tests/test_app_update_headless.py) 전용."""
    preserve_after, preserve_rollback = _preserve_lines()
    return f"""@echo off
setlocal DisableDelayedExpansion
title NVM2App Update
if not defined NVM2APP_SRC_DIR (
    echo [ERROR] This script is started by NVM2App during an update. Do not run it directly.
    pause
    exit /b 1
)
set "APP_DIR=%NVM2APP_APP_DIR%"
set "EXE_NAME=%NVM2APP_EXE_NAME%"
set "SRC_DIR=%NVM2APP_SRC_DIR%"
set "SYS32=%SystemRoot%\\System32"
set "NEW_DIR=%APP_DIR%\\.update_new"
set "OLD_DIR=%APP_DIR%\\.update_old"
set "JOURNAL=%APP_DIR%\\.update_journal"

echo ===================================================
echo  NVM2App update in progress. Please wait...
echo ===================================================

rem ---- 1. write-permission probe first: a denied write must not look like "still running" (N063)
( >"%APP_DIR%\\.nvm2app_write_test" (call ) ) 2>nul || goto no_permission
del "%APP_DIR%\\.nvm2app_write_test" >nul 2>&1
rem a read-only attribute on the exe would also fail the lock test below; the file is replaced anyway
"%SYS32%\\attrib.exe" -r "%APP_DIR%\\%EXE_NAME%" >nul 2>&1

rem ---- 2. wait until the application has exited (a running exe cannot be opened for writing)
set /a retry=0
:wait_lock
( >>"%APP_DIR%\\%EXE_NAME%" (call ) ) 2>nul && goto unlocked
set /a retry+=1
if %retry% gtr {LOCK_WAIT_RETRY} goto lock_failed
echo Waiting for the application to exit... (%retry%/{LOCK_WAIT_RETRY})
"%SYS32%\\ping.exe" -n 2 127.0.0.1 >nul
goto wait_lock

:lock_failed
echo [ERROR] The application did not exit. Update aborted.
pause
exit /b 3

:unlocked
rem ---- 3. leftovers of an earlier run. .update_old with a journal that says "committed" is a finished update whose
rem      cleanup did not complete: just delete it. Otherwise the swap was interrupted (power loss): put the old files back
if not exist "%OLD_DIR%" goto no_leftover
"%SYS32%\\findstr.exe" /c:"committed" "%JOURNAL%" >nul 2>&1 && goto leftover_committed
echo A previous update was interrupted. Restoring the previous files first...
>>"%JOURNAL%" echo leftover .update_old found - rolling back first
call :rollback
if exist "%OLD_DIR%" goto rollback_failed
goto no_leftover
:leftover_committed
rd /s /q "%OLD_DIR%" >nul 2>&1
:no_leftover
if exist "%NEW_DIR%" rd /s /q "%NEW_DIR%" >nul 2>&1

rem journal: a fresh file per run, left behind for diagnosis when the run fails, deleted when it succeeds.
rem The path is quoted - cmd re-parses expanded %variables% outside quotes, so an ^& in the path would split the line
>"%JOURNAL%" echo update started: src="%SRC_DIR%"

rem ---- 4. stage: copy the whole package next to the app first. A failure here leaves the app untouched
echo Copying files...
"%SYS32%\\xcopy.exe" "%SRC_DIR%" "%NEW_DIR%\\" /E /Y /Q /I /R >nul
if errorlevel 1 goto stage_failed
>>"%JOURNAL%" echo staged

rem ---- 5. swap: every top-level entry of the package is renamed into place (same volume, no copying).
rem      Each step is checked; on the first failure everything already swapped is put back (:rollback)
mkdir "%OLD_DIR%" >nul 2>&1
for /d %%D in ("%NEW_DIR%\\*") do (
    if exist "%APP_DIR%\\%%~nxD" (
        move /y "%APP_DIR%\\%%~nxD" "%OLD_DIR%\\%%~nxD" >nul || goto swap_failed
        >>"%JOURNAL%" echo old %%~nxD
    )
    move /y "%NEW_DIR%\\%%~nxD" "%APP_DIR%\\%%~nxD" >nul || goto swap_failed
    >>"%JOURNAL%" echo new %%~nxD
)
for %%F in ("%NEW_DIR%\\*") do (
    if exist "%APP_DIR%\\%%~nxF" (
        move /y "%APP_DIR%\\%%~nxF" "%OLD_DIR%\\%%~nxF" >nul || goto swap_failed
        >>"%JOURNAL%" echo old %%~nxF
    )
    move /y "%NEW_DIR%\\%%~nxF" "%APP_DIR%\\%%~nxF" >nul || goto swap_failed
    >>"%JOURNAL%" echo new %%~nxF
)

rem ---- 6. preserved folders live inside a swapped folder: bring them back from the old tree
{preserve_after}
rem ---- 7. commit: "committed" is written before the old tree is deleted, so a deletion that does not finish
rem      (power loss, a scanner holding a file) is recognised by the next run and never rolled back
>>"%JOURNAL%" echo committed
rd /s /q "%OLD_DIR%" >nul 2>&1
rd /s /q "%NEW_DIR%" >nul 2>&1
if not exist "%OLD_DIR%" del "%JOURNAL%" >nul 2>&1
goto restart

:no_permission
echo [ERROR] No write permission in "%APP_DIR%". Update aborted.
pause
exit /b 2

:stage_failed
echo [ERROR] File copy failed. The application was not changed.
>>"%JOURNAL%" echo stage failed
rd /s /q "%NEW_DIR%" >nul 2>&1
pause
exit /b 4

:swap_failed
echo [ERROR] File replacement failed. Restoring the previous version...
>>"%JOURNAL%" echo swap failed - rolling back
call :rollback
if exist "%OLD_DIR%" goto rollback_failed
rd /s /q "%NEW_DIR%" >nul 2>&1
echo [ERROR] Update aborted. The previous version was kept.
pause
exit /b 5

:rollback_failed
echo [ERROR] The previous version could not be fully restored. Its files are kept in "%OLD_DIR%".
echo         Close programs that use the application folder and run the update again (it restores them first).
>>"%JOURNAL%" echo rollback failed - .update_old kept
pause
exit /b 6

:rollback
rem Puts back whatever is in .update_old, using only the file system state (works for a mid-swap crash too).
rem Every step is checked: an entry that cannot be restored stops the rollback and .update_old is KEPT, so the
rem old files are never lost and the next run retries. .update_old is removed only when it is empty (plain rd).
{preserve_rollback}mkdir "%NEW_DIR%" >nul 2>&1
for /d %%D in ("%OLD_DIR%\\*") do (
    call :restore_entry "%%~nxD"
    if errorlevel 1 exit /b 1
)
for %%F in ("%OLD_DIR%\\*") do (
    call :restore_entry "%%~nxF"
    if errorlevel 1 exit /b 1
)
rd "%OLD_DIR%" >nul 2>&1
exit /b 0

:restore_entry
rem %~1 = entry name. The new entry (if any) is moved aside into .update_new, else deleted; it must be gone before
rem the old one returns (moving a folder onto an existing folder would nest it inside). Failure leaves the old entry
rem in .update_old and returns 1.
if exist "%APP_DIR%\\%~1" move /y "%APP_DIR%\\%~1" "%NEW_DIR%\\%~1" >nul 2>&1
if exist "%APP_DIR%\\%~1" rd /s /q "%APP_DIR%\\%~1" >nul 2>&1
if exist "%APP_DIR%\\%~1" del /f /q "%APP_DIR%\\%~1" >nul 2>&1
if exist "%APP_DIR%\\%~1" goto restore_blocked
move /y "%OLD_DIR%\\%~1" "%APP_DIR%\\%~1" >nul 2>&1 || goto restore_move_failed
>>"%JOURNAL%" echo restored %~1
exit /b 0
:restore_blocked
>>"%JOURNAL%" echo restore failed %~1 - the new entry could not be removed
exit /b 1
:restore_move_failed
>>"%JOURNAL%" echo restore failed %~1
exit /b 1

:restart
if defined NVM2APP_SKIP_RESTART goto cleanup
echo Update completed. Restarting the application in {RESTART_DELAY_S} seconds...
"%SYS32%\\ping.exe" -n {RESTART_DELAY_S + 1} 127.0.0.1 >nul
rem explorer.exe launches the app with the shell's own environment (as a double-click would)
"%SystemRoot%\\explorer.exe" "%APP_DIR%\\%EXE_NAME%"

:cleanup
rd /s /q "%SRC_DIR%" >nul 2>&1
rem self-delete: '(goto) 2>nul' leaves the batch context first, so cmd does not
rem try to read the next line from the deleted file (no "batch file not found")
(goto) 2>nul & del "%~f0"
"""
