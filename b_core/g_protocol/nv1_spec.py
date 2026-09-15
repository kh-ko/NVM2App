"""NV1 프로토콜 규약 (Nv1ReadSpec) — PacketSpec 4단계.

프레임:
    요청  i:93XX                       요청 문자열 그대로 (nv1_spec.json reads[].req)
    응답  i:93XX + 고정 폭 페이로드      정상 응답은 res_prefix 로 시작한다 (보통 요청과 같은 문자열)
    오류  E:nnn                        별도 패킷. 코드별 뜻은 두지 않고 "이 장비에 그 패킷이 없다" 로 본다

패킷 하나가 param 여러 개를 싣는다. 자리(offset, len)와 해석(codec)은 nv1_spec.json 의
reads[].fields 가 주고, offset 은 접두(res_prefix)를 뺀 페이로드 기준 0 이다 (결정 5).
워커는 읽기 목록을 spec 기준으로 중복 제거하므로 소속 param 17개가 요청 1건이 된다.

응답 판정 — ver1 nv1_protocol_check_error 와 필드 절단 규칙을 ParamParseErrType 로 옮겼다:
    빈 응답                          COMMUNICATION_ERR, 재시도        (전원 is_err)
    "E:" 로 시작                     ERR_89_NOT_SUPPORTED, 재시도 없음 (전원 is_not_support — NV2 의
                                     NOT_SUPPORT_CODES 처리와 같이 is_err 는 건드리지 않는다)
    res_prefix 불일치                WRONG_PREFIX, 재시도
    페이로드가 마지막 필드보다 짧음     WRONG_PARAM_LENGTH, 재시도
    codec 형식 불량                  DATA_TYPE_ERROR, 재시도          (도메인 값 미반영, 선로 원문은 반영)
    정상                             NONE — 전원 is_err/is_not_support 해제, str_value(선로 원문) · value(도메인)

쓰기(Nv1WriteSpec)는 6단계에서 추가한다.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, NamedTuple

from b_core.b_datatype.general_enum import ParamParseErrType
from b_core.g_protocol.codec import Codec
from b_core.g_protocol.packet_spec import PacketSpec

if TYPE_CHECKING:
    from b_core.b_datatype.parameter import Parameter

ERR_PREFIX = "E:"


class Nv1Field(NamedTuple):
    param: "Parameter"
    offset: int      # 페이로드 기준 0
    length: int
    codec: Codec


class Nv1ReadSpec(PacketSpec):

    def __init__(self, name: str, req: str, res_prefix: str, fields: tuple[Nv1Field, ...]):
        super().__init__(tuple(f.param for f in fields))
        self.name = name
        self.req = req
        self.res_prefix = res_prefix
        self.fields = fields
        self.payload_len = max(f.offset + f.length for f in fields)  # 응답이 최소한 가져야 하는 페이로드 길이

    @property
    def expected_response_prefix(self) -> str:
        return self.res_prefix

    def describe(self) -> str:
        return f"{self.name} [NV1 {self.req}] {len(self.params)} params"

    def codec_of(self, param: "Parameter") -> Codec | None:
        for field in self.fields:
            if field.param is param:
                return field.codec
        return None

    def build_request(self, values=None) -> str:
        return self.req

    def apply_response(self, resp: str | None) -> tuple[ParamParseErrType, bool]:
        if not resp:
            self.set_error_state(True, None)
            return ParamParseErrType.COMMUNICATION_ERR, True

        if resp.startswith(ERR_PREFIX):
            self.set_error_state(None, True)
            return ParamParseErrType.ERR_89_NOT_SUPPORTED, False

        if not resp.startswith(self.res_prefix):
            self.set_error_state(True, None)
            return ParamParseErrType.WRONG_PREFIX, True

        payload = resp[len(self.res_prefix):]
        if len(payload) < self.payload_len:
            self.set_error_state(True, None)
            return ParamParseErrType.WRONG_PARAM_LENGTH, True

        # 선로 원문은 필드마다 먼저 반영하고(NV2 와 같은 순서), 도메인 값은 전 필드가 풀린 뒤 반영한다 —
        # 한 자리라도 형식 불량이면 패킷 전체를 불신해 값을 바꾸지 않는다
        values = []
        for field in self.fields:
            text = payload[field.offset:field.offset + field.length]
            field.param.str_value = text
            try:
                values.append(field.codec.decode(text))
            except ValueError:
                self.set_error_state(True, None)
                return ParamParseErrType.DATA_TYPE_ERROR, True

        self.set_error_state(False, False)
        for field, value in zip(self.fields, values):
            field.param.value = value  # 문맥 미준비(None)도 값으로 반영 — NV2 와 동일
        return ParamParseErrType.NONE, False
