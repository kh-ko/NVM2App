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
    (워커)  download_package -> extract_package
    (UI)    launch_installer -> 앱 종료
    (스크립트) exe 잠금 해제 대기(=앱 종료 확인) -> _internal 을 .old 로 보관 -> 덮어쓰기 복사
               -> 성공: .old 삭제 / 실패: .old 복원 -> 앱 재실행 -> 임시 정리

ver1 에서 달라진 점:
- PRESERVED_RELATIVE_DIRS(3_log) 는 패키지에 들어 있어도 배포하지 않는다.
  그 외(2_resource 포함)는 ver1 과 같이 배포본으로 덮어쓴다 (사용자 결정).
- 배치 스크립트는 ASCII 전용 + 콘솔 OEM 코드페이지로 저장한다 (ver1 은 UTF-8
  한글 + chcp 65001 — cmd 의 UTF-8 배치 해석은 불안정하다. build.bat 주석 참고).
  잠금 검사는 'exe 를 쓰기 모드로 열기' 로 한다 — ver1 의 ren 은 실행 중인
  exe 도 이름이 바뀔 수 있어 잠금 검사가 되지 않는다.
- 소스 실행(python main.py) 상태에서는 설치를 거부한다 — ver1 은 sys.argv[0]
  폴더(= 프로젝트 소스 폴더)에 배포본을 덮어썼다.

네트워크/파일 I/O 함수는 블로킹이다 — 워커 스레드에서 호출한다.
실패는 예외로 전파하며 호출측이 메시지로 바꾼다.
"""

import ctypes
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

# 업데이트가 건드리지 않는 앱 폴더 내 상대 경로 — 패키지에 들어 있어도 배포하지
# 않는다. 사용자 결정(2026-09-09): 로그만 유지하고 2_resource 는 전부 배포본으로 덮어쓴다
PRESERVED_RELATIVE_DIRS = ("3_log",)

# PyInstaller --onedir 의 라이브러리 폴더. 새 패키지에 이 폴더가 있으면 복사 전에
# 앱 폴더의 것을 통째로 교체한다 — 덮어쓰기만 하면 구버전에만 있던 DLL/모듈이 남는다.
# (앱 종료 후이므로 안전. 삭제가 아니라 .old 로 이름을 바꿔 두고 복사 실패 시 되돌린다)
PYINSTALLER_INTERNAL_DIR = "_internal"

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


def is_installed_version(version: str) -> bool:
    """릴리스 이름이 현재 실행 중인 앱 버전인가.
    '20260616-v0.0.2' / 'v0.0.2' / '0.0.2' 모두 APP_VERSION '0.0.2' 와 일치."""
    tail = version.strip().rsplit("-", 1)[-1]
    return tail.lstrip("vV") == app_info.APP_VERSION


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
    """zip 을 WORK_DIR/{version}/ 에 풀고 교체 원본 폴더(exe 가 있는 폴더)를 반환한다.

    zip 루트에 exe 가 없고 폴더 하나만 있으면(폴더째 압축) 그 안을 원본으로 본다.
    exe 를 찾지 못하면 예외 — 잘못된 패키지로 앱 폴더를 덮어쓰지 않기 위함.
    zip 은 풀고 나면 지운다."""
    extract_dir = local_extract_dir(version)
    if os.path.isdir(extract_dir):
        shutil.rmtree(extract_dir)

    with zipfile.ZipFile(zip_path) as zf:
        zf.extractall(extract_dir)
    os.remove(zip_path)

    exe_name = installed_exe_name()
    root = _find_package_root(extract_dir, exe_name)
    if root is None:
        raise RuntimeError(f"'{exe_name}' was not found in the package '{version}.zip'.")
    return root


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
def launch_installer(package_root: str) -> str:
    """교체 배치 스크립트를 만들어 새 콘솔로 기동하고 스크립트 경로를 반환한다.

    호출 직후 앱을 종료해야 한다 — 스크립트가 exe 잠금 해제(=앱 종료)를 기다린다.
    배포 exe 에서만 동작한다 (소스 실행이면 예외)."""
    if not is_deployed_exe():
        raise RuntimeError("Application update works only in the deployed executable "
                           f"({APP_EXE_NAME}), not when running from source.")

    _drop_preserved_dirs(package_root)

    script = _build_install_script(app_dir=installed_app_dir(), exe_name=installed_exe_name(),
                                   package_root=package_root)
    script_path = os.path.join(WORK_DIR, INSTALL_SCRIPT_NAME)
    with open(script_path, "w", encoding=_console_encoding(), newline="\r\n") as f:
        f.write(script)

    # PyInstaller 부트로더 환경변수는 넘기지 않는다 — 재실행되는 새 exe 가
    # 이미 종료된 부모의 임시 폴더를 자기 것으로 오인하지 않게
    env = {key: value for key, value in os.environ.items()
           if not key.startswith(("_MEIPASS", "_PYI", "PYI_"))}

    subprocess.Popen(["cmd.exe", "/c", script_path], cwd=WORK_DIR, env=env,
                     creationflags=subprocess.CREATE_NEW_CONSOLE)
    return script_path


def _drop_preserved_dirs(package_root: str) -> None:
    """보존 폴더는 패키지에서 통째로 지워 앱 폴더의 것을 그대로 둔다
    (xcopy 는 원본에 없는 대상 파일을 건드리지 않는다)."""
    for relative in PRESERVED_RELATIVE_DIRS:
        packaged_dir = os.path.join(package_root, *relative.split("/"))
        if os.path.isdir(packaged_dir):
            shutil.rmtree(packaged_dir)


def _console_encoding() -> str:
    """cmd 가 배치 파일을 해석하는 콘솔(OEM) 코드페이지 — 한글 경로가 들어갈 수 있다."""
    try:
        return f"cp{ctypes.windll.kernel32.GetOEMCP()}"
    except (AttributeError, OSError):
        return "mbcs"


def _build_install_script(app_dir: str, exe_name: str, package_root: str) -> str:
    """교체 배치 스크립트 본문 (ASCII 전용 — 경로 외 비ASCII 문자를 넣지 않는다).

    - 잠금 검사: 실행 중인 exe 는 쓰기 모드로 열 수 없다 (>> 리다이렉션 실패).
      PyInstaller onefile 은 부모/자식 두 프로세스가 같은 exe 라 둘 다 끝나야 통과.
    - %변수% 를 괄호 블록 안에서 갱신/참조하지 않는다 (지연 확장 문제 회피).
    - 시스템 도구는 절대 경로로 부른다 — PATH 에 동명의 다른 도구(Git 의 GNU
      timeout 등)가 앞서 있어도 영향받지 않게.
    - 대기는 'ping -n (초+1) 127.0.0.1' 로 한다 — timeout.exe 는 stdin 이 콘솔이
      아니면(리다이렉션) 즉시 종료해 대기가 되지 않는다.
    - 마지막 줄에서 자기 자신을 지운다 ((goto) 2>nul & del 관용구)."""
    return f"""@echo off
setlocal
title NVM2App Update
set "APP_DIR={app_dir}"
set "EXE_NAME={exe_name}"
set "SRC_DIR={package_root}"
set "SYS32=%SystemRoot%\\System32"

echo ===================================================
echo  NVM2App update in progress. Please wait...
echo ===================================================

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
exit /b 1

:unlocked
rem one-folder layout: the library folder is replaced as a whole so stale files do not
rem survive. The app has exited here (lock test passed), so nothing holds its DLLs.
rem It is renamed, not deleted, so a failed copy can be rolled back.
set "OLD_INTERNAL=%APP_DIR%\\{PYINSTALLER_INTERNAL_DIR}.old"
if exist "%OLD_INTERNAL%" rd /s /q "%OLD_INTERNAL%" >nul 2>&1
if exist "%SRC_DIR%\\{PYINSTALLER_INTERNAL_DIR}" if exist "%APP_DIR%\\{PYINSTALLER_INTERNAL_DIR}" ren "%APP_DIR%\\{PYINSTALLER_INTERNAL_DIR}" "{PYINSTALLER_INTERNAL_DIR}.old" >nul 2>&1

echo Copying files...
"%SYS32%\\xcopy.exe" "%SRC_DIR%" "%APP_DIR%\\" /E /Y /Q /I /R >nul
if errorlevel 1 goto copy_failed

if exist "%OLD_INTERNAL%" rd /s /q "%OLD_INTERNAL%" >nul 2>&1
goto restart

:copy_failed
echo [ERROR] File copy failed. Restoring the previous library folder...
if exist "%OLD_INTERNAL%" (
    rd /s /q "%APP_DIR%\\{PYINSTALLER_INTERNAL_DIR}" >nul 2>&1
    ren "%OLD_INTERNAL%" "{PYINSTALLER_INTERNAL_DIR}" >nul 2>&1
)
echo [ERROR] Update aborted. The previous version was kept.
pause
exit /b 1

:restart

echo Update completed. Restarting the application in {RESTART_DELAY_S} seconds...
"%SYS32%\\ping.exe" -n {RESTART_DELAY_S + 1} 127.0.0.1 >nul
rem explorer.exe launches the app with the shell's own environment (as a double-click would)
"%SystemRoot%\\explorer.exe" "%APP_DIR%\\%EXE_NAME%"

rd /s /q "%SRC_DIR%" >nul 2>&1
rem self-delete: '(goto) 2>nul' leaves the batch context first, so cmd does not
rem try to read the next line from the deleted file (no "batch file not found")
(goto) 2>nul & del "%~f0"
"""
