"""1회성 마이그레이션 (4·6단계): param_nv1.json 의 Cluster.Device x 항목 전부를
params.json / nv2_spec.json / nv1_spec.json 으로 옮긴다. (tools/migrate_nv1_status.py 를 대체)

원본 항목(장치 30대, 장치 번호 외 동일 — 검증 후 진행):
- Status 그룹        → 읽기 device_status  `i:93{dev:02X}` 필드 17개 (4단계, 2026-09-15 적용분과 동일)
- Setting.Option 그룹 → 읽기 device_option  `G:{dev:02d}i:04` 페이로드 8자, 필드 6개(자리 0,1,3,4,6,7; 2·5 예약 '0')
                      → 쓰기 device_option  `G:{dev:02d}s:04{payload}` 같은 자리 (사용자 확인 2026-09-15)
- NV2 4개             → nv2_spec.json 템플릿 4줄, id "20{dev+14:02X}xxxx" (장치 코드 = 0x0E + 번호)
- Control.Target Position   → 쓰기 device_target  `G:{dev:02d}R:{payload}` 6자 posiold (음수만 부호, 30 % → 030000)
- Control.Restart Controller → 쓰기 device_restart `G:{dev:02d}c:82{payload}` 2자, 버튼 값 "01"

사용자 결정(2026-09-15): 경로를 Setting / Control 두 폴더로 정리(ver1 의 Homing.* 와 Device 직하 항목 →
Setting.*), Target Position 은 posi(백분율) 표시, Control Mode Setpoint 는 ControlModeSetpointEnum,
Position Offset 은 다른 NV2 posi 와 같은 codec, backup 플래그 전부 false (Device 28 만 true 인 것은 복사 오류),
오타 "Siganl" → "Signal". NV1 G: 패킷의 장치 번호는 10진 2자리, i:93 은 16진.

다시 실행해도 결과 동일: params.json / nv2_spec.json 은 이 도구가 만드는 템플릿 줄을 (있으면 지우고)
정해진 자리에 다시 넣고, nv1_spec.json 은 전체를 다시 쓴다. 원본 줄바꿈(CRLF)을 보존한다.
param_nv1.json 은 남긴다 (참고 자료).

사용:  python tools/migrate_nv1_cluster.py   (프로젝트 루트에서)
검증:  python tools/test_nv1_step4.py && python tools/test_nv1_step6.py
"""

import json
import os
import re
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SCHEMA_DIR = os.path.join(ROOT, "2_resource", "param_schema")
SRC_NV1 = os.path.join(SCHEMA_DIR, "param_nv1.json")
PARAMS = os.path.join(SCHEMA_DIR, "params.json")
NV2_SPEC = os.path.join(SCHEMA_DIR, "nv2_spec.json")
NV1_SPEC = os.path.join(SCHEMA_DIR, "nv1_spec.json")

DEV = "dev"
DEV_RANGE = [0, 29]
EXPAND = {DEV: DEV_RANGE}
DEVICE = f"Cluster.Device {{{DEV}}}."                # 템플릿 path 접두
INSERT_AFTER = "Cluster.Settings.Baud Rate V2"       # params.json 에서 이 항목 뒤에 넣는다
NV2_CODE_OFFSET = 0x0E                               # NV2 id 의 장치 코드 = 0x0E + 장치 번호

STATUS_PREFIX_LEN = len("i:9300")
OPTION_PREFIX_LEN = len("G:00i:04")
OPTION_PAYLOAD_LEN = 8

DISPLAY_TYPE = {"posiold": "posi", "scale1000": "scale"}
LINE_CODEC = {"posiold": "posiold", "scale1000": "scale1000"}
NV2_CODEC = {"posi": "posi", "scale": "scale100"}     # tools/add_codecs_to_nv2_spec.py 와 같은 규칙
CODECS = {
    "posiold":   {"kind": "scale", "factor": 0.001},
    "scale1000": {"kind": "scale", "factor": 0.1},
}
TYPO_FIX = {"No ADC Siganl On Logic": "No ADC Signal On Logic"}

# ver1 sub_item 이름 → 정리된 path (Setting 폴더)
OPTION_PATHS = {
    "Cluster.Device N.Homing.End Position": "Setting.Homing End Position",
    "Cluster.Device N.Homing.Start Condition": "Setting.Homing Start Condition",
    "Cluster.Device N.Homing.Mode": "Setting.Homing Mode",
    "Cluster.Device N.Position Control Stroke Limitation": "Setting.Position Control Stroke Limitation",
    "Cluster.Device N.Power Failure Option": "Setting.Power Failure Option",
    "Cluster.Device N.Network Failure Option": "Setting.Network Failure Option",
}
# ver1 NV2 항목 (path 끝부분) → (id 접미, codec)
NV2_ITEMS = {
    "Setting.Position Control Speed (%)": "0800",
    "Setting.Position Offset": "2100",
    "Control.Freeze": "0100",
    "Control.Control Mode Setpoint": "0300",
}
CONTROL_MODE_SETPOINT_ENUM = "ControlModeSetpointEnum"

PARAM_KEY_ORDER = ["type", "path", "expand", "acc", "local_acc", "nor_backup", "fu_backup",
                   "min", "max", "enum", "value", "desc"]


def _dump(item) -> str:
    return json.dumps(item, ensure_ascii=False)


def _dev_no(path: str) -> int:
    return int(re.search(r"Device (\d+)", path).group(1))


def _norm(path: str) -> str:
    return re.sub(r"Device \d+\.", "Device N.", path)


# ================================================================== 원본 읽기 + 동일성 검증
def load_source() -> dict:
    with open(SRC_NV1, "r", encoding="utf-8") as f:
        data = json.load(f)

    by_key: dict[str, dict[int, dict]] = {}
    for item in data:
        path = item.get("path", "")
        if path.startswith("Cluster.Device "):
            by_key.setdefault(_norm(path), {})[_dev_no(path)] = item

    expected_count = DEV_RANGE[1] - DEV_RANGE[0] + 1
    for key, by_n in by_key.items():
        if sorted(by_n) != list(range(DEV_RANGE[0], DEV_RANGE[1] + 1)):
            raise SystemExit(f"{key}: 장치 {expected_count}대가 아님: {sorted(by_n)}")
        base = _strip_device(by_n[0])
        for n, item in by_n.items():
            if _strip_device(item) != base:
                raise SystemExit(f"{key}: Device {n} 이 Device 0 과 다름")
    return by_key


def _strip_device(item: dict) -> str:
    """장치 번호에 의존하는 값과 복사 오류(backup 플래그)를 뺀 정규형."""
    y = json.loads(json.dumps(item))
    for k in ("rreq", "rres", "wreq", "wres", "id", "path"):
        y.pop(k, None)
    y.pop("nor_backup", None)
    y.pop("fu_backup", None)
    for s in y.get("sub_items", []):
        s.pop("path", None)
        s.pop("nor_backup", None)
        s.pop("fu_backup", None)
    return json.dumps(y, sort_keys=True)


def _check_pattern(by_n: dict[int, dict], key: str, pattern) -> None:
    for n, item in by_n.items():
        expected = pattern(n)
        if item.get(key) != expected:
            raise SystemExit(f"{_norm(item['path'])}: Device {n} {key} {item.get(key)!r} != {expected!r}")


# ================================================================== 값 정의 (params.json)
def _param(type_: str, path: str, acc: str, **extra) -> dict:
    p = {"type": type_, "path": DEVICE + path, "expand": EXPAND, "acc": acc,
         "local_acc": False, "nor_backup": False, "fu_backup": False}
    p.update(extra)
    p.setdefault("desc", None)
    return {k: p[k] for k in PARAM_KEY_ORDER if k in p}


def build(src: dict):
    params: list[dict] = []
    nv2: list[dict] = []
    reads: list[dict] = []
    writes: list[dict] = []

    # ---- Status (읽기 전용 그룹)
    status = src["Cluster.Device N.Status"]
    _check_pattern(status, "rreq", lambda n: f"i:93{n:02X}")
    _check_pattern(status, "rres", lambda n: f"i:93{n:02X}")
    fields = []
    for sub in status[0]["sub_items"]:
        name = TYPO_FIX.get(sub["path"].rsplit(".", 1)[1], sub["path"].rsplit(".", 1)[1])
        path = f"Status.{name}"
        extra = {k: sub[k] for k in ("min", "max", "enum") if k in sub}
        params.append(_param(DISPLAY_TYPE.get(sub["type"], sub["type"]), path, "RO", **extra))
        field = {"path": DEVICE + path, "offset": sub["offset"] - STATUS_PREFIX_LEN, "len": sub["len"]}
        if sub["type"] in LINE_CODEC:
            field["as"] = LINE_CODEC[sub["type"]]
        fields.append(field)
    reads.append({"name": "device_status", "expand": EXPAND,
                  "req": f"i:93{{{DEV}:02X}}", "res_prefix": f"i:93{{{DEV}:02X}}", "fields": fields})

    # ---- Setting.Option (NV1 읽기 + 쓰기, 같은 자리)
    option = src["Cluster.Device N.Setting.Option"]
    _check_pattern(option, "rreq", lambda n: f"G:{n:02d}i:04")
    _check_pattern(option, "rres", lambda n: f"G:{n:02d}i:04")
    _check_pattern(option, "wreq", lambda n: f"G:{n:02d}s:04")
    _check_pattern(option, "wres", lambda n: f"G:{n:02d}s:04")
    fields = []
    for sub in option[0]["sub_items"]:   # 원본 순서(Homing 3 → Stroke → Power → Network) = 화면 폴더 순서
        path = OPTION_PATHS[_norm(sub["path"])]
        params.append(_param("enum", path, "RW", enum=sub["enum"]))
        fields.append({"path": DEVICE + path, "offset": sub["offset"] - OPTION_PREFIX_LEN, "len": sub["len"]})
    reads.append({"name": "device_option", "expand": EXPAND,
                  "req": f"G:{{{DEV}:02d}}i:04", "res_prefix": f"G:{{{DEV}:02d}}i:04", "fields": fields})
    writes.append({"name": "device_option", "expand": EXPAND,
                   "req": f"G:{{{DEV}:02d}}s:04{{payload}}", "res_prefix": f"G:{{{DEV}:02d}}s:04",
                   "payload_len": OPTION_PAYLOAD_LEN, "fill": "0", "fields": fields})

    # ---- NV2 4개 (Setting 2 + Control 2)
    for tail, suffix in NV2_ITEMS.items():
        by_n = src[f"Cluster.Device N.{tail}"]
        _check_pattern(by_n, "id", lambda n: f"20{n + NV2_CODE_OFFSET:02X}{suffix}")
        item = by_n[0]
        extra = {k: item[k] for k in ("min", "max", "enum") if k in item}
        if tail == "Control.Control Mode Setpoint":
            extra["enum"] = CONTROL_MODE_SETPOINT_ENUM
        params.append(_param(item["type"], tail, "RW", **extra))
        entry = {"path": DEVICE + tail, "expand": EXPAND, "id": f"20{{{DEV}+{NV2_CODE_OFFSET}:02X}}{suffix}", "idx": 0}
        if item["type"] in NV2_CODEC:
            entry["as"] = NV2_CODEC[item["type"]]
        nv2.append(entry)

    # ---- Control.Target Position (NV1 WO, 6자 posiold)
    target = src["Cluster.Device N.Control.Target Position"]
    _check_pattern(target, "wreq", lambda n: f"G:{n:02d}R:")
    _check_pattern(target, "wres", lambda n: f"G:{n:02d}R:")
    params.append(_param("posi", "Control.Target Position", "WO", min=target[0]["min"], max=target[0]["max"]))
    writes.append({"name": "device_target", "expand": EXPAND,
                   "req": f"G:{{{DEV}:02d}}R:{{payload}}", "res_prefix": f"G:{{{DEV}:02d}}R:",
                   "payload_len": target[0]["len"],
                   "fields": [{"path": DEVICE + "Control.Target Position", "offset": 0, "len": target[0]["len"], "as": "posiold"}]})

    # ---- Control.Restart Controller (NV1 WO, 버튼 값 "01")
    restart = src["Cluster.Device N.Control.Restart Controller"]
    value = restart[0]["value"]
    _check_pattern(restart, "wreq", lambda n: f"G:{n:02d}c:82{value}")
    _check_pattern(restart, "wres", lambda n: f"G:{n:02d}c:82")
    params.append(_param("btn", "Control.Restart Controller", "WO", value=value))
    writes.append({"name": "device_restart", "expand": EXPAND,
                   "req": f"G:{{{DEV}:02d}}c:82{{payload}}", "res_prefix": f"G:{{{DEV}:02d}}c:82",
                   "payload_len": len(value),
                   "fields": [{"path": DEVICE + "Control.Restart Controller", "offset": 0, "len": len(value)}]})

    spec = {"codecs": CODECS, "reads": reads, "writes": writes}
    return params, nv2, spec


# ================================================================== 파일 쓰기
def _read_lines(path: str) -> tuple[list[str], str]:
    with open(path, "r", encoding="utf-8", newline="") as f:
        text = f.read()
    nl = "\r\n" if "\r\n" in text else "\n"
    return text.split(nl), nl


def _write_lines(path: str, lines: list[str], nl: str) -> None:
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(nl.join(lines))


def _remove_template_lines(lines: list[str], paths: set[str]) -> list[str]:
    return [ln for ln in lines if not any(f'"path": "{p}"' in ln for p in paths)]


def write_params(params: list[dict]) -> int:
    lines, nl = _read_lines(PARAMS)
    lines = _remove_template_lines(lines, {p["path"] for p in params})
    idx = next(i for i, ln in enumerate(lines) if f'"path": "{INSERT_AFTER}"' in ln)
    assert lines[idx].rstrip().endswith("},"), lines[idx]
    lines[idx + 1:idx + 1] = ["  " + _dump(p) + "," for p in params]
    _write_lines(PARAMS, lines, nl)
    return len(params)


def write_nv2(entries: list[dict]) -> int:
    lines, nl = _read_lines(NV2_SPEC)
    lines = _remove_template_lines(lines, {e["path"] for e in entries})
    end = next(i for i, ln in enumerate(lines) if ln.rstrip() == "  ]")   # params 배열 닫힘
    lines[end - 1] = lines[end - 1].rstrip().rstrip(",") + ","
    new_lines = ["    " + _dump(e) + "," for e in entries]
    new_lines[-1] = new_lines[-1].rstrip(",")
    lines[end:end] = new_lines
    _write_lines(NV2_SPEC, lines, nl)
    return len(entries)


def write_nv1_spec(spec: dict) -> None:
    """한 항목 = 한 줄 (nv2_spec.json 과 같은 결)."""
    def packets(items: list[dict], extra_keys: tuple[str, ...]) -> str:
        chunks = []
        for it in items:
            head = f'"name": {json.dumps(it["name"])}, "expand": {_dump(it["expand"])}, ' \
                   f'"req": {json.dumps(it["req"])}, "res_prefix": {json.dumps(it["res_prefix"])}'
            for key in extra_keys:
                head += f', "{key}": {_dump(it[key])}'
            body = ",\n".join("       " + _dump(fd) for fd in it["fields"])
            chunks.append("    {" + head + ",\n" + '     "fields": [\n' + body + "\n     ]}")
        return ",\n".join(chunks)

    with open(NV1_SPEC, "w", encoding="utf-8", newline="\n") as f:
        f.write("{\n")
        f.write('  "codecs": {\n' + ",\n".join(f"    {json.dumps(k)}: {_dump(v)}" for k, v in spec["codecs"].items()) + "\n  },\n")
        f.write('  "reads": [\n' + packets(spec["reads"], ()) + "\n  ],\n")
        f.write('  "writes": [\n' + packets(spec["writes"], ("payload_len", "fill")) + "\n  ]\n")
        f.write("}\n")


def main() -> int:
    src = load_source()
    params, nv2, spec = build(src)
    # 쓰기 항목 중 fill 이 없는 것(단일 값)은 기본 "0" 으로 채워 둔다
    for w in spec["writes"]:
        w.setdefault("fill", "0")

    write_nv1_spec(spec)
    n_params = write_params(params)
    n_nv2 = write_nv2(nv2)
    print(f"nv1_spec.json: reads {len(spec['reads'])} / writes {len(spec['writes'])} / codecs {list(spec['codecs'])}")
    print(f"params.json: 템플릿 {n_params} 줄 ('{INSERT_AFTER}' 뒤)")
    print(f"nv2_spec.json: 템플릿 {n_nv2} 줄 (params 배열 끝)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
