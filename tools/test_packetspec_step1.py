"""PacketSpec 1단계 차등 테스트 — 구 Parameter(프로토콜 내장) vs 새 SpecRegistry + Nv2 spec.

"외부 동작 불변" 을 기계적으로 확인한다. 비교 대상은 마지막 커밋(기본 61025d3)의
parameter.py 와 param.json 을 git 에서 꺼내 그대로 실행한 결과다.

    python tools/test_packetspec_step1.py                      # git show 61025d3:... 로 구 코드 확보
    python tools/test_packetspec_step1.py --old-commit <sha>

검사 항목
  1. 정적: 2,679 param 의 경로/타입/범위/acc/플래그/설명/enum 참조가 동일
     (의도된 편차 1건: "num " 오타 수정 → 표시 타입 None → NUMBER)
  2. enable/visible 조건: 옛 ref id → 마이그레이션이 고른 path 가 새 ref_path 와 동일
  3. 요청 문자열/응답 접두: 읽기·쓰기 요청과 정상 응답 접두가 바이트 단위 동일
  4. NV2 역조회: get_nv2_key == 옛 (id, idx), get_by_nv2_key == 옛 dict(마지막 등록 우선)
  5. 응답 차등: param 마다 읽기 14건 + 쓰기 8건의 응답을 양쪽에 넣고
     (반환값, is_err, is_not_support, value, str_value) 동일
  6. 워커: spec 중복 제거 순서, 쓰기 묶음, 미연결 시 NOT_CONNECTED
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import subprocess
import sys
import tempfile

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)

from PySide6.QtCore import QCoreApplication  # noqa: E402

_app = QCoreApplication.instance() or QCoreApplication(sys.argv)

from b_core.b_datatype.general_enum import (PARAM_DISPLAY_TYPE_MAP, ParamAccType,  # noqa: E402
                                            ParamDataType, ParamDisplayType, ParamParseErrType)
from b_core.c_manager.parameter_manager import ParamManager  # noqa: E402
from b_core.g_protocol.codec import TextCodec  # noqa: E402
from b_core.g_protocol.spec_registry import SpecRegistry  # noqa: E402

NUM_TYPO_PATH = "Interface RS232/RS485.Settings.Address"  # "num " → "num" 의도된 편차


class Report:
    def __init__(self):
        self.fail = 0
        self.checks = 0
        self.notes: list[str] = []

    def check(self, ok: bool, msg: str):
        self.checks += 1
        if not ok:
            self.fail += 1
            if self.fail <= 30:
                print(f"  FAIL {msg}")


def git_show(commit: str, path: str) -> str:
    return subprocess.check_output(["git", "-C", ROOT, "show", f"{commit}:{path}"]).decode("utf-8")


def load_old(commit: str, parameter_py: str | None, schema_json: str | None):
    tmp = tempfile.mkdtemp(prefix="packetspec_old_")
    if parameter_py is None:
        parameter_py = os.path.join(tmp, "old_parameter.py")
        with open(parameter_py, "w", encoding="utf-8") as f:
            f.write(git_show(commit, "b_core/b_datatype/parameter.py"))
    if schema_json is None:
        schema_json = os.path.join(tmp, "old_param.json")
        with open(schema_json, "w", encoding="utf-8") as f:
            f.write(git_show(commit, "2_resource/param_schema/param.json"))

    spec = importlib.util.spec_from_file_location("old_parameter", parameter_py)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    with open(schema_json, "r", encoding="utf-8") as f:
        items = json.load(f)
    olds = [mod.Parameter(item, PARAM_DISPLAY_TYPE_MAP.get(item.get("type", ""))) for item in items]
    return olds, items


def reset(param):
    param._value = None
    param.str_value = ""
    param._is_err = False
    param._is_not_support = False


def good_value(data_type) -> str:
    if data_type is ParamDataType.STR:
        return "abc"
    if data_type is ParamDataType.BASE_36:
        return "1Z"
    if data_type in (ParamDataType.FLOAT, ParamDataType.DOUBLE):
        return "1.5"
    return "123"


def read_cases(id_code: str, idx: int, data_type):
    h = f"{id_code}{idx:02X}"
    g = good_value(data_type)
    return [
        ("normal", f"p:000B{h}{g}"), ("empty", f"p:000B{h}"),
        ("err6E", f"p:6E0B{h}"), ("err76", f"p:760B{h}"), ("err50", f"p:500B{h}"), ("err89", f"p:890B{h}"),
        ("unknown", f"p:ZZ0B{h}"), ("otherid", f"p:000BFFFFFFFF{idx:02X}{g}"), ("svc", f"p:0001{h}{g}"),
        ("short", "p:0"), ("prefix", f"x:000B{h}{g}"), ("blank", ""), ("none", None), ("badtype", f"p:000B{h}abc!"),
    ]


def write_cases(id_code: str, idx: int):
    h = f"{id_code}{idx:02X}"
    return [
        ("ok", f"p:0001{h}"), ("short", "p:0"), ("err6E", f"p:6E01{h}"), ("err76", f"p:7601{h}"),
        ("unknown", f"p:ZZ01{h}"), ("otherid", f"p:0001FFFFFFFF{idx:02X}"), ("blank", ""), ("none", None),
    ]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--old-commit", default="61025d3")
    ap.add_argument("--old-parameter")
    ap.add_argument("--old-schema")
    args = ap.parse_args()

    rep = Report()
    olds, old_items = load_old(args.old_commit, args.old_parameter, args.old_schema)
    news = ParamManager().get_param_list()
    reg = SpecRegistry()
    print(f"old params {len(olds)} / new params {len(news)}")
    rep.check(len(olds) == len(news), "param 수 불일치")

    # 옛 ref id → path (마이그레이션과 같은 규칙: idx 0 우선, 없으면 첫 등장)
    by_id: dict[str, str] = {}
    for item in old_items:
        if item["idx"] == 0:
            by_id.setdefault(item["id"], item["path"])
    for item in old_items:
        by_id.setdefault(item["id"], item["path"])
    params_per_id: dict[str, set] = {}
    for item in old_items:
        params_per_id.setdefault(item["id"], set()).add(item["path"])

    # ---------------------------------------------------------------- 1. 정적 비교
    static_fields = ("path", "name", "data_type", "min_value", "max_value", "acc", "is_only_local_acc",
                     "is_nor_backup", "is_fu_backup", "description", "is_need_reconnect", "ref_list")
    ambiguous_refs = set()
    for o, n in zip(olds, news):
        tag = f"{o.path}.{o.name}"
        for f in static_fields:
            if tag == NUM_TYPO_PATH and f in ("data_type", "min_value", "max_value"):
                continue  # 의도된 편차: 표시 타입이 바뀌어 FLOAT(범위 없음) → UINT32(0~255)
            rep.check(getattr(o, f) == getattr(n, f), f"{tag}: {f} {getattr(o, f)!r} != {getattr(n, f)!r}")
        if tag == NUM_TYPO_PATH:
            rep.check(o.display_type is None and n.display_type is ParamDisplayType.NUMBER,
                      f"{tag}: 의도된 편차(None→NUMBER)가 아님: {o.display_type} → {n.display_type}")
            rep.check(n.data_type is ParamDataType.UINT32 and (n.min_value, n.max_value) == (0, 255),
                      f"{tag}: 의도된 편차 결과가 아님: {n.data_type} {n.min_value}~{n.max_value}")
            rep.notes.append(f"의도된 편차: {tag} 표시 타입 None → NUMBER, 값 타입 FLOAT(범위 없음) → "
                             f"UINT32 0~255 (\"num \" 오타 수정). 응답 차등에서 제외")
        else:
            rep.check(o.display_type == n.display_type, f"{tag}: display_type {o.display_type} != {n.display_type}")
        if o.display_type is ParamDisplayType.BTN:
            rep.check(o.btn_str_value == n.btn_str_value, f"{tag}: btn_str_value")
        rep.check(n.full_path == tag, f"{tag}: full_path {n.full_path}")

        # ------------------------------------------------------------ 2. enable/visible 조건
        for attr in ("enable_conditions", "visible_conditions"):
            oc, nc = getattr(o, attr), getattr(n, attr)
            rep.check((oc is None) == (nc is None) and (oc is None or len(oc) == len(nc)),
                      f"{tag}: {attr} 개수")
            if oc:
                for a, b in zip(oc, nc):
                    rep.check(by_id.get(a.ref_id) == b.ref_path, f"{tag}: {attr} ref {a.ref_id} → {b.ref_path}")
                    rep.check(a.values == b.values, f"{tag}: {attr} values")
                    if len(params_per_id.get(a.ref_id, ())) > 1:
                        ambiguous_refs.add(a.ref_id)

    # ---------------------------------------------------------------- 3. 요청/응답 접두
    for o, n in zip(olds, news):
        tag = f"{o.path}.{o.name}"
        rs, ws = reg.get_read_spec(n), reg.get_write_spec(n)
        rep.check(rs is not None and ws is not None, f"{tag}: spec 없음")
        if rs is None or ws is None:
            continue
        rep.check(rs.build_request() == f"p:0B{o.id}{o.index:02X}", f"{tag}: read req {rs.build_request()}")
        # 3단계: 쓰기 값은 도메인 값이라 codec param 은 선로 문자열이 달라진다 — 선로 원문 경로
        # (build_request_line, 백업 파일용)로 틀을 대조하고, 형 변환만 하는 param 은 값 경로도 같아야 한다
        rep.check(ws.build_request_line("1") == f"p:01{o.id}{o.index:02X}1", f"{tag}: write req (line)")
        if isinstance(reg.get_param_codec(n), TextCodec):
            rep.check(ws.build_request({n: "1"}) == f"p:01{o.id}{o.index:02X}1", f"{tag}: write req")
        rep.check(rs.expected_response_prefix == f"p:000B{o.id}{o.index:02X}", f"{tag}: read prefix")
        rep.check(ws.expected_response_prefix == f"p:0001{o.id}{o.index:02X}", f"{tag}: write prefix")
        rep.check(rs.params == (n,) and ws.params == (n,), f"{tag}: spec.params")

    # ---------------------------------------------------------------- 4. NV2 역조회
    old_last = {(o.id, o.index): o for o in olds}
    for o, n in zip(olds, news):
        rep.check(reg.get_nv2_key(n) == (o.id, o.index), f"{o.path}.{o.name}: get_nv2_key")
    for (id_code, idx), o in old_last.items():
        p = reg.get_by_nv2_key(id_code, idx)
        rep.check(p is not None and p.full_path == f"{o.path}.{o.name}", f"get_by_nv2_key({id_code},{idx})")
    dup = len(olds) - len(old_last)
    rep.notes.append(f"(id, idx) 중복 {dup}건 → 역조회는 마지막 등록 우선 (기존 동작 유지)")

    # ---------------------------------------------------------------- 5. 응답 차등
    cases = 0
    codec_cases = 0
    for o, n in zip(olds, news):
        tag = f"{o.path}.{o.name}"
        rs, ws = reg.get_read_spec(n), reg.get_write_spec(n)
        if rs is None or ws is None or tag == NUM_TYPO_PATH:
            continue
        # 3단계: codec 이 붙은 param(posi/pres/scale)은 value 가 도메인 값이라 구 값(선로 숫자)과
        # 다르다 — 그 param 은 value 를 codec.from_line(구 값) 과 비교한다 (문맥 없는 테스트라 None)
        codec = reg.get_param_codec(n)
        is_text = isinstance(codec, TextCodec)
        for name, resp in read_cases(o.id, o.index, o.data_type):
            reset(o); reset(n)
            r_old = o.set_read_response_packet(resp)
            r_new = rs.apply_response(resp)
            if is_text:
                s_old = (r_old, o.is_err, o.is_not_support, o.value, o.str_value)
                s_new = (r_new, n.is_err, n.is_not_support, n.value, n.str_value)
            else:
                expected_value = codec.from_line(o.value) if o.value is not None else None
                s_old = (r_old, o.is_err, o.is_not_support, expected_value, o.str_value)
                s_new = (r_new, n.is_err, n.is_not_support, n.value, n.str_value)
                codec_cases += 1
            rep.check(s_old == s_new, f"{tag}: read/{name} {s_old} != {s_new}")
            cases += 1
        for name, resp in write_cases(o.id, o.index):
            reset(o); reset(n)
            r_old = o.set_write_response_packet(resp)
            r_new = ws.apply_response(resp)
            s_old = (r_old, o.is_err, o.is_not_support, o.value, o.str_value)
            s_new = (r_new, n.is_err, n.is_not_support, n.value, n.str_value)
            rep.check(s_old == s_new, f"{tag}: write/{name} {s_old} != {s_new}")
            cases += 1
    rep.notes.append(f"응답 차등 {cases:,} 케이스 (그중 codec param 읽기 {codec_cases:,} 건은 value 를 codec.from_line(구 값) 과 대조)")

    # ---------------------------------------------------------------- 6. 워커 큐 구성
    # 구 워커(61025d3)의 규칙을 그대로 기대값으로 쓴다:
    #   refresh : init → write 목록(WO 제외) → read 목록, 전부 읽기
    #   write   : [Local 전환] → 쓰기 → 쓴 param read-back(WO 제외) → read 목록
    # 새 워커는 같은 spec 을 한 번만 보내므로, 목록에 중복이 없을 때 두 순서가 같아야 한다.
    from b_core.b_datatype import param_enum as p_enum
    from b_core.d_dal.service_port import ServicePort
    from b_core.e_worker_ver2.parameter_run_worker import ParameterRunWorker, StartResult, _JobOp

    old_by_path = {f"{o.path}.{o.name}": o for o in olds}

    def old_read(p):
        o = old_by_path[p.full_path]
        return f"p:0B{o.id}{o.index:02X}"

    def old_write(p, v):
        o = old_by_path[p.full_path]
        return f"p:01{o.id}{o.index:02X}{v}"

    pm = ParamManager()
    acc = pm.get_by_full_path("System.Access Mode")
    sn = pm.get_by_full_path("System.Identification.Serial Number")
    rw_params = [p for p in news if p.acc == ParamAccType.RW and not p.is_only_local_acc and p is not acc][:3]
    wo_param = next(p for p in news if p.acc == ParamAccType.WO)
    local_param = next(p for p in news if p.acc == ParamAccType.RW and p.is_only_local_acc)
    init_params = [sn, acc]
    write_params = [rw_params[0], wo_param, local_param]
    read_params = [rw_params[1], rw_params[2]]

    w = ParameterRunWorker(log_source="test")
    svc = ServicePort()
    try:
        rep.check(w.refresh() == StartResult.EMPTY, "refresh 미등록 EMPTY (구 워커와 같이 연결 검사보다 앞)")
        for p in init_params:
            w.add_init_param_ptr(p)
        for p in write_params:
            w.add_write_param_ptr(p)
        for p in read_params:
            w.add_read_param_ptr(p)

        rep.check(w.refresh() == StartResult.NOT_CONNECTED, "refresh NOT_CONNECTED")
        rep.check(w.write([(rw_params[0], "1")]) == StartResult.NOT_CONNECTED, "write NOT_CONNECTED")

        # 미연결 판정만 우회한다 — 요청은 포트가 없어 즉시 OPEN_ERROR 로 실패하고,
        # 이벤트 루프를 돌리지 않으므로 응답 처리는 일어나지 않는다. 큐만 본다
        svc._connect_info = "test"

        rep.check(w.refresh() == StartResult.OK, "refresh OK")
        actual = [j.spec.build_request(j.values) for j in w._jobs]
        w._stop_all()
        # 3단계: codec 문맥 param 이 맨 앞에 붙는다 (이 목록의 param 은 문맥이 없어 빈 목록)
        listed = init_params + [p for p in write_params if p.acc != ParamAccType.WO] + read_params
        ctx = reg.get_context_params(listed)
        expected = ([old_read(p) for p in ctx]
                    + [old_read(p) for p in init_params]
                    + [old_read(p) for p in write_params if p.acc != ParamAccType.WO]
                    + [old_read(p) for p in read_params])
        rep.check(actual == expected, f"refresh 큐 순서\n    구: {expected}\n    신: {actual}")

        acc._value = p_enum.AccModeEnum.REMOTE.value  # Local 전환이 필요한 상태
        pairs = [(local_param, "5"), (rw_params[0], "7"), (wo_param, "1")]
        rep.check(w.write(pairs) == StartResult.NEED_LOCAL_SWITCH, "write NEED_LOCAL_SWITCH")
        rep.check(w.write(pairs, switch_to_local=True) == StartResult.OK, "write OK")
        actual = [(j.op, j.spec.build_request(j.values)) for j in w._jobs]
        w._stop_all()
        expected = ([(_JobOp.WRITE, old_write(acc, str(p_enum.AccModeEnum.LOCAL.value)))]
                    + [(_JobOp.WRITE, old_write(p, v)) for p, v in pairs]
                    + [(_JobOp.READ, old_read(p)) for p, _ in pairs if p.acc != ParamAccType.WO]
                    + [(_JobOp.READ, old_read(p)) for p in read_params])
        rep.check(actual == expected, f"write 큐 순서\n    구: {expected}\n    신: {actual}")

        # 의도된 차이: 같은 param 이 두 목록에 있으면 구 워커는 두 번, 새 워커는 한 번 읽는다
        w.add_read_param_ptr(sn)
        rep.check(w.refresh() == StartResult.OK, "refresh(중복) OK")
        n_new = len(w._jobs)
        w._stop_all()
        n_old = len(init_params) + sum(1 for p in write_params if p.acc != ParamAccType.WO) + len(read_params) + 1
        rep.check(n_new == n_old - 1, f"중복 등록 시 요청 수: 구 {n_old} / 신 {n_new}")
        rep.notes.append(f"의도된 차이: 같은 param 을 두 목록에 등록하면 구 워커 {n_old}건, 새 워커 {n_new}건 요청 "
                         f"(중복 1건 제거). 실제 창의 중복 등록 여부는 test_windows_headless 가 보고")
    finally:
        svc._connect_info = ""
        acc._value = None
        w.cleanup()

    print()
    for note in rep.notes:
        print(f"  note: {note}")
    if ambiguous_refs:
        print(f"  note: enable/visible 참조 중 여러 param 이 공유하는 id {len(ambiguous_refs)}건 "
              f"(마이그레이션은 idx 0 param 의 path 를 택함): {sorted(ambiguous_refs)}")
    print(f"\nchecks {rep.checks:,}  fail {rep.fail}  → {'ALL PASS' if rep.fail == 0 else 'FAILED'}")
    return 0 if rep.fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
