"""테스트 하네스 — tools/tests 의 스크립트가 공유하는 받침대 (배포 앱과 무관, 개발 환경 전용).

테스트가 '무엇을 확인할지' 가 아니라, 테스트가 안전하고 같은 조건에서 돌아가게 하는 주변 장치를 모은다
(2026-09-28 코드 검토 보고서 5절 5위). 지금까지 scratchpad 의 _env.py / FakeSerial / Report 복사본으로
임시로 하던 것을 한 곳에 둔다.

- isolate_runtime()      : 설정·로그·펌웨어 캐시 경로를 임시 폴더로 돌린다 — 실제 2_resource/config 를 더럽히지 않는다.
                           매니저 3종(AppLog/LocalSetting/ConnectionSetting)·ServicePort·펌웨어 창은 호출 시점에
                           path_def 를 읽으므로 앱 코드 수정 없이 동작한다. 반드시 b_core 매니저 import 전에 부른다.
                           임시 폴더는 프로세스 종료 때 지운다 (F106/N131 — %TEMP% 누적 없음).
- Report                 : 검사 수 / 실패 수 / 메모 집계와 결과 출력 (파일마다 복사되던 클래스의 단일본, F107).
- make_app()             : offscreen QApplication (이미 있으면 그것).
- fake_connected(svc)    : ServicePort 를 '연결된 것처럼' 두는 컨텍스트 — 포트는 열지 않는다. transport 를 주입하지 않은
                           워커는 큐 구성만 보고 _stop_all() 로 멈추고, ScriptedTransport 를 주입하면(F110) 상태 전이를 끝까지 돌린다.
- destroy_window(win)    : 창을 WA_DeleteOnClose 로 닫아 파괴한다 (closeEvent 가 워커 cleanup).
- emit_signals_capture() : 시그널(또는 호출 가능 항목)을 차례로 쏘며 excepthook/stderr 의 'already deleted'/RuntimeError 를 모은다.
- assert_no_zombie()     : 위 둘의 합성 — 창을 만들었다 파괴한 뒤 싱글턴 시그널을 쏴서 파괴된 창의 슬롯이 남아 있지 않은지
                           (좀비 연결, F111) 확인한다. 문제가 있으면 그 내용을 돌려준다.
- silence_message_boxes(): QMessageBox 정적 대화상자와 QMessageBox/QDialog 의 exec() 를 무음으로 — 헤드리스 창 테스트용.

사용 (각 테스트 머리):
    TOOLS = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    sys.path.insert(0, TOOLS)
    import _harness
    ROOT = _harness.ROOT
    _harness.isolate_runtime()
    sys.path.insert(0, ROOT)
    ... 이후 b_core / c_ui import

실행은 tools/run_tests.py (테스트마다 서브프로세스) 또는 개별 스크립트.
가짜 serial.Serial 은 하네스에 두지 않는다 — 통신 대역은 워커의 transport 주입(F110)으로 다룬다.
"""

from __future__ import annotations

import atexit
import contextlib
import io
import os
import shutil
import sys
import tempfile
import traceback

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
TOOLS_DIR = os.path.dirname(os.path.abspath(__file__))
FIXTURES_DIR = os.path.join(TOOLS_DIR, "fixtures")

_runtime_dir: tempfile.TemporaryDirectory | None = None
_CONFIG_FILES = ("local_setting.json", "connections.json", "ftp_connection.json")


# ------------------------------------------------------------ 런타임 격리
def isolate_runtime(name: str = "nvm2app_test", copy_config: bool = True) -> str:
    """path_def 의 설정/로그/펌웨어 캐시 경로를 임시 폴더로 돌리고 그 폴더를 돌려준다 (멱등 — 두 번 부르면 같은 폴더).

    copy_config: 실제 2_resource/config 의 json 3개를 사본으로 복사한다 (False 면 빈 폴더 — 매니저가 기본값으로 시작).
    주의: b_core 매니저를 import 하기 전에 불러야 한다. 이미 만들어진 싱글턴은 옛 경로를 캐시하고 있을 수 있다."""
    global _runtime_dir
    if _runtime_dir is not None:
        return _runtime_dir.name

    if ROOT not in sys.path:
        sys.path.insert(0, ROOT)
    from b_core.a_define import file_folder_path as path_def  # noqa: E402  (매니저 아님 — 상수 모듈)

    _runtime_dir = tempfile.TemporaryDirectory(prefix=f"{name}_", ignore_cleanup_errors=True)
    atexit.register(_cleanup_runtime)
    base = _runtime_dir.name

    config_dir = os.path.join(base, "config")
    os.makedirs(config_dir)
    if copy_config:
        for file_name in _CONFIG_FILES:
            src = os.path.join(ROOT, "2_resource", "config", file_name)
            if os.path.isfile(src):
                shutil.copy(src, os.path.join(config_dir, file_name))

    path_def.LOG_PATH = os.path.join(base, "log")
    path_def.RSRC_CONFIG_PATH = config_dir
    path_def.RSRC_LOCAL_SETTING_JSON_FILE = os.path.join(config_dir, "local_setting.json")
    path_def.RSRC_CONNECTIONS_JSON_FILE = os.path.join(config_dir, "connections.json")
    path_def.RSRC_FTP_SETTING_FILE = os.path.join(config_dir, "ftp_connection.json")
    # 펌웨어 다운로드 캐시(temp) 도 격리 — 커널(firmware/)은 읽기 전용 배포 자산이라 그대로 둔다
    path_def.RSRC_TEMP_PATH = os.path.join(base, "temp")
    path_def.RSRC_APP_CPU1_NEW_FILE = os.path.join(path_def.RSRC_TEMP_PATH, "fcpuan.dlla")
    path_def.RSRC_APP_CPU2_NEW_FILE = os.path.join(path_def.RSRC_TEMP_PATH, "fcpubn.dlla")
    path_def.RSRC_APP_CPU1_FILE = os.path.join(path_def.RSRC_TEMP_PATH, "fcpua.dlla")
    path_def.RSRC_APP_CPU2_FILE = os.path.join(path_def.RSRC_TEMP_PATH, "fcpub.dlla")
    return base


def runtime_dir() -> str | None:
    """isolate_runtime() 이 만든 폴더 (아직이면 None)."""
    return None if _runtime_dir is None else _runtime_dir.name


def assert_isolated() -> None:
    """실제 2_resource/config · 3_log 를 가리키는 경로 상수가 남아 있으면 AssertionError — 테스트 끝에서 한 번 부른다."""
    from b_core.a_define import file_folder_path as path_def

    real = os.path.normcase(os.path.join(ROOT, "2_resource"))
    for attr in ("LOG_PATH", "RSRC_CONFIG_PATH", "RSRC_LOCAL_SETTING_JSON_FILE",
                 "RSRC_CONNECTIONS_JSON_FILE", "RSRC_FTP_SETTING_FILE", "RSRC_TEMP_PATH"):
        value = os.path.normcase(getattr(path_def, attr))
        assert not value.startswith(real) and not value.startswith(os.path.normcase(os.path.join(ROOT, "3_log"))), \
            f"{attr} 가 실제 경로를 가리킨다: {value}"


def _cleanup_runtime() -> None:
    global _runtime_dir
    if _runtime_dir is not None:
        _close_log_file()
        _runtime_dir.cleanup()
        _runtime_dir = None


def _close_log_file() -> None:
    """AppLogManager 가 열어 둔 로그 파일을 닫고 이번 실행의 파일 기록을 끝낸다 — Windows 는 열린 파일이 있는 폴더를
    지우지 못해 임시 폴더가 남는다 (하네스 전용으로 매니저의 내부 필드를 만진다)."""
    mod = sys.modules.get("b_core.c_manager.app_log_manager")
    manager = getattr(mod, "AppLogManager", None)
    inst = getattr(manager, "_instance", None)
    if inst is None or not getattr(inst, "_initialized", False):
        return
    with inst._lock:
        if inst._file is not None:
            try:
                inst._file.close()
            except Exception:
                pass
            inst._file = None
        inst._file_failed = True  # 종료 중의 늦은 로그가 폴더를 다시 만들지 않게


# ------------------------------------------------------------ 결과 집계
class Report:
    """check(ok, msg) 로 세고 summary() 로 끝낸다. 실패 메시지는 처음 max_fail_lines 개만 바로 출력한다."""

    def __init__(self, max_fail_lines: int = 30):
        self.checks = 0
        self.fail = 0
        self.notes: list[str] = []
        self._max_fail_lines = max_fail_lines

    def check(self, ok: bool, msg: str) -> bool:
        self.checks += 1
        if not ok:
            self.fail += 1
            if self.fail <= self._max_fail_lines:
                print(f"  FAIL {msg}", flush=True)
            elif self.fail == self._max_fail_lines + 1:
                print(f"  ... (이후 실패 메시지 생략, 집계는 계속)", flush=True)
        return ok

    def note(self, msg: str) -> None:
        self.notes.append(msg)

    def summary(self) -> int:
        """메모와 집계를 출력하고 종료 코드(0 = 전부 통과)를 돌려준다. 마지막 줄 형식은 run_tests.py 가 읽는다."""
        for note in self.notes:
            print(f"  note: {note}")
        print(f"\nchecks {self.checks:,}  fail {self.fail}  → {'ALL PASS' if self.fail == 0 else 'FAILED'}", flush=True)
        return 0 if self.fail == 0 else 1


# ------------------------------------------------------------ Qt / ServicePort
def make_app():
    """offscreen QApplication — 이미 있으면 그것을 돌려준다. 창을 만들기 전에 부른다."""
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication

    return QApplication.instance() or QApplication(sys.argv)


@contextlib.contextmanager
def fake_connected(svc, info: str = "test"):
    """ServicePort 를 연결 상태로 보이게 한다 (포트는 열지 않는다, 시그널 없음).

    워커의 refresh()/write() 가 NOT_CONNECTED 가 아닌 경로를 타게 한다. transport 를 주입하지 않은 워커는 요청이 즉시
    실패하므로 큐만 보고 _stop_all() 로 멈추고, ScriptedTransport 를 주입하면(F110, test_worker_state) 상태 전이를 끝까지
    돌릴 수 있다. 블록을 나가면 미연결로 되돌린다."""
    svc._connect_info = info
    try:
        yield svc
    finally:
        svc._connect_info = ""


def destroy_window(win, app=None) -> None:
    """창을 닫아 파괴한다 (WA_DeleteOnClose + DeferredDelete 처리) — closeEvent 가 워커 cleanup 을 수행한다."""
    from PySide6.QtCore import QCoreApplication, QEvent, Qt

    app = app or make_app()
    win.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
    if not win.isVisible():
        win.show()
    app.processEvents()
    win.close()
    app.processEvents()
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    app.processEvents()


def emit_signals_capture(signals, app=None, process_events_each: bool = True) -> list[str]:
    """signals 를 차례로 발화하면서 슬롯 예외를 모은다 (빈 목록 = 정상).

    파괴된 창의 슬롯이 싱글턴 시그널에 남아 있으면(좀비 연결, F111) PySide6 가 'Internal C++ object already deleted'
    RuntimeError 를 내는데, 이를 sys.excepthook 과 stderr 양쪽에서 잡는다.
    signals: 인자 없이 emit() 할 수 있는 시그널, (signal, args 튜플), 또는 인자 없는 호출 가능 객체(시그널을 내는 호출)의 목록.
    process_events_each: 항목마다 processEvents (기본). 수천 개를 쏠 때는 False 로 두고 끝에 한 번 처리한다."""
    app = app or make_app()
    problems: list[str] = []
    captured = io.StringIO()
    old_hook = sys.excepthook

    def hook(exc_type, exc, tb):
        problems.append("".join(traceback.format_exception(exc_type, exc, tb)).strip())

    sys.excepthook = hook
    try:
        with contextlib.redirect_stderr(captured):
            for entry in signals:
                if callable(entry) and not hasattr(entry, "emit"):
                    entry()
                else:
                    signal, args = (entry if isinstance(entry, tuple) else (entry, ()))
                    signal.emit(*args)
                if process_events_each:
                    app.processEvents()
            app.processEvents()
    finally:
        sys.excepthook = old_hook

    text = captured.getvalue()
    if "already deleted" in text or "RuntimeError" in text:
        problems.append(text.strip())
    return problems


def assert_no_zombie(win_factory, signals, app=None) -> list[str]:
    """창을 만들고 파괴한 뒤 signals 를 발화해 좀비 연결 문제 목록을 돌려준다 (destroy_window + emit_signals_capture)."""
    app = app or make_app()
    destroy_window(win_factory(), app)
    return emit_signals_capture(signals, app)


def silence_message_boxes() -> None:
    """모달 대화상자가 헤드리스 이벤트 루프를 삼키지 않게 한다 (프로세스 전체).

    - QMessageBox 정적 대화상자(information/warning/critical)는 Ok, question 은 '아니오' 쪽(StandardButton.No).
    - 인스턴스 exec()(QMessageBox / QDialog)는 즉시 0(Rejected) 으로 돌아온다 — clickedButton() 은 None 이므로
      x_message 의 ask_* 함수들은 '닫음' 분기를 탄다. 특정 답이 필요한 테스트는 해당 ask_* 를 직접 스텁한다."""
    from PySide6.QtWidgets import QDialog, QMessageBox

    QMessageBox.information = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Ok)
    QMessageBox.warning = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Ok)
    QMessageBox.critical = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Ok)
    QMessageBox.question = staticmethod(lambda *a, **k: QMessageBox.StandardButton.No)
    QMessageBox.exec = lambda self: 0
    QDialog.exec = lambda self: 0
