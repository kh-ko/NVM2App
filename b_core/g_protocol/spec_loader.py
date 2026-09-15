"""프로토콜 스펙 파일 로더 — params.json 으로 만든 Parameter 에 spec 과 codec 을 붙인다.

nv2_spec.json:
    {
      "read":  { "req": "p:0B{id}{idx:02X}",        "res_prefix": "p:000B{id}{idx:02X}" },
      "write": { "req": "p:01{id}{idx:02X}{value}", "res_prefix": "p:0001{id}{idx:02X}" },
      "codecs": {                                   ← 3단계 (결정 G, H)
        "posi":     { "kind": "posi", "unit": "<path>", "min": "<path>", "max": "<path>" },
        "pres":     { "kind": "pres", "mode": "auto", "iface_unit": "<path>", "iface_min": "<path>",
                      "iface_max": "<path>", "sens1": { "avail": "<path>", "enable": "<path>",
                      "unit": "<path>", "min": "<path>", "max": "<path>" }, "sens2": { ... } },
        "pres_s1":  { "kind": "pres", "mode": "s1", ... }, "pres_s2": { ..., "mode": "s2" },
        "scale100": { "kind": "scale", "factor": 100 }, "scale10000": { "kind": "scale", "factor": 10000 }
      },
      "params": [ { "path": "<full path>", "id": "<8자>", "idx": <int>, "as": "posi" },
                  { "path": "Cluster.Device {dev}.Control.Freeze", "expand": { "dev": [0, 29] },
                    "id": "20{dev+14:02X}0100", "idx": 0 }, ... ]          ← 템플릿 항목 (6단계)
    }
    항목마다 Nv2ReadSpec / Nv2WriteSpec 을 만들어 SpecRegistry 에 등록한다. "as" 가 없으면
    형 변환만 하는 TextCodec(param.data_type). 읽기/쓰기 사용 여부는 param.acc 로 워커가 정한다.

nv1_spec.json (4·6단계):
    {
      "codecs": { "posiold": { "kind": "scale", "factor": 0.001 }, "scale1000": { "kind": "scale", "factor": 0.1 } },
      "reads": [
        { "name": "device_status", "expand": { "dev": [0, 29] },
          "req": "i:93{dev:02X}", "res_prefix": "i:93{dev:02X}",
          "fields": [ { "path": "Cluster.Device {dev}.Status.Actual Position", "offset": 0, "len": 6, "as": "posiold" },
                      { "path": "Cluster.Device {dev}.Status.Freeze",          "offset": 16, "len": 1 }, ... ] }
      ],
      "writes": [
        { "name": "device_option", "expand": { "dev": [0, 29] },
          "req": "G:{dev:02d}s:04{payload}", "res_prefix": "G:{dev:02d}s:04", "payload_len": 8, "fill": "0",
          "fields": [ { "path": "Cluster.Device {dev}.Setting.Homing End Position", "offset": 0, "len": 1 }, ... ] }
      ]
    }
    reads 항목마다 Nv1ReadSpec, writes 항목마다 Nv1WriteSpec 하나를 만들어 소속 param 전부에 등록한다.
    "expand" 항목은 템플릿이며 f_helper.schema_template.expand_items 가 변수 범위대로 펼친다 (params.json 도
    같은 규칙, ParamManager). offset 은 접두(res_prefix)를 뺀 페이로드 기준 0. 쓰기의 req 는 "{payload}" 자리
    하나를 가져야 하고(요청 시점에 채움), 필드는 payload_len 안에 들어가야 한다. codecs 절은 nv2 와 같은
    등록부에 들어가므로 이름이 겹치면 오류. 한 param 은 읽기 spec 하나, 쓰기 spec 하나만 가진다 (두 패킷이
    같은 path 를 참조하면 오류). "when"(조건부 선택) 은 아직 없다.

검증: 스펙이 참조한 path 가 params.json 에 없거나, 어느 스펙에도 참조되지 않은 param 이 있거나,
codec 정의(kind / 문맥 path / 'as' 이름)가 어긋나면 오류 로그를 남기고 같은 문구를 errors 목록에
모은다. 스키마 파일은 앱과 함께 배포되는 것이라 불일치는 손상으로 본다 — main.py 가 ParamManager
의 load_errors 를 보고 대화상자로 알린 뒤 종료한다 (2026-09-14 사용자 결정; 이전의 '앱은 계속
뜬다 + Not Support 표시' 정책(결정 9)을 대체). errors 를 넘기지 않은 호출(테스트 도구)은 로그만 남긴다.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Callable, Optional

from b_core.c_manager.app_log_manager import AppLogManager
from b_core.f_helper.schema_template import expand_items
from b_core.g_protocol.codec import Codec, PosiCodec, PresCodec, ScaleCodec, TextCodec
from b_core.g_protocol.nv1_spec import PAYLOAD_KEY, PAYLOAD_VAR, Nv1Field, Nv1ReadSpec, Nv1WriteSpec
from b_core.g_protocol.nv2_spec import Nv2ReadSpec, Nv2WriteSpec
from b_core.g_protocol.spec_registry import SpecRegistry

if TYPE_CHECKING:
    from b_core.b_datatype.parameter import Parameter

_log = AppLogManager().get_logger("SpecLoader", is_global=True)

FindParam = Callable[[str], Optional["Parameter"]]
Errors = Optional[list]  # 호출측이 넘긴 오류 수집 목록 (None 이면 로그만)


def _fail(errors: Errors, msg: str) -> None:
    """오류 로그 + (수집 목록이 있으면) 같은 문구를 모은다 — 기동 시 대화상자용."""
    _log.error(msg)
    if errors is not None:
        errors.append(msg)


def _load_json(label: str, file_path: str, errors: Errors) -> Optional[dict]:
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        _fail(errors, f"{label} 로드 실패: {file_path} ({e})")
        return None
    if not isinstance(data, dict):
        _fail(errors, f"{label}: 최상위가 객체가 아님: {file_path}")
        return None
    return data


def _expand(label: str, section: str, items, errors: Errors, keep: tuple[str, ...] = ()) -> Optional[list]:
    """템플릿 항목 펼치기. 형식 오류면 오류 + None."""
    if not isinstance(items, list):
        _fail(errors, f"{label} {section}: 배열이 아님")
        return None
    try:
        return expand_items(items, keep)
    except ValueError as e:
        _fail(errors, f"{label} {section}: {e}")
        return None


# ================================================================== codecs 절 (nv2 / nv1 공용)
def _ctx(label: str, find_param: FindParam, codec_name: str, cfg: dict, key: str, errors: Errors) -> Optional["Parameter"]:
    """codecs 절의 문맥 path 하나를 Parameter 로. 누락/미존재는 오류 + None."""
    path = cfg.get(key)
    if not path:
        _fail(errors, f"{label} codecs.{codec_name}: 문맥 키 누락: {key}")
        return None
    param = find_param(path)
    if param is None:
        _fail(errors, f"{label} codecs.{codec_name}.{key}: params.json 에 없는 path: {path}")
    return param


def _build_codec(label: str, name: str, cfg: dict, find_param: FindParam, errors: Errors) -> Optional[Codec]:
    kind = cfg.get("kind")
    if kind == "scale":
        return ScaleCodec(name, cfg.get("factor", 1.0))
    if kind == "posi":
        return PosiCodec(name, _ctx(label, find_param, name, cfg, "unit", errors),
                         _ctx(label, find_param, name, cfg, "min", errors),
                         _ctx(label, find_param, name, cfg, "max", errors))
    if kind == "pres":
        sens = {}
        for sens_key in ("sens1", "sens2"):
            sub = cfg.get(sens_key, {})
            sens[sens_key] = {k: _ctx(label, find_param, f"{name}.{sens_key}", sub, k, errors)
                              for k in ("avail", "enable", "unit", "min", "max")}
        try:
            return PresCodec(name, cfg.get("mode", "auto"),
                             _ctx(label, find_param, name, cfg, "iface_unit", errors),
                             _ctx(label, find_param, name, cfg, "iface_min", errors),
                             _ctx(label, find_param, name, cfg, "iface_max", errors),
                             sens["sens1"], sens["sens2"])
        except ValueError as e:
            _fail(errors, f"{label} codecs.{name}: {e}")
            return None
    _fail(errors, f"{label} codecs.{name}: 알 수 없는 kind: {kind}")
    return None


def _load_codecs(label: str, data: dict, find_param: FindParam, registry: SpecRegistry, errors: Errors) -> None:
    """codecs 절을 등록부에 넣는다. 등록부는 파일 공용이라 같은 이름은 오류."""
    for name, cfg in data.get("codecs", {}).items():
        if registry.get_codec(name) is not None:
            _fail(errors, f"{label} codecs.{name}: 이미 등록된 codec 이름")
            continue
        codec = _build_codec(label, name, cfg, find_param, errors)
        if codec is not None:
            registry.add_codec(name, codec)


def _resolve_codec(label: str, registry: SpecRegistry, param: "Parameter", as_name, where: str, errors: Errors) -> Codec:
    """항목의 "as" → 등록된 codec. 없으면 형 변환만 하는 TextCodec(param.data_type)."""
    codec = TextCodec.of(param.data_type)
    if as_name is None:
        return codec
    named = registry.get_codec(as_name)
    if named is None:
        _fail(errors, f"{label}: 정의되지 않은 codec '{as_name}': {where} — 형 변환만 적용")
        return codec
    return named


# ================================================================== NV2
def load_nv2_specs(file_path: str, find_param: FindParam, registry: SpecRegistry, errors: Errors = None) -> int:
    """nv2_spec.json 을 읽어 registry 에 codec 과 spec 을 등록한다. find_param(full_path) -> Parameter | None.
    반환: 등록한 param 항목 수 (템플릿을 펼친 뒤). 파일이 없거나 깨졌으면 0. 오류는 로그 + errors(있으면) 에 모은다."""
    label = "nv2 spec"
    data = _load_json(label, file_path, errors)
    if data is None:
        return 0

    read_tpl = data.get("read", {})
    write_tpl = data.get("write", {})
    read_req, read_res = read_tpl.get("req"), read_tpl.get("res_prefix")
    write_req, write_res = write_tpl.get("req"), write_tpl.get("res_prefix")
    if not all((read_req, read_res, write_req, write_res)):
        _fail(errors, f"{label}: read/write 템플릿 누락: {file_path}")
        return 0

    _load_codecs(label, data, find_param, registry, errors)

    items = _expand(label, "params", data.get("params", []), errors)
    if items is None:
        return 0

    count = 0
    for item in items:
        path = item.get("path")
        id_code = item.get("id")
        index = item.get("idx")
        if not path or not isinstance(id_code, str) or not isinstance(index, int):
            _fail(errors, f"{label}: 항목 형식 오류: {item}")
            continue

        param = find_param(path)
        if param is None:
            _fail(errors, f"{label}: params.json 에 없는 path: {path}")
            continue

        codec = _resolve_codec(label, registry, param, item.get("as"), path, errors)
        registry.add_read_spec(param, Nv2ReadSpec(param, id_code, index, read_req, read_res, codec))
        registry.add_write_spec(param, Nv2WriteSpec(param, id_code, index, write_req, write_res, codec))
        registry.add_nv2_key(param, id_code, index)
        count += 1

    return count


# ================================================================== NV1
def _nv1_fields(label: str, name: str, fields, find_param: FindParam, registry: SpecRegistry,
                errors: Errors, is_write: bool, payload_len: Optional[int]) -> Optional[list[Nv1Field]]:
    """reads/writes 항목의 fields → Nv1Field 목록. 하나라도 어긋나면 오류 + None (패킷 전체를 등록하지 않는다)."""
    if not isinstance(fields, list) or not fields:
        _fail(errors, f"{label} {name}: fields 가 비어 있음")
        return None

    result: list[Nv1Field] = []
    seen: set = set()
    ok = True
    for fd in fields:
        path, offset, length = fd.get("path"), fd.get("offset"), fd.get("len")
        if (not path or not isinstance(offset, int) or not isinstance(length, int)
                or isinstance(offset, bool) or isinstance(length, bool) or offset < 0 or length < 1):
            _fail(errors, f"{label} {name}: 필드 형식 오류 (path/offset/len): {fd}")
            ok = False
            continue
        if payload_len is not None and offset + length > payload_len:
            _fail(errors, f"{label} {name}: 필드가 payload_len {payload_len} 을 넘음: {fd}")
            ok = False
            continue

        param = find_param(path)
        if param is None:
            _fail(errors, f"{label} {name}: params.json 에 없는 path: {path}")
            ok = False
            continue

        existing = registry.get_write_spec(param) if is_write else registry.get_read_spec(param)
        if param in seen or existing is not None:
            _fail(errors, f"{label} {name}: {'쓰기' if is_write else '읽기'} spec 이 이미 있는 param: {path}")
            ok = False
            continue

        seen.add(param)
        result.append(Nv1Field(param, offset, length,
                               _resolve_codec(label, registry, param, fd.get("as"), f"{name} {path}", errors)))
    return result if ok else None


def load_nv1_specs(file_path: str, find_param: FindParam, registry: SpecRegistry,
                   errors: Errors = None) -> tuple[int, int]:
    """nv1_spec.json 을 읽어 reads 항목마다 Nv1ReadSpec, writes 항목마다 Nv1WriteSpec 을 만들고 소속 param
    전부에 등록한다. 반환: (읽기 spec 수, 쓰기 spec 수) — 템플릿을 펼친 뒤. 파일이 없거나 깨졌으면 (0, 0)."""
    label = "nv1 spec"
    data = _load_json(label, file_path, errors)
    if data is None:
        return 0, 0

    _load_codecs(label, data, find_param, registry, errors)

    read_count = 0
    reads = _expand(label, "reads", data.get("reads", []), errors)
    for item in reads or []:
        name, req, res_prefix = item.get("name"), item.get("req"), item.get("res_prefix")
        if not (isinstance(name, str) and name and isinstance(req, str) and req
                and isinstance(res_prefix, str) and res_prefix):
            _fail(errors, f"{label} reads: 항목 형식 오류 (name/req/res_prefix): {item}")
            continue

        fields = _nv1_fields(label, name, item.get("fields"), find_param, registry, errors, False, None)
        if fields is None:
            continue

        spec = Nv1ReadSpec(name, req, res_prefix, tuple(fields))
        for field in fields:
            registry.add_read_spec(field.param, spec)
        read_count += 1

    write_count = 0
    writes = _expand(label, "writes", data.get("writes", []), errors, keep=(PAYLOAD_VAR,))
    for item in writes or []:
        name, req, res_prefix = item.get("name"), item.get("req"), item.get("res_prefix")
        payload_len, fill = item.get("payload_len"), item.get("fill", "0")
        if not (isinstance(name, str) and name and isinstance(req, str) and req
                and isinstance(res_prefix, str) and res_prefix):
            _fail(errors, f"{label} writes: 항목 형식 오류 (name/req/res_prefix): {item}")
            continue
        if req.count(PAYLOAD_KEY) != 1 or req.count("{") != 1:
            _fail(errors, f"{label} {name}: req 는 {PAYLOAD_KEY} 자리 하나를 가져야 함: {req!r}")
            continue
        if not isinstance(payload_len, int) or isinstance(payload_len, bool) or payload_len < 1:
            _fail(errors, f"{label} {name}: payload_len 은 1 이상의 정수여야 함: {payload_len!r}")
            continue
        if not isinstance(fill, str) or len(fill) != 1:
            _fail(errors, f"{label} {name}: fill 은 한 글자여야 함: {fill!r}")
            continue

        fields = _nv1_fields(label, name, item.get("fields"), find_param, registry, errors, True, payload_len)
        if fields is None:
            continue

        spec = Nv1WriteSpec(name, req, res_prefix, payload_len, fill, tuple(fields))
        for field in fields:
            registry.add_write_spec(field.param, spec)
        write_count += 1

    return read_count, write_count


# ================================================================== 검증
def validate_specs(params: list["Parameter"], registry: SpecRegistry, errors: Errors = None) -> int:
    """어느 스펙에도 없는 param 을 찾아 오류 + Not Support 처리. 반환: 그 수."""
    missing = 0
    for param in params:
        if not registry.has_spec(param):
            _fail(errors, f"spec 없음 (params.json 에만 존재): {param.path}.{param.name}")
            param.is_not_support = True
            missing += 1
    return missing
