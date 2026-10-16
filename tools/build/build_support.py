# -*- coding: utf-8 -*-
"""build.bat 보조 스크립트 — cmd 로 쓰기 어려운 일만 맡는다 (정규식 검사, 비 ASCII 텍스트 생성, 압축, 날짜 한 번 계산).
앱 코드가 아니며 배포본에 들어가지 않는다 (tools/). build.bat 이 프로젝트 루트에서 서브커맨드로 부른다.
결과는 stdout 한 줄 또는 파일, 실패는 stderr 메시지 + exit 1 (build.bat 은 `|| goto :fail` 로 받는다).

    python tools/build/build_support.py check-version <입력>                 순수 버전 한 줄 (공백·앞의 v 제거, 형식 검사)
    python tools/build/build_support.py dates                                'YYYYMMDD YYYY-MM-DD' 한 줄 (같은 시각에서)
    python tools/build/build_support.py version-file <출력 경로>              PyInstaller --version-file 용 VSVersionInfo 텍스트
    python tools/build/build_support.py zip <릴리스 폴더> <릴리스 이름>       {릴리스 폴더}/{릴리스 이름}.zip — 평평 레이아웃
    python tools/build/build_support.py note-stub <릴리스 폴더> <릴리스 이름> {릴리스 폴더}/release_note_entry.txt

결정(2026-10-16): app_info.py 의 APP_VERSION/APP_BUILD_DATE 주입·원복은 build.bat 이 그대로 맡는다(추적 파일 두 줄 치환).
version-file 은 주입된 뒤 불려야 app_info 가 릴리스 값이다. FTP 업로드와 version_info.txt 편집은 사용자가 직접 한다 —
note-stub 은 그때 맨 위에 붙일 항목의 머리만 만들어 zip 이름과 '[VER : x]' 가 어긋나는 사고를 막는다.
"""

from __future__ import annotations

import os
import re
import shutil
import sys
import zipfile
from datetime import datetime

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, ROOT)

from b_core.a_define import app_info  # noqa: E402
from b_core.f_helper.app_update_helper import APP_EXE_NAME  # noqa: E402

DEPLOY_DIR_NAME = "NVM2App"                 # build.bat 의 --name — 릴리스 폴더 안의 배포 폴더
NOTE_STUB_NAME = "release_note_entry.txt"
NOTE_SEPARATOR = "-" * 67                   # version_info.txt 의 항목 구분선 (파서는 '-----' 접두만 본다)

# X.Y.Z 또는 X.Y.Z-접미. 접미는 점으로 나뉜 비어 있지 않은 영숫자 조각 — 끝 점·연속 점은 Windows 가 폴더 이름에서 지워
# 폴더·zip·[VER] 이 어긋나므로 받지 않는다. ASCII 숫자만([0-9]). 이 형식은 업데이터의 이름 규칙(app_update_helper.is_valid_version_name:
# 영숫자·점·밑줄·하이픈)의 부분집합이라 릴리스 이름 YYYYMMDD-v<버전> 은 항상 그 규칙을 통과한다
_VERSION = re.compile(r"^([0-9]+)\.([0-9]+)\.([0-9]+)(-[A-Za-z0-9]+(?:\.[A-Za-z0-9]+)*)?$")


# ============================================================================
#  버전 / 날짜
# ============================================================================
def check_version(raw: str) -> str:
    """입력의 양끝 공백과 앞의 v/V 를 떼고 형식을 검사해 순수 버전을 돌려준다 (중간 공백은 형식 오류). 숫자 자리의 65535 상한도
    여기서 본다 — version-file 단계(app_info 주입 뒤)가 아니라 입력 직후 거부되게. 틀리면 ValueError."""
    text = raw.strip()
    if text[:1] in ("v", "V"):
        text = text[1:]
    if _VERSION.match(text) is None:
        raise ValueError(f"version must be X.Y.Z or X.Y.Z-suffix (digits, letters, '.'): {raw!r}")
    numeric_version(text)
    return text


def dates() -> tuple[str, str]:
    """(YYYYMMDD, YYYY-MM-DD) — 한 시각에서 둘을 만든다. 폴더 이름과 APP_BUILD_DATE 가 자정에 어긋나지 않게."""
    now = datetime.now()
    return f"{now:%Y%m%d}", now.date().isoformat()


def release_name(yyyymmdd: str, version: str) -> str:
    return f"{yyyymmdd}-v{version}"


def numeric_version(version: str) -> tuple[int, int, int, int]:
    """Windows 버전 리소스의 숫자 4자리 — X.Y.Z.0. 접미(-rc1 등)는 숫자 자리에 들어갈 수 없어 버린다(문자열 항목에만 남는다)."""
    match = _VERSION.match(version)
    if match is None:
        raise ValueError(f"not a release version: {version!r}")
    major, minor, patch = (int(match.group(i)) for i in (1, 2, 3))
    for part in (major, minor, patch):
        if part > 0xFFFF:
            raise ValueError(f"version part exceeds 65535: {version!r}")
    return major, minor, patch, 0


# ============================================================================
#  Windows 버전 리소스 (PyInstaller --version-file)
# ============================================================================
def version_file_text() -> str:
    """exe 속성 > 자세히 탭에 보이는 값 — 주입된 app_info 에서. 버전 문자열은 날짜 없이 버전만 (2026-10-16 결정),
    언어는 영어(1033). PyInstaller 가 eval 하는 파이썬 표현식이라 문자열은 repr 로 넣는다 (© 포함, UTF-8)."""
    version = app_info.APP_VERSION
    numeric = numeric_version(version)
    rows = [
        ("CompanyName", app_info.APP_COMPANY),
        ("FileDescription", app_info.APP_NAME),
        ("FileVersion", version),
        ("InternalName", DEPLOY_DIR_NAME),
        ("LegalCopyright", app_info.APP_COPYRIGHT),
        ("OriginalFilename", APP_EXE_NAME),
        ("ProductName", app_info.APP_NAME),
        ("ProductVersion", version),
    ]
    strings = ",\n".join(f"        StringStruct({key!r}, {value!r})" for key, value in rows)
    return (
        "# UTF-8\n"
        "# build.bat 이 build_support.py version-file 로 만든다 — 손으로 고치지 말 것 (app_info.py 가 원본)\n"
        "VSVersionInfo(\n"
        "  ffi=FixedFileInfo(\n"
        f"    filevers={numeric!r},\n"
        f"    prodvers={numeric!r},\n"
        "    mask=0x3f,\n"
        "    flags=0x0,\n"
        "    OS=0x40004,\n"
        "    fileType=0x1,\n"
        "    subtype=0x0,\n"
        "    date=(0, 0)\n"
        "  ),\n"
        "  kids=[\n"
        "    StringFileInfo([\n"
        "      StringTable('040904B0', [\n"
        f"{strings}])\n"
        "    ]),\n"
        "    VarFileInfo([VarStruct('Translation', [1033, 1200])])\n"
        "  ]\n"
        ")\n"
    )


def write_version_file(out_path: str) -> str:
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    with open(out_path, "w", encoding="utf-8", newline="\n") as f:
        f.write(version_file_text())
    return out_path


# ============================================================================
#  릴리스 zip / 릴리스 노트 항목
# ============================================================================
def make_zip(release_dir: str, name: str) -> str:
    """{release_dir}/NVM2App 의 내용물을 {release_dir}/{name}.zip 으로 — 평평 레이아웃(zip 루트에 NVM2App.exe).
    앱 업데이트의 extract_package 가 1순위로 받는 형태다. 만든 뒤 루트에 exe 가 있는지 확인한다."""
    deploy_dir = os.path.join(release_dir, DEPLOY_DIR_NAME)
    if not os.path.isfile(os.path.join(deploy_dir, APP_EXE_NAME)):
        raise FileNotFoundError(f"deploy folder has no {APP_EXE_NAME}: {deploy_dir}")
    zip_path = shutil.make_archive(os.path.join(release_dir, name), "zip", root_dir=deploy_dir)
    with zipfile.ZipFile(zip_path) as zf:
        if APP_EXE_NAME not in zf.namelist():
            raise RuntimeError(f"{APP_EXE_NAME} is not at the zip root: {zip_path}")
    return zip_path


def note_stub_text(name: str) -> str:
    """version_info.txt 맨 위에 붙일 항목의 머리 — 수정 내용은 사람이 채운다 (최신이 위, 구분선으로 끝)."""
    return f"[VER : {name}]\n1. (modified items)\n{NOTE_SEPARATOR}\n"


def write_note_stub(release_dir: str, name: str) -> str:
    path = os.path.join(release_dir, NOTE_STUB_NAME)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(note_stub_text(name))
    return path


# ============================================================================
#  진입점
# ============================================================================
def main(argv: list[str]) -> int:
    usage = "usage:\n" + "\n".join(__doc__.strip().splitlines()[4:9])
    try:
        if not argv:
            raise ValueError(usage)
        command, args = argv[0], argv[1:]
        if command == "check-version" and len(args) == 1:
            print(check_version(args[0]))
        elif command == "dates" and not args:
            print(" ".join(dates()))
        elif command == "version-file" and len(args) == 1:
            write_version_file(args[0])
        elif command == "zip" and len(args) == 2:
            print(make_zip(*args))
        elif command == "note-stub" and len(args) == 2:
            print(write_note_stub(*args))
        else:
            raise ValueError(usage)
    except (ValueError, OSError, RuntimeError) as error:
        print(f"[build_support] {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
