"""완성된 패킷 1건의 규약 (RawPacketSpec) — 복원 창이 백업 파일의 선로 원문(NV2 쓰기 패킷)을 그대로 보낼 때 쓴다
(data-protocol-2, 2026-10-12).

param 이 없다(params=()). 판정은 응답으로만 하고 바꿀 플래그도 없다 — 워커는 Outcome.verdict 로 재시도(TRANSIENT) / 실패 기록
(그 밖)을 정하고, 창은 시퀀스 보고(SequenceReport)의 작업별 Outcome 으로 항목의 성공/실패를 안다.

    RawPacketSpec(request, expected_prefix)   접두 일치 → NONE / 빈 응답 → COMMUNICATION_ERR / 그 밖 → WRONG_PREFIX(재시도)
                                              expected_prefix 가 None 이면 빈 응답만 실패 — 판정 규칙이 없는 패킷
    Nv2RawWriteSpec(packet)                   "p:01[ID 8][INDEX 2][VALUE]" — NV2 헤더 판정(nv2_spec.judge_header)을 그대로 써서
                                              장비 오류 코드(p:78…)는 REJECTED/NOT_SUPPORT 로 재시도 없이 실패 기록, 잡음만 재시도
    raw_write_spec_of(packet)                 패킷 접두로 spec 을 고른다 — NV2 쓰기 패킷이면 Nv2RawWriteSpec; "p:01" 인데 INDEX 가
                                              16진수가 아닌(손상된) 패킷은 접두 비교만 하는 RawPacketSpec; 그 밖은 RawPacketSpec(None)

백업 파일의 행 형식(헤더·"<path>.<name>, <패킷>")은 f_helper/backup_file_helper 가 맡고, 패킷의 응답 판정은 여기가 맡는다 —
expected_write_response_prefix 는 이 모듈로 흡수된다.
"""

from __future__ import annotations

from b_core.b_datatype.general_enum import ParamParseErrType
from b_core.g_protocol import nv2_spec
from b_core.g_protocol.packet_spec import Judgement, PacketSpec


class RawPacketSpec(PacketSpec):

    def __init__(self, request: str, expected_prefix: str | None):
        super().__init__(())
        self.request = request
        self._expected_prefix = expected_prefix

    @property
    def expected_response_prefix(self) -> str:
        return self._expected_prefix or ""

    def describe(self) -> str:
        return f"raw {self.request}"

    def build_request(self, values=None) -> str:
        return self.request

    def _judge(self, resp: str | None) -> Judgement:
        if not resp:
            return Judgement(ParamParseErrType.COMMUNICATION_ERR)
        if self._expected_prefix is None or resp.startswith(self._expected_prefix):
            return Judgement(ParamParseErrType.NONE)
        return Judgement(ParamParseErrType.WRONG_PREFIX)


class Nv2RawWriteSpec(RawPacketSpec):
    """NV2 쓰기 패킷 "p:01" + ID(8) + INDEX(2) + VALUE. 응답은 _Nv2Spec 과 같은 헤더 판정 — 오류 코드는 사유로 매핑된다."""

    def __init__(self, packet: str):
        self.id = packet[4:12]
        self.index = int(packet[12:14], 16)
        prefix = f"{nv2_spec.PREFIX}00{nv2_spec.SVC_WRITE}{self.id}{self.index:02X}"
        super().__init__(packet, prefix)

    def describe(self) -> str:
        return f"raw NV2 write {self.id}/{self.index}"

    def _judge(self, resp: str | None) -> Judgement:
        return Judgement(nv2_spec.judge_header(resp, nv2_spec.SVC_WRITE, self.id, self.index))


def raw_write_spec_of(packet: str) -> RawPacketSpec:
    """패킷 원문으로 쓰기 spec 을 고른다. NV2 쓰기 패킷(p:01 + ID 8 + INDEX 2, INDEX 는 16진수)이면 Nv2RawWriteSpec.
    INDEX 자리가 16진수가 아닌 "p:01" 패킷(손상된 행)은 오류 코드를 해석할 수 없으므로 접두 비교("p:0001" + ID + INDEX 원문)만 한다 —
    장비 응답이 어떤 것이든 접두가 다르면 WRONG_PREFIX 로 재시도 뒤 실패 (구 expected_write_response_prefix 와 같은 판정)."""
    if packet.startswith(nv2_spec.PREFIX + nv2_spec.SVC_WRITE) and len(packet) >= 14:
        try:
            int(packet[12:14], 16)
        except ValueError:
            return RawPacketSpec(packet, f"{nv2_spec.PREFIX}00{nv2_spec.SVC_WRITE}{packet[4:14]}")
        return Nv2RawWriteSpec(packet)
    return RawPacketSpec(packet, None)
