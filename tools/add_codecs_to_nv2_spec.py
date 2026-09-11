"""1회성 마이그레이션 (3단계): nv2_spec.json 에 "codecs" 절과 항목별 "as" 를 추가한다.

"as" 는 params.json 의 표시 타입에서 한 번 만든다 (결정 G — 이후로는 규약 파일이 소유):
    posi → posi, pres → pres, presslope → pres (결정 J: 압력과 같은 변환),
    s1pres → pres_s1, s2pres → pres_s2, scale → scale100, ifgain → scale10000
그 외 타입은 "as" 없음 (형 변환만).

사용:  python tools/add_codecs_to_nv2_spec.py   (프로젝트 루트에서, 다시 실행해도 결과 동일)
"""

import json
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SCHEMA_DIR = os.path.join(ROOT, "2_resource", "param_schema")
PARAMS = os.path.join(SCHEMA_DIR, "params.json")
NV2 = os.path.join(SCHEMA_DIR, "nv2_spec.json")

TYPE_TO_CODEC = {
    "posi": "posi",
    "pres": "pres",
    "presslope": "pres",
    "s1pres": "pres_s1",
    "s2pres": "pres_s2",
    "scale": "scale100",
    "ifgain": "scale10000",
}

_PRES_CTX = {
    "iface_unit": "Interface.Scaling.Pressure.Pressure Unit",
    "iface_min": "Interface.Scaling.Pressure.Value Pressure Min",
    "iface_max": "Interface.Scaling.Pressure.Value Pressure Sensor Full Scale",
    "sens1": {
        "avail": "Sensor.Sensor 1.Basic.Available",
        "enable": "Sensor.Sensor 1.Basic.Enable",
        "unit": "Sensor.Sensor 1.Range.Data Unit",
        "min": "Sensor.Sensor 1.Range.Lower Limit Data Value",
        "max": "Sensor.Sensor 1.Range.Upper Limit Data Value",
    },
    "sens2": {
        "avail": "Sensor.Sensor 2.Basic.Available",
        "enable": "Sensor.Sensor 2.Basic.Enable",
        "unit": "Sensor.Sensor 2.Range.Data Unit",
        "min": "Sensor.Sensor 2.Range.Lower Limit Data Value",
        "max": "Sensor.Sensor 2.Range.Upper Limit Data Value",
    },
}

CODECS = {
    "posi": {
        "kind": "posi",
        "unit": "Interface.Scaling.Position.Position Unit",
        "min": "Interface.Scaling.Position.Value Closest Position",
        "max": "Interface.Scaling.Position.Value Open Position",
    },
    "pres": {"kind": "pres", "mode": "auto", **_PRES_CTX},
    "pres_s1": {"kind": "pres", "mode": "s1", **_PRES_CTX},
    "pres_s2": {"kind": "pres", "mode": "s2", **_PRES_CTX},
    "scale100": {"kind": "scale", "factor": 100},
    "scale10000": {"kind": "scale", "factor": 10000},
}


def _dump_lines(items: list, indent: str) -> str:
    return ",\n".join(indent + json.dumps(item, ensure_ascii=False) for item in items)


def main() -> int:
    with open(PARAMS, "r", encoding="utf-8") as f:
        type_of = {item["path"]: item["type"] for item in json.load(f)}
    with open(NV2, "r", encoding="utf-8") as f:
        spec = json.load(f)

    # 문맥 path 가 스키마에 있는지 확인
    missing = []
    for name, cfg in CODECS.items():
        for key, value in cfg.items():
            if isinstance(value, dict):
                missing += [f"{name}.{key}.{k}: {p}" for k, p in value.items() if p not in type_of]
            elif key not in ("kind", "mode", "factor") and value not in type_of:
                missing.append(f"{name}.{key}: {value}")
    if missing:
        for m in missing:
            print(f"[ERROR] codec 문맥 path 없음: {m}", file=sys.stderr)
        return 1

    counts: dict[str, int] = {}
    items = []
    for item in spec["params"]:
        item = {k: v for k, v in item.items() if k != "as"}
        codec = TYPE_TO_CODEC.get(type_of.get(item["path"], ""))
        if codec is not None:
            item["as"] = codec
            counts[codec] = counts.get(codec, 0) + 1
        items.append(item)

    with open(NV2, "w", encoding="utf-8", newline="\n") as f:
        f.write("{\n")
        f.write(f'  "read":  {json.dumps(spec["read"])},\n')
        f.write(f'  "write": {json.dumps(spec["write"])},\n')
        f.write('  "codecs": {\n')
        codec_lines = [f'    {json.dumps(name)}: {json.dumps(cfg, ensure_ascii=False)}' for name, cfg in CODECS.items()]
        f.write(",\n".join(codec_lines) + "\n  },\n")
        f.write('  "params": [\n' + _dump_lines(items, "    ") + "\n  ]\n")
        f.write("}\n")

    print(f"nv2_spec.json: {len(items)} items, codecs {len(CODECS)}, as: {counts}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
