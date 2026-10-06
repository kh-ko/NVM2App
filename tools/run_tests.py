"""테스트 러너 — tools/tests/test_*.py 를 하나씩 서브프로세스로 돌리고 한 줄씩 요약한다 (개발 환경 전용).

    python tools/run_tests.py                 # 전부
    python tools/run_tests.py --only nv1      # 파일 이름에 'nv1' 이 들어간 것만
    python tools/run_tests.py --list          # 목록만
    python tools/run_tests.py --timeout 900   # 테스트당 제한(초), 기본 600
    python tools/run_tests.py --verbose       # 각 테스트의 출력 전체를 그대로 보인다

테스트마다 새 프로세스 — 싱글턴(ParamManager/ServicePort 등)과 QApplication 이 서로 섞이지 않는다.
각 테스트는 _harness.isolate_runtime() 으로 실제 2_resource/config 를 건드리지 않으며, 러너는 끝에 git status 로
작업 트리가 더러워지지 않았는지 한 번 더 확인한다. 종료 코드: 0 = 전부 통과, 1 = 실패/시간 초과 있음.
"""

from __future__ import annotations

import argparse
import glob
import os
import subprocess
import sys
import time

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
TESTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tests")


def discover(only: str | None) -> list[str]:
    files = sorted(glob.glob(os.path.join(TESTS_DIR, "test_*.py")))
    if only:
        files = [f for f in files if only.lower() in os.path.basename(f).lower()]
    return files


def run_one(path: str, timeout: float, verbose: bool) -> tuple[str, int | None, str, float]:
    """(이름, 종료 코드 | None(시간 초과), 마지막 의미 있는 줄, 소요 초)."""
    env = dict(os.environ, QT_QPA_PLATFORM="offscreen", PYTHONIOENCODING="utf-8", PYTHONUNBUFFERED="1")
    started = time.perf_counter()
    try:
        proc = subprocess.run([sys.executable, path], cwd=ROOT, env=env, capture_output=True,
                              text=True, encoding="utf-8", errors="replace", timeout=timeout)
        code, out = proc.returncode, proc.stdout + proc.stderr
    except subprocess.TimeoutExpired as e:
        code = None
        out = ((e.stdout or b"").decode("utf-8", "replace") if isinstance(e.stdout, bytes) else (e.stdout or "")) + \
              "\n[run_tests] TIMEOUT"
    elapsed = time.perf_counter() - started

    if verbose:
        print(f"\n===== {os.path.basename(path)}\n{out}", flush=True)

    lines = [line.strip() for line in out.splitlines() if line.strip() and not line.startswith("[")]
    last = lines[-1] if lines else ""
    return os.path.basename(path), code, last, elapsed


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", help="파일 이름 부분 일치 필터")
    ap.add_argument("--timeout", type=float, default=600.0, help="테스트당 제한 시간(초)")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()

    files = discover(args.only)
    if args.list:
        for f in files:
            print(os.path.relpath(f, ROOT))
        return 0
    if not files:
        print("실행할 테스트가 없습니다.")
        return 1

    dirty_before = _git_status()
    results = []
    for path in files:
        name = os.path.basename(path)
        print(f"... {name}", flush=True)
        results.append(run_one(path, args.timeout, args.verbose))

    width = max(len(r[0]) for r in results)
    print("\n" + "=" * (width + 48))
    failed = 0
    for name, code, last, elapsed in results:
        if code == 0:
            verdict = "PASS"
        elif code is None:
            verdict = "TIMEOUT"; failed += 1
        else:
            verdict = f"FAIL({code})"; failed += 1
        print(f"{name:<{width}}  {verdict:<9} {elapsed:7.1f}s  {last[:70]}")
    print("=" * (width + 48))

    dirty_after = _git_status()
    newly_dirty = sorted(set(dirty_after) - set(dirty_before))
    if newly_dirty:
        print("작업 트리가 테스트로 더러워졌습니다 (격리 누락):\n  " + "\n  ".join(newly_dirty))
        failed += 1

    print(f"{len(results) - failed} / {len(results)} 통과" + ("" if failed == 0 else f" — {failed} 실패"))
    return 0 if failed == 0 else 1


def _git_status() -> list[str]:
    try:
        out = subprocess.run(["git", "-C", ROOT, "status", "--short"], capture_output=True, text=True,
                             encoding="utf-8", errors="replace", timeout=30)
        return [line for line in out.stdout.splitlines() if line.strip()]
    except (OSError, subprocess.TimeoutExpired):
        return []


if __name__ == "__main__":
    sys.exit(main())
