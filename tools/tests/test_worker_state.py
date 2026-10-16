"""ParameterRunWorker 상태 전이 테스트 — 장비 없이 {요청: 응답} 스크립트 transport 로 워커 상태 머신을 확인한다 (F110).

    python tools/tests/test_worker_state.py

검사 항목
  1. refresh → 등록 param(init/read) 읽기 → MONITOR: 요청 순서, 값 반영, sig_finish_refresh 1회, is_working 복귀,
     모니터링이 read 목록을 계속 읽음
  2. 잡음 재시도: 형식이 깨진 응답(너무 짧음 = WRONG_FORMAT, 접두 불일치 = WRONG_PREFIX; 둘 다 need_retry)과 통신 오류
     (READ_TIMEOUT)는 같은 요청을 다시 보낸다
  3. 기준 워커 PENDING: 기준(MainWin) 워커가 refresh 중이면 다른 워커의 refresh 는 PENDING(잠김·write BUSY),
     기준 시퀀스가 끝나면 자동으로 시작해 MONITOR 에 닿는다; 기준 워커 자신도 refresh 중 write 는 BUSY
  4. write: MONITOR 중 write → 쓰기 요청 1건 → read-back → MONITOR 복귀, sig_finish_refresh 는 발화하지 않음
  5. 끊김: handle_disconnected → DISCONNECTED, 타이머 정지, 요청 중단; 미연결 refresh 는 NOT_CONNECTED
  6. capture(백업, data-protocol-2): 잡음은 max_retry 까지 같은 작업 재시도 뒤 실패 기록, 성공은 값 반영, 보고 1회(COMPLETED, 작업별
     Outcome), 시퀀스 중 is_working·BUSY, 끝나면 MONITOR 복귀
  7. raw_write(복원): NV2 쓰기 패킷의 장비 거부(p:78)는 재시도 없이 REJECTED, 빈 응답은 상한까지 재시도 뒤 TRANSIENT, 정상은 OK —
     꼬리표가 보고에 그대로
  8. abort_sequence: 보내 둔 요청의 응답은 폐기, ABORTED 보고(그때까지의 결과), MONITOR 복귀; refresh/write 시퀀스에는 False
  9. 끊김 중 보고: capture 도중 handle_disconnected → DISCONNECTED 보고 뒤 DISCONNECTED 상태
 10. 재부팅 대기(start_reboot_wait) 뒤 probe 성공 → ServicePort.open 실패: sig_reboot_finished(False) 1회, REBOOT 해제, 포트 닫힘 (F030)
"""

from __future__ import annotations

import os
import sys
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

from PySide6.QtCore import QTimer  # noqa: E402

QTimer.singleShot(90000, lambda: (print("TIMEOUT", flush=True), os._exit(3)))

from b_core.b_datatype.general_enum import ParamAccType, ParamDataType, SvcPortErrType  # noqa: E402
from b_core.c_manager.parameter_manager import ParamManager  # noqa: E402
from b_core.d_dal.serial_setting import SerialSetting  # noqa: E402
from b_core.d_dal.service_port import ServicePort  # noqa: E402
from b_core.e_worker_ver2.parameter_run_worker import (ParameterRunWorker, SequenceEnd, SequenceKind,  # noqa: E402
                                                       StartResult, _WorkerState)
from b_core.g_protocol.codec import TextCodec  # noqa: E402
from b_core.g_protocol.packet_spec import Verdict  # noqa: E402
from b_core.g_protocol.spec_registry import SpecRegistry  # noqa: E402

ScriptedTransport = _harness.ScriptedTransport   # 하네스 단일본 (창 테스트와 공유)


def pump(cond, timeout_s: float, label: str) -> bool:
    deadline = time.time() + timeout_s
    while not cond():
        app.processEvents()
        time.sleep(0.005)
        if time.time() > deadline:
            print(f"  timeout: {label}", flush=True)
            return False
    return True


def main() -> int:
    rep = _harness.Report()
    pm, reg, svc = ParamManager(), SpecRegistry(), ServicePort()
    rep.check(not pm.load_errors, f"스키마 오류 {pm.load_errors}")

    # 대상 param: SN(문자열, init) + 숫자 RW 2개 (한 창의 read 목록용 / 다른 창의 read 목록용)
    sn = pm.get_by_full_path("System.Identification.Serial Number")
    nums = [p for p in pm.get_param_list()
            if p.acc == ParamAccType.RW and p.data_type is ParamDataType.UINT32 and p.display_type.name == "NUMBER"
            and isinstance(reg.get_param_codec(p), TextCodec) and reg.get_read_spec(p) and reg.get_write_spec(p)][:2]
    rep.check(sn is not None and len(nums) == 2, "대상 param 확보")
    if rep.fail:
        return rep.summary()
    num_a, num_b = nums
    rs_sn, rs_a, rs_b = (reg.get_read_spec(p) for p in (sn, num_a, num_b))
    ws_a, ws_b = reg.get_write_spec(num_a), reg.get_write_spec(num_b)
    req_sn, req_a, req_b = rs_sn.build_request(), rs_a.build_request(), rs_b.build_request()
    write_b = ws_b.build_request({num_b: 5})
    raw_ok, raw_rej, raw_noise = ws_b.build_request({num_b: 6}), ws_a.build_request({num_a: 3}), ws_b.build_request({num_b: 9})

    def ok(spec, value):
        return spec.expected_response_prefix + str(value)

    # 기준 워커(MainWin 역할): init [SN], read [num_a]. 보조 워커(설정 창 역할): read [num_b]
    t_main = ScriptedTransport({req_sn: [SvcPortErrType.READ_TIMEOUT_ERROR, ok(rs_sn, "SN123")],   # 통신 오류 1회 → 재시도
                                req_a: ["p:", "garbage", ok(rs_a, 7)]})                           # WRONG_FORMAT, WRONG_PREFIX → 재시도
    t_sub = ScriptedTransport({req_b: ok(rs_b, 11), write_b: ws_b.expected_response_prefix,
                               req_a: ["p:", "x", "y", "z", ok(rs_a, 42)],                 # capture: 잡음 4번 뒤 정상
                               raw_ok: ws_b.expected_response_prefix,                        # raw: 정상
                               raw_rej: "p:78" + ws_a.expected_response_prefix[4:],         # raw: 장비 거부 (오류 코드 78)
                               raw_noise: ["", "", "", "", ws_b.expected_response_prefix]})  # raw: 빈 응답 4번 뒤 정상
    reports = []
    w_sub_report = reports.append
    w_main = ParameterRunWorker(log_source="T_main", is_primary=True, transport=t_main, monitor_tick=10)
    w_sub = ParameterRunWorker(log_source="T_sub", transport=t_sub, monitor_tick=10)
    w_main.add_init_param_ptr(sn); w_main.add_read_param_ptr(num_a)
    w_sub.add_read_param_ptr(num_b)
    finished = {"main": 0, "sub": 0}
    w_main.sig_finish_refresh.connect(lambda: finished.__setitem__("main", finished["main"] + 1))
    w_sub.sig_finish_refresh.connect(lambda: finished.__setitem__("sub", finished["sub"] + 1))
    w_sub.sig_sequence_report.connect(w_sub_report)
    for p in (sn, num_a, num_b):
        p._value = None; p.str_value = ""

    try:
        with _harness.fake_connected(svc):
            # ---------------------------------------------------- 1·2. refresh → MONITOR (재시도 포함)
            rep.check(w_main.refresh() is StartResult.OK, "기준 refresh 시작 OK")
            rep.check(w_main.is_working and w_main._state is _WorkerState.SEQUENCE, "refresh 중 is_working/SEQUENCE")
            rep.check(w_main.write([(num_a, 1)]) is StartResult.BUSY, "refresh 중 write → BUSY")
            pump(lambda: w_main._state is _WorkerState.MONITOR, 5, "기준 refresh → MONITOR")
            rep.check(w_main._state is _WorkerState.MONITOR and not w_main.is_working, "refresh 완료 → MONITOR, is_working False")
            rep.check(finished["main"] == 1, f"sig_finish_refresh 1회 (실제 {finished['main']})")
            rep.check(sn.value == "SN123" and num_a.value == 7, f"값 반영 SN={sn.value!r} num_a={num_a.value!r}")
            rep.check(t_main.count(req_sn) == 2, f"통신 오류 뒤 같은 요청 재시도 (SN 요청 {t_main.count(req_sn)}회)")
            rep.check(t_main.count(req_a) >= 3, f"형식 오류 2종 뒤 같은 요청 재시도 (num_a 요청 {t_main.count(req_a)}회)")
            rep.check(t_main.requests[0] == req_sn and t_main.requests.index(req_a) > t_main.requests.index(req_sn),
                      "요청 순서: init(SN) 뒤 read(num_a)")
            before = t_main.count(req_a)
            pump(lambda: t_main.count(req_a) >= before + 3, 3, "모니터링 반복 읽기")
            rep.check(t_main.count(req_a) >= before + 3, "MONITOR 가 read 목록을 계속 읽는다")

            # ---------------------------------------------------- 3. 기준 워커 PENDING
            t_main.gate[req_sn] = threading.Event()   # 기준 refresh 를 SN 응답에서 붙들어 둔다
            rep.check(w_main.refresh() is StartResult.OK, "기준 refresh 재시작")
            pump(lambda: t_main.count(req_sn) >= 3, 3, "SN 요청 도착")   # 워커 스레드가 gate 에서 대기 중
            rep.check(w_sub.refresh() is StartResult.PENDING, "기준 refresh 중 보조 refresh → PENDING")
            rep.check(w_sub.is_working and w_sub._state is _WorkerState.PENDING, "PENDING 은 잠김(is_working)")
            rep.check(w_sub.write([(num_b, 5)]) is StartResult.BUSY, "PENDING 중 write → BUSY")
            rep.check(w_sub.refresh() is StartResult.PENDING and ParameterRunWorker._pending_refresh.count(w_sub) == 1,
                      "PENDING 중 refresh 재호출은 중복 예약 없음")
            rep.check(t_sub.requests == [], "PENDING 동안 보조 워커는 요청을 보내지 않는다")
            t_main.gate[req_sn].set()
            pump(lambda: w_sub._state is _WorkerState.MONITOR, 5, "기준 완료 뒤 보조 자동 refresh → MONITOR")
            rep.check(w_sub._state is _WorkerState.MONITOR and not w_sub.is_working and finished["sub"] == 1,
                      f"보조 워커 자동 refresh 완료 (finish {finished['sub']})")
            rep.check(num_b.value == 11 and t_sub.requests[0] == req_b, "보조 워커 값 반영")
            rep.check(finished["main"] == 2, f"기준 refresh 완료 2회 (실제 {finished['main']})")

            # ---------------------------------------------------- 4. write (MONITOR 중)
            rep.check(w_sub.write([(num_b, 5)]) is StartResult.OK, "MONITOR 중 write → OK")
            pump(lambda: t_sub.count(write_b) >= 1 and w_sub._state is _WorkerState.MONITOR and not w_sub.is_working, 5,
                 "write → read-back → MONITOR")
            rep.check(t_sub.count(write_b) == 1, f"쓰기 요청 1건 (실제 {t_sub.count(write_b)})")
            idx = t_sub.requests.index(write_b)
            rep.check(req_b in t_sub.requests[idx + 1:], "쓰기 뒤 read-back")
            rep.check(finished["sub"] == 1, "write 완료에는 sig_finish_refresh 가 발화하지 않는다")

            # ---------------------------------------------------- 6. capture (백업) — 상한 재시도·실패 기록·보고
            n_a0 = t_sub.count(req_a)
            rep.check(w_sub.capture([num_a, num_b], max_retry=2) is StartResult.OK, "capture 시작 OK")
            rep.check(w_sub.is_working and w_sub._state is _WorkerState.SEQUENCE, "capture 중 is_working/SEQUENCE")
            rep.check(w_sub.capture([num_a], max_retry=2) is StartResult.BUSY and w_sub.write([(num_b, 5)]) is StartResult.BUSY,
                      "capture 중 capture/write → BUSY")
            pump(lambda: len(reports) == 1, 5, "capture 보고")
            r = reports[0] if reports else None
            rep.check(r is not None and r.kind is SequenceKind.CAPTURE and r.end is SequenceEnd.COMPLETED and r.total == 2,
                      f"capture 보고: {r}")
            rep.check(r is not None and [x.params for x in r.results] == [(num_a,), (num_b,)], "보고 순서 = 작업 순서, params 포함")
            rep.check(r is not None and r.results[0].lines == {} and r.results[1].lines == {num_b: "11"},
                      f"성공 작업만 읽은 선로 원문 사본(lines): {[x.lines for x in r.results] if r else None}")
            rep.check(r is not None and r.results[0].outcome.verdict is Verdict.TRANSIENT and r.results[1].outcome.verdict is Verdict.OK,
                      f"num_a 는 재시도 소진(TRANSIENT), num_b 는 OK: {[x.outcome.verdict.name for x in r.results] if r else None}")
            rep.check(t_sub.count(req_a) - n_a0 == 3, f"max_retry=2 → 같은 요청 3번 (실제 {t_sub.count(req_a) - n_a0})")
            rep.check(num_b.value == 11 and not num_b.is_err,
                      "성공 param 은 값 반영 (num_a 의 is_err 는 기준 워커의 모니터링 정상 읽기가 곧바로 되돌리므로 보고의 Outcome 으로 본다)")
            rep.check(w_sub._state is _WorkerState.MONITOR and not w_sub.is_working, "capture 뒤 MONITOR 복귀")

            # ---------------------------------------------------- 7. raw_write (복원) — 거부는 재시도 없음, 잡음은 상한까지
            reports.clear()
            rep.check(w_sub.raw_write([("ok", raw_ok), ("rej", raw_rej), ("noise", raw_noise)], max_retry=1) is StartResult.OK,
                      "raw_write 시작 OK")
            pump(lambda: len(reports) == 1, 5, "raw 보고")
            r = reports[0] if reports else None
            rep.check(r is not None and r.kind is SequenceKind.RAW and r.end is SequenceEnd.COMPLETED and r.total == 3
                      and [x.tag for x in r.results] == ["ok", "rej", "noise"], f"raw 보고 꼬리표: {r}")
            rep.check(r is not None and [x.outcome.verdict.name for x in r.results] == ["OK", "REJECTED", "TRANSIENT"],
                      f"raw 부류: {[x.outcome.verdict.name for x in r.results] if r else None}")
            rep.check(t_sub.count(raw_rej) == 1 and t_sub.count(raw_noise) == 2,
                      f"거부 1회(재시도 없음) / 빈 응답은 max_retry=1 → 2회 (실제 {t_sub.count(raw_rej)}, {t_sub.count(raw_noise)})")
            rep.check(all(x.params == () for x in r.results) if r else False, "raw 작업은 params 없음")
            rep.check(w_sub._state is _WorkerState.MONITOR and not w_sub.is_working, "raw 뒤 MONITOR 복귀")

            # ---------------------------------------------------- 8. abort_sequence
            reports.clear()
            t_sub.gate[raw_ok] = threading.Event()
            n_ok0 = t_sub.count(raw_ok)
            rep.check(w_sub.raw_write([("ok", raw_ok), ("rej", raw_rej)], max_retry=1) is StartResult.OK, "abort 용 raw 시작")
            pump(lambda: t_sub.count(raw_ok) > n_ok0, 3, "첫 요청 도착")
            rep.check(w_sub.abort_sequence() and len(reports) == 1 and reports[0].end is SequenceEnd.ABORTED
                      and reports[0].results == [] and reports[0].total == 2, f"abort → ABORTED 보고(결과 0/2): {reports}")
            rep.check(w_sub._state is _WorkerState.MONITOR and not w_sub.is_working, "abort 뒤 MONITOR 복귀·잠금 해제")
            t_sub.gate[raw_ok].set()
            app.processEvents(); time.sleep(0.05); app.processEvents()
            rep.check(len(reports) == 1 and t_sub.count(raw_rej) == 1, "늦은 응답은 폐기 — 다음 작업으로 가지 않는다")
            del t_sub.gate[raw_ok]
            rep.check(not w_sub.abort_sequence(), "시퀀스 없을 때 abort → False")
            rep.check(w_sub.write([(num_b, 5)]) is StartResult.OK and not w_sub.abort_sequence(), "write 시퀀스에는 abort → False")
            pump(lambda: w_sub._state is _WorkerState.MONITOR, 5, "write 종료")

            # ---------------------------------------------------- 9. 끊김 중 보고 (capture 도중 끊김) — 5 와 이어진다
            reports.clear()
            t_sub.gate[req_a] = threading.Event()
            n_a1 = t_sub.count(req_a)
            rep.check(w_sub.capture([num_a], max_retry=1) is StartResult.OK, "끊김 용 capture 시작")
            pump(lambda: t_sub.count(req_a) > n_a1, 3, "요청 도착")

            # ---------------------------------------------------- 5. 끊김
            w_sub.handle_disconnected()
            rep.check(len(reports) == 1 and reports[0].kind is SequenceKind.CAPTURE and reports[0].end is SequenceEnd.DISCONNECTED
                      and reports[0].results == [], f"끊김 → DISCONNECTED 보고: {reports}")
            t_sub.gate[req_a].set()
            n_before = len(t_sub.requests)
            rep.check(w_sub._state is _WorkerState.DISCONNECTED and not w_sub.is_working
                      and not w_sub.monitor_timer.isActive(), "handle_disconnected → DISCONNECTED, 타이머 정지")
            app.processEvents(); time.sleep(0.05); app.processEvents()
            rep.check(len(t_sub.requests) <= n_before + 1, "끊김 뒤 요청 중단 (전송 중이던 1건까지만)")

        rep.check(w_sub.refresh() is StartResult.NOT_CONNECTED, "미연결 refresh → NOT_CONNECTED")
        rep.check(w_sub.write([(num_b, 5)]) is StartResult.NOT_CONNECTED, "미연결 write → NOT_CONNECTED")
    finally:
        w_sub.cleanup(); w_main.cleanup()
        for p in (sn, num_a, num_b):
            p._value = None; p.str_value = ""

    # ---------------------------------------------------- 10. 재부팅 대기 뒤 재연결 실패 (F030)
    # probe 성공을 직접 넣으면 워커가 ServicePort.open 으로 정식 연결을 시도한다 — 없는 포트라 실패하고 False 가 나와야 한다
    w_rb = ParameterRunWorker(log_source="T_reboot", transport=ScriptedTransport({}), monitor_tick=10)
    finished = []

    def on_reboot_finished(ok):
        finished.append(ok)

    w_rb.sig_reboot_finished.connect(on_reboot_finished)
    try:
        setting = SerialSetting("COM_NONE_NVM2", 9600, 8, 0, 1, 0)
        rep.check(w_rb.start_reboot_wait(setting) and w_rb._state is _WorkerState.REBOOT, "재부팅 대기 시작 (외부 시작 경로)")
        w_rb._handle_reboot_probe_result(w_rb._seq, True, "probe ok")
        rep.check(finished == [False] and w_rb._state is not _WorkerState.REBOOT and svc.setting is None,
                  f"probe 성공 뒤 포트 열기 실패 → sig_reboot_finished(False), 대기 해제, 포트 닫힘 (F030): {finished}")
    finally:
        w_rb.cleanup()

    _harness.assert_isolated()
    return rep.summary()


if __name__ == "__main__":
    sys.exit(main())
