"""NV1 읽기 spec (4단계) 테스트 — 실제 로더 / Nv1ReadSpec / 워커로 Cluster Status 30대분을 확인한다.

    python tools/test_nv1_step4.py

검사 항목
  1. 로더: load_errors 없음. Cluster.Device n.Status param 510개, 읽기 spec 30개(각 17 param),
     요청 i:9300 ~ i:931D, 응답 접두 = 요청.
  2. ver1 param_nv1.json 대조: 필드 (offset + 6, len), 표시 타입(posiold → posi, scale1000 → scale),
     data_type / enum / min / max / acc, codec(posiold · scale1000 는 등록된 ScaleCodec, 그 외 TextCodec).
  3. 샘플 응답: 구 C++ viewtagcontainermodel.h 주석의 10건 + 30대분 합성 응답. apply_response 결과를
     ver1 규칙(절대 offset 절단 → 형 변환 → 배율)으로 계산한 기대값과 대조 (value / str_value / 플래그).
  4. 오류 경로: 빈 응답 / E: / 접두 불일치 / 길이 부족 / 형식 불량 → (ParamParseErrType, 재시도) 와
     is_err / is_not_support, 형식 불량 시 값 미반영.
  5. 등록부·워커: get_param_codec / decode_line 이 posiold codec 을 쓰는지, refresh 큐가 17 param → 요청 1건,
     NV2 param 과 섞여도 spec 등장 순서 유지, 30대 등록 → 30건.
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
from b_core.b_datatype.general_enum import ParamAccType, ParamDataType, ParamDisplayType, ParamParseErrType  # noqa: E402
from b_core.c_manager.parameter_manager import ParamManager  # noqa: E402
from b_core.g_protocol.codec import ScaleCodec, TextCodec  # noqa: E402
from b_core.g_protocol.nv1_spec import Nv1ReadSpec  # noqa: E402
from b_core.g_protocol.spec_registry import SpecRegistry  # noqa: E402

SRC_NV1 = os.path.join(ROOT, "2_resource", "param_schema", "param_nv1.json")
PREFIX_LEN = 6
TYPO_FIX = {"No ADC Siganl On Logic": "No ADC Signal On Logic"}
DISPLAY = {"posiold": ParamDisplayType.POSI, "scale1000": ParamDisplayType.SCALE, "enum": ParamDisplayType.ENUM,
           "enum36": ParamDisplayType.ENUM, "real": ParamDisplayType.REAL}
DATA_TYPE = {"posiold": ParamDataType.FLOAT, "scale1000": ParamDataType.FLOAT, "enum": ParamDataType.UINT32,
             "enum36": ParamDataType.BASE_36, "real": ParamDataType.FLOAT}
FACTOR = {"posiold": 0.001, "scale1000": 0.1}

# 구 C++ viewtagcontainermodel.h 111~120 행 주석
SAMPLES = [
    "i:9301100000+3000010000011000000000000000100000",
    "i:9302090000-3000001001020100000000000000010000",
    "i:930308000003000000900130010000000000000001000",
    "i:930407000000300000800240001000000000000000100",
    "i:930506000000030000700050000100000000000000010",
    "i:930605000000003000600060000001000000000000001",
    "i:930704000000000300500070000000010000000000000",
    "i:9308030000+03000004000C0000000001000000000000",
    "i:9309020000-00030003000D0000000000100000000000",
    "i:930A001000000000000100E0000000000010000000000",
]


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


def ver1_expected(sub: dict, resp: str):
    """ver1 규칙: 절대 offset 절단 → 타입별 형 변환 → 배율(사용자 요구 4·5)."""
    text = resp[sub["offset"]:sub["offset"] + sub["len"]]
    t = sub["type"]
    if t in FACTOR:
        return text, float(text) * FACTOR[t]
    if t == "enum36":
        return text, int(text, 36)
    if t == "enum":
        return text, int(text)
    return text, float(text)


def synth_response(n: int) -> str:
    """장치 n 의 합성 응답 (필드마다 n 에 따라 다른 값, 자리 47자)."""
    flags = "".join(str((n >> i) & 1) for i in range(10))                       # 10 플래그 (svc..logic 순서와 무관, 자리별 검사)
    ctrl = "0123456789ABCDE"[n % 15]
    payload = (f"{(n * 3333) % 100001:06d}" + f"{'+' if n % 2 else '-'}{n * 1000:05d}" + f"{n * 30:04d}"
               + str(n % 2) + str(n % 3) + ctrl + flags[0:5] + "0" + flags[5] + "0" + flags[6:10] + "0000"
               + f"{n * 100:06d}")
    assert len(payload) == 41, len(payload)
    return f"i:93{n:02X}" + payload


def main() -> int:
    rep = Report()
    pm = ParamManager()
    reg = SpecRegistry()
    for e in pm.load_errors:
        print(f"  load error: {e}")
    rep.check(not pm.load_errors, f"load_errors {len(pm.load_errors)} 건")

    # ---------------------------------------------------------------- 1. 로더
    status_params = [p for p in pm.get_param_list() if re.fullmatch(r"Cluster\.Device \d+\.Status", p.path)]
    rep.check(len(status_params) == 510, f"Cluster Status param 수 {len(status_params)} != 510")
    specs: dict[int, Nv1ReadSpec] = {}
    for p in status_params:
        spec = reg.get_read_spec(p)
        rep.check(isinstance(spec, Nv1ReadSpec), f"{p.full_path}: 읽기 spec 이 Nv1ReadSpec 이 아님: {spec}")
        rep.check(reg.get_write_spec(p) is None, f"{p.full_path}: 쓰기 spec 이 있음 (RO)")
        if isinstance(spec, Nv1ReadSpec):
            specs[id(spec)] = spec
    rep.check(len(specs) == 30, f"읽기 spec 수 {len(specs)} != 30")
    by_req = {s.build_request(): s for s in specs.values()}
    rep.check(set(by_req) == {f"i:93{n:02X}" for n in range(30)}, f"요청 문자열: {sorted(by_req)[:3]} …")
    for s in specs.values():
        rep.check(len(s.params) == 17 and len(s.fields) == 17, f"{s.describe()}: param 수 {len(s.params)}")
        rep.check(s.expected_response_prefix == s.build_request(), f"{s.describe()}: 응답 접두 != 요청")
        rep.check(s.payload_len == 41, f"{s.describe()}: 페이로드 길이 {s.payload_len}")
        rep.check(all(p.path == f"Cluster.Device {int(s.req[4:6], 16)}.Status" for p in s.params),
                  f"{s.describe()}: 다른 장치의 param 이 섞임")

    # ---------------------------------------------------------------- 2. ver1 대조
    with open(SRC_NV1, "r", encoding="utf-8") as f:
        groups = {g["path"]: g for g in json.load(f)
                  if g.get("type") == "nv1_group" and re.fullmatch(r"Cluster\.Device \d+\.Status", g["path"])}
    rep.check(len(groups) == 30, f"ver1 status 그룹 {len(groups)}")
    subs_by_param: dict = {}   # param → ver1 sub_item (3. 에서 재사용)
    for gpath, g in groups.items():
        spec = by_req.get(g["rreq"])
        if spec is None:
            rep.check(False, f"{gpath}: 요청 {g['rreq']} 에 해당하는 spec 없음")
            continue
        rep.check(spec.res_prefix == g["rres"], f"{gpath}: 응답 접두 {spec.res_prefix} != {g['rres']}")
        field_of = {fd.param: fd for fd in spec.fields}
        rep.check(len(spec.fields) == len(g["sub_items"]), f"{gpath}: 필드 수")
        for sub in g["sub_items"]:
            name = sub["path"].rsplit(".", 1)[1]
            path = f"{gpath}.{TYPO_FIX.get(name, name)}"
            param = pm.get_by_full_path(path)
            fd = field_of.get(param)
            if param is None or fd is None:
                rep.check(False, f"{path}: param/필드 없음")
                continue
            subs_by_param[param] = sub
            rep.check(fd.offset + PREFIX_LEN == sub["offset"] and fd.length == sub["len"],
                      f"{path}: (offset {fd.offset}+6, len {fd.length}) != ver1 ({sub['offset']}, {sub['len']})")
            t = sub["type"]
            rep.check(param.display_type == DISPLAY[t], f"{path}: 표시 타입 {param.display_type} (ver1 {t})")
            rep.check(param.data_type == DATA_TYPE[t], f"{path}: data_type {param.data_type} (ver1 {t})")
            rep.check(param.acc == ParamAccType.RO and not param.is_nor_backup and not param.is_fu_backup
                      and not param.is_only_local_acc, f"{path}: acc/backup/local_acc")
            if t in FACTOR:
                rep.check(fd.codec is reg.get_codec(t) and isinstance(fd.codec, ScaleCodec) and fd.codec.factor == FACTOR[t],
                          f"{path}: codec {fd.codec.name}")
            else:
                rep.check(isinstance(fd.codec, TextCodec) and fd.codec.data_type == DATA_TYPE[t], f"{path}: codec {fd.codec.name}")
            if "enum" in sub:
                rep.check(param.ref_list is getattr(p_enum, sub["enum"]), f"{path}: enum {sub['enum']}")
            if "min" in sub:
                rep.check(param.min_value == float(sub["min"]) and param.max_value == float(sub["max"]),
                          f"{path}: min/max {param.min_value}/{param.max_value}")

    # ---------------------------------------------------------------- 3. 샘플 응답
    def check_response(resp: str, label: str):
        spec = by_req[resp[:PREFIX_LEN]]
        err, retry = spec.apply_response(resp)
        rep.check(err is ParamParseErrType.NONE and retry is False, f"{label}: apply_response → {err.name}, retry {retry}")
        for fd in spec.fields:
            text, expected = ver1_expected(subs_by_param[fd.param], resp)
            rep.check(fd.param.str_value == text, f"{label} {fd.param.name}: str_value {fd.param.str_value!r} != {text!r}")
            rep.check(fd.param.value == expected, f"{label} {fd.param.name}: value {fd.param.value!r} != {expected!r}")
            rep.check(not fd.param.is_err and not fd.param.is_not_support, f"{label} {fd.param.name}: 플래그")

    for resp in SAMPLES:
        check_response(resp, resp[:6])
    for n in range(30):
        check_response(synth_response(n), f"합성 {n}")

    # 샘플 i:9301 의 대표값 (사람이 읽는 확인)
    s1 = by_req["i:9301"]
    s1.apply_response(SAMPLES[0])
    val = {fd.param.name: fd.param.value for fd in s1.fields}
    rep.check(val["Actual Position"] == 100.0 and val["Position Offset Used"] == 30.0
              and val["Position Control Speed Used (%)"] == 100.0 and val["Control Mode Used"] == 1
              and val["Service Request"] == 1 and val["Compressed Air Value(mbar)"] == 100000.0,
              f"i:9301 대표값: {val}")
    s8 = by_req["i:9308"]
    s8.apply_response(SAMPLES[7])
    rep.check(next(fd.param.value for fd in s8.fields if fd.param.name == "Control Mode Used") == 12,
              "i:9308 Control Mode 'C' → 12 (base36)")

    # ---------------------------------------------------------------- 4. 오류 경로
    s0 = by_req["i:9300"]
    good = synth_response(0)
    s0.apply_response(good)
    values_before = [fd.param.value for fd in s0.fields]

    err, retry = s0.apply_response("")
    rep.check((err, retry) == (ParamParseErrType.COMMUNICATION_ERR, True) and all(p.is_err for p in s0.params),
              f"빈 응답: {err.name}, {retry}")
    err, retry = s0.apply_response("E:001")
    rep.check((err, retry) == (ParamParseErrType.ERR_89_NOT_SUPPORTED, False) and all(p.is_not_support for p in s0.params),
              f"E: 응답: {err.name}, {retry}")
    err, retry = s0.apply_response(synth_response(1))
    rep.check((err, retry) == (ParamParseErrType.WRONG_PREFIX, True), f"접두 불일치: {err.name}, {retry}")
    err, retry = s0.apply_response(good[:-1])
    rep.check((err, retry) == (ParamParseErrType.WRONG_PARAM_LENGTH, True), f"길이 부족: {err.name}, {retry}")
    bad = good[:PREFIX_LEN] + "ABCDEF" + good[PREFIX_LEN + 6:]
    err, retry = s0.apply_response(bad)
    rep.check((err, retry) == (ParamParseErrType.DATA_TYPE_ERROR, True), f"형식 불량: {err.name}, {retry}")
    rep.check([fd.param.value for fd in s0.fields] == values_before, "형식 불량 시 도메인 값 미반영")
    rep.check(s0.fields[0].param.str_value == "ABCDEF", "형식 불량 시 선로 원문은 반영")
    err, retry = s0.apply_response(good)
    rep.check(err is ParamParseErrType.NONE and not any(p.is_err or p.is_not_support for p in s0.params),
              "정상 응답 후 플래그 해제")

    # ---------------------------------------------------------------- 5. 등록부 · 워커
    act0 = pm.get_by_full_path("Cluster.Device 0.Status.Actual Position")
    rep.check(reg.get_param_codec(act0) is reg.get_codec("posiold"), "get_param_codec → posiold")
    rep.check(reg.decode_line(act0, 50000.0) == 50.0, "decode_line posiold 50000 → 50")
    rep.check(reg.apply_line_text(act0, "025000") and act0.value == 25.0 and act0.str_value == "025000",
              f"apply_line_text posiold: {act0.value} / {act0.str_value!r}")

    from b_core.d_dal.service_port import ServicePort
    from b_core.e_worker_ver2.parameter_run_worker import ParameterRunWorker, StartResult, _JobOp
    acc_mode = pm.get_by_full_path("System.Access Mode")
    w = ParameterRunWorker(log_source="test")
    svc = ServicePort()
    try:
        for p in by_req["i:9300"].params:
            w.add_read_param_ptr(p)
        w.add_read_param_ptr(acc_mode)
        for p in by_req["i:9301"].params:
            w.add_read_param_ptr(p)
        svc._connect_info = "test"
        rep.check(w.refresh() == StartResult.OK, "refresh OK")
        jobs = list(w._jobs)
        w._stop_all()
        rep.check(len(jobs) == 3 and all(j.op is _JobOp.READ for j in jobs),
                  f"refresh 큐: 34 + 1 param → 요청 {len(jobs)} 건 (기대 3)")
        rep.check([j.spec.build_request() for j in jobs] == ["i:9300", "p:0B0F0B000000", "i:9301"],
                  f"refresh 큐 순서: {[j.spec.build_request() for j in jobs]}")

        w.read_param_list.clear()
        for p in status_params:
            w.add_read_param_ptr(p)
        rep.check(w.refresh() == StartResult.OK, "refresh(30대) OK")
        jobs = list(w._jobs)
        w._stop_all()
        rep.check(len(jobs) == 30 and [j.spec.build_request() for j in jobs] == [f"i:93{n:02X}" for n in range(30)],
                  f"30대 등록 → 요청 {len(jobs)} 건, 순서 0 → 29")
    finally:
        svc._connect_info = ""
        w.cleanup()

    print(f"\nchecks {rep.checks} / fail {rep.fail}")
    print("ALL PASS" if rep.fail == 0 else f"{rep.fail} FAIL")
    return 0 if rep.fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
