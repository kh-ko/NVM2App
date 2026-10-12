"""NV2 프로토콜 규약 (Nv2ReadSpec / Nv2WriteSpec).

프레임 (ver1 부터 동일):
    요청  p:[서비스 2][ID 8][INDEX 2][VALUE n]        읽기 0B 는 VALUE 없음
    응답  p:[오류 2][서비스 2][ID 8][INDEX 2][VALUE n]  오류 "00" 이 정상
요청/응답 접두 템플릿은 nv2_spec.json 이 주고, 응답의 자리(오류/서비스/ID/INDEX = 16자 헤더)는 NV2 고정 규격이라 여기 상수로 둔다.

이 파일은 판정만 한다 — _judge 가 사유(와 읽기의 값 구간 원문)를 돌려주고, 사유 → 부류, 플래그, 값 반영 순서는
packet_spec.PacketSpec 이 한 곳에서 적용한다 (6위 본안, 2026-10-12). 장비 오류 코드 → 사유는 ERR_CODE_MAP 이 맡고, 그중
"장비에 그 param 이 없다" 는 코드(6E/73/7B/7E/89)를 NOT_SUPPORT 로 보는 판정은 packet_spec.NOT_SUPPORT_REASONS 에 있다.

판정 규칙 (구 Parameter.check_error 와 같다; INDEX 자리가 16진수가 아닌 잡음도 예외 없이 WRONG_ID_OR_INDEX — F041):
    빈 응답 → COMMUNICATION_ERR / 4자 미만 → WRONG_FORMAT / "p:" 아님 → WRONG_PREFIX
    오류 "00": 16자 미만 → WRONG_PARAM_LENGTH / 서비스 불일치 → WRONG_SVC_CODE / ID·INDEX 불일치 → WRONG_ID_OR_INDEX / 일치 → NONE
    그 밖의 오류 코드 → ERR_CODE_MAP 의 사유, 표에 없으면 UNKNOWN_ERROR_CODE (오류 응답은 서비스/ID/INDEX 를 보지 않는다)
    읽기는 헤더가 맞으면 값 구간(17자째부터)을 원문으로 넘긴다 — 없으면 STR 만 빈 문자열, 그 밖은 WRONG_PARAM_LENGTH
    쓰기 응답은 WO param 만 판정한다 — RW 는 None(UNCHECKED, N009 결정; 이어지는 read-back 이 확인)
값의 형 변환은 spec 에 붙은 codec 의 영역이다 (선로 문자열 ↔ 도메인 값).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from b_core.b_datatype.general_enum import ParamAccType, ParamDataType, ParamParseErrType
from b_core.g_protocol.codec import Codec
from b_core.g_protocol.packet_spec import BuildFailure, Judgement, PacketSpec

if TYPE_CHECKING:
    from b_core.b_datatype.parameter import Parameter

PREFIX = "p:"
HEADER_LEN = 16   # "p:"(2) + 오류(2) + 서비스(2) + ID(8) + INDEX(2)
SVC_READ = "0B"
SVC_WRITE = "01"

ERR_CODE_MAP = {
    "0C": ParamParseErrType.ERR_0C_WRONG_CMD_LEN,
    "1C": ParamParseErrType.ERR_1C_WRONG_CMD_LEN,
    "1D": ParamParseErrType.ERR_1D_VALUE_TOO_LOW,
    "20": ParamParseErrType.ERR_20_RESULTING_ZERO_ADJUST_OFFSET_VALUE_OUT_OF_RANGE,
    "21": ParamParseErrType.ERR_21_NOT_VALID_BECAUSE_NO_SENSOR_ENABLED,
    "50": ParamParseErrType.ERR_50_WRONG_ACCESS_MODE,
    "51": ParamParseErrType.ERR_51_TIMEOUT,
    "6D": ParamParseErrType.ERR_6D_EEPROM_NOT_READY,
    "6E": ParamParseErrType.ERR_6E_WRONG_PARAMETER_ID,
    "6F": ParamParseErrType.ERR_6F_SET_TO_DEFAULT_VALUE_NOT_ALLOWED,
    "70": ParamParseErrType.ERR_70_PARAMETER_NOT_SETTABLE,
    "71": ParamParseErrType.ERR_71_PARAMETER_NOT_READABLE,
    "72": ParamParseErrType.ERR_72_SET_TO_INITIAL_VALUE_NOT_ALLOWED,
    "73": ParamParseErrType.ERR_73_WRONG_PARAMETER_INDEX,
    "74": ParamParseErrType.ERR_74_INITIAL_VALUE_OUT_OF_RANGE,
    "76": ParamParseErrType.ERR_76_WRONG_VALUE,
    "77": ParamParseErrType.ERR_77_WRONG_VALUE_ONLY_RESET_POSSIBLE,
    "78": ParamParseErrType.ERR_78_NOT_ALLOWED_IN_THIS_STATE,
    "7A": ParamParseErrType.ERR_7A_WRONG_SERVICE,
    "7B": ParamParseErrType.ERR_7B_PARAMETER_NOT_ACTIVE,
    "7C": ParamParseErrType.ERR_7C_PARAMETER_SYSTEM_ERROR,
    "7D": ParamParseErrType.ERR_7D_COMMUNICATION_ERROR,
    "7E": ParamParseErrType.ERR_7E_UNKNOWN_SERVICE,
    "7F": ParamParseErrType.ERR_7F_UNEXPECTED_CHARACTER,
    "80": ParamParseErrType.ERR_80_NO_ACCESS_RIGHTS,
    "81": ParamParseErrType.ERR_81_NO_ADEQUATELY_HARDWARE,
    "82": ParamParseErrType.ERR_82_WRONG_OBJECT_STATE,
    "84": ParamParseErrType.ERR_84_NO_SLAVE_COMMAND,
    "85": ParamParseErrType.ERR_85_COMMAND_TO_UNKNOWN_SLAVE,
    "87": ParamParseErrType.ERR_87_COMMAND_TO_MASTER_ONLY,
    "88": ParamParseErrType.ERR_88_ONLY_G_COMMAND_ALLOWED,
    "89": ParamParseErrType.ERR_89_NOT_SUPPORTED,
    "A0": ParamParseErrType.ERR_A0_FUNCTION_IS_DISABLED,
    "A1": ParamParseErrType.ERR_A1_ALREADY_DONE,
}


def judge_header(resp: str | None, svc_code: str, id_code: str, index: int) -> ParamParseErrType:
    """NV2 응답 헤더 판정 — NONE 이면 오류 "00" 이고 서비스/ID/INDEX 가 주어진 값과 일치한다.
    _Nv2Spec 과 raw_packet_spec.Nv2RawWriteSpec(백업 파일의 쓰기 패킷)이 함께 쓴다."""
    if not resp:
        return ParamParseErrType.COMMUNICATION_ERR
    if len(resp) < 4:
        return ParamParseErrType.WRONG_FORMAT
    if resp[0:2] != PREFIX:
        return ParamParseErrType.WRONG_PREFIX

    err_code = resp[2:4]
    if err_code == "00":
        if len(resp) < HEADER_LEN:
            return ParamParseErrType.WRONG_PARAM_LENGTH
        if resp[4:6] != svc_code:
            return ParamParseErrType.WRONG_SVC_CODE
        try:
            index_ok = int(resp[14:16], 16) == index
        except ValueError:
            index_ok = False  # INDEX 자리가 16진수가 아님 — ID/INDEX 불일치와 같이 취급
        if resp[6:14] == id_code and index_ok:
            return ParamParseErrType.NONE
        return ParamParseErrType.WRONG_ID_OR_INDEX

    return ERR_CODE_MAP.get(err_code, ParamParseErrType.UNKNOWN_ERROR_CODE)


class _Nv2Spec(PacketSpec):
    """NV2 spec 공통 — param 1개 = 패킷 1개. 응답 헤더 판정을 공유한다."""

    SVC_CODE = ""  # 하위 클래스가 지정 (0B / 01)

    def __init__(self, param: "Parameter", id_code: str, index: int,
                 req_template: str, res_prefix_template: str, codec: Codec):
        super().__init__((param,))
        self.param = param
        self.id = id_code
        self.index = index
        self._req_template = req_template
        self._res_prefix_template = res_prefix_template
        self.codec = codec  # 선로 문자열 ↔ 도메인 값 (3단계). 문맥은 codec.context_params

    @property
    def expected_response_prefix(self) -> str:
        return self._res_prefix_template.format(id=self.id, idx=self.index)

    def describe(self) -> str:
        return f"{self.param.path}.{self.param.name} [NV2 {self.id}/{self.index} {self.codec.name}]"

    def codec_of(self, param: "Parameter") -> Codec | None:
        return self.codec if param is self.param else None

    def _judge_header(self, resp: str | None) -> ParamParseErrType:
        return judge_header(resp, self.SVC_CODE, self.id, self.index)


class Nv2ReadSpec(_Nv2Spec):
    SVC_CODE = SVC_READ

    def build_request(self, values=None) -> str:
        return self._req_template.format(id=self.id, idx=self.index)

    def _judge(self, resp: str | None) -> Judgement:
        reason = self._judge_header(resp)
        if reason is not ParamParseErrType.NONE:
            return Judgement(reason)

        # 값 구간 원문만 넘긴다 — 디코드·값·플래그는 기본 클래스가 한다 (형식 불량이면 거기서 DATA_TYPE_ERROR)
        if len(resp) > HEADER_LEN:
            text = resp[HEADER_LEN:]
        elif self.param.data_type is ParamDataType.STR and len(resp) == HEADER_LEN:
            text = ""  # 빈 문자열 값
        else:
            return Judgement(ParamParseErrType.WRONG_PARAM_LENGTH)
        return Judgement(ParamParseErrType.NONE, {self.param: text})


class Nv2WriteSpec(_Nv2Spec):
    SVC_CODE = SVC_WRITE

    def build_request(self, values) -> str | BuildFailure:
        """values[param] 은 도메인 값(숫자 또는 그 문자열)."""
        value = values[self.param]
        if value is None:
            return BuildFailure.VALUE_MISSING
        try:
            text = self.codec.encode(value)
        except (ValueError, TypeError):
            return BuildFailure.BAD_VALUE
        if text is None:
            return BuildFailure.CONTEXT_NOT_READY
        return self.build_request_line(text)

    def build_request_line(self, line_text: str) -> str:
        """이미 선로 문자열인 값으로 요청을 만든다 — 백업 파일(선로 원문 보존)용."""
        return self._req_template.format(id=self.id, idx=self.index, value=line_text)

    def _judge(self, resp: str | None) -> Judgement | None:
        if self.param.acc != ParamAccType.WO:
            return None  # RW 쓰기 응답은 판정하지 않는다 (N009 결정)
        return Judgement(self._judge_header(resp))
