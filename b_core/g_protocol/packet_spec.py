"""패킷 규약(PacketSpec) 계층 — 값(Parameter)과 전송 규약을 분리한다.

Parameter 는 값의 정의(타입/범위/값/시그널)만 갖고, "그 값이 어떤 패킷의 어느
자리에 어떻게 실리는가" 는 PacketSpec 이 맡는다. 워커는 spec 의 두 메서드만
호출하고, ServicePort 는 문자열 전송만 한다 — 프로토콜 지식은 이 폴더 밖으로
나가지 않는다.

    PacketSpec (읽기 또는 쓰기 1건의 규약, 상태 없음)
      ├ params                       이 패킷이 실어 나르는 Parameter 들
      ├ build_request(values)        요청 문자열 (읽기는 values 없이)
      ├ apply_response(resp)         응답 검증 + 소속 param 전부에 값/오류 반영
      │                              반환 (ParamParseErrType, 재시도 필요 여부)
      └ expected_response_prefix     정상 응답이 시작해야 하는 문자열 (raw 응답 검증용)

    SpecSelector (SpecRegistry 가 param 마다 읽기용/쓰기용 하나씩 보유)
      [(조건, spec), …] 을 갖고 resolve() 시점의 문맥으로 spec 하나를 고른다.
      조건 없는 항목이 기본값. 보통 param 은 항목이 하나뿐이다.
      조건은 인자 없는 callable — 로더가 참조 param 의 현재 값을 읽는 클로저로
      만든다 (결정 8: 선택기가 문맥을 직접 읽는다).

    바인딩(어떤 param 이 어떤 spec 을 쓰는가)은 Parameter 가 아니라
    spec_registry.SpecRegistry 가 갖는다 (결정 A, 2026-09-11) — Parameter 는 값만 안다.

구현체: nv2_spec.py (Nv2ReadSpec / Nv2WriteSpec), nv1_spec.py (NV1 단계).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Callable

from b_core.b_datatype.general_enum import ParamParseErrType

if TYPE_CHECKING:
    from b_core.b_datatype.parameter import Parameter

# 인자 없이 호출되어 "지금 이 규칙이 적용되는가" 를 답한다
Condition = Callable[[], bool]


class PacketSpec(ABC):

    def __init__(self, params: tuple["Parameter", ...]):
        self.params = params

    @abstractmethod
    def build_request(self, values: dict["Parameter", str] | None = None) -> str:
        """요청 문자열. 읽기 spec 은 values 를 무시하고, 쓰기 spec 은 values 에서
        소속 param 의 값을 꺼내 채운다."""

    @abstractmethod
    def apply_response(self, resp: str | None) -> tuple[ParamParseErrType, bool]:
        """응답을 검증하고 소속 param 들에 값 / is_err / is_not_support 를 반영한다.
        반환 (오류 종류, 재시도 필요) — 기존 Parameter.set_read_response_packet 과 같은 계약."""

    @property
    @abstractmethod
    def expected_response_prefix(self) -> str:
        """정상 응답이 시작해야 하는 문자열. 워커 밖에서 raw 응답을 검증하는 창
        (백업/복원)이 프로토콜을 모른 채 쓸 수 있게 노출한다."""

    def describe(self) -> str:
        """로그용 한 줄 설명."""
        names = ", ".join(f"{p.path}.{p.name}" for p in self.params)
        return f"{type(self).__name__}({names})"

    def set_error_state(self, is_err: bool | None, is_not_support: bool | None) -> None:
        """소속 param 전부의 오류 플래그를 한 번에 바꾼다 (None 은 유지)."""
        for param in self.params:
            if is_err is not None:
                param.is_err = is_err
            if is_not_support is not None:
                param.is_not_support = is_not_support


class SpecSelector:
    """조건에 따라 spec 하나를 고르는 선택기.

    규칙은 등록 순서대로 평가한다. 조건이 있는 규칙 중 처음 참인 것을 고르고,
    없으면 조건 없는 첫 규칙(기본)을 고른다. 아무것도 없으면 None — 호출측은
    "이 문맥에서는 이 값이 없다(Not Support)" 로 처리한다."""

    __slots__ = ("_rules",)

    def __init__(self):
        self._rules: list[tuple[Condition | None, PacketSpec]] = []

    def add(self, spec: PacketSpec, when: Condition | None = None) -> None:
        self._rules.append((when, spec))

    def resolve(self) -> PacketSpec | None:
        default = None
        for when, spec in self._rules:
            if when is None:
                if default is None:
                    default = spec
            elif when():
                return spec
        return default

    @property
    def is_empty(self) -> bool:
        return not self._rules

    def all_specs(self) -> list[PacketSpec]:
        return [spec for _, spec in self._rules]
