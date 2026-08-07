import os
import time
import serial
from enum import Enum, auto
from PySide6.QtCore import QThread, Signal
import ftd2xx as ftd
#from ftd2xx.defines import Status


AUTOBAUD_CHAR   = 0x41          # 'A' : 부트ROM/커널 오토보 감지용 문자
SCI8_KEY        = (0xAA, 0x08)  # SCI 8bit 부트 스트림 키값(0x08AA, LSB 우선)
RW_TIMEOUT_S    = 10.0          # 바이트 송수신 타임아웃 (C++ 원본: 10000ms)

FW_KERNEL_DN_BAUDRATE = 38400
FW_KERNEL_BAUDRATE    = 115200      

# ---- 단계 간 대기 시간 (C++ startTimer 값과 동일) ----
DELAY_AFTER_KERNEL_S = 3.006    # 커널 다운로드 후 커널 기동 대기
DELAY_STEP_S         = 2.0      # 그 외 단계 간 대기
 
# ---- 플래시 커널 커맨드 (C++ #define 과 동일) ----
DFU_CPU1            = 0x0100
DFU_CPU2            = 0x0200
ERASE_CPU1          = 0x0300
ERASE_CPU2          = 0x0400
VERIFY_CPU1         = 0x0500
VERIFY_CPU2         = 0x0600
RUN_CPU1_BOOT_CPU2  = 0x0004
RESET_CPU1_BOOT_CPU2 = 0x0007
RESET_CPU2          = 0x0020
 
ERASE_SECTOR_MASK   = 0x00003FFF   # eraseCPU()의 sectorMask (14개 섹터)
 
# ---- 상태/에러 코드 ----
NO_ERROR        = 0x1000
STATUS_ERR_STR = {
    0x2000: "ERROR Status: BLANK_ERROR",
    0x3000: "ERROR Status: VERIFY_ERROR",
    0x4000: "ERROR Status: PROGRAM_ERROR",
    0x5000: "ERROR Status: COMMAND_ERROR",
    0x6000: "ERROR Status: UNLOCK_ERROR",
}
FLASH_API_ERR_STR = {
    0x7000: "Flash API Error: Incorrect Data Buffer Length",
    0x8000: "Flash API Error: Incorrect ECC Buffer Length",
    0x9000: "Flash API Error: Data ECC Buffer Length Mismatch",
    0xA000: "Flash API Error: Flash Registers not Writable",
    0xB000: "Flash API Error: Feature not Available",
    0xC000: "Flash API Error: Invalid Address",
    0xD000: "Flash API Error: Invalid CPUID",
    0xE000: "Flash API Error: Failure",
}
 
ACK             = 0x2D
NAK             = 0xA5
STX_WORD        = 0x1BE4        # 패킷 시작 (바이트 순서: E4 1B)
ETX_WORD        = 0xE41B        # 패킷 끝   (바이트 순서: 1B E4)
BLOCK_WORDS     = 0x80          # g_bBlockSize : 128워드마다 중간 체크섬 수신

class FirmwarePhase(Enum):
    SET_EEPROM_IO_PIN = "Set EEPRom(I/O Mode) Pin"
    SET_BOOT_MODE  = "Set Boot Mode"
    CPU1_KERNEL_DN = "CPU1 Kernel Download"
    CPU1_ERASE     = "CPU1 Flash Erase"
    CPU1_APP_DN    = "CPU1 App Download"
    CPU1_VERIFY    = "CPU1 Verify"
    CPU1_RESET     = "CPU1 Reset (Boot CPU2)"
    CPU2_KERNEL_DN = "CPU2 Kernel Download"
    CPU2_ERASE     = "CPU2 Flash Erase"
    CPU2_APP_DN    = "CPU2 App Download"
    CPU2_VERIFY    = "CPU2 Verify"
    CPU2_RESET     = "CPU2 Reset"
    AUTO_REBOOT    = "Auto Reboot"


FT_232R_CBUS_IOMODE = 0x0A

FT_BITMODE_RESET = 0x00
FT_BITMODE_CBUS_BITBANG = 0x20

class FTDHelper:
    """C++ FTDHelper 와 동일한 역할.
 
    ready_port / finish_port 는 (성공여부: bool, 에러메시지: str) 튜플을 반환합니다.
    C++ 원본에서는 errMsg 가 값 전달(QString errMsg)이라 호출자에게 전달되지
    않는 버그가 있었는데, 파이썬에서는 튜플 반환으로 해결했습니다.
    """
 
    # ------------------------------------------------------------------
    # 내부 공통 함수: COM 포트 번호로 장치를 찾아 핸들을 반환
    # ------------------------------------------------------------------
    def _open_by_comport(self, comport: int):
        """comport 번호에 해당하는 FTDI 장치를 열어 핸들 반환.
 
        반환: (handle | None, 에러메시지)
        """
        try:
            num_devs = ftd.createDeviceInfoList()
        except ftd.DeviceError:
            return None, "can not found device"
 
        if num_devs == 0:
            return None, "can not found device"
 
        # C++ 의 FT_GetDeviceInfoList 에 해당 (여기서는 검증 용도)
        #try:
        #    ftd.getDeviceInfoList()
        #except ftd.DeviceError:
        #    return None, "can not search device list"
 
        # COM 포트 번호로 검색 (예: 4 -> COM4)
        for i in range(num_devs):
            try:
                handle = ftd.open(i)
            except ftd.DeviceError:
                continue
 
            try:
                com_port_number = handle.getComPortNumber()
                if com_port_number == comport:
                    return handle, ""  # 찾음 - 핸들을 열어둔 채 반환
            except ftd.DeviceError:
                pass
 
            handle.close()  # 아니면 닫기
 
        return None, "can not found target comport"
 
     # ------------------------------------------------------------------
    # EEPROM CBUS 설정 확인 및 자동 프로그래밍
    # (FT_Prog 에서 C2, C3 를 "IO MODE" 로 수동 설정하던 작업의 자동화)
    # ------------------------------------------------------------------
    def ensure_cbus_iomode(self, comport: int) -> tuple[bool, str, bool]:
        """C2, C3 핀이 EEPROM 에서 IOMODE 로 설정되어 있는지 확인하고,
        아니라면 자동으로 설정한다.
 
        반환: (성공여부, 에러메시지, 재열거필요여부)
            재열거필요여부가 True 이면 EEPROM 을 새로 썼다는 뜻이며,
            설정이 적용되도록 장치가 USB 재열거(cyclePort)된 상태이므로
            수 초 기다린 뒤 ready_port 등을 호출해야 한다.
        """
        handle, err = self._open_by_comport(comport)
        if handle is None:
            return False, err, False
 
        try:
            # 1. 현재 EEPROM 내용 읽기 (모든 필드 보존을 위해 전체 읽기)
            try:
                ee = handle.eeRead()
            except ftd.DeviceError:
                return False, "can not read eeprom", False
 
            # 2. 이미 IOMODE 면 아무것도 안 함
            if ee.Cbus2 == FT_232R_CBUS_IOMODE and ee.Cbus3 == FT_232R_CBUS_IOMODE:
                return True, "", False
 
            # 3. C2, C3 만 IOMODE 로 변경하고 나머지는 읽은 값 그대로 재기록
            ee.Cbus2 = FT_232R_CBUS_IOMODE
            ee.Cbus3 = FT_232R_CBUS_IOMODE
            try:
                handle.eeProgram(ee)
            except ftd.DeviceError:
                return False, "can not program eeprom", False
 
            # 4. 설정 적용을 위해 USB 재열거 (물리적으로 뽑았다 꽂는 것과 동일)
            try:
                handle.cyclePort()
            except ftd.DeviceError:
                # cyclePort 실패 시 사용자가 직접 재연결해야 함
                return True, "eeprom programmed - please replug device", True
 
            return True, "", True
        finally:
            try:
                handle.close()
            except ftd.DeviceError:
                pass  # cyclePort 후에는 핸들이 이미 무효화되었을 수 있음

    # ------------------------------------------------------------------
    # 부트모드 진입 시퀀스
    # c2: reset pin - 0b0100, c3: bootmode pin - 0b1000
    # 시나리오:
    #   c3 __|￣￣￣￣￣￣￣￣￣
    #   c2 ____|￣￣|__________
    # ------------------------------------------------------------------
    def ready_port(self, comport: int) -> tuple[bool, str]:
        handle, err = self._open_by_comport(comport)
        if handle is None:
            return False, err
 
        # (비트마스크, 실패 시 에러메시지) 순서대로 실행
        sequence = [
            (0xF0, "can not C3, C2 LOW"),
            (0xF8, "can not C3 HIGH"),
            (0xFC, "can not C3, C2 HIGH"),
            (0xF8, "can not remain C3 HIGH"),
        ]
        return self._run_sequence(handle, sequence)
 
    # ------------------------------------------------------------------
    # 종료(리셋) 시퀀스
    # 시나리오:
    #   c3 ___________________
    #   c2 ____|￣￣|__________
    # ------------------------------------------------------------------
    def finish_port(self, comport: int) -> tuple[bool, str]:
        handle, err = self._open_by_comport(comport)
        if handle is None:
            return False, err
 
        sequence = [
            (0xF0, "can not C3, C2 LOW"),
            (0xF4, "can not C3, C2 HIGH"),
            (0xF0, "can not remain C3 HIGH"),
        ]
        return self._run_sequence(handle, sequence)
 
    # ------------------------------------------------------------------
    # 공통 시퀀스 실행부
    # ------------------------------------------------------------------
    def _run_sequence(self, handle, sequence) -> tuple[bool, str]:
        try:
            # 먼저 비트뱅 모드 리셋
            try:
                handle.setBitMode(0x00, FT_BITMODE_RESET)
            except ftd.DeviceError:
                return False, "can not C BITBANG reset"
 
            time.sleep(1.0)
 
            for mask, err_msg in sequence:
                try:
                    handle.setBitMode(mask, FT_BITMODE_CBUS_BITBANG)
                except ftd.DeviceError:
                    return False, err_msg
                time.sleep(1.0)
 
            return True, ""
        finally:
            # C++ 원본과 달리 실패 경로에서도 핸들이 반드시 닫히도록 보장
            handle.close()
# ============================================================================
#  SCI8 부트 이미지 파일 로더 (hex2000 -boot -sci8 출력물)
# ============================================================================
def load_boot_image(path: str) -> bytes:
    """
    hex2000 -sci8 출력 파일을 읽어 바이트열로 반환.
      - ASCII 포맷(-a): 공백/개행으로 구분된 16진수 2자리 토큰
      - 바이너리 포맷(-b): 그대로 사용
    파일 선두가 AA 08 (키값 0x08AA) 인지 검증한다.
    """
    with open(path, "rb") as f:
        raw = f.read()
 
    if len(raw) >= 2 and raw[0] == SCI8_KEY[0] and raw[1] == SCI8_KEY[1]:
        data = raw                                   # 바이너리 포맷
    else:
        # ASCII 포맷 파싱 (hex2000 -boot -sci8 -a 출력)
        # 주의: hex2000 ASCII-Hex 출력은 데이터 앞뒤에 STX(0x02)/ETX(0x03)
        #       제어문자가 붙는다. 기존 C++ readHexFile()처럼 16진수 문자
        #       연속열만 추출하고 나머지(제어문자, 공백, 개행)는 건너뛴다.
        text = raw.decode("ascii", errors="strict")
        hexdigits = set("0123456789abcdefABCDEF")
        tokens = []
        run = []
        for ch in text:
            if ch in hexdigits:
                run.append(ch)
            elif run:
                tokens.append("".join(run))
                run = []
        if run:
            tokens.append("".join(run))
 
        # hex2000 출력은 바이트당 2자리 토큰이어야 한다 (파일 손상 검출)
        bad = [t for t in tokens if len(t) != 2]
        if bad:
            raise ValueError(
                f"Non-2-digit hex tokens found (file corrupted?): {bad[:5]}")

        data = bytes(int(t, 16) for t in tokens)

    if len(data) < 2 or data[0] != SCI8_KEY[0] or data[1] != SCI8_KEY[1]:
        raise ValueError(f"Boot stream key value (AA 08) missing: {os.path.basename(path)}")
    return data

class FirmwareWriterWorker(QThread):
    sig_log      = Signal(str)          # 로그 문자열
    sig_phase    = Signal(FirmwarePhase)          # 현재 단계 이름
    sig_progress = Signal(FirmwarePhase, int, int)     # (진행 바이트, 전체 바이트)
    sig_finished = Signal(bool, str)    # (성공 여부, 결과 메시지)
 
    def __init__(self, is_rs232_type: bool, port_name: str,
                 kernel_cpu1: str, kernel_cpu2: str,
                 flash_cpu1: str, flash_cpu2: str, parent=None):
        super().__init__(parent)
        self.ftd_helper = FTDHelper()
        self._is_rs232_type = is_rs232_type
        self._port_name  = port_name
        self._files = {
            "kernel_cpu1": kernel_cpu1,
            "kernel_cpu2": kernel_cpu2,
            "flash_cpu1":  flash_cpu1,
            "flash_cpu2":  flash_cpu2,
        }
        self._abort = False
        self._ser: serial.Serial | None = None
        self._current_phase = FirmwarePhase.CPU1_KERNEL_DN
 
    def request_abort(self):
        self._abort = True
 
    # ------------------------------------------------------------------ run
    def run(self):
        try:
            # 파일 로드/검증 (hex ASCII → bytes)
            img = {}
            for key, path in self._files.items():
                img[key] = load_boot_image(path)
                self.sig_log.emit(f"[File] {key} :{len(img[key])} bytes")

            if self._is_rs232_type == False:
                self.step(FirmwarePhase.SET_EEPROM_IO_PIN)
                if self._ensure_cbus_iomode():
                    self._sleep(DELAY_STEP_S * 3)
                
                self.step(FirmwarePhase.SET_BOOT_MODE)
                self._set_boot_mode()
                self._sleep(DELAY_STEP_S)

 
            # 시리얼 연결 (C++: connectSerial, Baud19200 하드코딩)
            self._ser = serial.Serial(
                port=self._port_name,
                baudrate=FW_KERNEL_DN_BAUDRATE, #38400 
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                timeout=RW_TIMEOUT_S,
                write_timeout=RW_TIMEOUT_S,
            )
            self._ser.reset_input_buffer()
            self._ser.reset_output_buffer()
            self.sig_log.emit(f"[Kernel 1 Download Port] {self._port_name} @ {FW_KERNEL_DN_BAUDRATE}bps 열림")
 
            # ---------------- CPU1 ----------------
            self.step(FirmwarePhase.CPU1_KERNEL_DN)
            self._download_kernel(img["kernel_cpu1"])
            self._sleep(DELAY_AFTER_KERNEL_S)

            self._ser.close()
            self._ser = serial.Serial(
                port=self._port_name,
                baudrate=FW_KERNEL_BAUDRATE, #38400 
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                timeout=RW_TIMEOUT_S,
                write_timeout=RW_TIMEOUT_S,
            )
            self._ser.reset_input_buffer()
            self._ser.reset_output_buffer()

            self.sig_log.emit(f"[Kernel 1 Port] {self._port_name} @ {FW_KERNEL_BAUDRATE}bps 열림")
 
            self.step(FirmwarePhase.CPU1_ERASE)
            self._erase_cpu(ERASE_CPU1)
            self._sleep(DELAY_STEP_S)
 
            self.step(FirmwarePhase.CPU1_APP_DN)
            self._download_app(DFU_CPU1, img["flash_cpu1"])
            self._sleep(DELAY_STEP_S)
 
            self.step(FirmwarePhase.CPU1_VERIFY)
            self._download_app(VERIFY_CPU1, img["flash_cpu1"])
            self._sleep(DELAY_STEP_S)
 
            self.step(FirmwarePhase.CPU1_RESET)
            self._reset_cpu(RESET_CPU1_BOOT_CPU2)
            self._sleep(DELAY_STEP_S)
 
            # ---------------- CPU2 ----------------

            self._ser.close()
            self._ser = serial.Serial(
                port=self._port_name,
                baudrate=FW_KERNEL_DN_BAUDRATE, #38400 
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                timeout=RW_TIMEOUT_S,
                write_timeout=RW_TIMEOUT_S,
            )
            self._ser.reset_input_buffer()
            self._ser.reset_output_buffer()

            self.sig_log.emit(f"[Kernel 2 Download Port] {self._port_name} @ {FW_KERNEL_DN_BAUDRATE}bps 열림")

            self.step(FirmwarePhase.CPU2_KERNEL_DN)
            self._download_kernel(img["kernel_cpu2"])
            self._sleep(DELAY_AFTER_KERNEL_S)

            self._ser.close()
            self._ser = serial.Serial(
                port=self._port_name,
                baudrate=FW_KERNEL_BAUDRATE, #38400 
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                timeout=RW_TIMEOUT_S,
                write_timeout=RW_TIMEOUT_S,
            )
            self._ser.reset_input_buffer()
            self._ser.reset_output_buffer()

            self.sig_log.emit(f"[Kernel 2 Port] {self._port_name} @ {FW_KERNEL_BAUDRATE}bps 열림")
 
            self.step(FirmwarePhase.CPU2_ERASE)
            self._erase_cpu(ERASE_CPU2)
            self._sleep(DELAY_STEP_S)
 
            self.step(FirmwarePhase.CPU2_APP_DN)
            self._download_app(DFU_CPU2, img["flash_cpu2"])
            self._sleep(DELAY_STEP_S)
 
            self.step(FirmwarePhase.CPU2_VERIFY)
            self._download_app(VERIFY_CPU2, img["flash_cpu2"])
            self._sleep(DELAY_STEP_S)
 
            self.step(FirmwarePhase.CPU2_RESET)
            self._reset_cpu(RESET_CPU2)
 
            self._ser.close()

            if self._is_rs232_type == False:
                self.step(FirmwarePhase.AUTO_REBOOT)
                self._auto_reboot()
                self._sleep(DELAY_STEP_S)

            self.sig_finished.emit(True, "Firmware Update is Completed.")
 
        except Exception as e:
            if self._ser and self._ser.is_open:
                self._ser.close()
            self.sig_finished.emit(False, str(e))
 
    # ------------------------------------------------------------ 공용 유틸
    def step(self, phase: FirmwarePhase):
        if self._abort:
            raise RuntimeError("Aborted by user.")
        self._current_phase = phase
        self.sig_phase.emit(phase)
        self.sig_log.emit(f"[Step] {phase.value}")
 
    def _sleep(self, sec: float):
        # C++ startTimer() 의 단계 간 대기에 해당. 중단 요청 반응성 확보를 위해 분할 대기.
        end = time.monotonic() + sec
        while time.monotonic() < end:
            if self._abort:
                raise RuntimeError("Aborted by user.")
            time.sleep(0.05)
 
    def _write(self, data: bytes):
        self._ser.write(data)
 
    def _read1(self) -> int:
        """1바이트 수신 (타임아웃 시 예외). C++ pValve->read(1, 10000) 대응."""
        rx = self._ser.read(1)
        if len(rx) != 1:
            raise RuntimeError("Receive timeout (no response from device)")
        return rx[0]
 
    def _read_byte_with_ack(self) -> int:
        """C++ readByteFromValve : 1바이트 수신 후 ACK(0x2D) 회신."""
        b = self._read1()
        self._write(bytes([ACK]))
        return b
 
    def _set_boot_mode(self):
        port_num:int = int(self._port_name.replace("COM", ""))
        result, msg = self.ftd_helper.ready_port(port_num)        

        if result:
            self.sig_log.emit(f"[Change BootMode] Success : COM{port_num}")
        else:
            raise RuntimeError(f"[Change BootMode] Failed: COM{port_num} : {msg}")

    def _ensure_cbus_iomode(self) -> bool:
        port_num:int = int(self._port_name.replace("COM", ""))
        result, msg, need_recycle = self.ftd_helper.ensure_cbus_iomode(port_num)

        if result:
            if need_recycle:
                self.sig_log.emit(f"[Change EEPRom I/O pin] Success : COM{port_num}")
            else:
                self.sig_log.emit(f"[Change EEPRom I/O pin] Already changed : COM{port_num}")
            return need_recycle
        else:
            raise RuntimeError(f"[Change EEPRom I/O pin] Failed: COM{port_num} : {msg}")

    def _auto_reboot(self):
        port_num:int = int(self._port_name.replace("COM", ""))
        result, msg = self.ftd_helper.finish_port(port_num)        

        if result:
            self.sig_log.emit(f"[Auto Reboot] Success : COM{port_num}")
        else:
            raise RuntimeError(f"[Auto Reboot] Failed: COM{port_num} : {msg}")

    # ------------------------------------------------------------ 오토보
    def _autobaud_lock(self):
        """C++ autoBaudLock : 'A' 1회 송신 → 동일 문자 에코 확인 (10초 대기).
 
        전송 전에 입출력 버퍼를 비운다. 직전 단계의 DSP 리셋(RESET_CPU1_
        BOOT_CPU2 등) 과정에서 SCI 핀 재구성으로 인한 라인 글리치나,
        호스트가 읽지 않은 잔류 바이트가 수신 버퍼에 남아 있으면 'A' 에코
        판정을 오염시키기 때문. 오토보 시점에는 상대측이 'A'를 받기 전까지
        아무것도 송신하지 않으므로 이 클리어는 프로토콜에 영향이 없다.
        """
        self._ser.reset_input_buffer()
        self._ser.reset_output_buffer()
        self._write(bytes([AUTOBAUD_CHAR]))
        rx = self._read1()
        if rx != AUTOBAUD_CHAR:
            raise RuntimeError(f"Autobaud failed: Received 0x{rx:02X} (Expected 0x41)")
        self.sig_log.emit("[Autobaud] Success")
 
    # ---------------------------------------------------- 커널 다운로드
    def _download_kernel(self, data: bytes):
        """C++ downloadKernel = autoBaudLock + loadProgram(바이트 에코 검증)."""
        self._autobaud_lock()
 
        total = len(data)
        self.sig_progress.emit(self._current_phase, 0, total)
        for idx, b in enumerate(data):
            if self._abort:
                raise RuntimeError("Aborted by user.")
            self._write(bytes([b]))
            echo = self._read1()
            if echo != b:
                raise RuntimeError(
                    f"Kernel echo mismatch @ {idx}/{total} : "
                    f"Sent 0x{b:02X} / Received 0x{echo:02X}")
            if idx % 32 == 0 or idx == total - 1:
                self.sig_progress.emit(self._current_phase,idx + 1, total)
 
        self._ser.reset_input_buffer()   # C++ clearReadBuffer()
 
    # ------------------------------------------------------- 패킷 송수신
    @staticmethod
    def _construct_packet(cmd: int, data: bytes = b"") -> bytes:
        """C++ constructPacket 과 동일한 프레이밍."""
        pkt = bytearray([0xE4, 0x1B])                      # STX
        pkt += len(data).to_bytes(2, "little")             # length
        pkt += cmd.to_bytes(2, "little")                   # command
        pkt += data                                        # data
        csum = ((cmd & 0xFF) + ((cmd >> 8) & 0xFF) + sum(data)) & 0xFFFF
        pkt += csum.to_bytes(2, "little")                  # checksum (cmd+data)
        pkt += bytes([0x1B, 0xE4])                         # ETX
        return bytes(pkt)
 
    def _send_packet(self, cmd: int, data: bytes = b""):
        """C++ sendPacket : 패킷 송신 후 ACK(0x2D) 1바이트 확인."""
        self._write(self._construct_packet(cmd, data))
        rx = self._read1()
        if rx != ACK:
            raise RuntimeError(f"Command 0x{cmd:04X} : ACK error (Received 0x{rx:02X})")

    def _get_word(self, checksum: int) -> tuple[int, int]:
        """C++ getWord : LSB,MSB 순 2바이트 수신(각 바이트마다 ACK 회신).
        반환 (word, 갱신된 checksum)."""
        lsb = self._read_byte_with_ack()
        checksum = (checksum + lsb) & 0xFFFF
        msb = self._read_byte_with_ack()
        checksum = (checksum + msb) & 0xFFFF
        return ((msb << 8) | lsb), checksum

    def _get_packet(self, expect_cmd: int) -> list[int]:
        """C++ getPacket / getPacketEx : 커널 상태 패킷 수신.
        데이터 워드 리스트를 반환한다."""
        self._ser.reset_input_buffer()                    # C++ clearReadBuffer()

        word, _ = self._get_word(0)
        if word != STX_WORD:
            raise RuntimeError(f"Status packet STX error (Received 0x{word:04X})")

        length, _ = self._get_word(0)

        data_csum = 0
        cmd, data_csum = self._get_word(data_csum)

        words = []
        for _ in range(length // 2):
            w, data_csum = self._get_word(data_csum)
            words.append(w)

        rcv_csum, _ = self._get_word(0)
        if rcv_csum != data_csum:
            raise RuntimeError(
                f"Status packet checksum error (Calculated 0x{data_csum:04X} / Received 0x{rcv_csum:04X})")

        word, _ = self._get_word(0)
        if word != ETX_WORD:
            raise RuntimeError(f"Status packet ETX error (Received 0x{word:04X})")

        self._write(bytes([ACK]))                          # 최종 ACK

        if cmd != expect_cmd:
            raise RuntimeError(
                f"Status packet command mismatch (Expected 0x{expect_cmd:04X} / Received 0x{cmd:04X})")
        return words

    # ----------------------------------------------------------- 소거
    def _erase_cpu(self, cmd: int):
        """C++ eraseCPU : 오토보 → ERASE 패킷(sectorMask 4바이트 LE) → 상태 패킷."""
        self._autobaud_lock()
        self._send_packet(cmd, ERASE_SECTOR_MASK.to_bytes(4, "little"))
        self._get_packet(cmd)
        self.sig_log.emit(f"[Erase] Command 0x{cmd:04X} completed")

    # ----------------------------------------------------------- 리셋
    def _reset_cpu(self, cmd: int):
        """C++ resetCPU : RESET 패킷 송신 + ACK 확인."""
        self._send_packet(cmd)
        self.sig_log.emit(f"[Reset] Command 0x{cmd:04X} sent")

    # ------------------------------------------- 앱 다운로드 / 검증 (DFU)
    def _download_app(self, cmd: int, data: bytes):
        """C++ downloadApp : DFU/VERIFY 패킷 → downloadImage → 상태 패킷 판정."""
        self._send_packet(cmd)
        self._download_image(data)
        status = self._get_packet(cmd)

        if not status or status[0] != NO_ERROR:
            s0 = status[0] if len(status) > 0 else 0
            s3 = status[3] if len(status) > 3 else 0
            err  = STATUS_ERR_STR.get(s0, "ERROR Status: Not Recognized Error")
            err2 = FLASH_API_ERR_STR.get(s3, "Error not recognized")
            raise RuntimeError(f"Command 0x{cmd:04X} failed\n{err}\n{err2}")

        self._ser.reset_input_buffer()

    def _download_image(self, data: bytes):
        """C++ downloadImage : SCI8 이미지를 블록 단위로 전송하며
        커널이 회신하는 러닝 체크섬(2바이트)을 검증한다. (에코 없음)
 
        커널과의 핸드셰이크는 체크섬 회신 시점에만 존재하므로, 체크섬
        지점 사이의 바이트들은 한 번에 write 해도 와이어 상 동일하다.
        (C++는 1바이트씩 write했지만 UART 상 연속 스트림으로 동일)
        """
        total = len(data)
        pos = 0
        checksum = 0

        def send_range(nbytes: int):
            """pos부터 nbytes 바이트를 일괄 전송하고 체크섬/진행률 갱신."""
            nonlocal pos, checksum
            if pos + nbytes > total:
                raise RuntimeError("Image file is shorter than expected (format error)")
            chunk = data[pos : pos + nbytes]
            self._write(chunk)
            checksum = (checksum + sum(chunk)) & 0xFFFF
            pos += nbytes
            self.sig_progress.emit(self._current_phase, pos, total)

        def recv_and_check_checksum():
            lsb = self._read_byte_with_ack()
            msb = self._read_byte_with_ack()
            rcv = ((msb << 8) | lsb) & 0xFFFF
            if rcv != checksum:
                raise RuntimeError(
                    f"Image checksum error @ {pos}/{total} "
                    f"(Calculated 0x{checksum:04X} / Received 0x{rcv:04X})")

        self.sig_progress.emit(self._current_phase, 0, total)

        # 선두 22바이트 : 키값(2) + 예약(16) + 엔트리주소(4)
        send_range(22)
        recv_and_check_checksum()          # 커널이 즉시 체크섬 회신
 
        # 블록 반복 : [blockSize(2)] [destAddr(4)] [data words ...]
        while pos < total:
            if self._abort:
                raise RuntimeError("Aborted by user.")
 
            bs_lsb = data[pos]
            bs_msb = data[pos + 1]
            block_size = ((bs_msb << 8) | bs_lsb) & 0xFFFF
 
            if block_size == 0x0000:       # 종단 블록
                send_range(2)
                self.sig_progress.emit(self._current_phase, total, total)
                break
 
            # 블록사이즈(2) + 주소(4) + 첫 구간(최대 128워드)을 일괄 전송
            first_words = min(block_size, BLOCK_WORDS)
            send_range(2 + 4 + first_words * 2)
 
            # 이후 128워드 구간마다 : 체크섬 수신 → 다음 구간 전송
            sent_words = first_words
            while sent_words < block_size:
                if self._abort:
                    raise RuntimeError("사용자에 의해 중단되었습니다.")
                recv_and_check_checksum()  # 128워드마다 중간 체크섬 (C++ 동일)
                run_words = min(block_size - sent_words, BLOCK_WORDS)
                send_range(run_words * 2)
                sent_words += run_words

            # 블록 종료 체크섬
            recv_and_check_checksum()