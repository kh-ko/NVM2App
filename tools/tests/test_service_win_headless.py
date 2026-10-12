"""ServiceWin 골격 헤드리스 테스트 — 계약(2단계 초기화·잠금 단일 지점·본문 교체·선택 구성)과 그 위의 창 7개를 장비 없이 확인한다.

    python tools/tests/test_service_win_headless.py

검사 항목
  1. 계약(합성 서브클래스 3종): 생성만으로는 start 훅이 불리지 않음, start() 멱등·on_start 1회, has_refresh / with_param_worker /
     locks_content, 워커 동작(is_working) → 본문·locked_actions 잠김, set_body 교체 뒤 잠금 재확정, 편집 잠금(edit_locked_actions ·
     Enable Edit 은 동작 중만 잠김 · 동작이 끝나면 다시 잠김), 파괴 뒤 좀비 연결 없음.
  2. 창 7개(2단계 ②·data-protocol-2): Backup/Restore 는 워커 시퀀스(capture/raw_write)로 돌며 is_working 으로 잠기고 Abort 만 살아 있다 —
     ScriptedTransport 로 끝까지 돌려 재시도 상한·누락 질문·부분 파일·늦은 응답 재시도(F086)·거부 즉시 실패·Abort·끊김 보고를 본다.
     Restore(FU 모드)의 start() 뒤 자동 로드, Sensor Analysis 의 샘플 타이머가 start() 의 연결 동기화로 시작하고 끊김에 정지, Cluster Monitor 의 set_body 잠금 · Apply
     표시, Firmware Update 의 폴더 카드 1 · 표시 전용 본문(locks_content=False) · Refresh 없음, About/Update 의 param 워커 없음 · 상태바,
     Update 의 릴리스 노트 조회가 on_start 에서 시작(FTP 는 스텁), 클래스 기본값·'항상 활성' 오버라이드 잔존 없음,
     파괴 뒤 connect_info_changed 좀비 없음.
통신은 없다 — 워커 동작은 param_worker.is_working 대입(setter 가 시그널을 낸다)으로, 연결은 _harness.fake_connected 로, 장비 응답은
_harness.ScriptedTransport 를 워커 스레드의 transport 자리에 꽂아 흉내 낸다.
"""

from __future__ import annotations

import os
import sys
import tempfile
import threading
import time

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

TOOLS = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, TOOLS)
import _harness  # noqa: E402

ROOT = _harness.ROOT
_harness.isolate_runtime()  # 실제 2_resource/config · 3_log 를 건드리지 않는다 — 매니저 import 전에
sys.path.insert(0, ROOT)

app = _harness.make_app()
_harness.silence_message_boxes()

from PySide6.QtCore import Qt  # noqa: E402
from PySide6.QtWidgets import QFileDialog, QMessageBox, QTreeWidget  # noqa: E402

import resources_rc  # noqa: E402,F401
from b_core.d_dal.service_port import ServicePort  # noqa: E402
from b_core.e_worker_ver2.parameter_run_worker import SequenceEnd  # noqa: E402
from b_core.f_helper import backup_file_helper  # noqa: E402
from b_core.g_protocol.spec_registry import SpecRegistry  # noqa: E402
from c_ui.c_window_ver2.param_win import ParamWin  # noqa: E402
from c_ui.c_window_ver2.service_win import ServiceWin  # noqa: E402
from c_ui.c_window_ver2.c_analysis.sensor_analysis_win import SensorAnalysisWin  # noqa: E402
from c_ui.c_window_ver2.d_backup_restore import backup_win as backup_win_mod  # noqa: E402
from c_ui.c_window_ver2.d_backup_restore.backup_win import BackupWin  # noqa: E402
from c_ui.c_window_ver2.d_backup_restore.restore_win import RestoreWin  # noqa: E402
from c_ui.c_window_ver2.f_cluster.cluster_monitor_win import ClusterMonitorWin  # noqa: E402
from c_ui.c_window_ver2.g_factory.factory_firmware_update_win import FactoryFirmwareUpdateWin  # noqa: E402
from c_ui.c_window_ver2.h_help import help_nvm_update_win as update_mod  # noqa: E402
from c_ui.c_window_ver2.h_help.help_about_win import HelpAboutWin  # noqa: E402
from c_ui.c_window_ver2.h_help.help_nvm_update_win import HelpNvmUpdateWin  # noqa: E402


# ------------------------------------------------------------ 합성 서브클래스 (계약 검사용)
class TreeWin(ServiceWin):
    """Backup 창 모양 — 트리 본문, Backup 액션은 워커 동작 중 잠김, Refresh 없음."""

    def __init__(self, parent=None):
        super().__init__(parent, "TreeWin", has_refresh=False)
        self.toolbar.add_action("Backup", self.on_clicked_backup)
        self.tree = QTreeWidget(self)
        self.set_body(self.tree)
        self.started = 0

    def on_clicked_backup(self):
        pass

    def locked_actions(self):
        return ("Backup",)

    def on_start(self):
        self.started += 1


class EditWin(ServiceWin):
    """편집 잠금 창 모양 — Apply 는 편집 잠금·워커 동작 중 잠김, Enable Edit 은 워커 동작 중만 잠김."""

    def __init__(self, parent=None):
        super().__init__(parent, "EditWin")
        self.toolbar.add_action("Apply", self.on_clicked_apply)
        self.toolbar.add_action("Enable Edit", self.on_clicked_enable_edit)
        self.set_body(QTreeWidget(self))
        self.set_edit_locked(True)

    def on_clicked_apply(self):
        pass

    def on_clicked_enable_edit(self):
        self.set_edit_locked(False)

    def locked_actions(self):
        return ("Enable Edit",)

    def edit_locked_actions(self):
        return ("Apply",)

    def on_working_changed(self, working):
        self._edit_locked = True   # 워커 동작 시작/종료마다 다시 잠근다 (ParamWin 의 규칙)


class ViewWin(ServiceWin):
    """표시 전용·워커 없는 창 모양 (About)."""

    def __init__(self, parent=None):
        super().__init__(parent, "ViewWin", has_refresh=False, with_param_worker=False, locks_content=False)
        self.set_body(QTreeWidget(self))


def actions(win):
    return {name: act.isEnabled() for name, act in win.toolbar._actions.items()}


def set_worker_busy(win, busy):
    win.param_worker.is_working = busy   # setter 가 sig_is_working_changed → handle_changed_working → _sync_lock_state
    app.processEvents()


def pump(cond, timeout_s: float, label: str) -> bool:
    deadline = time.time() + timeout_s
    while not cond():
        app.processEvents()
        time.sleep(0.005)
        if time.time() > deadline:
            print(f"  timeout: {label}", flush=True)
            return False
    return True


def plug_transport(win, script: dict):
    """워커 스레드의 transport 를 스크립트 대역으로 바꾼다 (창은 ServicePort 를 쓰도록 만들어졌으므로 테스트가 끼워 넣는다)."""
    transport = _harness.ScriptedTransport(script)
    win.param_worker._param_thread._transport = transport
    return transport


def check_only(win, params):
    """백업 트리의 체크를 params 만 남긴다 (기본은 전체 체크)."""
    win._updating_checks = True
    try:
        for param, item in win._item_by_param.items():
            item.setCheckState(0, Qt.CheckState.Checked if param in params else Qt.CheckState.Unchecked)
        win.tree.recompute_all_folder_check_states()
    finally:
        win._updating_checks = False


class _FakeWaitBox:
    def __init__(self, events):
        self._events = events

    def accept(self):
        self._events.append("accept")


def main() -> int:
    rep = _harness.Report()
    svc = ServicePort()
    probe = [(svc.connect_info_changed, ("",))]

    # ======================================================== 1. 계약
    w = TreeWin(); w.show(); app.processEvents()
    rep.check(w.started == 0 and not w._started, "계약: 생성자에서는 start 훅이 불리지 않는다")
    w.start(); w.start()
    rep.check(w.started == 1 and w._started, "계약: start() 멱등, on_start 1회")
    rep.check(w.content_widget is w.tree and w.tree.isEnabled() and actions(w)["Backup"], "계약: 미연결·유휴 — 본문·Backup 활성")
    rep.check("Refresh" not in actions(w) and w.windowTitle() == "TreeWin", "계약: has_refresh=False → Refresh 없음, 제목 = win_name")
    rep.check(w.statusbar.labels[0].text() == "Disconnected", "계약: 상태바 Disconnected")
    set_worker_busy(w, True)
    rep.check(not w.tree.isEnabled() and not actions(w)["Backup"], "계약: 워커 동작 → 본문·Backup 비활성")
    new_tree = QTreeWidget(w)
    w.set_body(new_tree)
    rep.check(w.content_widget is new_tree and not new_tree.isEnabled(), "계약: set_body 가 교체 뒤 잠금을 다시 확정")
    set_worker_busy(w, False)
    rep.check(new_tree.isEnabled() and actions(w)["Backup"], "계약: 워커 유휴 → 활성")
    _harness.destroy_window(w, app)
    problems = _harness.emit_signals_capture(probe, app, process_events_each=False)
    rep.check(not problems, f"계약: 파괴 뒤 좀비 연결 없음 {problems}")

    e = EditWin(); e.show(); e.start(); app.processEvents()
    rep.check(not e.content_widget.isEnabled() and not actions(e)["Apply"] and actions(e)["Enable Edit"],
              "계약: 편집 잠금 — 본문·Apply 비활성, Enable Edit 활성")
    e.set_edit_locked(False)
    rep.check(e.content_widget.isEnabled() and actions(e)["Apply"], "계약: Enable Edit → 본문·Apply 활성")
    set_worker_busy(e, True)
    rep.check(not actions(e)["Enable Edit"] and not actions(e)["Apply"] and not e.content_widget.isEnabled(),
              "계약: 워커 동작 → Enable Edit·Apply·본문 비활성")
    set_worker_busy(e, False)
    rep.check(not e.content_widget.isEnabled() and actions(e)["Enable Edit"], "계약: 동작 끝 → 다시 편집 잠금 (Enable Edit 만 활성)")
    _harness.destroy_window(e, app)

    v = ViewWin(); v.show(); v.start(); app.processEvents()
    rep.check(v.param_worker is None and not v.is_working and v.content_widget.isEnabled(),
              "계약: with_param_worker=False — 워커 없음, 본문 활성")
    svc.connect_info_changed.emit("COM9 9600")
    app.processEvents()
    rep.check(v.content_widget.isEnabled() and v.statusbar.labels[0].text() == "COM9 9600", "계약: 연결 신호 → 상태바만 갱신, 본문 활성")
    svc.connect_info_changed.emit("")
    _harness.destroy_window(v, app)

    # ======================================================== 2. 창 7개 (2단계 ②)
    rep.check(all(issubclass(c, ServiceWin) and not issubclass(c, ParamWin)
                  for c in (BackupWin, RestoreWin, SensorAnalysisWin, HelpAboutWin, HelpNvmUpdateWin)),
              "Backup/Restore/SensorAnalysis/About/Update 는 ServiceWin 직계")
    rep.check(issubclass(FactoryFirmwareUpdateWin, ParamWin) and issubclass(ClusterMonitorWin, ParamWin),
              "Firmware Update / Cluster Monitor 는 ParamWin 위")
    leftovers = [(c.__name__, n) for c in (BackupWin, RestoreWin, SensorAnalysisWin, ClusterMonitorWin,
                                           FactoryFirmwareUpdateWin, HelpAboutWin, HelpNvmUpdateWin)
                 for n in ("_is_backup_running", "is_fu_backup", "_fu_saved_file", "_is_restore_running", "sample_timer",
                           "table", "_stage", "_wait_box", "content_widget", "handle_changed_working")
                 if n in c.__dict__]
    rep.check(not leftovers, f"클래스 기본값·'항상 활성' 오버라이드 잔존 없음: {leftovers}")

    # --- BackupWin — 워커 CAPTURE 시퀀스 (data-protocol-2)
    reg = SpecRegistry()
    win = BackupWin(parent=None, win_name="Backup", is_fu_backup=False)
    win.start(); app.processEvents()   # 미연결로 시작 — 초기 refresh 없음 (이 창의 읽기 2개는 스크립트에 없다)
    rep.check(win.windowTitle() == "Backup" and set(actions(win)) == {"Backup", "Abort"} and not actions(win)["Abort"],
              f"Backup: 제목/툴바 {win.windowTitle()!r} {list(actions(win))}, Abort 는 유휴 시 비활성")
    rep.check(win.content_widget is win.tree and win.centralWidget() is win.tree, "Backup: 본문 = 트리")
    rep.check(len(win.param_worker.read_param_list) == 2 and win.tree.topLevelItemCount() > 0,
              f"Backup: 읽기 등록 2 ({len(win.param_worker.read_param_list)}), 트리 {win.tree.topLevelItemCount()} 폴더")
    set_worker_busy(win, True)
    rep.check(not win.tree.isEnabled() and not actions(win)["Backup"], "Backup: 워커 동작 중 — 트리·Backup 잠김")
    set_worker_busy(win, False)
    rep.check(win.tree.isEnabled() and actions(win)["Backup"], "Backup: 워커 유휴 — 풀림")

    pa, pb, pc, pd = list(win._item_by_param)[:4]            # 스키마 순서의 백업 대상 4개
    ra, rb, rc, rd = (reg.get_read_spec(p) for p in (pa, pb, pc, pd))
    late = ra.expected_response_prefix[:6] + "FFFFFFFF" + ra.expected_response_prefix[14:] + "1"   # 다른 id 의 늦은 응답
    t = plug_transport(win, {ra.build_request(): [late, ra.expected_response_prefix + "1"],        # F086: 늦은 응답 뒤 정상 → 재시도로 성공
                             rb.build_request(): ["p:", "x", "y", "z", rb.expected_response_prefix + "2"],  # 잡음 4번 → 상한 3 소진 → 누락
                             rc.build_request(): "p:89" + rc.expected_response_prefix[4:],          # 미지원 → 재시도 없이 누락
                             rd.build_request(): rd.expected_response_prefix + "4"})
    check_only(win, (pa, pb, pc, pd))
    asked, saved = [], []
    backup_win_mod.ask_save_partial_backup = lambda parent, names: asked.append(list(names)) or True
    with tempfile.TemporaryDirectory() as tmp:
        out_path = os.path.join(tmp, "backup_test.txt")
        QFileDialog.getSaveFileName = staticmethod(lambda *a, **k: saved.append(out_path) or (out_path, ""))
        with _harness.fake_connected(svc):
            win.on_clicked_backup()
            rep.check(win.is_working and not win.tree.isEnabled() and not actions(win)["Backup"] and actions(win)["Abort"],
                      "Backup: 시퀀스 중 — 트리·Backup 잠김, Abort 활성")
            pump(lambda: not win.is_working, 8, "백업 시퀀스 종료")
        rep.check(not win.is_working and win.tree.isEnabled() and actions(win)["Backup"] and not actions(win)["Abort"],
                  "Backup: 종료 — 풀림, Abort 비활성")
        rep.check(t.count(ra.build_request()) == 2 and t.count(rb.build_request()) == 4 and t.count(rc.build_request()) == 1,
                  f"Backup: 늦은 응답 재시도 2회(F086) / 잡음 상한 3 → 4회 / 미지원 1회 (실제 {t.count(ra.build_request())}, "
                  f"{t.count(rb.build_request())}, {t.count(rc.build_request())})")
        rep.check(asked == [[f"{pb.path}.{pb.name}", f"{pc.path}.{pc.name}"]], f"Backup: 누락 2건을 묻는다(F087): {asked}")
        rep.check(saved == [out_path] and os.path.isfile(out_path), "Backup: 질문에 Yes → 파일 저장")
        lines = open(out_path, encoding="utf-8").read().splitlines() if os.path.isfile(out_path) else []
        ws_a, ws_d = reg.get_write_spec(pa), reg.get_write_spec(pd)
        rep.check(len(lines) == 3 and lines[1] == f"{pa.path}.{pa.name}, {ws_a.build_request_line('1')}"
                  and lines[2] == f"{pd.path}.{pd.name}, {ws_d.build_request_line('4')}",
                  f"Backup: 파일 = 헤더 + 성공 2행(선로 원문, 스키마 순서): {lines}")
        rep.check(pa.str_value == "1" and pd.value == 4 and pb.is_err and pc.is_not_support,
                  "Backup: 성공 param 은 값 반영, 실패 param 은 is_err / 미지원은 Not Support")

        # Abort: 두 번째 요청에서 붙들어 두고 취소 — 파일 없음, 보고 ABORTED
        asked.clear(); saved.clear(); os.remove(out_path)
        for p in (pa, pb, pc, pd):
            p.is_err = False; p.is_not_support = False
        t = plug_transport(win, {ra.build_request(): ra.expected_response_prefix + "1", rb.build_request(): rb.expected_response_prefix + "2"})
        t.gate[rb.build_request()] = threading.Event()
        check_only(win, (pa, pb))
        with _harness.fake_connected(svc):
            win.on_clicked_backup()
            pump(lambda: t.count(rb.build_request()) == 1, 5, "두 번째 요청 도착")
            win.on_clicked_abort()
            rep.check(not win.is_working and win.tree.isEnabled() and not actions(win)["Abort"], "Backup: Abort → 즉시 풀림")
            t.gate[rb.build_request()].set()
            app.processEvents(); time.sleep(0.05); app.processEvents()
        rep.check(asked == [] and saved == [] and not os.path.exists(out_path), "Backup: Abort 면 질문·저장 없음")
    _harness.destroy_window(win, app)

    # --- RestoreWin — 워커 RAW 시퀀스
    win = RestoreWin(parent=None, win_name="Restore")
    win.start(); app.processEvents()
    rep.check(set(actions(win)) == {"Load File", "Restore", "Abort"} and not actions(win)["Abort"] and win.edit_locked_actions() == (),
              f"Restore: 툴바 {list(actions(win))}, Abort 유휴 시 비활성, 편집 잠금 목록 없음")
    rep.check(win.content_widget is win.tree and len(win.param_worker.read_param_list) == 2 and win.acc_mode_param is not None,
              "Restore: 본문 = 트리, 읽기 등록 2, Access Mode param")
    set_worker_busy(win, True)
    rep.check(not win.tree.isEnabled() and not actions(win)["Restore"] and not actions(win)["Load File"],
              "Restore: 워커 동작 중 — 트리·Restore·Load File 잠김")
    set_worker_busy(win, False)
    rep.check(win.tree.isEnabled() and actions(win)["Restore"] and actions(win)["Load File"], "Restore: 워커 유휴 — 풀림")

    acc = win.acc_mode_param
    local_packet = reg.get_write_spec(acc).build_request({acc: "0"})
    packets = [reg.get_write_spec(p).build_request_line(str(i + 1)) for i, p in enumerate((pa, pb, pc))]
    prefixes = ["p:0001" + pk[4:14] for pk in packets]
    summaries = []
    QMessageBox.warning = staticmethod(lambda parent, title, text: summaries.append(text) or QMessageBox.StandardButton.Ok)
    QMessageBox.information = staticmethod(lambda parent, title, text: summaries.append(text) or QMessageBox.StandardButton.Ok)
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "restore_test.txt")
        with open(path, "w", encoding="utf-8") as f:
            f.write(backup_file_helper.build_header("6.2.3", 0) + "\n")
            for p, pk in zip((pa, pb, pc), packets):
                f.write(f"{p.path}.{p.name}, {pk}\n")
        win.is_fu_restore = True   # 헤더 비교 건너뜀 (장비 값 없음)
        win.load_backup_file(path)
        summaries.clear()
        rep.check(len(win.loaded_items) == 3, f"Restore: 파일 로드 3항목 ({len(win.loaded_items)})")
        t = plug_transport(win, {local_packet: "p:0001" + local_packet[4:14],
                                 packets[0]: prefixes[0],
                                 packets[1]: "p:78" + prefixes[1][4:],              # 장비 거부 → 재시도 없이 실패
                                 packets[2]: ["", "", "", ""]})                    # 빈 응답 → 상한 3 소진 → 실패
        with _harness.fake_connected(svc):
            win.on_clicked_restore()
            rep.check(win.is_working and not win.tree.isEnabled() and not actions(win)["Restore"] and actions(win)["Abort"],
                      "Restore: 시퀀스 중 — 잠김, Abort 활성")
            pump(lambda: not win.is_working, 8, "복원 시퀀스 종료")
        rep.check(t.count(local_packet) == 1 and t.count(packets[1]) == 1 and t.count(packets[2]) == 4,
                  f"Restore: Local 전환 1 / 거부 1회 / 빈 응답 4회 (실제 {t.count(local_packet)}, {t.count(packets[1])}, {t.count(packets[2])})")
        rep.check(len(summaries) == 1 and "2 failed" in summaries[0] and f"{pb.path}.{pb.name}" in summaries[0]
                  and f"{pc.path}.{pc.name}" in summaries[0] and "3 items" in summaries[0], f"Restore: 요약 = 3항목 중 실패 2: {summaries}")
        rep.check(not actions(win)["Abort"] and win.tree.isEnabled(), "Restore: 종료 — Abort 비활성, 풀림")

        # 끊김 중 보고 — 두 번째 항목에서 끊는다
        summaries.clear()
        t = plug_transport(win, {local_packet: "p:0001" + local_packet[4:14], packets[0]: prefixes[0], packets[1]: prefixes[1], packets[2]: prefixes[2]})
        t.gate[packets[1]] = threading.Event()
        with _harness.fake_connected(svc):
            win.on_clicked_restore()
            pump(lambda: t.count(packets[1]) == 1, 5, "두 번째 항목 요청 도착")
            win.param_worker.handle_disconnected()
            t.gate[packets[1]].set()
            app.processEvents(); time.sleep(0.05); app.processEvents()
        rep.check(len(summaries) == 1 and "disconnected after 1 of 3" in summaries[0] and "partially" in summaries[0],
                  f"Restore: 끊김 → '1/3 까지 쓰고 중단' 요약: {summaries}")
        rep.check(not win.is_working and not actions(win)["Abort"], "Restore: 끊김 뒤 풀림")
    _harness.destroy_window(win, app)

    with tempfile.TemporaryDirectory() as tmp:   # 자동 로드(on_start) — FU 복원 모드로 헤더 비교를 건너뛴다
        path = os.path.join(tmp, "fu_backup_test.txt")
        with open(path, "w", encoding="utf-8") as f:
            f.write(backup_file_helper.build_header("6.2.3", 0) + "\n")
            f.write("Valve.Basic.Position Unit, p:0A0100000001\n")
        win = RestoreWin(parent=None, win_name="Firmware Restore", is_fu_restore=True, initial_file_path=path)
        rep.check(win.loaded_items == [], "Restore(FU): 생성 직후에는 아직 로드 안 함")
        win.start(); app.processEvents(); app.processEvents()
        rep.check(len(win.loaded_items) == 1 and win.tree.topLevelItemCount() == 1,
                  f"Restore(FU): start() 뒤 자동 로드 — 항목 {len(win.loaded_items)}, 트리 {win.tree.topLevelItemCount()}")
        _harness.destroy_window(win, app)

    # --- SensorAnalysisWin
    win = SensorAnalysisWin(parent=None, win_name="Sensor Analysis")
    rep.check(set(actions(win)) == {"Refresh"} and not win.sample_timer.isActive(), "SensorAnalysis: 툴바 Refresh 만, 타이머는 start 전 정지")
    rep.check(len(win.param_worker.read_param_list) == 2 and win.act_pres_param is not None, "SensorAnalysis: 센서 1/2 읽기 등록 2")
    with _harness.fake_connected(svc):
        win.start(); app.processEvents()
        rep.check(win.sample_timer.isActive(), "SensorAnalysis: 연결 중 start() → 샘플 타이머 시작")
        rep.check(win.content_widget is win.centralWidget() and win.content_widget is not None, "SensorAnalysis: 본문 = 차트 중앙 위젯")
    svc.connect_info_changed.emit("")
    app.processEvents()
    rep.check(not win.sample_timer.isActive(), "SensorAnalysis: 끊김 → 타이머 정지")
    _harness.destroy_window(win, app)

    # --- ClusterMonitorWin (ParamWin 위)
    win = ClusterMonitorWin(parent=None, win_name="Cluster Monitor")
    win.start(); app.processEvents()
    rep.check(win.content_widget is win.centralWidget() and win.table.parent() is win.content_widget, "ClusterMonitor: 본문 = 표+패널 (set_body)")
    rep.check("Refresh" in actions(win) and win.action_apply.isVisible() and win.table.rowCount() == 0,
              "ClusterMonitor: Refresh 있음, Apply 표시, 장치 수 미수신 행 0")
    set_worker_busy(win, True)
    rep.check(not win.content_widget.isEnabled() and not actions(win)["Apply"], "ClusterMonitor: 워커 동작 중 본문·Apply 잠김")
    set_worker_busy(win, False)
    rep.check(win.content_widget.isEnabled() and actions(win)["Apply"], "ClusterMonitor: 유휴 — 풀림")
    _harness.destroy_window(win, app)

    # --- FactoryFirmwareUpdateWin (ParamWin 위, 표시 전용 본문)
    win = FactoryFirmwareUpdateWin(parent=None, win_name="Firmware Update", backup_file_path=None)
    win.start(); app.processEvents()
    rep.check(set(actions(win)) >= {"Update", "Abort"} and "Refresh" not in actions(win) and not win.locks_content,
              f"FU: 툴바 {list(actions(win))}, Refresh 없음, locks_content=False")
    rep.check(len(win.folder_widgets) == 1 and win.windowTitle() == "Factory >> Firmware Update",
              f"FU: 상단 폴더 카드 1 ({len(win.folder_widgets)}), 제목 {win.windowTitle()!r}")
    rep.check(actions(win)["Update"] and not actions(win)["Abort"], "FU: IDLE — Update 활성, Abort 비활성")
    set_worker_busy(win, True)
    rep.check(win.content_widget.isEnabled() and actions(win)["Update"], "FU: 워커 동작 중에도 본문·Update 활성 (표시 전용)")
    set_worker_busy(win, False)
    _harness.destroy_window(win, app)

    # --- HelpAboutWin (param 워커 없음)
    win = HelpAboutWin(parent=None, win_name="About")
    win.start(); app.processEvents()
    rep.check(win.param_worker is None and not win.is_working, "About: param 워커 없음")
    rep.check(set(actions(win)) == set() and win.windowTitle() == "Help >> About", f"About: 툴바 비어 있음 {list(actions(win))}, 제목")
    rep.check(win.content_widget.isEnabled() and win.license_list.count() > 0 and win.license_list.currentRow() == 0,
              "About: 본문 활성, 라이선스 목록 첫 항목 선택")
    rep.check(win.statusbar.labels[0].text() == "Disconnected" and win.statusbar.labels[1].text().startswith("SN:"),
              f"About: 상태바 {win.statusbar.labels[0].text()!r} / {win.statusbar.labels[1].text()!r}")
    svc.connect_info_changed.emit("COM9 9600")
    app.processEvents()
    rep.check(win.content_widget.isEnabled() and win.statusbar.labels[0].text() == "COM9 9600", "About: 연결 신호 → 상태바만, 본문 활성")
    svc.connect_info_changed.emit("")
    _harness.destroy_window(win, app)

    # --- HelpNvmUpdateWin (param 워커 없음, 조회는 on_start — FTP 는 스텁)
    events = []
    original_wait_box = update_mod.show_wait_message_box
    update_mod.show_wait_message_box = lambda *a, **k: events.append("wait") or _FakeWaitBox(events)
    try:
        win = HelpNvmUpdateWin(parent=None, win_name="Application Update")
        rep.check(win.param_worker is None and set(actions(win)) == {"Update", "Abort"}, f"Update: param 워커 없음, 툴바 {list(actions(win))}")
        rep.check(win._stage is update_mod._Stage.IDLE and win._wait_box is None and events == [],
                  "Update: 생성만으로는 릴리스 노트 조회를 시작하지 않는다")
        rep.check(not actions(win)["Update"] and not actions(win)["Abort"] and win.content_widget.isEnabled(),
                  "Update: IDLE·선택 없음 — Update/Abort 비활성, 본문 활성")
        started = []
        win.update_worker.start_release_notes = lambda: started.append(1) or True
        win.start(); app.processEvents()
        rep.check(started == [1] and events == ["wait"] and win._stage is update_mod._Stage.LISTING,
                  f"Update: start() → on_start 가 조회 시작 (대기 박스 1, 워커 호출 {started})")
        win.handle_release_notes_finished(True, [], "")
        app.processEvents()
        rep.check(win._stage is update_mod._Stage.IDLE and events == ["wait", "accept"], "Update: 조회 완료 → IDLE, 대기 박스 닫힘")
        _harness.destroy_window(win, app)
    finally:
        update_mod.show_wait_message_box = original_wait_box

    # --- 파괴 뒤 좀비 연결 (7종)
    for cls, kwargs in ((BackupWin, dict(win_name="Backup")), (RestoreWin, dict(win_name="Restore")),
                        (SensorAnalysisWin, dict(win_name="Sensor Analysis")), (HelpAboutWin, dict(win_name="About")),
                        (HelpNvmUpdateWin, dict(win_name="Application Update")),
                        (FactoryFirmwareUpdateWin, dict(win_name="Firmware Update", backup_file_path=None)),
                        (ClusterMonitorWin, dict(win_name="Cluster Monitor"))):
        w = cls(parent=None, **kwargs)
        if cls is not HelpNvmUpdateWin:   # Update 의 start() 는 FTP 조회 — 생성·파괴만
            w.start()
        app.processEvents()
        _harness.destroy_window(w, app)
        problems = _harness.emit_signals_capture(probe, app, process_events_each=False)
        rep.check(not problems, f"{cls.__name__}: 파괴 뒤 connect_info_changed 좀비 없음 {problems}")

    _harness.assert_isolated()
    return rep.summary()


if __name__ == "__main__":
    sys.exit(main())
