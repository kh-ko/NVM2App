"""1회성 마이그레이션 (4단계): param_nv1.json 의 "Cluster.Device x.Status" 30개 nv1_group 을
params.json 추가분 + nv1_spec.json 으로 옮긴다 (2026-09-15 사용자 결정: 템플릿, 오타 수정, factor).

- 30개 그룹이 장치 번호만 다르고 동일한지 먼저 확인한다 (다르면 실패, 아무것도 쓰지 않음).
- params.json: 값 정의만 (offset/len/id/idx 제거). 표시 타입은 posiold → posi (백분율 표시, 기존 POSI
  위젯), scale1000 → scale, 그 외 그대로. 장치 번호는 템플릿 변수 {dev} 로 한 번만 쓰고
  "expand": {"dev": [0, 29]} 를 붙인다 (17줄). "Cluster.Settings.Baud Rate V2" 뒤에 넣어 Cluster 트리를
  잇는다. 이미 들어 있으면 건너뛴다 (다시 실행해도 결과 동일). 원본의 CRLF 줄바꿈을 보존한다.
- nv1_spec.json: codecs(posiold ×0.001 / scale1000 ×0.1 = ScaleCodec) + reads 1건(템플릿, 필드 17개).
  offset 은 접두 "i:93XX"(6자) 를 뺀 페이로드 기준 0 (결정 5) — ver1 의 절대 offset 에서 6 을 뺀다.
- 오타 "No ADC Siganl On Logic" → "No ADC Signal On Logic" (신규 param, 호환 대상 없음).
- param_nv1.json 은 남긴다: Status 외 항목(Setting.Option 쓰기 그룹 등)이 6단계 참고 자료다.

사용:  python tools/migrate_nv1_status.py   (프로젝트 루트에서)
검증:  python tools/test_nv1_step4.py
"""

import json
import os
import re
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SCHEMA_DIR = os.path.join(ROOT, "2_resource", "param_schema")
SRC_NV1 = os.path.join(SCHEMA_DIR, "param_nv1.json")
PARAMS = os.path.join(SCHEMA_DIR, "params.json")
NV1_SPEC = os.path.join(SCHEMA_DIR, "nv1_spec.json")

DEV_VAR = "dev"
DEV_RANGE = [0, 29]                                 # 포함 범위 (장치 0 ~ 29)
PREFIX_LEN = len("i:9300")                          # 응답 접두 = 요청 문자열 그대로 (ver1 rres == rreq)
INSERT_AFTER = "Cluster.Settings.Baud Rate V2"      # params.json 에서 이 항목 뒤에 넣는다
TEMPLATE_PATH_PREFIX = f"Cluster.Device {{{DEV_VAR}}}.Status."

DISPLAY_TYPE = {"posiold": "posi", "scale1000": "scale"}   # params.json 의 type
LINE_CODEC = {"posiold": "posiold", "scale1000": "scale1000"}  # nv1_spec.json 의 "as"
CODECS = {
    "posiold":   {"kind": "scale", "factor": 0.001},   # 선로 100000 = 100 %
    "scale1000": {"kind": "scale", "factor": 0.1},     # 선로 1000 = 100 %
}
TYPO_FIX = {"No ADC Siganl On Logic": "No ADC Signal On Logic"}
PARAM_KEY_ORDER = ["type", "path", "expand", "acc", "local_acc", "nor_backup", "fu_backup", "min", "max", "enum", "desc"]


def _dump(item) -> str:
    return json.dumps(item, ensure_ascii=False)


def load_status_groups() -> list[dict]:
    with open(SRC_NV1, "r", encoding="utf-8") as f:
        data = json.load(f)
    groups = [g for g in data
              if g.get("type") == "nv1_group" and re.fullmatch(r"Cluster\.Device \d+\.Status", g["path"])]
    groups.sort(key=lambda g: int(re.search(r"Device (\d+)", g["path"]).group(1)))
    return groups


def normalize(group: dict) -> tuple[str, int]:
    """장치 번호를 {dev} 로 치환한 정규형 (동일성 비교용) + 번호."""
    n = int(re.search(r"Device (\d+)", group["path"]).group(1))
    g = json.loads(json.dumps(group))
    g["path"] = g["path"].replace(f"Device {n}.", "Device {dev}.")
    for s in g["sub_items"]:
        s["path"] = s["path"].replace(f"Device {n}.", "Device {dev}.")
    g["rreq"] = g["rres"] = "i:93{dev:02X}"
    return json.dumps(g, sort_keys=True), n


def build() -> tuple[list[dict], dict]:
    groups = load_status_groups()
    if len(groups) != DEV_RANGE[1] - DEV_RANGE[0] + 1:
        raise SystemExit(f"status group 수 {len(groups)} != {DEV_RANGE}")

    base_key, _ = normalize(groups[0])
    for g in groups:
        key, n = normalize(g)
        if key != base_key:
            raise SystemExit(f"Device {n} 의 Status 그룹이 Device 0 과 다름")
        if g["rreq"] != f"i:93{n:02X}" or g["rres"] != g["rreq"]:
            raise SystemExit(f"Device {n}: rreq/rres 가 i:93{n:02X} 형식이 아님: {g['rreq']} / {g['rres']}")
        if g["acc"] != "RO" or g["wreq"] or g["wres"]:
            raise SystemExit(f"Device {n}: 읽기 전용 그룹이 아님")

    params_tpl: list[dict] = []
    fields_tpl: list[dict] = []
    for sub in groups[0]["sub_items"]:
        old_type = sub["type"]
        name = sub["path"].rsplit(".", 1)[1]
        name = TYPO_FIX.get(name, name)
        path = TEMPLATE_PATH_PREFIX + name
        if sub["acc"] != "RO" or sub.get("id") or sub.get("idx"):
            raise SystemExit(f"{sub['path']}: RO 가 아니거나 NV2 id 가 남아 있음")

        p = {"type": DISPLAY_TYPE.get(old_type, old_type), "path": path,
             "expand": {DEV_VAR: list(DEV_RANGE)},
             "acc": sub["acc"], "local_acc": sub["local_acc"],
             "nor_backup": sub["nor_backup"], "fu_backup": sub["fu_backup"]}
        for k in ("min", "max", "enum"):
            if k in sub:
                p[k] = sub[k]
        p["desc"] = sub.get("desc")
        params_tpl.append({k: p[k] for k in PARAM_KEY_ORDER if k in p})

        field = {"path": path, "offset": sub["offset"] - PREFIX_LEN, "len": sub["len"]}
        if old_type in LINE_CODEC:
            field["as"] = LINE_CODEC[old_type]
        fields_tpl.append(field)

    spec = {
        "codecs": CODECS,
        "reads": [{
            "name": "device_status",
            "expand": {DEV_VAR: list(DEV_RANGE)},
            "req": f"i:93{{{DEV_VAR}:02X}}",
            "res_prefix": f"i:93{{{DEV_VAR}:02X}}",
            "fields": fields_tpl,
        }],
        "writes": [],
    }
    return params_tpl, spec


def write_nv1_spec(spec: dict) -> None:
    """한 항목 = 한 줄 (nv2_spec.json 과 같은 결)."""
    with open(NV1_SPEC, "w", encoding="utf-8", newline="\n") as f:
        f.write("{\n")
        f.write('  "codecs": {\n' + ",\n".join(f"    {json.dumps(k)}: {_dump(v)}" for k, v in spec["codecs"].items()) + "\n  },\n")
        f.write('  "reads": [\n')
        for i, rd in enumerate(spec["reads"]):
            f.write("    {" + f'"name": {json.dumps(rd["name"])}, "expand": {_dump(rd["expand"])}, '
                    f'"req": {json.dumps(rd["req"])}, "res_prefix": {json.dumps(rd["res_prefix"])},\n')
            f.write('     "fields": [\n' + ",\n".join("       " + _dump(fd) for fd in rd["fields"]) + "\n     ]}")
            f.write(",\n" if i < len(spec["reads"]) - 1 else "\n")
        f.write("  ],\n")
        f.write('  "writes": []\n')
        f.write("}\n")


def insert_params(params_tpl: list[dict]) -> int:
    """params.json 에 템플릿 줄을 넣는다. 이미 있으면 0. 반환: 넣은 줄 수."""
    with open(PARAMS, "r", encoding="utf-8", newline="") as f:
        text = f.read()
    if f'"path": "{TEMPLATE_PATH_PREFIX}' in text:
        return 0
    nl = "\r\n" if "\r\n" in text else "\n"
    lines = text.split(nl)
    idx = next(i for i, ln in enumerate(lines) if f'"path": "{INSERT_AFTER}"' in ln)
    assert lines[idx].rstrip().endswith("},"), lines[idx]
    lines[idx + 1:idx + 1] = ["  " + _dump(p) + "," for p in params_tpl]
    with open(PARAMS, "w", encoding="utf-8", newline="") as f:
        f.write(nl.join(lines))
    return len(params_tpl)


def main() -> int:
    params_tpl, spec = build()
    write_nv1_spec(spec)
    inserted = insert_params(params_tpl)
    print(f"nv1_spec.json: reads {len(spec['reads'])} (fields {len(spec['reads'][0]['fields'])}), codecs {list(spec['codecs'])}")
    print(f"params.json: 템플릿 {inserted} 줄 추가" if inserted else "params.json: 이미 추가되어 있음 (변경 없음)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
