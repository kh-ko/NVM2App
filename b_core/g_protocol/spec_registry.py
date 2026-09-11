"""SpecRegistry — "어떤 Parameter 가 어떤 PacketSpec 을 쓰는가" 의 단일 보관소.

값(Parameter) / 전송 규약(PacketSpec) / 둘의 바인딩 을 세 덩어리로 나눈 것 중
바인딩 담당이다 (결정 A, 2026-09-11). Parameter 는 spec 객체를 참조하지 않고,
워커·창은 여기서 param 으로 spec 을 찾는다.

    SpecRegistry()                       싱글턴 (ParamManager 와 같은 패턴)
      ├ add_read_spec(param, spec, when)      로더가 등록. when 은 조건 callable (없으면 기본)
      ├ add_write_spec(param, spec, when)
      ├ get_read_spec(param)             지금 문맥에서 쓸 읽기 spec. 없으면 None
      ├ get_write_spec(param)
      ├ has_spec(param)                  어느 규약에도 없는 param 검증용
      ├ add_nv2_key / get_nv2_key / get_by_nv2_key
      │                                  NV2 식별자 역조회 — 백업 파일(p:01 패킷)과
      │                                  Compound 프로토콜이 NV2 id/idx 를 값으로 쓰기 때문
      ├ add_codec / get_codec            이름 → Codec (nv2_spec.json "codecs" 절, 로더가 등록)
      ├ get_param_codec(param)           param 의 현재 읽기 spec 이 쓰는 codec
      ├ get_context_params(params)       params 의 codec 들이 읽는 문맥 param (순서 유지, 중복·자기 제외)
      │                                  — 워커가 refresh 큐 맨 앞에 넣는다 (3단계 결정 E)
      ├ decode_line(param, v)            숫자 선로값 → 도메인 값 (Compound 폴링 샘플용)
      ├ apply_line_text(param, text)     선로 문자열을 param 에 반영 (구 set_force_value 대체)
      └ clear()                          테스트용

조회는 param 객체를 키로 하는 dict 한 번이다. 워커는 시퀀스 시작 시 작업 큐를
만들 때만 조회하고, 응답 처리는 큐에 담긴 spec 을 그대로 쓴다 — 2,679개 전체를
한 번 조회하는 데 0.1 ms 미만 (2026-09-11 실측).

NV2 식별자 역조회 규칙: 같은 (id, idx) 를 공유하는 param 이 스키마에 8쌍 있어
get_by_nv2_key 는 "마지막 등록이 이긴다" — 기존 RestoreWin 의 dict 동작과 동일
(결정 C, 유지).
"""

from __future__ import annotations

import threading
from typing import TYPE_CHECKING, Iterable, Optional

from b_core.c_manager.app_log_manager import AppLogManager
from b_core.g_protocol.codec import Codec, TextCodec
from b_core.g_protocol.packet_spec import Condition, PacketSpec, SpecSelector

if TYPE_CHECKING:
    from b_core.b_datatype.parameter import Parameter

_log = AppLogManager().get_logger("SpecRegistry", is_global=True)


class SpecRegistry:
    _instance = None
    _creation_lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        with cls._creation_lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self.clear()

    def clear(self) -> None:
        self._read: dict["Parameter", SpecSelector] = {}
        self._write: dict["Parameter", SpecSelector] = {}
        self._nv2_key: dict["Parameter", tuple[str, int]] = {}
        self._param_of_nv2: dict[tuple[str, int], "Parameter"] = {}
        self._codecs: dict[str, Codec] = {}

    # ------------------------------------------------------------ 등록 (로더)
    def add_read_spec(self, param: "Parameter", spec: PacketSpec, when: Condition | None = None) -> None:
        self._read.setdefault(param, SpecSelector()).add(spec, when)

    def add_write_spec(self, param: "Parameter", spec: PacketSpec, when: Condition | None = None) -> None:
        self._write.setdefault(param, SpecSelector()).add(spec, when)

    def add_nv2_key(self, param: "Parameter", id_code: str, index: int) -> None:
        self._nv2_key[param] = (id_code, index)
        self._param_of_nv2[(id_code, index)] = param  # 중복 키는 마지막이 이긴다 (모듈 주석)

    def add_codec(self, name: str, codec: Codec) -> None:
        self._codecs[name] = codec

    # ------------------------------------------------------------ 조회 (워커·창)
    def get_read_spec(self, param: "Parameter") -> Optional[PacketSpec]:
        selector = self._read.get(param)
        return selector.resolve() if selector is not None else None

    def get_write_spec(self, param: "Parameter") -> Optional[PacketSpec]:
        selector = self._write.get(param)
        return selector.resolve() if selector is not None else None

    def has_spec(self, param: "Parameter") -> bool:
        return param in self._read or param in self._write

    def get_nv2_key(self, param: "Parameter") -> Optional[tuple[str, int]]:
        """param 의 NV2 (id, index). NV2 spec 이 없는 param 이면 None."""
        return self._nv2_key.get(param)

    def get_by_nv2_key(self, id_code: str, index: int) -> Optional["Parameter"]:
        """NV2 (id, index) 로 param 찾기. 같은 키를 공유하는 param 이 있으면 마지막 등록."""
        return self._param_of_nv2.get((id_code, index))

    # ------------------------------------------------------------ codec
    def get_codec(self, name: str) -> Optional[Codec]:
        return self._codecs.get(name)

    def get_param_codec(self, param: "Parameter") -> Codec:
        """param 의 현재 읽기(없으면 쓰기) spec 이 쓰는 codec. spec 이 없으면 형 변환 codec."""
        spec = self.get_read_spec(param) or self.get_write_spec(param)
        codec = getattr(spec, "codec", None)
        return codec if codec is not None else TextCodec.of(param.data_type)

    def get_context_params(self, params: Iterable["Parameter"]) -> list["Parameter"]:
        """params 의 codec 들이 읽는 문맥 param 목록 — 등장 순서 유지, 중복과 params 자신은 제외.
        워커가 refresh 큐 맨 앞에 넣어 decode 시점의 문맥이 최신임을 보장한다."""
        own = set(params)
        seen: set = set()
        result: list["Parameter"] = []
        for param in params:
            for ctx in self.get_param_codec(param).context_params:
                if ctx in own or ctx in seen:
                    continue
                seen.add(ctx)
                result.append(ctx)
        return result

    def decode_line(self, param: "Parameter", line_value: float) -> float | None:
        """숫자 선로값 → 도메인 값 (Compound 폴링 샘플 등). 문맥 미준비면 None."""
        if line_value is None:
            return None
        return self.get_param_codec(param).from_line(line_value)

    def apply_line_text(self, param: "Parameter", text: str) -> bool:
        """선로 문자열을 param 에 반영한다 — str_value 에 원문, value 에 codec 결과.
        형식 불량이면 False (구 set_force_value 와 같이 오류 로그). 성공 시 is_err 해제."""
        param.str_value = text
        try:
            param.value = self.get_param_codec(param).decode(text)
        except ValueError:
            _log.error(f"apply_line_text() 값 형식 오류: {param.path}, {param.name}, {text!r}")
            return False
        param.is_err = False
        return True
