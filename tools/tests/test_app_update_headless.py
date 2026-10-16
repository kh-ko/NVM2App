"""앱 업데이트 헬퍼 헤드리스 테스트 — 버전 판정·이름 검증·압축 해제 정리와 교체 스크립트의 트랜잭션을 장비·FTP 없이 확인한다.

    python tools/tests/test_app_update_headless.py

검사 항목
  1. is_installed_version: [YYYYMMDD-][v]<버전> 분해 — 하이픈 버전(1.0.0-rc1) 일치, 빌드 날짜가 있으면 날짜까지 비교 (F034/N060)
  2. is_valid_version_name: 영숫자·점·밑줄·하이픈만, '.'/'..'·경로 구분자·공백 거부 (N061)
  3. extract_package: 평평한 zip / 폴더째 zip(안쪽을 한 단계 올림) → 패키지 루트 = 압축 해제 폴더, zip 삭제; exe 없는 zip → 예외 +
     폴더 정리; discard_package 는 폴더·zip·.part 를 지우고 없으면 조용 (F037)
  4. 교체 스크립트(_build_install_script 본문을 실제 cmd 로): 가짜 앱 폴더(더미 exe, _internal, 2_resource\\temp, 3_log)와 패키지로
     - 정상 교체: exe/_internal/2_resource 통째 교체(구버전 전용 파일 사라짐), temp 보존, 3_log 그대로, .update_* /저널/패키지/스크립트 정리
     - 교체 도중 실패(_internal 안의 파일을 열어 둠): exit 5, 앱 폴더 원상 복구, 저널에 기록, .update_* 정리
     - 중단 복구: .update_old 가 남은 채 재기동 → 먼저 되돌린 뒤 새로 설치
     - exe 잠금: 앱 종료(잠금 해제)를 기다렸다 진행
     - 환경변수 없이 직접 실행: exit 1, 변경 없음
     - 되돌리기 실패(새 항목 안의 파일이 열려 있음): exit 6, 옛 파일은 .update_old 에 유지, 새 설치 시작 안 함; 재실행하면 먼저 되돌림
     - 확정 잔재(저널에 committed 인 .update_old): 되돌리지 않고 삭제; 읽기 전용 exe 도 교체
     재실행은 NVM2APP_SKIP_RESTART 로 건너뛴다 (실제 배포 exe 의 재실행·FTP 경로는 수동 검증).
  5. app_temp_helper.sweep_stale_update_files: 폴더 없음 → (0, 0); 1시간 넘은 폴더·파일만 삭제, 새 것은 유지
"""

from __future__ import annotations

import ctypes
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import zipfile

TOOLS = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, TOOLS)
import _harness  # noqa: E402

ROOT = _harness.ROOT
_harness.isolate_runtime()
sys.path.insert(0, ROOT)

from b_core.a_define import app_info  # noqa: E402
from b_core.a_define import file_folder_path as path_def  # noqa: E402
from b_core.f_helper import app_update_helper as helper  # noqa: E402

EXE = helper.APP_EXE_NAME

# 공유 모드 0 으로 열어 둔다 — 실행 중 exe(쓰기 불가)·폴더 안의 열린 파일(이름 바꾸기 불가) 흉내
_k32 = ctypes.windll.kernel32
_k32.CreateFileW.restype = ctypes.c_void_p
_k32.CloseHandle.argtypes = [ctypes.c_void_p]
_INVALID = ctypes.c_void_p(-1).value


def hold_exclusive(path: str):
    handle = _k32.CreateFileW(path, 0x80000000, 0, None, 3, 0x80, None)
    assert handle and handle != _INVALID, f"CreateFile failed: {path} ({ctypes.GetLastError()})"
    return handle


def write(path: str, text: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def listing(root: str) -> dict[str, str]:
    out = {}
    for d, _, files in os.walk(root):
        for name in files:
            path = os.path.join(d, name)
            with open(path, encoding="utf-8", errors="replace") as f:
                out[os.path.relpath(path, root).replace("\\", "/")] = f.read()
    return out


def make_app(root: str, version: str) -> str:
    app = os.path.join(root, "app")
    write(os.path.join(app, EXE), f"exe {version}")
    write(os.path.join(app, "_internal", "lib.dll"), f"lib {version}")
    if version == "old":
        write(os.path.join(app, "_internal", "old_only.dll"), "stale")
    write(os.path.join(app, "2_resource", "config", "a.json"), f"cfg {version}")
    write(os.path.join(app, "2_resource", "temp", "cache.bin"), "cache")   # 보존 대상
    write(os.path.join(app, "3_log", "x.log"), "log")                       # 패키지에 없음 → 그대로
    return app


def make_pkg(root: str, version: str) -> str:
    pkg = os.path.join(root, "pkg", "0.0.2")
    write(os.path.join(pkg, EXE), f"exe {version}")
    write(os.path.join(pkg, "_internal", "lib.dll"), f"lib {version}")
    write(os.path.join(pkg, "_internal", "new_only.dll"), "fresh")
    write(os.path.join(pkg, "2_resource", "config", "a.json"), f"cfg {version}")
    return pkg


def run_script(app: str, pkg: str, no_env: bool = False, timeout: float = 120):
    """실제 _build_install_script 본문을 임시 파일로 써서 cmd 로 돌린다 (start_install_script 와 같은 명령줄·환경변수)."""
    script_dir = tempfile.mkdtemp(prefix="nvm2app_upd_test_")
    script = os.path.join(script_dir, helper.INSTALL_SCRIPT_NAME)
    with open(script, "w", encoding="ascii", newline="\r\n") as f:
        f.write(helper._build_install_script())
    env = dict(os.environ)
    if not no_env:
        env.update({"NVM2APP_APP_DIR": app, "NVM2APP_EXE_NAME": EXE, "NVM2APP_SRC_DIR": pkg, "NVM2APP_SKIP_RESTART": "1"})
    proc = subprocess.run(f'cmd.exe /s /c ""{script}""', cwd=script_dir, env=env, stdin=subprocess.DEVNULL,
                          capture_output=True, text=True, timeout=timeout)
    script_left = os.path.exists(script)
    shutil.rmtree(script_dir, ignore_errors=True)
    return proc.returncode, proc.stdout, script_left


def main() -> int:
    rep = _harness.Report()

    # ---------------------------------------------------------------- 1. is_installed_version
    saved = (app_info.APP_VERSION, app_info.APP_BUILD_DATE)
    try:
        app_info.APP_VERSION, app_info.APP_BUILD_DATE = "0.0.2", ""
        for name, expected in (("20260616-v0.0.2", True), ("v0.0.2", True), ("0.0.2", True), ("V0.0.2", True),
                               ("0.0.3", False), ("20260616-v0.0.20", False), ("", False)):
            rep.check(helper.is_installed_version(name) is expected, f"installed(빌드 날짜 없음) {name!r} → {expected}")
        app_info.APP_VERSION = "1.0.0-rc1"
        rep.check(helper.is_installed_version("20260616-v1.0.0-rc1") and helper.is_installed_version("1.0.0-rc1"),
                  "하이픈 버전 1.0.0-rc1 도 일치 (F034)")
        app_info.APP_VERSION, app_info.APP_BUILD_DATE = "0.0.2", "2026-06-16"
        for name, expected in (("20260616-v0.0.2", True), ("20260617-v0.0.2", False), ("v0.0.2", True)):
            rep.check(helper.is_installed_version(name) is expected, f"installed(빌드 날짜 2026-06-16) {name!r} → {expected} (N060)")
    finally:
        app_info.APP_VERSION, app_info.APP_BUILD_DATE = saved

    # ---------------------------------------------------------------- 2. is_valid_version_name
    for name, expected in (("20260616-v0.0.2", True), ("v1.0.0-rc1", True), ("a_b.c", True),
                           (".", False), ("..", False), ("a/b", False), ("a\\b", False), ("x y", False), ("", False), ("../x", False),
                           ("v0.0.2\n", False)):
        rep.check(helper.is_valid_version_name(name) is expected, f"valid name {name!r} → {expected} (N061)")

    # ---------------------------------------------------------------- 3. extract_package / discard_package (작업 폴더는 isolate_runtime 이 격리)
    os.makedirs(path_def.APP_TEMP_UPDATE_PATH, exist_ok=True)

    def make_zip(version: str, folder_wrapped: bool, with_exe: bool = True) -> str:
        path = helper.local_package_path(version)
        prefix = "NVM2App/" if folder_wrapped else ""
        with zipfile.ZipFile(path, "w") as zf:
            if with_exe:
                zf.writestr(prefix + EXE, "exe")
            zf.writestr(prefix + "_internal/lib.dll", "lib")
            zf.writestr(prefix + "2_resource/config/a.json", "cfg")
        return path

    rep.check(helper.local_package_path("x").startswith(path_def.APP_TEMP_UPDATE_PATH), "작업 폴더 = path_def.APP_TEMP_UPDATE_PATH (호출 시점)")
    root = helper.extract_package(make_zip("flat", False), "flat")
    rep.check(root == helper.local_extract_dir("flat") and os.path.isfile(os.path.join(root, EXE))
              and not os.path.exists(helper.local_package_path("flat")), "평평한 zip: 루트 = 압축 해제 폴더, zip 삭제")
    root = helper.extract_package(make_zip("wrapped", True), "wrapped")
    rep.check(root == helper.local_extract_dir("wrapped") and os.path.isfile(os.path.join(root, EXE))
              and os.path.isfile(os.path.join(root, "2_resource", "config", "a.json"))
              and not os.path.isdir(os.path.join(root, "NVM2App")), "폴더째 zip: 안쪽을 한 단계 올려 루트 = 압축 해제 폴더 (F037)")
    try:
        helper.extract_package(make_zip("noexe", False, with_exe=False), "noexe")
        rep.check(False, "exe 없는 zip → 예외")
    except RuntimeError:
        rep.check(not os.path.exists(helper.local_extract_dir("noexe")), "exe 없는 zip → 예외 + 압축 해제 폴더 정리 (F037)")
    write(helper.local_package_path("left") + ".part", "half")
    make_zip("left", False)                                        # zip 은 풀지 않은 채 (다운로드 직후 중단 흉내)
    os.makedirs(helper.local_extract_dir("left"))                  # 폴더도 함께
    helper.discard_package("left")
    rep.check(not os.path.exists(helper.local_extract_dir("left")) and not os.path.exists(helper.local_package_path("left"))
              and not os.path.exists(helper.local_package_path("left") + ".part"), "discard_package: 폴더·zip·.part 삭제")
    try:
        helper.discard_package("never")
        quiet = True
    except OSError:
        quiet = False
    rep.check(quiet, "discard_package: 없는 이름은 예외 없이 조용히")

    # ---------------------------------------------------------------- 4. 교체 스크립트 (실제 cmd)
    with tempfile.TemporaryDirectory() as root:
        app, pkg = make_app(root, "old"), make_pkg(root, "new")
        rc, out, script_left = run_script(app, pkg)
        files = listing(app)
        rep.check(rc == 0, f"정상 교체: exit {rc}\n{out[-400:] if rc else ''}")
        rep.check(files.get(EXE) == "exe new" and files.get("_internal/lib.dll") == "lib new" and files.get("_internal/new_only.dll") == "fresh"
                  and "_internal/old_only.dll" not in files, f"정상 교체: exe/_internal 통째 교체 (구버전 전용 파일 사라짐): {sorted(files)}")
        rep.check(files.get("2_resource/config/a.json") == "cfg new" and files.get("2_resource/temp/cache.bin") == "cache"
                  and files.get("3_log/x.log") == "log", "정상 교체: 2_resource 교체 + temp 보존 + 3_log 그대로")
        rep.check(not os.path.exists(os.path.join(app, ".update_old")) and not os.path.exists(os.path.join(app, ".update_new"))
                  and not os.path.exists(os.path.join(app, ".update_journal")) and not os.path.exists(pkg) and not script_left,
                  "정상 교체: .update_old/.update_new/저널/패키지/스크립트 정리")

    with tempfile.TemporaryDirectory() as root:
        app, pkg = make_app(root, "old"), make_pkg(root, "new")
        before = listing(app)
        handle = hold_exclusive(os.path.join(app, "_internal", "lib.dll"))   # 2_resource 는 바뀐 뒤 _internal 에서 실패
        try:
            rc, out, _ = run_script(app, pkg)
        finally:
            _k32.CloseHandle(handle)
        after = listing(app)
        journal = after.pop(".update_journal", "")
        rep.check(rc == 5, f"교체 실패: exit {rc} (5 = 되돌림)\n{out[-500:] if rc != 5 else ''}")
        rep.check(after == before, f"교체 실패: 앱 폴더 원상 복구 (차이 {sorted(set(after.items()) ^ set(before.items()))})")
        rep.check("swap failed" in journal and "restored 2_resource" in journal and 'src="' in journal and "committed" not in journal,
                  f"교체 실패: 저널에 기록 (경로는 따옴표 안, committed 없음)\n{journal}")
        rep.check(not os.path.exists(os.path.join(app, ".update_old")) and not os.path.exists(os.path.join(app, ".update_new")),
                  "교체 실패: .update_old/.update_new 정리")

    with tempfile.TemporaryDirectory() as root:
        app, pkg = make_app(root, "old"), make_pkg(root, "new")
        os.makedirs(os.path.join(app, ".update_old"))                          # 전원 차단 흉내: 옛 2_resource 는 .update_old 에,
        shutil.move(os.path.join(app, "2_resource"), os.path.join(app, ".update_old", "2_resource"))
        write(os.path.join(app, "2_resource", "config", "a.json"), "cfg half")   # 앱 폴더에는 반쯤 새것(temp 없음)
        write(os.path.join(app, ".update_journal"), 'update started: src="x"\nstaged\nold 2_resource\n')   # committed 없음
        rc, out, _ = run_script(app, pkg)
        files = listing(app)
        rep.check(rc == 0 and "interrupted" in out, f"중단 복구: 남은 .update_old 를 먼저 되돌린 뒤 진행 (exit {rc})")
        rep.check(files.get("2_resource/config/a.json") == "cfg new" and files.get("2_resource/temp/cache.bin") == "cache",
                  f"중단 복구: 최종 상태 = 새 설치 + temp 보존: {sorted(files)}")

    with tempfile.TemporaryDirectory() as root:
        app, pkg = make_app(root, "old"), make_pkg(root, "new")
        handle = hold_exclusive(os.path.join(app, EXE))
        threading.Timer(2.5, lambda: _k32.CloseHandle(handle)).start()
        rc, out, _ = run_script(app, pkg)
        rep.check(rc == 0 and "Waiting for the application to exit" in out, f"exe 잠금: 해제를 기다렸다 진행 (exit {rc})")

    with tempfile.TemporaryDirectory() as root:
        app, pkg = make_app(root, "old"), make_pkg(root, "new")
        before = listing(app)
        rc, out, _ = run_script(app, pkg, no_env=True)
        rep.check(rc == 1 and listing(app) == before and os.path.isdir(pkg), f"직접 실행: exit {rc}, 변경 없음")

    with tempfile.TemporaryDirectory() as root:
        # 되돌리기 실패: 남은 .update_old 의 2_resource 를 되돌려야 하는데 앱 폴더의 새 2_resource 안 파일이 열려 있다
        app, pkg = make_app(root, "old"), make_pkg(root, "new")
        os.makedirs(os.path.join(app, ".update_old"))
        shutil.move(os.path.join(app, "2_resource"), os.path.join(app, ".update_old", "2_resource"))
        write(os.path.join(app, "2_resource", "config", "a.json"), "cfg half")
        write(os.path.join(app, ".update_journal"), 'update started: src="x"\nstaged\nold 2_resource\n')
        handle = hold_exclusive(os.path.join(app, "2_resource", "config", "a.json"))
        try:
            rc, out, _ = run_script(app, pkg)
        finally:
            _k32.CloseHandle(handle)
        files = listing(app)
        journal = files.get(".update_journal", "")
        rep.check(rc == 6 and files.get(".update_old/2_resource/config/a.json") == "cfg old"
                  and files.get(".update_old/2_resource/temp/cache.bin") == "cache",
                  f"되돌리기 실패: exit {rc} (6), 옛 파일은 .update_old 에 그대로\n{out[-500:] if rc != 6 else ''}")
        rep.check("restore failed 2_resource" in journal and "rollback failed" in journal, f"되돌리기 실패: 저널에 기록\n{journal}")
        rep.check(files.get(EXE) == "exe old" and files.get("_internal/lib.dll") == "lib old", "되돌리기 실패: 새 설치는 시작하지 않음")
        rc, out, _ = run_script(app, pkg)                                        # 잠금이 풀린 뒤 다시: 먼저 되돌리고 새로 설치
        files = listing(app)
        rep.check(rc == 0 and "interrupted" in out and files.get("2_resource/config/a.json") == "cfg new"
                  and files.get("2_resource/temp/cache.bin") == "cache" and files.get(EXE) == "exe new"
                  and not os.path.exists(os.path.join(app, ".update_old")) and ".update_journal" not in files,
                  f"되돌리기 실패 뒤 재실행: 먼저 되돌리고 새로 설치 (exit {rc})")

    with tempfile.TemporaryDirectory() as root:
        # 확정된 뒤 삭제가 덜 끝난 .update_old (저널에 committed) → 되돌리지 않고 지운다; 읽기 전용 exe 도 교체된다
        app, pkg = make_app(root, "old"), make_pkg(root, "new")
        write(os.path.join(app, ".update_old", "3_log", "extra.log"), "would reappear if rolled back")
        write(os.path.join(app, ".update_journal"), 'update started: src="x"\nstaged\nold 3_log\nnew 3_log\ncommitted\n')
        os.chmod(os.path.join(app, EXE), 0o444)
        rc, out, _ = run_script(app, pkg)
        files = listing(app)
        rep.check(rc == 0 and "interrupted" not in out and "3_log/extra.log" not in files and files.get(EXE) == "exe new"
                  and not os.path.exists(os.path.join(app, ".update_old")) and ".update_journal" not in files,
                  f"확정 잔재: 되돌리지 않고 삭제, 읽기 전용 exe 교체 (exit {rc})")

    # ---------------------------------------------------------------- 5. 기동 시 임시 잔재 정리 (app_temp_helper)
    from b_core.f_helper import app_temp_helper  # noqa: E402
    upd = path_def.APP_TEMP_UPDATE_PATH
    shutil.rmtree(upd, ignore_errors=True)
    rep.check(app_temp_helper.sweep_stale_update_files() == (0, 0), "sweep: 폴더가 없으면 (0, 0)")
    write(os.path.join(upd, "old_pkg", EXE), "x")
    write(os.path.join(upd, "old.zip"), "x")
    write(os.path.join(upd, "fresh.zip"), "x")
    old = time.time() - app_temp_helper.STALE_AFTER_SEC - 60
    os.utime(os.path.join(upd, "old_pkg"), (old, old))
    os.utime(os.path.join(upd, "old.zip"), (old, old))
    rep.check(app_temp_helper.sweep_stale_update_files() == (2, 0) and sorted(os.listdir(upd)) == ["fresh.zip"],
              f"sweep: 1시간 넘은 폴더·파일만 삭제, 새 것은 유지: {sorted(os.listdir(upd))}")

    _harness.assert_isolated()
    return rep.summary()


if __name__ == "__main__":
    sys.exit(main())
