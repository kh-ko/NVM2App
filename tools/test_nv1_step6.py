"""NV1 쓰기 spec (6단계) 테스트 — Cluster.Device x 의 Setting / Control 을 실제 로더 / spec / 워커로 확인한다.

    python tools/test_nv1_step6.py

검사 항목
  1. 로더: load_errors 없음. Setting 8 + Control 4 param × 30대. Option 6개는 읽기 device_option + 쓰기 device_option
     (같은 spec 객체 공유), NV2 4개는 id "20{dev+14:02X}xxxx" 로 역조회, Target/Restart 는 쓰기 spec 만(WO).
     기존 NV2 (id, idx) 와 충돌 없음.
  2. ver1 param_nv1.json 대조: 요청/응답 접두, Option 필드 자리(절대 offset − 8), NV2 id, enum/min/max.
  3. 읽기: Option 응답 "G:05i:04" + 8자 → 6 param 값 (예약 자리 2·5 무시).
  4. 쓰기 요청: Option 조합 쓰기(지정 값 + 현재 값, 예약 '0'), 미확정 값 → None, 문자열 값 허용.
     Target 30 → "030000" / -30 → "-30000" / -3 → "-03000" / 12.3456 → "012346" / 1000 → None(폭 초과) / None → None.
     Restart 버튼 "01" → "G:07c:8201".
  5. 쓰기 응답: RW 만 실린 Option 은 판정 없음(NONE). WO Target 은 빈 응답 / E: / 접두 불일치 / 정상.
  6. 워커: Option 2개 + NV2 Freeze 쓰기 → 쓰기 2건(Option 은 spec 기준 1건) + read-back(device_option 읽기 1건 + Freeze).
  7. ADC Calibration.Calibration (WO enum, 2026-09-16): 쓰기 spec 만, 요청 "G:" + enum 값 2자리 ("11" → G:11), 응답 접두 "G:".
"""

from __future__ import annotations

import json
import os
import re
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)

from PySide6.QtWidgets import QApplication  # noqa: E402

_app = QApplication.instance() or QApplication(sys.argv)

from b_core.b_datatype import param_enum as p_enum  # noqa: E402
from b_core.b_datatype.general_enum import ParamAccType, ParamDisplayType, ParamParseErrType  # noqa: E402
from b_core.c_manager.parameter_manager import ParamManager  # noqa: E402
from b_core.g_protocol.nv1_spec import Nv1ReadSpec, Nv1WriteSpec  # noqa: E402
from b_core.g_protocol.nv2_spec import Nv2ReadSpec, Nv2WriteSpec  # noqa: E402
from b_core.g_protocol.spec_registry import SpecRegistry  # noqa: E402

SRC_NV1 = os.path.join(ROOT, "2_resource", "param_schema", "param_nv1.json")
OPTION_PREFIX_LEN = 8
OPTION_PATHS = {  # ver1 이름 → 정리된 path 끝부분
    "Homing.End Position": "Setting.Homing End Position",
    "Homing.Start Condition": "Setting.Homing Start Condition",
    "Homing.Mode": "Setting.Homing Mode",
    "Position Control Stroke Limitation": "Setting.Position Control Stroke Limitation",
    "Power Failure Option": "Setting.Power Failure Option",
    "Network Failure Option": "Setting.Network Failure Option",
}
SETTING_NAMES = ["Homing End Position", "Homing Start Condition", "Homing Mode", "Position Control Stroke Limitation",
                 "Power Failure Option", "Network Failure Option", "Position Control Speed (%)", "Position Offset"]
CONTROL_NAMES = ["Freeze", "Control Mode Setpoint", "Target Position", "Restart Controller"]
NV2_SUFFIX = {"Setting.Position Control Speed (%)": "0800", "Setting.Position Offset": "2100",
              "Control.Freeze": "0100", "Control.Control Mode Setpoint": "0300"}


class Report:
    def __init__(self):
        self.fail = 0
        self.checks = 0

    def check(self, ok: bool, msg: str):
        self.checks += 1
        if not ok:
            self.fail += 1
            if self.fail <= 30:
                print(f"  FAIL {msg}")


def main() -> int:
    rep = Report()
    pm = ParamManager()
    reg = SpecRegistry()
    for e in pm.load_errors:
        print(f"  load error: {e}")
    rep.check(not pm.load_errors, f"load_errors {len(pm.load_errors)} 건")

    def dev(n: int, tail: str):
        return pm.get_by_full_path(f"Cluster.Device {n}.{tail}")

    # ---------------------------------------------------------------- 1. 로더
    setting = [p for p in pm.get_param_list() if re.fullmatch(r"Cluster\.Device \d+\.Setting", p.path)]
    control = [p for p in pm.get_param_list() if re.fullmatch(r"Cluster\.Device \d+\.Control", p.path)]
    rep.check(len(setting) == 8 * 30 and len(control) == 4 * 30, f"Setting {len(setting)} / Control {len(control)}")
    folder_setting = [p.name for p in pm.get_params_in_folder("Cluster.Device 0.Setting")]
    folder_control = [p.name for p in pm.get_params_in_folder("Cluster.Device 0.Control")]
    rep.check(folder_setting == SETTING_NAMES and folder_control == CONTROL_NAMES,
              f"폴더 내 순서: {folder_setting} / {folder_control}")

    option_read: dict[int, Nv1ReadSpec] = {}
    option_write: dict[int, Nv1WriteSpec] = {}
    for n in range(30):
        option_params = [dev(n, tail) for tail in list(OPTION_PATHS.values())]
        reads = {id(reg.get_read_spec(p)): reg.get_read_spec(p) for p in option_params}
        writes = {id(reg.get_write_spec(p)): reg.get_write_spec(p) for p in option_params}
        rep.check(len(reads) == 1 and isinstance(next(iter(reads.values())), Nv1ReadSpec)
                  and len(writes) == 1 and isinstance(next(iter(writes.values())), Nv1WriteSpec),
                  f"Device {n}: Option 6개가 읽기/쓰기 spec 하나씩 공유")
        option_read[n] = next(iter(reads.values()))
        option_write[n] = next(iter(writes.values()))
        rep.check(option_read[n].build_request() == f"G:{n:02d}i:04" and option_read[n].res_prefix == f"G:{n:02d}i:04",
                  f"Device {n}: Option 읽기 요청 {option_read[n].build_request()}")
        rep.check(option_write[n].res_prefix == f"G:{n:02d}s:04" and option_write[n].payload_len == 8
                  and option_write[n].fill == "0" and len(option_write[n].fields) == 6,
                  f"Device {n}: Option 쓰기 spec {option_write[n].describe()}")
        rep.check(all(p.acc == ParamAccType.RW and p.display_type == ParamDisplayType.ENUM for p in option_params),
                  f"Device {n}: Option param RW enum")

        for tail, suffix in NV2_SUFFIX.items():
            p = dev(n, tail)
            key = (f"20{n + 0x0E:02X}{suffix}", 0)
            rep.check(reg.get_nv2_key(p) == key and reg.get_by_nv2_key(*key) is p
                      and isinstance(reg.get_read_spec(p), Nv2ReadSpec) and isinstance(reg.get_write_spec(p), Nv2WriteSpec),
                      f"Device {n}: {tail} NV2 키 {reg.get_nv2_key(p)} (기대 {key})")

        target, restart = dev(n, "Control.Target Position"), dev(n, "Control.Restart Controller")
        rep.check(reg.get_read_spec(target) is None and isinstance(reg.get_write_spec(target), Nv1WriteSpec)
                  and target.acc == ParamAccType.WO and target.display_type == ParamDisplayType.POSI,
                  f"Device {n}: Target Position WO posi, 쓰기 spec 만")
        rep.check(reg.get_read_spec(restart) is None and isinstance(reg.get_write_spec(restart), Nv1WriteSpec)
                  and restart.acc == ParamAccType.WO and restart.btn_str_value == "01",
                  f"Device {n}: Restart Controller WO btn")

    rep.check(dev(0, "Control.Control Mode Setpoint").ref_list is p_enum.ControlModeSetpointEnum, "Control Mode Setpoint enum")
    rep.check(reg.get_param_codec(dev(0, "Setting.Position Offset")) is reg.get_codec("posi"), "Position Offset → posi codec")
    rep.check(reg.get_param_codec(dev(0, "Setting.Position Control Speed (%)")) is reg.get_codec("scale100"), "Speed → scale100")
    rep.check(reg.get_param_codec(dev(0, "Control.Target Position")) is reg.get_codec("posiold"), "Target → posiold")

    # ---------------------------------------------------------------- 2. ver1 대조
    with open(SRC_NV1, "r", encoding="utf-8") as f:
        src = [x for x in json.load(f) if x.get("path", "").startswith("Cluster.Device ")]
    for item in src:
        n = int(re.search(r"Device (\d+)", item["path"]).group(1))
        tail = re.sub(r"^Cluster\.Device \d+\.", "", item["path"])
        if tail == "Setting.Option":
            for sub in item["sub_items"]:
                sub_tail = re.sub(r"^Cluster\.Device \d+\.", "", sub["path"])
                p = dev(n, OPTION_PATHS[sub_tail])
                fd = next((fd for fd in option_read[n].fields if fd.param is p), None)
                wf = next((fd for fd in option_write[n].fields if fd.param is p), None)
                rep.check(fd is not None and wf is not None
                          and fd.offset + OPTION_PREFIX_LEN == sub["offset"] and fd.length == sub["len"]
                          and (wf.offset, wf.length) == (fd.offset, fd.length)
                          and p.ref_list is getattr(p_enum, sub["enum"]),
                          f"Device {n} {sub_tail}: 자리/enum 대조")
        elif tail in NV2_SUFFIX:
            p = dev(n, tail)
            ok = reg.get_nv2_key(p) == (item["id"], 0)
            if "min" in item:
                ok = ok and p.min_value == float(item["min"]) and p.max_value == float(item["max"])
            rep.check(ok, f"Device {n} {tail}: ver1 id {item['id']} / min max")
        elif tail == "Control.Target Position":
            p = dev(n, tail)
            spec = reg.get_write_spec(p)
            rep.check(spec.res_prefix == item["wres"] and spec.payload_len == item["len"]
                      and p.min_value == float(item["min"]) and p.max_value == float(item["max"]),
                      f"Device {n} Target: {spec.res_prefix} / {spec.payload_len}")
        elif tail == "Control.Restart Controller":
            spec = reg.get_write_spec(dev(n, tail))
            rep.check(spec.build_request({dev(n, tail): "01"}) == item["wreq"] and spec.res_prefix == item["wres"],
                      f"Device {n} Restart: {spec.build_request({dev(n, tail): '01'})} (ver1 {item['wreq']})")

    # ---------------------------------------------------------------- 3. Option 읽기
    n = 5
    end, start, mode, stroke, power, network = (dev(n, t) for t in (
        "Setting.Homing End Position", "Setting.Homing Start Condition", "Setting.Homing Mode",
        "Setting.Position Control Stroke Limitation", "Setting.Power Failure Option", "Setting.Network Failure Option"))
    err, retry = option_read[n].apply_response("G:05i:04" + "10210103")
    rep.check((err, retry) == (ParamParseErrType.NONE, False), f"Option 읽기: {err.name}")
    rep.check((end.value, power.value, stroke.value, network.value, start.value, mode.value) == (1, 0, 1, 0, 0, 3),
              f"Option 값: {(end.value, power.value, stroke.value, network.value, start.value, mode.value)}")
    rep.check(end.str_value == "1" and mode.str_value == "3", "Option 선로 원문")
    err, retry = option_read[n].apply_response("G:05i:04" + "1021010")
    rep.check((err, retry) == (ParamParseErrType.WRONG_PARAM_LENGTH, True), f"Option 길이 부족: {err.name}")

    # ---------------------------------------------------------------- 4. 쓰기 요청
    option_read[n].apply_response("G:05i:04" + "10210103")
    req = option_write[n].build_request({end: 0, mode: "1"})
    rep.check(req == "G:05s:04" + "00010001", f"Option 조합 쓰기(지정 2 + 현재 4, 예약 0): {req}")
    req = option_write[n].build_request({})
    rep.check(req == "G:05s:04" + "10010003", f"Option 현재 값 그대로: {req}")
    start.value = None
    rep.check(option_write[n].build_request({end: 0}) is None, "미확정 값이 있으면 요청 없음")
    rep.check(option_write[n].build_request({end: 0, start: 2}) == "G:05s:04" + "00010023", "미확정 필드를 값으로 주면 생성")
    rep.check(option_write[n].build_request({end: "x"}) is None, "형식 불량 값 → None")
    rep.check(option_write[n].build_request({end: 12, start: 0}) is None, "폭 초과(12 → 2자) → None")

    target = dev(0, "Control.Target Position")
    tspec = reg.get_write_spec(target)
    cases = [(30, "G:00R:030000"), (-30, "G:00R:-30000"), (-3, "G:00R:-03000"), (12.3456, "G:00R:012346"),
             (100, "G:00R:100000"), ("50", "G:00R:050000"), (0, "G:00R:000000"), (1000, None), (None, None), ("abc", None)]
    for value, expected in cases:
        got = tspec.build_request({target: value})
        rep.check(got == expected, f"Target {value!r} → {got!r} (기대 {expected!r})")
    rep.check(tspec.build_request({}) is None, "Target 값 없이(WO 현재값 None) → None")

    restart = dev(7, "Control.Restart Controller")
    rep.check(reg.get_write_spec(restart).build_request({restart: restart.btn_str_value}) == "G:07c:8201", "Restart 요청")

    # ---------------------------------------------------------------- 5. 쓰기 응답
    rep.check(option_write[n].apply_response("") == (ParamParseErrType.NONE, False), "RW 조합 쓰기는 응답 판정 없음")
    err, retry = tspec.apply_response("")
    rep.check((err, retry) == (ParamParseErrType.COMMUNICATION_ERR, True) and target.is_err, f"Target 빈 응답: {err.name}")
    err, retry = tspec.apply_response("E:001")
    rep.check((err, retry) == (ParamParseErrType.ERR_89_NOT_SUPPORTED, False) and target.is_not_support, f"Target E:: {err.name}")
    err, retry = tspec.apply_response("G:01R:")
    rep.check((err, retry) == (ParamParseErrType.WRONG_PREFIX, True), f"Target 접두 불일치: {err.name}")
    err, retry = tspec.apply_response("G:00R:030000")
    rep.check((err, retry) == (ParamParseErrType.NONE, False) and not target.is_err and not target.is_not_support,
              "Target 정상 응답 → 플래그 해제")

    # ---------------------------------------------------------------- 6. 워커
    from b_core.d_dal.service_port import ServicePort
    from b_core.e_worker_ver2.parameter_run_worker import ParameterRunWorker, StartResult, _JobOp
    freeze = dev(n, "Control.Freeze")
    w = ParameterRunWorker(log_source="test")
    svc = ServicePort()
    try:
        for p in (end, start, mode, stroke, power, network, freeze):
            w.add_write_param_ptr(p)
        svc._connect_info = "test"
        rep.check(w.refresh() == StartResult.OK, "refresh OK")
        specs = [j.spec.build_request() for j in w._jobs]
        w._stop_all()
        rep.check(specs == ["G:05i:04", f"p:0B{reg.get_nv2_key(freeze)[0]}00"],
                  f"refresh 큐: Option 읽기 1건 + Freeze 읽기 1건 — {specs}")

        option_read[n].apply_response("G:05i:04" + "10210103")
        rep.check(w.write([(end, 0), (mode, 1), (freeze, 1)]) == StartResult.OK, "write OK")
        jobs = list(w._jobs)
        w._stop_all()
        write_jobs = [j for j in jobs if j.op is _JobOp.WRITE]
        read_jobs = [j for j in jobs if j.op is _JobOp.READ]
        rep.check(len(write_jobs) == 2 and write_jobs[0].spec is option_write[n]
                  and write_jobs[0].spec.build_request(write_jobs[0].values) == "G:05s:04" + "00010001",
                  f"쓰기 큐: Option 1건(조합) + Freeze 1건 — {[j.spec.describe() for j in write_jobs]}")
        rep.check([j.spec.build_request() for j in read_jobs] == ["G:05i:04", f"p:0B{reg.get_nv2_key(freeze)[0]}00"],
                  f"read-back: {[j.spec.build_request() for j in read_jobs]}")
    finally:
        svc._connect_info = ""
        w.cleanup()
        for p in (end, start, mode, stroke, power, network, freeze, target):
            p.value = None
            p.is_err = False
            p.is_not_support = False

    # ---------------------------------------------------------------- 7. ADC Calibration
    adc = pm.get_by_full_path("ADC Calibration.Calibration")
    adc_spec = reg.get_write_spec(adc)
    rep.check(adc is not None and adc.acc == ParamAccType.WO and adc.ref_list is p_enum.AdcCalibrationEnum
              and reg.get_read_spec(adc) is None and isinstance(adc_spec, Nv1WriteSpec),
              "ADC Calibration: WO enum, 쓰기 spec 만")
    for value, expected in (("11", "G:11"), (12, "G:12"), ("13", "G:13"), (1, "G:01"), (None, None), (123, None)):
        got = adc_spec.build_request({adc: value})
        rep.check(got == expected, f"ADC Calibration {value!r} → {got!r} (기대 {expected!r})")
    rep.check(adc_spec.apply_response("G:11") == (ParamParseErrType.NONE, False) and not adc.is_err, "ADC 응답 G:11 → 정상")
    err, retry = adc_spec.apply_response("E:001")
    rep.check((err, retry) == (ParamParseErrType.ERR_89_NOT_SUPPORTED, False) and adc.is_not_support, f"ADC E: → {err.name}")
    adc.is_not_support = False
    adc.is_err = False

    print(f"\nchecks {rep.checks} / fail {rep.fail}")
    print("ALL PASS" if rep.fail == 0 else f"{rep.fail} FAIL")
    return 0 if rep.fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
