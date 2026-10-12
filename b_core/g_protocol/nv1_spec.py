"""NV1 프로토콜 규약 (Nv1ReadSpec / Nv1WriteSpec) — PacketSpec 4·6단계.

프레임:
    읽기 요청  i:93XX / G:00i:04           요청 문자열 그대로 (nv1_spec.json reads[].req)
    읽기 응답  접두 + 고정 폭 페이로드        정상 응답은 res_prefix 로 시작한다 (보통 요청과 같은 문자열)
    쓰기 요청  G:00s:04 + 페이로드          req 템플릿의 {payload} 자리에 고정 폭 페이로드를 채운다
    쓰기 응답  접두                         res_prefix 로 시작하면 정상
    오류       E:nnn                        별도 패킷. 코드별 뜻은 두지 않고 "이 장비에 그 패킷이 없다" 로 본다 (미결 ⑦)

패킷 하나가 param 여러 개를 싣는다. 자리(offset, len)와 해석(codec)은 nv1_spec.json 의 reads[].fields / writes[].fields 가 주고,
offset 은 접두를 뺀 페이로드 기준 0 이다 (결정 5). 워커는 읽기 목록과 쓰기 pending 을 spec 기준으로 묶으므로 소속 param 이
몇 개든 요청 1건이다.

이 파일은 판정만 한다 — _judge 가 사유(와 읽기의 필드별 선로 원문)를 돌려주고, 사유 → 부류, 플래그, 값 반영 순서는
packet_spec.PacketSpec 이 한 곳에서 적용한다 (6위 본안, 2026-10-12).

읽기 판정 (ver1 nv1_protocol_check_error 와 필드 절단 규칙):
    빈 응답                          COMMUNICATION_ERR
    "E:" 로 시작                     ERR_89_NOT_SUPPORTED (부류 NOT_SUPPORT — 전원 is_not_support, 재시도 없음)
    res_prefix 불일치                WRONG_PREFIX
    페이로드가 마지막 필드보다 짧음     WRONG_PARAM_LENGTH
    정상                             NONE + 필드별 원문 — 기본 클래스가 원문 전부 대입 → 전부 디코드 → 값 반영. 한 자리라도
                                     형식 불량이면 DATA_TYPE_ERROR 로 값을 바꾸지 않는다 (선로 원문은 반영)

쓰기 (Nv1WriteSpec, 2026-09-15 사용자 확정):
    페이로드 = fill 문자 × payload_len 에 필드마다 (offset, len) 자리를 덮어쓴 것. 자리 값은 codec.to_line(도메인 값) 을
    정수로 반올림해 len 폭으로 왼쪽 0 채움 — 음수는 부호 뒤에 채운다 (30 % → "030000", -3 % → "-03000"). 숫자 선로값이 없는
    codec(TextCodec — enum/버튼)은 encode 문자열을 그대로 채운다.
    values 에 없는 필드는 param.value(현재 값) 로 채운다 — read-modify-write (결정 6). 만들 수 없으면 BuildFailure:
    어느 필드든 값이 None 이면 VALUE_MISSING, 숫자가 아닌 입력은 BAD_VALUE, codec 문맥 미준비는 CONTEXT_NOT_READY, 폭을 넘치면
    WIDTH_OVERFLOW (워커가 건너뛰고 사유를 로그에 남긴다).
    응답은 NV2 와 같이 WO param 이 있을 때만 판정한다 (RW 는 None → UNCHECKED, 이어지는 read-back 이 확인):
        빈 응답 → COMMUNICATION_ERR / "E:" → NV1_ERROR_RESPONSE / 접두 불일치 → WRONG_PREFIX / 정상 → NONE
    "E:" 는 부류 REJECTED 다 — is_err 를 켜고 재시도하지 않는다 (2026-10-12 결정). Not Support 로 잠그지 않는 이유는
    2026-09-28 결정 그대로: WO param 은 refresh·read-back 어디서도 읽히지 않아 잠기면 그 쓰기를 일으킬 위젯이 비활성이 되어
    앱 재시작 전까지 복구 불가. is_err 는 위젯을 잠그지 않으며 다음 성공한 쓰기가 지운다.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, NamedTuple

from b_core.b_datatype.general_enum import ParamAccType, ParamParseErrType
from b_core.g_protocol.codec import Codec
from b_core.g_protocol.packet_spec import BuildFailure, Judgement, PacketSpec

if TYPE_CHECKING:
    from b_core.b_datatype.parameter import Parameter

ERR_PREFIX = "E:"
PAYLOAD_VAR = "payload"            # 쓰기 요청 템플릿에서 페이로드가 들어갈 자리표시자 이름
PAYLOAD_KEY = "{" + PAYLOAD_VAR + "}"


class Nv1Field(NamedTuple):
    param: "Parameter"
    offset: int      # 페이로드 기준 0
    length: int
    codec: Codec


def _fit_width(text: str, length: int) -> str | None:
    """고정 폭 정렬: 왼쪽 0 채움, 음수는 부호 뒤에 채움. 폭을 넘치면 None."""
    sign, body = ("-", text[1:]) if text.startswith("-") else ("", text)
    fitted = sign + body.rjust(length - len(sign), "0")
    return fitted if len(fitted) == length else None


class _Nv1Spec(PacketSpec):
    """NV1 spec 공통 — 필드 목록과 codec 조회."""

    def __init__(self, name: str, res_prefix: str, fields: tuple[Nv1Field, ...]):
        super().__init__(tuple(f.param for f in fields))
        self.name = name
        self.res_prefix = res_prefix
        self.fields = fields

    @property
    def expected_response_prefix(self) -> str:
        return self.res_prefix

    def codec_of(self, param: "Parameter") -> Codec | None:
        for field in self.fields:
            if field.param is param:
                return field.codec
        return None


class Nv1ReadSpec(_Nv1Spec):

    def __init__(self, name: str, req: str, res_prefix: str, fields: tuple[Nv1Field, ...]):
        super().__init__(name, res_prefix, fields)
        self.req = req
        self.payload_len = max(f.offset + f.length for f in fields)  # 응답이 최소한 가져야 하는 페이로드 길이

    def describe(self) -> str:
        return f"{self.name} [NV1 {self.req}] {len(self.params)} params"

    def build_request(self, values=None) -> str:
        return self.req

    def _judge(self, resp: str | None) -> Judgement:
        if not resp:
            return Judgement(ParamParseErrType.COMMUNICATION_ERR)
        if resp.startswith(ERR_PREFIX):
            return Judgement(ParamParseErrType.ERR_89_NOT_SUPPORTED)
        if not resp.startswith(self.res_prefix):
            return Judgement(ParamParseErrType.WRONG_PREFIX)

        payload = resp[len(self.res_prefix):]
        if len(payload) < self.payload_len:
            return Judgement(ParamParseErrType.WRONG_PARAM_LENGTH)
        return Judgement(ParamParseErrType.NONE,
                         {f.param: payload[f.offset:f.offset + f.length] for f in self.fields})


class Nv1WriteSpec(_Nv1Spec):

    def __init__(self, name: str, req_template: str, res_prefix: str, payload_len: int, fill: str,
                 fields: tuple[Nv1Field, ...]):
        super().__init__(name, res_prefix, fields)
        self.req_template = req_template   # "{payload}" 자리를 포함한다 (로더가 검증)
        self.payload_len = payload_len
        self.fill = fill
        # NV2 와 같은 규칙: 쓰기 응답은 WO param 이 있을 때만 판정한다
        self._judges_response = any(p.acc == ParamAccType.WO for p in self.params)

    def describe(self) -> str:
        return f"{self.name} [NV1 write {self.res_prefix}] {len(self.params)} params"

    def build_request(self, values=None) -> str | BuildFailure:
        """values[param] 은 도메인 값(숫자 또는 그 문자열). 없는 필드는 현재 값."""
        payload = list(self.fill * self.payload_len)
        for field in self.fields:
            value = values.get(field.param, field.param.value) if values else field.param.value
            text = self._field_text(field, value)
            if isinstance(text, BuildFailure):
                return text
            payload[field.offset:field.offset + field.length] = text
        return self.req_template.replace(PAYLOAD_KEY, "".join(payload))

    @staticmethod
    def _field_text(field: Nv1Field, value) -> str | BuildFailure:
        if value is None:
            return BuildFailure.VALUE_MISSING
        codec = field.codec
        try:
            line = codec.to_line(value)          # 숫자 선로값이 있는 codec (Scale / Posi / Pres)
        except TypeError:                          # TextCodec — 숫자 선로값 없음, encode 문자열 그대로
            try:
                text = codec.encode(value)
            except (ValueError, TypeError):
                return BuildFailure.BAD_VALUE
        except ValueError:                         # 숫자가 아닌 입력
            return BuildFailure.BAD_VALUE
        else:
            if line is None:                       # codec 문맥 미준비
                return BuildFailure.CONTEXT_NOT_READY
            text = str(int(round(line)))
        fitted = _fit_width(text, field.length)
        return BuildFailure.WIDTH_OVERFLOW if fitted is None else fitted

    def _judge(self, resp: str | None) -> Judgement | None:
        if not self._judges_response:
            return None  # RW 만 실린 쓰기 — 이어지는 read-back 이 확인

        if not resp:
            return Judgement(ParamParseErrType.COMMUNICATION_ERR)
        if resp.startswith(ERR_PREFIX):
            return Judgement(ParamParseErrType.NV1_ERROR_RESPONSE)   # 장비가 거부 — 부류 REJECTED (모듈 docstring)
        if not resp.startswith(self.res_prefix):
            return Judgement(ParamParseErrType.WRONG_PREFIX)
        return Judgement(ParamParseErrType.NONE)
