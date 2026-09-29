"""시리얼 연결 설정 — connections.json 코드 → pyserial 값 변환의 단일 출처 (F014/F018/F025).

connections.json 항목의 코드는 그대로 둔다 (Qt QSerialPort 열거값과 같은 번호):
    parity      0 NONE, 2 EVEN, 3 ODD, 4 SPACE, 5 MARK
    stopBits    1 ONE, 2 TWO, 3 ONE_POINT_FIVE
    termination 0 CR+LF, 1 LF, 2 CR
표에 없는 코드는 ValueError — 조용한 폴백은 두지 않는다 (2026-09-29 결정). 이 파일은 편집
UI 없이 손으로 고치는 것이라 오타가 바로 드러나야 한다. (이전에는 같은 표가 세 곳에 복사돼
있었고 open()/probe 는 NONE, 스캔은 EVEN 으로 제각각 폴백했다)

probe_once(): ServicePort 를 거치지 않는 임시 raw 포트 1왕복 — 재부팅 대기 probe 와 COM
포트 스캔이 공유한다. 프로토콜은 모른다: 패킷 문자열에 종료문자를 붙여 보내고, 종료문자까지
읽은 바이트를 그대로 돌려준다 (판정은 호출측).
"""

from typing import NamedTuple

import serial

_PARITY = {0: serial.PARITY_NONE, 2: serial.PARITY_EVEN, 3: serial.PARITY_ODD,
           4: serial.PARITY_SPACE, 5: serial.PARITY_MARK}
_STOP_BITS = {1: serial.STOPBITS_ONE, 2: serial.STOPBITS_TWO, 3: serial.STOPBITS_ONE_POINT_FIVE}
_TERMINATION = {0: (b"\r\n", "CR+LF"), 1: (b"\n", "LF"), 2: (b"\r", "CR")}
_DATA_BITS = (5, 6, 7, 8)

PROBE_MAX_BYTES = 256  # 종료문자 없이 계속 바이트를 뿜는 장치가 물려 있어도 read_until 이 끝나게


def _int_field(connection: dict, key: str) -> int:
    """connections.json 의 정수 필드 — 없거나 정수가 아니면(실수·문자열·bool·null) 키 이름을 담아 ValueError.
    int() 로 바꾸지 않는다 — 1.5 가 1 로 조용히 잘리는 것도 폴백이다."""
    if key not in connection:
        raise ValueError(f"{key}: missing")
    value = connection[key]
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{key}: {value!r} is not an integer")
    return value


class SerialSetting(NamedTuple):
    port_name: str
    baudrate: int
    data_bits: int
    parity: int        # 0 NONE, 2 EVEN, 3 ODD, 4 SPACE, 5 MARK
    stop_bits: int     # 1, 2, 3(=1.5)
    termination: int   # 0 CR+LF, 1 LF, 2 CR

    @classmethod
    def from_connection(cls, port_name: str, connection: dict) -> "SerialSetting":
        """connections.json 항목(dict) → 설정. 키가 없거나 정수가 아니거나 코드가 표에 없으면 ValueError
        (메시지에 키 이름·값이 들어간다 — 손으로 고친 파일의 어느 칸이 틀렸는지 알 수 있게)."""
        setting = cls(port_name, _int_field(connection, "baudrate"), _int_field(connection, "dataBits"),
                      _int_field(connection, "parity"), _int_field(connection, "stopBits"),
                      _int_field(connection, "termination"))
        setting.validate()
        return setting

    def validate(self) -> None:
        """코드가 표에 없으면 ValueError (조용한 폴백 없음)."""
        if self.baudrate <= 0:
            raise ValueError(f"unsupported baudrate {self.baudrate}")  # pyserial 은 음수를 ValueError 로 낸다
        if self.data_bits not in _DATA_BITS:
            raise ValueError(f"unsupported dataBits {self.data_bits} (5-8)")
        if self.parity not in _PARITY:
            raise ValueError(f"unsupported parity code {self.parity} (0/2/3/4/5)")
        if self.stop_bits not in _STOP_BITS:
            raise ValueError(f"unsupported stopBits code {self.stop_bits} (1/2/3)")
        if self.termination not in _TERMINATION:
            raise ValueError(f"unsupported termination code {self.termination} (0/1/2)")

    def pyserial_kwargs(self, timeout: float) -> dict:
        """serial.Serial(**kwargs) 인자. 읽기/쓰기 타임아웃은 같은 값."""
        self.validate()
        return dict(port=self.port_name, baudrate=self.baudrate, bytesize=self.data_bits,
                    parity=_PARITY[self.parity], stopbits=_STOP_BITS[self.stop_bits],
                    timeout=timeout, write_timeout=timeout)

    @property
    def term_bytes(self) -> bytes:
        return _TERMINATION[self.termination][0]

    def describe(self) -> str:
        """상태바 연결 정보 문자열 — 'COM3-38400-7-E-1-CR+LF' (parity 는 pyserial 문자, 정지 비트는 1/2/1.5)."""
        return (f"{self.port_name}-{self.baudrate}-{self.data_bits}-{_PARITY[self.parity]}-"
                f"{_STOP_BITS[self.stop_bits]}-{_TERMINATION[self.termination][1]}")


def probe_once(setting: SerialSetting, packet: str, timeout: float = 0.5) -> bytes:
    """임시 raw 포트로 1왕복: 열기 → 입력 버퍼 비우기 → packet+종료문자 전송 → 종료문자까지 읽기 → 닫기.

    응답이 없으면 b"" (읽기 타임아웃). 포트를 열 수 없거나 쓰기 타임아웃이면 serial.SerialException 이
    그대로 전파된다 — 스캔은 '실패 포트', 재부팅 probe 는 '아직 재부팅 중' 으로 해석한다."""
    term = setting.term_bytes
    with serial.Serial(**setting.pyserial_kwargs(timeout)) as ser:
        ser.reset_input_buffer()
        ser.write(packet.encode("utf-8") + term)
        ser.flush()
        return ser.read_until(term, size=PROBE_MAX_BYTES)
