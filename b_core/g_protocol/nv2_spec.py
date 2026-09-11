"""NV2 프로토콜 규약 (Nv2ReadSpec / Nv2WriteSpec).

프레임 (ver1 부터 동일):
    요청  p:[서비스 2][ID 8][INDEX 2][VALUE n]        읽기 0B 는 VALUE 없음
    응답  p:[오류 2][서비스 2][ID 8][INDEX 2][VALUE n]  오류 "00" 이 정상
요청/응답 접두 템플릿은 nv2_spec.json 이 주고, 응답의 자리(오류/서비스/ID/INDEX
= 16자 헤더)는 NV2 고정 규격이라 여기 상수로 둔다.

기존 Parameter.check_error / set_read_response_packet / set_write_response_packet
의 로직을 그대로 옮겼다 (1단계 = 동작 변화 없음). 값의 형 변환은 Parameter 의
영역이 아니라 spec 에 붙은 codec 의 영역이다 (3단계: 선로 문자열 ↔ 도메인 값).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from b_core.b_datatype.general_enum import ParamAccType, ParamDataType, ParamParseErrType
from b_core.g_protocol.codec import Codec
from b_core.g_protocol.packet_spec import PacketSpec

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

# 이 오류 코드들은 "장비에 그 param 이 없다" 는 뜻 — is_err 대신 is_not_support
NOT_SUPPORT_CODES = frozenset({"6E", "73", "7B", "7E", "89"})


class _Nv2Spec(PacketSpec):
    """NV2 spec 공통 — param 1개 = 패킷 1개. 응답 헤더 검증을 공유한다."""

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

    def _check_response(self, resp: str | None, is_read: bool) -> tuple[ParamParseErrType, bool]:
        """기존 Parameter.check_error 와 동일한 판정 순서/결과."""
        param = self.param

        # 쓰기 응답은 WO param 만 검증한다 (기존 동작 유지)
        if not is_read and param.acc != ParamAccType.WO:
            return ParamParseErrType.NONE, False

        if not resp:
            param.is_err = True
            return ParamParseErrType.COMMUNICATION_ERR, True

        if len(resp) < 4:
            param.is_err = True
            return ParamParseErrType.WRONG_FORMAT, True

        if resp[0:2] != PREFIX:
            param.is_err = True
            return ParamParseErrType.WRONG_PREFIX, True

        err_code = resp[2:4]

        if err_code == "00":
            if len(resp) < HEADER_LEN:
                param.is_err = True
                return ParamParseErrType.WRONG_PARAM_LENGTH, True

            if resp[4:6] != self.SVC_CODE:
                param.is_err = True
                return ParamParseErrType.WRONG_SVC_CODE, True

            if resp[6:14] == self.id and int(resp[14:16], 16) == self.index:
                param.is_err = False
                param.is_not_support = False
                return ParamParseErrType.NONE, False

            param.is_err = True
            return ParamParseErrType.WRONG_ID_OR_INDEX, True

        mapped = ERR_CODE_MAP.get(err_code)
        if mapped is None:
            param.is_err = True  # 알 수 없는 오류 코드
            return ParamParseErrType.UNKNOWN_ERROR_CODE, True

        if err_code in NOT_SUPPORT_CODES:
            param.is_not_support = True
        else:
            param.is_err = True
        return mapped, False


class Nv2ReadSpec(_Nv2Spec):
    SVC_CODE = SVC_READ

    def build_request(self, values=None) -> str:
        return self._req_template.format(id=self.id, idx=self.index)

    def apply_response(self, resp: str | None) -> tuple[ParamParseErrType, bool]:
        err, need_retry = self._check_response(resp, is_read=True)
        if err != ParamParseErrType.NONE:
            return err, need_retry

        # 값 반영: 선로 원문은 str_value 에, codec 이 푼 도메인 값은 value 에.
        # [기존 동작 유지] str_value 는 변환 전에 대입되므로 형식 불량이어도 그 문자열이 남는다
        if len(resp) > HEADER_LEN:
            text = resp[HEADER_LEN:]
        elif self.param.data_type is ParamDataType.STR and len(resp) == HEADER_LEN:
            text = ""  # 빈 문자열 값
        else:
            return ParamParseErrType.WRONG_PARAM_LENGTH, True

        self.param.str_value = text
        try:
            value = self.codec.decode(text)
        except ValueError:
            return ParamParseErrType.DATA_TYPE_ERROR, True

        # 문맥 미준비(None)도 값으로 반영한다 — 화면은 Unknown. 재디코드는 하지 않고 다음 읽기가 갱신
        self.param.value = value
        return ParamParseErrType.NONE, False


class Nv2WriteSpec(_Nv2Spec):
    SVC_CODE = SVC_WRITE

    def build_request(self, values) -> str | None:
        """values[param] 은 도메인 값(숫자 또는 그 문자열). codec 문맥 미준비면 None —
        워커는 그 작업을 건너뛰고 로그를 남긴다."""
        try:
            text = self.codec.encode(values[self.param])
        except (ValueError, TypeError):
            return None
        if text is None:
            return None
        return self.build_request_line(text)

    def build_request_line(self, line_text: str) -> str:
        """이미 선로 문자열인 값으로 요청을 만든다 — 백업 파일(선로 원문 보존)용."""
        return self._req_template.format(id=self.id, idx=self.index, value=line_text)

    def apply_response(self, resp: str | None) -> tuple[ParamParseErrType, bool]:
        return self._check_response(resp, is_read=False)
