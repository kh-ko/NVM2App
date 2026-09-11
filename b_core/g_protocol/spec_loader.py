"""프로토콜 스펙 파일 로더 — params.json 으로 만든 Parameter 에 spec 을 붙인다.

nv2_spec.json:
    {
      "read":  { "req": "p:0B{id}{idx:02X}",        "res_prefix": "p:000B{id}{idx:02X}" },
      "write": { "req": "p:01{id}{idx:02X}{value}", "res_prefix": "p:0001{id}{idx:02X}" },
      "params": [ { "path": "<full path>", "id": "<8자>", "idx": <int> }, ... ]
    }
    항목마다 Nv2ReadSpec / Nv2WriteSpec 을 만들어 SpecRegistry 에 등록한다.
    읽기/쓰기 사용 여부는 지금처럼 param.acc 로 워커가 정한다.
    "when"(조건부) 과 "expand"(템플릿) 는 NV1 단계에서 추가한다.

nv1_spec.json: NV1 단계.

검증 (결정 9): 스펙이 참조한 path 가 params.json 에 없으면 오류 로그, 어느
스펙에도 참조되지 않은 param 은 오류 로그 + is_not_support. 앱은 계속 뜬다 —
스키마 실수가 화면(Not Support 표시)과 로그에서 바로 드러나게 하는 것이 목적.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Callable, Optional

from b_core.c_manager.app_log_manager import AppLogManager
from b_core.g_protocol.nv2_spec import Nv2ReadSpec, Nv2WriteSpec
from b_core.g_protocol.spec_registry import SpecRegistry

if TYPE_CHECKING:
    from b_core.b_datatype.parameter import Parameter

_log = AppLogManager().get_logger("SpecLoader", is_global=True)

FindParam = Callable[[str], Optional["Parameter"]]


def load_nv2_specs(file_path: str, find_param: FindParam, registry: SpecRegistry) -> int:
    """nv2_spec.json 을 읽어 registry 에 spec 을 등록한다. find_param(full_path) -> Parameter | None.
    반환: 등록한 항목 수. 파일이 없거나 깨졌으면 0 (오류 로그)."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        _log.error(f"nv2 spec 로드 실패: {file_path} ({e})")
        return 0

    read_tpl = data.get("read", {})
    write_tpl = data.get("write", {})
    read_req, read_res = read_tpl.get("req"), read_tpl.get("res_prefix")
    write_req, write_res = write_tpl.get("req"), write_tpl.get("res_prefix")
    if not all((read_req, read_res, write_req, write_res)):
        _log.error(f"nv2 spec: read/write 템플릿 누락: {file_path}")
        return 0

    count = 0
    for item in data.get("params", []):
        path = item.get("path")
        id_code = item.get("id")
        index = item.get("idx")
        if not path or not isinstance(id_code, str) or not isinstance(index, int):
            _log.error(f"nv2 spec: 항목 형식 오류: {item}")
            continue

        param = find_param(path)
        if param is None:
            _log.error(f"nv2 spec: params.json 에 없는 path: {path}")
            continue

        registry.add_read_spec(param, Nv2ReadSpec(param, id_code, index, read_req, read_res))
        registry.add_write_spec(param, Nv2WriteSpec(param, id_code, index, write_req, write_res))
        registry.add_nv2_key(param, id_code, index)
        count += 1

    return count


def validate_specs(params: list["Parameter"], registry: SpecRegistry) -> int:
    """어느 스펙에도 없는 param 을 찾아 오류 로그 + Not Support 처리. 반환: 그 수."""
    missing = 0
    for param in params:
        if not registry.has_spec(param):
            _log.error(f"spec 없음 (params.json 에만 존재): {param.path}.{param.name}")
            param.is_not_support = True
            missing += 1
    return missing
