"""스키마 템플릿 펼치기 — params.json / nv2_spec.json / nv1_spec.json 이 같은 규칙으로 쓴다 (PacketSpec 4·6단계).

"expand": {"<변수>": [lo, hi], ...} 를 가진 항목은 템플릿이다. 변수마다 lo..hi(포함) 를 돌며 항목 안의
모든 문자열 값의 자리표시자를 채운 복제본을 만들고 "expand" 키는 버린다. 변수가 둘 이상이면 곱집합이고
먼저 적힌 변수가 바깥 루프다. "expand" 가 없는 항목은 문자열을 건드리지 않고 그대로 둔다.

자리표시자 문법 (str.format 의 부분집합 + 정수 덧셈):
    {dev}            변수 값
    {dev:02X}        서식 지정 (Python format 서식 — 02d, 02X …)
    {dev+14:02X}     변수에 정수를 더한 값 (NV2 id 가 장치 번호 + 0x0E 인 경우). 뺄셈은 {dev-1}
    {payload}        keep 에 넣은 이름은 채우지 않고 그대로 남긴다 (쓰기 요청의 페이로드 자리 — 요청 시점에 채움)
그 밖의 알 수 없는 이름은 ValueError — 오타가 선로 문자열에 '{' 로 남는 것을 막는다.

    {"path": "Cluster.Device {dev}.Status.Freeze", "expand": {"dev": [0, 29]}, "type": "enum", ...}
    → {"path": "Cluster.Device 0.Status.Freeze", ...} … {"path": "Cluster.Device 29.Status.Freeze", ...}
    "i:93{dev:02X}" → "i:9300" … "i:931D"        "20{dev+14:02X}0800" → "200E0800" … "202B0800"

형식이 어긋나면 ValueError — 호출측(ParamManager / spec_loader)이 스키마 오류로 모은다.
"""

from __future__ import annotations

import re
from itertools import product

_PLACEHOLDER = re.compile(r"\{(\w+)([+-]\d+)?(?::([^{}]*))?\}")


def expand_items(items: list, keep: tuple[str, ...] = ()) -> list:
    """템플릿 항목을 펼친 새 목록. 순서는 등장 순서이며 템플릿 하나는 그 자리에 연속으로 펼쳐진다.
    keep: 채우지 않고 남겨 둘 자리표시자 이름 (예: 쓰기 요청의 "payload")."""
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
            out.append(_fill(body, dict(zip(names, values)), keep))
    return out


def _fill(obj, env: dict, keep: tuple[str, ...]):
    if isinstance(obj, str):
        return _fill_str(obj, env, keep)
    if isinstance(obj, list):
        return [_fill(x, env, keep) for x in obj]
    if isinstance(obj, dict):
        return {k: _fill(v, env, keep) for k, v in obj.items()}
    return obj


def _fill_str(text: str, env: dict, keep: tuple[str, ...]) -> str:
    def replace(match: re.Match) -> str:
        name, delta, spec = match.group(1), match.group(2), match.group(3)
        if name not in env:
            if name in keep and delta is None and spec is None:
                return match.group(0)
            raise ValueError(f"템플릿 변수 없음 {match.group(0)!r}: {text!r}")
        value = env[name] + (int(delta) if delta else 0)
        try:
            return format(value, spec or "")
        except ValueError as e:
            raise ValueError(f"템플릿 서식 오류 {match.group(0)!r}: {e}") from e

    return _PLACEHOLDER.sub(replace, text)
