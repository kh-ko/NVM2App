"""스키마 템플릿 펼치기 — params.json 과 nv1_spec.json 이 같은 규칙으로 쓴다 (PacketSpec 4단계).

"expand": {"<변수>": [lo, hi], ...} 를 가진 항목은 템플릿이다. 변수마다 lo..hi(포함) 를 돌며
항목 안의 모든 문자열 값을 str.format 으로 채운 복제본을 만들고 "expand" 키는 버린다.
변수가 둘 이상이면 곱집합이고 먼저 적힌 변수가 바깥 루프다. "expand" 가 없는 항목은
문자열을 건드리지 않고 그대로 둔다 (중괄호가 든 기존 path 도 안전).

    {"path": "Cluster.Device {dev}.Status.Freeze", "expand": {"dev": [0, 29]}, "type": "enum", ...}
    → {"path": "Cluster.Device 0.Status.Freeze", "type": "enum", ...}
      …
      {"path": "Cluster.Device 29.Status.Freeze", "type": "enum", ...}

    "req": "i:93{dev:02X}"  →  "i:9300" … "i:931D"   (format 지정자 그대로 사용)

형식이 어긋나면 ValueError — 호출측(ParamManager / spec_loader)이 스키마 오류로 모은다.
"""

from __future__ import annotations

from itertools import product


def expand_items(items: list) -> list:
    """템플릿 항목을 펼친 새 목록. 순서는 등장 순서이며 템플릿 하나는 그 자리에 연속으로 펼쳐진다."""
    out = []
    for item in items:
        if not isinstance(item, dict) or "expand" not in item:
            out.append(item)
            continue

        spec = item["expand"]
        if not isinstance(spec, dict) or not spec:
            raise ValueError(f"expand 는 {{변수: [lo, hi]}} 객체여야 함: {spec!r}")

        names, ranges = [], []
        for var, rng in spec.items():
            if (not isinstance(rng, list) or len(rng) != 2
                    or not all(isinstance(x, int) and not isinstance(x, bool) for x in rng)
                    or rng[0] > rng[1]):
                raise ValueError(f"expand.{var}: [lo, hi] 정수 범위가 아님: {rng!r}")
            names.append(var)
            ranges.append(range(rng[0], rng[1] + 1))

        body = {k: v for k, v in item.items() if k != "expand"}
        for values in product(*ranges):
            out.append(_fill(body, dict(zip(names, values))))
    return out


def _fill(obj, env: dict):
    if isinstance(obj, str):
        try:
            return obj.format(**env)
        except (KeyError, IndexError, ValueError) as e:
            raise ValueError(f"템플릿 문자열 오류 {obj!r}: {e}") from e
    if isinstance(obj, list):
        return [_fill(x, env) for x in obj]
    if isinstance(obj, dict):
        return {k: _fill(v, env) for k, v in obj.items()}
    return obj
