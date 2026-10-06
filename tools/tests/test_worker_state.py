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
from b_core.d_dal.service_port import ServicePort  # noqa: E402
from b_core.e_worker_ver2.parameter_run_worker import ParameterRunWorker, StartResult, _WorkerState  # noqa: E402
from b_core.g_protocol.codec import TextCodec  # noqa: E402
from b_core.g_protocol.spec_registry import SpecRegistry  # noqa: E402


class ScriptedTransport:
    """request_string(packet) 대역 — 요청마다 스크립트의 응답을 순서대로 돌려주고(마지막 것 반복) 요청을 기록한다.

    script: {요청 문자열: [응답, ...]}. 응답이 SvcPortErrType 이면 통신 오류로 ("", err) 를 돌려준다.
    gate: {요청 문자열: threading.Event} — 이벤트가 set 될 때까지 응답을 미룬다 (기준 워커를 refresh 중에 붙들어 두는 용도).
    스크립트에 없는 요청은 '응답 없음'(READ_TIMEOUT) 으로 처리한다."""

    def __init__(self, script: dict):
        self._script = {k: list(v) if isinstance(v, (list, tuple)) else [v] for k, v in script.items()}
        self._lock = threading.Lock()
        self.requests: list[str] = []
        self.gate: dict[str, threading.Event] = {}

    def request_string(self, packet: str):
        with self._lock:
            self.requests.append(packet)   # 도착 즉시 기록 — gate 에 붙들린 요청도 '보냈다' 로 센다
        gate = self.gate.get(packet)
        if gate is not None:
            gate.wait(10)
        with self._lock:
            responses = self._script.get(packet)
            if not responses:
                return "", SvcPortErrType.READ_TIMEOUT_ERROR
            response = responses.pop(0) if len(responses) > 1 else responses[0]
        if isinstance(response, SvcPortErrType):
            return "", response
        return response, SvcPortErrType.NONE

    def count(self, packet: str) -> int:
        with self._lock:
            return self.requests.count(packet)


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
    ws_b = reg.get_write_spec(num_b)
    req_sn, req_a, req_b = rs_sn.build_request(), rs_a.build_request(), rs_b.build_request()
    write_b = ws_b.build_request({num_b: 5})

    def ok(spec, value):
        return spec.expected_response_prefix + str(value)

    # 기준 워커(MainWin 역할): init [SN], read [num_a]. 보조 워커(설정 창 역할): read [num_b]
    t_main = ScriptedTransport({req_sn: [SvcPortErrType.READ_TIMEOUT_ERROR, ok(rs_sn, "SN123")],   # 통신 오류 1회 → 재시도
                                req_a: ["p:", "garbage", ok(rs_a, 7)]})                           # WRONG_FORMAT, WRONG_PREFIX → 재시도
    t_sub = ScriptedTransport({req_b: ok(rs_b, 11), write_b: ws_b.expected_response_prefix})
    w_main = ParameterRunWorker(log_source="T_main", is_primary=True, transport=t_main, monitor_tick=10)
    w_sub = ParameterRunWorker(log_source="T_sub", transport=t_sub, monitor_tick=10)
    w_main.add_init_param_ptr(sn); w_main.add_read_param_ptr(num_a)
    w_sub.add_read_param_ptr(num_b)
    finished = {"main": 0, "sub": 0}
    w_main.sig_finish_refresh.connect(lambda: finished.__setitem__("main", finished["main"] + 1))
    w_sub.sig_finish_refresh.connect(lambda: finished.__setitem__("sub", finished["sub"] + 1))
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

            # ---------------------------------------------------- 5. 끊김
            w_sub.handle_disconnected()
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

    _harness.assert_isolated()
    return rep.summary()


if __name__ == "__main__":
    sys.exit(main())
