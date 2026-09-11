"""1회성 마이그레이션: param.json -> params.json + nv2_spec.json

- params.json : id / idx 를 뺀 값 정의. enable / visible 조건의 참조는
                {"id": ...} -> {"path": "<full path>"} 로 바꾼다 (46개 ref id 가
                전부 경로 하나에 유일하게 대응됨을 2026-09-10 확인).
                "type" 값의 앞뒤 공백을 정리한다 ("num " 1건).
- nv2_spec.json: NV2 요청/응답 템플릿 + (path, id, idx) 목록.
- 항목 순서는 원본 그대로, 한 항목 = 한 줄 (diff 가독성).

사용:  python tools/split_param_schema.py   (프로젝트 루트에서)
결과 확인 후 원본 param.json 은 삭제한다.
"""

import json
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SCHEMA_DIR = os.path.join(ROOT, "2_resource", "param_schema")
SRC = os.path.join(SCHEMA_DIR, "param.json")
DST_PARAMS = os.path.join(SCHEMA_DIR, "params.json")
DST_NV2 = os.path.join(SCHEMA_DIR, "nv2_spec.json")

NV2_READ = {"req": "p:0B{id}{idx:02X}", "res_prefix": "p:000B{id}{idx:02X}"}
NV2_WRITE = {"req": "p:01{id}{idx:02X}{value}", "res_prefix": "p:0001{id}{idx:02X}"}


def _dump_lines(items: list, indent: str = "  ") -> str:
    lines = [indent + json.dumps(item, ensure_ascii=False) for item in items]
    return ",\n".join(lines)


def main() -> int:
    with open(SRC, "r", encoding="utf-8") as f:
        src = json.load(f)

    # ref id -> full path (idx 0 인 항목 우선, 없으면 첫 등장 항목)
    by_id: dict[str, str] = {}
    for item in src:
        if item["idx"] == 0:
            by_id.setdefault(item["id"], item["path"])
    for item in src:
        by_id.setdefault(item["id"], item["path"])

    params, specs = [], []
    unresolved = []
    for item in src:
        p = dict(item)
        p["type"] = p["type"].strip()
        id_code, index = p.pop("id"), p.pop("idx")

        for key in ("enable", "visible"):
            conds = p.get(key)
            if not conds:
                continue
            new_conds = []
            for cond in conds:
                ref_id = cond.get("id")
                ref_path = by_id.get(ref_id)
                if ref_path is None:
                    unresolved.append((p["path"], key, ref_id))
                    continue
                new_conds.append({"path": ref_path, "conditions": cond.get("conditions", [])})
            p[key] = new_conds

        params.append(p)
        specs.append({"path": p["path"], "id": id_code, "idx": index})

    if unresolved:
        for path, key, ref_id in unresolved:
            print(f"[ERROR] {path}: {key} ref id {ref_id} 를 경로로 바꾸지 못함", file=sys.stderr)
        return 1

    with open(DST_PARAMS, "w", encoding="utf-8", newline="\n") as f:
        f.write("[\n" + _dump_lines(params) + "\n]\n")

    with open(DST_NV2, "w", encoding="utf-8", newline="\n") as f:
        f.write("{\n")
        f.write(f'  "read":  {json.dumps(NV2_READ)},\n')
        f.write(f'  "write": {json.dumps(NV2_WRITE)},\n')
        f.write('  "params": [\n' + _dump_lines(specs, indent="    ") + "\n  ]\n")
        f.write("}\n")

    print(f"params.json  : {len(params)} items")
    print(f"nv2_spec.json: {len(specs)} items")
    return 0


if __name__ == "__main__":
    sys.exit(main())
