"""패킷 규약(PacketSpec) 계층 — 값(Parameter)과 전송 규약을 분리하고, 판정과 적용을 분리한다 (6위 본안, 2026-10-12).

Parameter 는 값의 정의(타입/범위/값/시그널)만 갖고, "그 값이 어떤 패킷의 어느 자리에 어떻게 실리는가" 는 PacketSpec 이
맡는다. 워커는 spec 의 두 메서드만 호출하고, ServicePort 는 문자열 전송만 한다 — 프로토콜 지식은 이 폴더 밖으로 나가지 않는다.

    PacketSpec (읽기 또는 쓰기 1건의 규약, 상태 없음)
      ├ params                        이 패킷이 실어 나르는 Parameter 들
      ├ build_request(values)         요청 문자열, 만들 수 없으면 BuildFailure(사유)    — 하위 클래스가 구현
      ├ _judge(resp)                  응답 판정: Judgement(사유, 필드별 선로 원문) / None — 하위 클래스가 구현 (프로토콜 지식)
      ├ apply_response(resp)          _judge 결과를 param 에 적용하고 Outcome(부류, 사유)  — 기본 클래스가 구현 (앱 정책)
      ├ expected_response_prefix      정상 응답이 시작해야 하는 문자열 (재부팅 probe 판정·RawPacketSpec 용)
      └ codec_of(param)               그 param 의 선로 ↔ 도메인 codec

판정(_judge)과 적용(apply_response)의 분리:
- 하위 클래스는 응답이 무엇인지만 말한다 — 사유(ParamParseErrType)와, 정상이면 필드별 선로 원문. 값 디코드·플래그·대입 순서는
  건드리지 않는다. 판정하지 않는 응답(RW 쓰기 — N009 결정)은 None 을 돌려준다.
- 기본 클래스는 사유를 부류(Verdict)로 매핑하고(REASON 표), 정상이면 [원문 전부 대입 → 전부 디코드 → 값 반영] 을 한 순서로 하며
  (한 필드라도 형식 불량이면 값을 바꾸지 않고 DATA_TYPE_ERROR), 부류별 정책(POLICY 표)으로 플래그를 세운다.
  부류와 정책표는 이 파일에만 있다 — 새 프로토콜/spec 은 _judge 와 build_request 만 쓴다.
- 워커는 Outcome.verdict 만 본다: TRANSIENT 는 같은 요청을 재시도(refresh·쓰기 read-back 시퀀스는 즉시·무제한(F028 결정),
  백업·복원(CAPTURE/RAW) 시퀀스는 _Job.max_retry 까지 뒤 실패 기록, 모니터링은 다음 틱에 같은 spec), 그 밖의 부류는 다음 작업.
  쓰기는 부류와 무관하게 진행하고 재접속 param 이면 재부팅 대기로 들어간다(N045 결정).
- 예외 방어는 두지 않는다 — _judge 가 예외를 던지면 결함이므로 그대로 드러난다(F032 결정).

의도된 동작 변화 (2026-10-12 사용자 결정):
- NV2 읽기에서 헤더는 맞고 값 구간이 틀린 응답(값 없음/형식 불량)은 TRANSIENT 라 재시도 중 is_err 가 켜진다 — 전에는 헤더 검사가
  플래그를 먼저 지워 오류 표시 없이 재시도했다 (F042).
- NV1 쓰기의 "E:" 는 REJECTED 라 is_err 가 켜진다 — 전에는 플래그 불변(N008 결정은 Not Support 잠금을 막는 것이 취지였고,
  is_err 는 위젯을 잠그지 않으며 다음 성공한 쓰기가 지운다). 재시도하지 않는 것은 그대로.
- NV1/NV2 의 값·플래그 대입 순서가 하나로 통일된다 (원문 → 디코드 → 값 → 플래그).
- build_request 실패 사유 4종은 워커 로그(LogView)에만 남는다 — 건너뜀 대화상자는 지금처럼 한 번, 문구 그대로.

    SpecSelector (SpecRegistry 가 param 마다 읽기용/쓰기용 하나씩 보유)
      [(조건, spec), …] 을 갖고 resolve() 시점의 문맥으로 spec 하나를 고른다. 조건 없는 항목이 기본값.
      조건부 선택은 미도입 — 로더는 when 을 넘기지 않으며 모든 param 은 항목이 하나다 (훅만 준비, N011).

    바인딩(어떤 param 이 어떤 spec 을 쓰는가)은 Parameter 가 아니라 spec_registry.SpecRegistry 가 갖는다 (결정 A, 2026-09-11).

구현체: nv2_spec.py (Nv2ReadSpec / Nv2WriteSpec — param 1개 = 패킷 1개),
        nv1_spec.py (Nv1ReadSpec / Nv1WriteSpec — param n개 = 패킷 1개).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum, auto
from typing import TYPE_CHECKING, Callable, NamedTuple

from b_core.b_datatype.general_enum import ParamParseErrType

if TYPE_CHECKING:
    from b_core.b_datatype.parameter import Parameter

# 인자 없이 호출되어 "지금 이 규칙이 적용되는가" 를 답한다
Condition = Callable[[], bool]


# ------------------------------------------------------------ 결과 계약
class Verdict(Enum):
    """응답의 부류 — 워커의 다음 행동과 param 플래그를 정하는 유일한 입력."""
    OK = auto()           # 정상 — 값 반영, is_err/is_not_support 해제
    TRANSIENT = auto()    # 잡음·통신 오류·형식 불량 — is_err 켬, 같은 요청 재시도
    NOT_SUPPORT = auto()  # 이 장비에 그 param/패킷이 없다 — is_not_support 켬, 재시도 없음
    REJECTED = auto()     # 장비가 요청을 거부했다 — is_err 켬, 재시도 없음
    UNCHECKED = auto()    # 판정하지 않았다 (RW 쓰기 응답) — 플래그 불변, 재시도 없음


class BuildFailure(Enum):
    """build_request 가 요청을 만들 수 없는 사유 — 워커가 그 작업을 건너뛰고 로그에 남긴다."""
    VALUE_MISSING = auto()      # 실을 값이 없다 (None — NV1 read-modify-write 의 이웃 필드 현재 값 없음 포함)
    CONTEXT_NOT_READY = auto()  # codec 문맥(Position Unit / Pressure Unit·범위 / 센서 구성) 미준비
    BAD_VALUE = auto()          # 숫자가 아닌 입력 등 codec 이 받을 수 없는 값
    WIDTH_OVERFLOW = auto()     # NV1 고정 폭에 들어가지 않는다


class Judgement(NamedTuple):
    """_judge 의 반환 — 하위 클래스만 만든다. reason 이 NONE 이면 정상이고, 읽기 spec 은 fields 에 필드별 선로 원문을 싣는다
    (쓰기 spec 의 정상 응답은 fields 없이 NONE)."""
    reason: ParamParseErrType
    fields: dict["Parameter", str] | None = None


class Outcome(NamedTuple):
    """apply_response 의 반환 — 워커는 verdict 를, 로그·테스트는 reason 을 본다."""
    verdict: Verdict
    reason: ParamParseErrType

    @property
    def need_retry(self) -> bool:
        return POLICY[self.verdict].retry


class _Policy(NamedTuple):
    is_err: bool | None          # None = 유지
    is_not_support: bool | None  # None = 유지
    retry: bool


# 부류 → (is_err, is_not_support, 재시도). 오류 부류는 반대쪽 플래그를 건드리지 않는다 (현행과 동일) — 정상 읽기/쓰기만 둘 다 해제
POLICY: dict[Verdict, _Policy] = {
    Verdict.OK:          _Policy(False, False, False),
    Verdict.TRANSIENT:   _Policy(True,  None,  True),
    Verdict.NOT_SUPPORT: _Policy(None,  True,  False),
    Verdict.REJECTED:    _Policy(True,  None,  False),
    Verdict.UNCHECKED:   _Policy(None,  None,  False),
}

# 사유 → 부류. NONE 은 OK, 아래 두 집합에 없는 장비 오류 코드(ERR_xx)와 NV1 의 "E:" 쓰기 응답은 REJECTED
TRANSIENT_REASONS = frozenset({
    ParamParseErrType.COMMUNICATION_ERR,     # 빈 응답 (통신 오류 포함)
    ParamParseErrType.WRONG_FORMAT,
    ParamParseErrType.WRONG_PREFIX,
    ParamParseErrType.WRONG_PARAM_LENGTH,
    ParamParseErrType.WRONG_SVC_CODE,
    ParamParseErrType.WRONG_ID_OR_INDEX,
    ParamParseErrType.UNKNOWN_ERROR_CODE,
    ParamParseErrType.DATA_TYPE_ERROR,
})
NOT_SUPPORT_REASONS = frozenset({            # NV2 6E/73/7B/7E/89 — NV1 읽기의 "E:" 도 ERR_89 로 판정한다
    ParamParseErrType.ERR_6E_WRONG_PARAMETER_ID,
    ParamParseErrType.ERR_73_WRONG_PARAMETER_INDEX,
    ParamParseErrType.ERR_7B_PARAMETER_NOT_ACTIVE,
    ParamParseErrType.ERR_7E_UNKNOWN_SERVICE,
    ParamParseErrType.ERR_89_NOT_SUPPORTED,
})


def verdict_of(reason: ParamParseErrType) -> Verdict:
    if reason is ParamParseErrType.NONE:
        return Verdict.OK
    if reason in TRANSIENT_REASONS:
        return Verdict.TRANSIENT
    if reason in NOT_SUPPORT_REASONS:
        return Verdict.NOT_SUPPORT
    return Verdict.REJECTED


# ------------------------------------------------------------ 규약
class PacketSpec(ABC):

    def __init__(self, params: tuple["Parameter", ...]):
        self.params = params

    @abstractmethod
    def build_request(self, values: dict["Parameter", float | int | str] | None = None) -> str | BuildFailure:
        """요청 문자열. 읽기 spec 은 values 를 무시하고 항상 문자열, 쓰기 spec 은 values 에서 소속 param 의 도메인 값
        (숫자 또는 그 문자열)을 꺼내 채우며 만들 수 없으면 BuildFailure 를 돌려준다."""

    @abstractmethod
    def _judge(self, resp: str | None) -> Judgement | None:
        """응답 판정 — 프로토콜 지식은 여기까지. 정상이면 Judgement(NONE, 필드별 선로 원문(읽기) / None(쓰기)),
        아니면 Judgement(사유). 이 spec 이 판정하지 않는 응답(RW 쓰기)은 None. param 을 건드리지 않는다."""

    @property
    @abstractmethod
    def expected_response_prefix(self) -> str:
        """정상 응답이 시작해야 하는 문자열 — 워커의 재부팅 probe 가 SN 읽기 응답을 param 에 적용하지 않고 판정하는 기준(F026)이고,
        RawPacketSpec 이 접두 판정에 쓴다. 창은 응답을 직접 판정하지 않는다 (복원 패킷의 판정은 raw_packet_spec, data-protocol-2)."""

    def describe(self) -> str:
        """로그용 한 줄 설명."""
        names = ", ".join(f"{p.path}.{p.name}" for p in self.params)
        return f"{type(self).__name__}({names})"

    def codec_of(self, param: "Parameter"):
        """param 의 선로 ↔ 도메인 codec. 이 spec 이 그 param 을 싣지 않으면 None."""
        return None

    # ---- 적용 (하위 클래스는 오버라이드하지 않는다)
    def apply_response(self, resp: str | None) -> Outcome:
        """_judge → 부류 → (정상이면 값 반영) → 정책표로 플래그. 하위 클래스는 _judge 만 구현한다."""
        judgement = self._judge(resp)
        if judgement is None:
            return Outcome(Verdict.UNCHECKED, ParamParseErrType.NONE)

        reason = judgement.reason
        if reason is ParamParseErrType.NONE and judgement.fields:
            reason = self._apply_fields(judgement.fields)

        verdict = verdict_of(reason)
        policy = POLICY[verdict]
        for param in self.params:
            if policy.is_err is not None:
                param.is_err = policy.is_err
            if policy.is_not_support is not None:
                param.is_not_support = policy.is_not_support
        return Outcome(verdict, reason)

    def _apply_fields(self, fields: dict["Parameter", str]) -> ParamParseErrType:
        """선로 원문을 전부 str_value 에 넣고, 전부 디코드한 뒤에야 value 에 반영한다 — 한 자리라도 형식 불량이면 패킷 전체를
        불신해 값을 바꾸지 않는다 (DATA_TYPE_ERROR). 문맥 미준비로 None 이 나온 값도 그대로 반영한다 (화면은 Unknown, 다음 읽기가
        갱신 — 재디코드하지 않는다)."""
        for param, text in fields.items():
            param.str_value = text

        decoded = []
        for param, text in fields.items():
            try:
                decoded.append((param, self.codec_of(param).decode(text)))
            except ValueError:
                return ParamParseErrType.DATA_TYPE_ERROR

        for param, value in decoded:
            param.value = value
        return ParamParseErrType.NONE


class SpecSelector:
    """조건에 따라 spec 하나를 고르는 선택기.

    규칙은 등록 순서대로 평가한다. 조건이 있는 규칙 중 처음 참인 것을 고르고, 없으면 조건 없는 첫 규칙(기본)을 고른다.
    아무것도 없으면 None — 호출측은 "이 문맥에서는 이 값이 없다(Not Support)" 로 처리한다.
    (조건부 규칙은 미도입 — 로더가 when 을 넘기지 않는다. 훅만 둔다, N011)"""

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
