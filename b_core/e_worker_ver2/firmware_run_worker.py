"""펌웨어 업데이트 워커 (기존 _firmware_write_worker.py = ver1 FirmwareWriterWorker 대응).

ver1 에서 달라진 점:
- QThread 직상속 단일 워커를 [FirmwareRunWorker(QObject) + 작업별 QThread] 로
  재구성 — CompoundRunWorker / ComportScanRunWorker 와 같은 외부 인터페이스
  (start_* / abort / cleanup, aboutToQuit·destroyed 정리). 윈도우는 래퍼의
  시그널에만 연결한다.
- FTP 작업(버전 목록 조회, 펌웨어 다운로드)을 워커 스레드로 옮겼다. ver1 은
  UI 스레드에서 블로킹 호출해 최대 10초 타임아웃 동안 GUI 가 멈췄고, 다운로드
  중에는 창이 응답하지 않았다. 다운로드는 쓰기 시퀀스의 첫 단계(DOWNLOAD)다.
- 로그: 스레드가 sig_log 로 넘기고 래퍼가 AppLogManager 에 기록한다
  (log_source 에 담당 윈도우 이름을 넘기면 그 창의 LogView 에 보인다).
  ver1 의 [Progress] n% 로그(바이트마다 발생)는 제거 — 진행률은 시그널로만.
- ftd2xx(FTDI D2XX) 임포트 실패(DLL 미배포 등)가 앱 기동을 막지 않도록 지연
  처리한다. USB 어댑터 단계에서 명확한 오류 메시지로 실패한다.
- 시리얼 포트 재오픈 코드 4벌 복붙 -> _open_serial(baudrate) 하나.
- 중단 요청 시 한 곳에서 같은 메시지로 실패한다 (ver1 은 영/한 메시지 혼재,
  창이 request_abort 를 호출하지도 않았다). 블로킹 read 타임아웃(10초) 안에
  반드시 중단된다.
- 이미지 파일 길이 검사 보강 (블록 헤더가 잘린 파일에서 IndexError 대신
  형식 오류 메시지).

프로토콜(부트ROM 오토보, SCI8 커널 다운로드, 플래시 커널 패킷, DFU 이미지
스트림)은 ver1 과 바이트 단위로 동일하다 — 원본 C++ ValveFirmwareUpgradeWorker
와 같은 시퀀스:
    [FTP 다운로드] -> 파일 로드 -> (USB: EEPROM I/O 핀, 부트모드 진입)
    -> CPU1: 커널 -> 소거 -> DFU -> 검증 -> 리셋(CPU2 부트)
    -> CPU2: 커널 -> 소거 -> DFU 검증 -> 리셋 -> (USB: 자동 리부트)
"""

import os
import re
import time
from enum import Enum, auto
from typing import NamedTuple

import serial
import serial.tools.list_ports
from PySide6.QtCore import QCoreApplication, QObject, QThread, Signal

from b_core.c_manager.app_log_manager import AppLogManager
from b_core.f_helper import firmware_ftp_helper

# FTDI D2XX 는 DLL 이 있어야 임포트된다 — 없으면 USB 어댑터 기능만 실패시킨다
try:
    import ftd2xx as ftd
except (ImportError, OSError):  # ImportError: 패키지 없음, OSError: DLL 로드 실패
    ftd = None


# ============================================================================
#  상수 (C++ #define / ver1 과 동일)
# ============================================================================
AUTOBAUD_CHAR   = 0x41          # 'A' : 부트ROM/커널 오토보 감지용 문자
SCI8_KEY        = (0xAA, 0x08)  # SCI 8bit 부트 스트림 키값(0x08AA, LSB 우선)
RW_TIMEOUT_S    = 10.0          # 바이트 송수신 타임아웃 (C++ 원본: 10000ms)

FW_KERNEL_DN_BAUDRATE = 38400   # 부트ROM 에 커널을 내려보낼 때
FW_KERNEL_BAUDRATE    = 115200  # 커널 기동 후 플래시 커맨드

# ---- 단계 간 대기 시간 (C++ startTimer 값과 동일) ----
DELAY_AFTER_KERNEL_S = 3.006    # 커널 다운로드 후 커널 기동 대기
DELAY_STEP_S         = 2.0      # 그 외 단계 간 대기

# ---- 플래시 커널 커맨드 ----
DFU_CPU1             = 0x0100
DFU_CPU2             = 0x0200
ERASE_CPU1           = 0x0300
ERASE_CPU2           = 0x0400
VERIFY_CPU1          = 0x0500
VERIFY_CPU2          = 0x0600
RUN_CPU1_BOOT_CPU2   = 0x0004
RESET_CPU1_BOOT_CPU2 = 0x0007
RESET_CPU2           = 0x0020

ERASE_SECTOR_MASK    = 0x00003FFF   # eraseCPU() 의 sectorMask (14개 섹터)

# ---- 상태/에러 코드 ----
NO_ERROR = 0x1000
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

ACK         = 0x2D
NAK         = 0xA5
STX_WORD    = 0x1BE4        # 패킷 시작 (바이트 순서: E4 1B)
ETX_WORD    = 0xE41B        # 패킷 끝   (바이트 순서: 1B E4)
BLOCK_WORDS = 0x80          # g_bBlockSize : 128워드마다 중간 체크섬 수신

# ---- FTDI CBUS ----
FT_232R_CBUS_IOMODE     = 0x0A
FT_BITMODE_RESET        = 0x00
FT_BITMODE_CBUS_BITBANG = 0x20

ABORT_MESSAGE = "Aborted by user."


class FirmwarePhase(Enum):
    """쓰기 시퀀스 단계 — 정의 순서 = 실행 순서 (윈도우가 체크리스트 진행
    표시에 이 순서를 그대로 쓴다). RS232 어댑터에서는 SET_EEPROM_IO_PIN /
    SET_BOOT_MODE / AUTO_REBOOT 이 수행되지 않는다 (사용자가 수동 조작)."""
    DOWNLOAD          = "Firmware Download (FTP)"
    LOAD_FILES        = "Load Firmware Files"
    SET_EEPROM_IO_PIN = "Set EEPROM (I/O Mode) Pin"
    SET_BOOT_MODE     = "Set Boot Mode"
    CPU1_KERNEL_DN    = "CPU1 Kernel Download"
    CPU1_ERASE        = "CPU1 Flash Erase"
    CPU1_APP_DN       = "CPU1 App Download"
    CPU1_VERIFY       = "CPU1 Verify"
    CPU1_RESET        = "CPU1 Reset (Boot CPU2)"
    CPU2_KERNEL_DN    = "CPU2 Kernel Download"
    CPU2_ERASE        = "CPU2 Flash Erase"
    CPU2_APP_DN       = "CPU2 App Download"
    CPU2_VERIFY       = "CPU2 Verify"
    CPU2_RESET        = "CPU2 Reset"
    AUTO_REBOOT       = "Auto Reboot"


class FirmwareSource(Enum):
    """펌웨어 파일 출처 — 윈도우의 선택 결과 (x_message 가 이 enum 으로 답한다)."""
    NETWORK     = auto()  # FTP 저장소에서 버전을 골라 내려받는다
    LOCAL_FILES = auto()  # 2_resource/temp 의 파일(마지막 다운로드본)을 그대로 쓴다


class AdapterType(Enum):
    """밸브 서비스 포트에 연결한 업데이트 어댑터 종류."""
    RS232 = auto()  # 부트모드 스위치/리셋을 사용자가 수동 조작
    USB   = auto()  # FTDI CBUS 핀으로 부트모드 진입/리셋을 자동 수행


class FirmwareWriteJob(NamedTuple):
    """start_write() 인자 — 호출 시점 스냅샷.

    network_version 이 None 이면 로컬 파일(flash_cpu1/2 경로)을 그대로 쓰고,
    문자열이면 그 버전을 FTP 에서 flash_cpu1/2 경로로 먼저 내려받는다."""
    adapter_type: AdapterType
    port_name: str
    kernel_cpu1: str
    kernel_cpu2: str
    flash_cpu1: str
    flash_cpu2: str
    network_version: str | None = None


def list_com_port_names() -> list[str]:
    """PC 의 시리얼 포트 이름 목록 (예: ["COM3", "COM7"])."""
    return [port.device for port in serial.tools.list_ports.comports()]


def _com_port_number(port_name: str) -> int:
    """"COM7" -> 7. FTDI D2XX 는 포트 번호로 장치를 찾는다."""
    match = re.fullmatch(r"COM(\d+)", port_name.strip(), re.IGNORECASE)
    if match is None:
        raise RuntimeError(f"Not a COM port name: '{port_name}' (USB adapter needs COMx)")
    return int(match.group(1))


# ============================================================================
#  FTDI CBUS 제어 (C++ FTDHelper 대응)
# ============================================================================
class FTDHelper:
    """USB 어댑터(FT232R)의 CBUS 핀으로 밸브의 부트모드/리셋 핀을 구동한다.

    ready_port / finish_port 는 (성공여부, 에러메시지) 튜플을 반환한다.
    (C++ 원본은 errMsg 를 값 전달해 호출자에게 전달되지 않는 버그가 있었다)
    핀 배치: c2 = reset (0b0100), c3 = bootmode (0b1000)
    """

    @staticmethod
    def _check_library() -> str:
        return "" if ftd is not None else "ftd2xx library is not available (ftd2xx.dll missing?)"

    # ------------------------------------------------------------------
    # COM 포트 번호로 장치를 찾아 핸들 반환 — (handle | None, 에러메시지)
    # ------------------------------------------------------------------
    def _open_by_comport(self, comport: int):
        try:
            num_devs = ftd.createDeviceInfoList()
        except ftd.DeviceError:
            return None, "can not found device"

        if num_devs == 0:
            return None, "can not found device"

        for i in range(num_devs):
            try:
                handle = ftd.open(i)
            except ftd.DeviceError:
                continue

            try:
                if handle.getComPortNumber() == comport:
                    return handle, ""  # 찾음 — 핸들을 열어둔 채 반환
            except ftd.DeviceError:
                pass

            handle.close()

        return None, "can not found target comport"

    # ------------------------------------------------------------------
    # EEPROM CBUS 설정 확인 및 자동 프로그래밍
    # (FT_Prog 에서 C2, C3 를 "IO MODE" 로 수동 설정하던 작업의 자동화)
    # ------------------------------------------------------------------
    def ensure_cbus_iomode(self, comport: int) -> tuple[bool, str, bool]:
        """C2, C3 핀이 EEPROM 에서 IOMODE 로 설정되어 있는지 확인하고 아니면
        설정한다. 반환 (성공여부, 메시지, 재열거됨) — 재열거됨이 True 면 EEPROM
        을 새로 써서 USB 재열거(cyclePort)했다는 뜻이므로 수 초 기다린 뒤
        다음 단계(ready_port)로 가야 한다."""
        err = self._check_library()
        if err:
            return False, err, False

        handle, err = self._open_by_comport(comport)
        if handle is None:
            return False, err, False

        try:
            try:
                ee = handle.eeRead()  # 모든 필드 보존을 위해 전체 읽기
            except ftd.DeviceError:
                return False, "can not read eeprom", False

            if ee.Cbus2 == FT_232R_CBUS_IOMODE and ee.Cbus3 == FT_232R_CBUS_IOMODE:
                return True, "", False

            ee.Cbus2 = FT_232R_CBUS_IOMODE
            ee.Cbus3 = FT_232R_CBUS_IOMODE
            try:
                handle.eeProgram(ee)
            except ftd.DeviceError:
                return False, "can not program eeprom", False

            # 설정 적용을 위해 USB 재열거 (물리적으로 뽑았다 꽂는 것과 동일)
            try:
                handle.cyclePort()
            except ftd.DeviceError:
                return True, "eeprom programmed - please replug device", True

            return True, "", True
        finally:
            try:
                handle.close()
            except ftd.DeviceError:
                pass  # cyclePort 후에는 핸들이 이미 무효화되었을 수 있음

    # ------------------------------------------------------------------
    # 부트모드 진입 시퀀스
    #   c3 __|￣￣￣￣￣￣￣￣￣
    #   c2 ____|￣￣|__________
    # ------------------------------------------------------------------
    def ready_port(self, comport: int) -> tuple[bool, str]:
        err = self._check_library()
        if err:
            return False, err

        handle, err = self._open_by_comport(comport)
        if handle is None:
            return False, err

        sequence = [
            (0xF0, "can not C3, C2 LOW"),
            (0xF8, "can not C3 HIGH"),
            (0xFC, "can not C3, C2 HIGH"),
            (0xF8, "can not remain C3 HIGH"),
        ]
        return self._run_sequence(handle, sequence)

    # ------------------------------------------------------------------
    # 종료(리셋) 시퀀스
    #   c3 ___________________
    #   c2 ____|￣￣|__________
    # ------------------------------------------------------------------
    def finish_port(self, comport: int) -> tuple[bool, str]:
        err = self._check_library()
        if err:
            return False, err

        handle, err = self._open_by_comport(comport)
        if handle is None:
            return False, err

        sequence = [
            (0xF0, "can not C3, C2 LOW"),
            (0xF4, "can not C3, C2 HIGH"),
            (0xF0, "can not remain C3 HIGH"),
        ]
        return self._run_sequence(handle, sequence)

    def _run_sequence(self, handle, sequence) -> tuple[bool, str]:
        try:
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
            handle.close()  # 실패 경로에서도 반드시 닫는다 (C++ 원본과 다름)


# ============================================================================
#  SCI8 부트 이미지 파일 로더 (hex2000 -boot -sci8 출력물)
# ============================================================================
def load_boot_image(path: str) -> bytes:
    """hex2000 -sci8 출력 파일을 읽어 바이트열로 반환.
      - ASCII 포맷(-a): 16진수 2자리 토큰 (STX/ETX 제어문자, 공백, 개행은 무시)
      - 바이너리 포맷(-b): 그대로 사용
    파일 선두가 AA 08 (키값 0x08AA) 인지 검증한다."""
    with open(path, "rb") as f:
        raw = f.read()

    if len(raw) >= 2 and raw[0] == SCI8_KEY[0] and raw[1] == SCI8_KEY[1]:
        data = raw
    else:
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

        bad = [t for t in tokens if len(t) != 2]
        if bad:
            raise ValueError(f"Non-2-digit hex tokens found (file corrupted?): {bad[:5]}")

        data = bytes(int(t, 16) for t in tokens)

    if len(data) < 2 or data[0] != SCI8_KEY[0] or data[1] != SCI8_KEY[1]:
        raise ValueError(f"Boot stream key value (AA 08) missing: {os.path.basename(path)}")
    return data


# ============================================================================
#  스레드
# ============================================================================
class _FirmwareThreadBase(QThread):
    sig_log = Signal(bool, str)  # is_err, message

    def __init__(self, parent=None):
        super().__init__(parent)
        self._abort = False

    def abort(self):
        self._abort = True

    def _check_abort(self):
        if self._abort:
            raise RuntimeError(ABORT_MESSAGE)


class FirmwareVersionListThread(_FirmwareThreadBase):
    """FTP version.txt 조회 1회."""

    sig_version_list_finished = Signal(bool, list, str)  # ok, versions, message

    def run(self):
        try:
            setting = firmware_ftp_helper.load_setting()
            self.sig_log.emit(False, f"[FTP] fetching version list from {setting.host}:{setting.port}{setting.path}")
            versions = firmware_ftp_helper.fetch_version_list(setting)
            self.sig_log.emit(False, f"[FTP] {len(versions)} version(s): {', '.join(versions)}")
            self.sig_version_list_finished.emit(True, versions, "")
        except Exception as e:
            self.sig_log.emit(True, f"[FTP] version list failed: {e}")
            self.sig_version_list_finished.emit(False, [], f"Failed to fetch firmware versions from FTP:\n{e}")


class FirmwareWriteThread(_FirmwareThreadBase):
    """(다운로드 ->) 파일 로드 -> CPU1 -> CPU2 쓰기 시퀀스 1회."""

    sig_phase_changed = Signal(FirmwarePhase)
    sig_progress_changed = Signal(FirmwarePhase, int, int)  # phase, done, total
    sig_write_finished = Signal(bool, str)                  # ok, message

    def __init__(self, job: FirmwareWriteJob, parent=None):
        super().__init__(parent)
        self._job = job
        self._ftd_helper = FTDHelper()
        self._ser: serial.Serial | None = None
        self._current_phase = FirmwarePhase.DOWNLOAD

    # ------------------------------------------------------------------ run
    def run(self):
        job = self._job
        is_usb = job.adapter_type == AdapterType.USB

        try:
            if job.network_version is not None:
                self._step(FirmwarePhase.DOWNLOAD)
                self._download_firmware(job)

            self._step(FirmwarePhase.LOAD_FILES)
            img = {}
            for key, path in (("kernel_cpu1", job.kernel_cpu1), ("kernel_cpu2", job.kernel_cpu2),
                              ("flash_cpu1", job.flash_cpu1), ("flash_cpu2", job.flash_cpu2)):
                img[key] = load_boot_image(path)
                self.sig_log.emit(False, f"[File] {key} : {os.path.basename(path)} ({len(img[key])} bytes)")

            if is_usb:
                self._step(FirmwarePhase.SET_EEPROM_IO_PIN)
                if self._ensure_cbus_iomode():
                    self._sleep(DELAY_STEP_S * 3)  # USB 재열거 대기

                self._step(FirmwarePhase.SET_BOOT_MODE)
                self._set_boot_mode()
                self._sleep(DELAY_STEP_S)

            # ---------------- CPU1 ----------------
            # 포트 (재)오픈은 단계 알림 뒤에 — 오픈 실패가 그 단계의 실패로 기록되게
            self._step(FirmwarePhase.CPU1_KERNEL_DN)
            self._open_serial(FW_KERNEL_DN_BAUDRATE)
            self._download_kernel(img["kernel_cpu1"])
            self._sleep(DELAY_AFTER_KERNEL_S)

            self._step(FirmwarePhase.CPU1_ERASE)
            self._open_serial(FW_KERNEL_BAUDRATE)
            self._erase_cpu(ERASE_CPU1)
            self._sleep(DELAY_STEP_S)

            self._step(FirmwarePhase.CPU1_APP_DN)
            self._download_app(DFU_CPU1, img["flash_cpu1"])
            self._sleep(DELAY_STEP_S)

            self._step(FirmwarePhase.CPU1_VERIFY)
            self._download_app(VERIFY_CPU1, img["flash_cpu1"])
            self._sleep(DELAY_STEP_S)

            self._step(FirmwarePhase.CPU1_RESET)
            self._reset_cpu(RESET_CPU1_BOOT_CPU2)
            self._sleep(DELAY_STEP_S)

            # ---------------- CPU2 ----------------
            self._step(FirmwarePhase.CPU2_KERNEL_DN)
            self._open_serial(FW_KERNEL_DN_BAUDRATE)
            self._download_kernel(img["kernel_cpu2"])
            self._sleep(DELAY_AFTER_KERNEL_S)

            self._step(FirmwarePhase.CPU2_ERASE)
            self._open_serial(FW_KERNEL_BAUDRATE)
            self._erase_cpu(ERASE_CPU2)
            self._sleep(DELAY_STEP_S)

            self._step(FirmwarePhase.CPU2_APP_DN)
            self._download_app(DFU_CPU2, img["flash_cpu2"])
            self._sleep(DELAY_STEP_S)

            self._step(FirmwarePhase.CPU2_VERIFY)
            self._download_app(VERIFY_CPU2, img["flash_cpu2"])
            self._sleep(DELAY_STEP_S)

            self._step(FirmwarePhase.CPU2_RESET)
            self._reset_cpu(RESET_CPU2)

            self._close_serial()  # FTDI 핸들을 열기 전에 시리얼 포트를 놓는다

            if is_usb:
                self._step(FirmwarePhase.AUTO_REBOOT)
                self._auto_reboot()
                self._sleep(DELAY_STEP_S)

            self.sig_log.emit(False, "[Done] firmware update completed")
            self.sig_write_finished.emit(True, "Firmware update is completed.")

        except Exception as e:
            self.sig_log.emit(True, f"[Failed] {self._current_phase.value} : {e}")
            self.sig_write_finished.emit(False, str(e))
        finally:
            self._close_serial()

    # ------------------------------------------------------------ 공용 유틸
    def _step(self, phase: FirmwarePhase):
        self._check_abort()
        self._current_phase = phase
        self.sig_phase_changed.emit(phase)
        self.sig_log.emit(False, f"[Step] {phase.value}")

    def _sleep(self, sec: float):
        # C++ startTimer() 의 단계 간 대기. 중단 반응성을 위해 분할 대기
        end = time.monotonic() + sec
        while time.monotonic() < end:
            self._check_abort()
            time.sleep(0.05)

    def _open_serial(self, baudrate: int):
        """포트를 (다시) 연다 — 커널 다운로드(38400)와 커널 커맨드(115200)의
        보레이트가 달라 CPU 마다 두 번씩 재오픈한다. (C++ connectSerial 대응)"""
        self._close_serial()
        self._ser = serial.Serial(
            port=self._job.port_name,
            baudrate=baudrate,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            timeout=RW_TIMEOUT_S,
            write_timeout=RW_TIMEOUT_S,
        )
        self._ser.reset_input_buffer()
        self._ser.reset_output_buffer()
        self.sig_log.emit(False, f"[Port] {self._job.port_name} opened @ {baudrate}bps")

    def _close_serial(self):
        if self._ser is not None:
            try:
                if self._ser.is_open:
                    self._ser.close()
            except serial.SerialException:
                pass
            self._ser = None

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

    # ------------------------------------------------------------ FTP
    def _download_firmware(self, job: FirmwareWriteJob):
        setting = firmware_ftp_helper.load_setting()
        remote_cpu1, remote_cpu2 = firmware_ftp_helper.remote_firmware_paths(
            setting, job.network_version, job.adapter_type == AdapterType.RS232)
        self.sig_log.emit(False, f"[FTP] {setting.host}:{setting.port} <- {remote_cpu1}, {remote_cpu2}")

        def on_progress(done: int, total: int):
            self._check_abort()  # 콜백에서 던진 예외는 retrbinary 를 뚫고 올라온다
            self.sig_progress_changed.emit(FirmwarePhase.DOWNLOAD, done, total)

        self.sig_progress_changed.emit(FirmwarePhase.DOWNLOAD, 0, 0)
        try:
            firmware_ftp_helper.download_firmware_files(
                setting, job.network_version, job.adapter_type == AdapterType.RS232,
                job.flash_cpu1, job.flash_cpu2, on_progress)
        except RuntimeError:
            raise  # 중단 요청
        except Exception as e:
            raise RuntimeError(f"Failed to download firmware files from FTP: {e}") from e

        self.sig_log.emit(False, f"[FTP] downloaded -> {job.flash_cpu1}, {job.flash_cpu2}")

    # ------------------------------------------------------------ FTDI
    def _ensure_cbus_iomode(self) -> bool:
        port_num = _com_port_number(self._job.port_name)
        result, msg, need_recycle = self._ftd_helper.ensure_cbus_iomode(port_num)

        if not result:
            raise RuntimeError(f"[Change EEPROM I/O pin] Failed: COM{port_num} : {msg}")

        if need_recycle:
            self.sig_log.emit(bool(msg), f"[Change EEPROM I/O pin] Programmed : COM{port_num} {msg}")
        else:
            self.sig_log.emit(False, f"[Change EEPROM I/O pin] Already set : COM{port_num}")
        return need_recycle

    def _set_boot_mode(self):
        port_num = _com_port_number(self._job.port_name)
        result, msg = self._ftd_helper.ready_port(port_num)
        if not result:
            raise RuntimeError(f"[Change BootMode] Failed: COM{port_num} : {msg}")
        self.sig_log.emit(False, f"[Change BootMode] Success : COM{port_num}")

    def _auto_reboot(self):
        port_num = _com_port_number(self._job.port_name)
        result, msg = self._ftd_helper.finish_port(port_num)
        if not result:
            raise RuntimeError(f"[Auto Reboot] Failed: COM{port_num} : {msg}")
        self.sig_log.emit(False, f"[Auto Reboot] Success : COM{port_num}")

    # ------------------------------------------------------------ 오토보
    def _autobaud_lock(self):
        """C++ autoBaudLock : 'A' 1회 송신 -> 동일 문자 에코 확인.

        전송 전에 입출력 버퍼를 비운다 — 직전 DSP 리셋 과정의 SCI 핀 재구성
        글리치나 미수신 잔류 바이트가 에코 판정을 오염시키기 때문. 오토보
        시점에는 상대가 'A' 를 받기 전까지 아무것도 보내지 않으므로 프로토콜에
        영향이 없다."""
        self._ser.reset_input_buffer()
        self._ser.reset_output_buffer()
        self._write(bytes([AUTOBAUD_CHAR]))
        rx = self._read1()
        if rx != AUTOBAUD_CHAR:
            raise RuntimeError(f"Autobaud failed: Received 0x{rx:02X} (Expected 0x41)")
        self.sig_log.emit(False, "[Autobaud] Success")

    # ---------------------------------------------------- 커널 다운로드
    def _download_kernel(self, data: bytes):
        """C++ downloadKernel = autoBaudLock + loadProgram(바이트 에코 검증)."""
        self._autobaud_lock()

        total = len(data)
        self.sig_progress_changed.emit(self._current_phase, 0, total)
        for idx, b in enumerate(data):
            self._check_abort()
            self._write(bytes([b]))
            echo = self._read1()
            if echo != b:
                raise RuntimeError(
                    f"Kernel echo mismatch @ {idx}/{total} : Sent 0x{b:02X} / Received 0x{echo:02X}")
            if idx % 32 == 0 or idx == total - 1:
                self.sig_progress_changed.emit(self._current_phase, idx + 1, total)

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
        """C++ getPacket / getPacketEx : 커널 상태 패킷 수신. 데이터 워드 리스트 반환."""
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

    # ----------------------------------------------------------- 소거 / 리셋
    def _erase_cpu(self, cmd: int):
        """C++ eraseCPU : 오토보 -> ERASE 패킷(sectorMask 4바이트 LE) -> 상태 패킷."""
        self._autobaud_lock()
        self._send_packet(cmd, ERASE_SECTOR_MASK.to_bytes(4, "little"))
        self._get_packet(cmd)
        self.sig_log.emit(False, f"[Erase] Command 0x{cmd:04X} completed")

    def _reset_cpu(self, cmd: int):
        """C++ resetCPU : RESET 패킷 송신 + ACK 확인."""
        self._send_packet(cmd)
        self.sig_log.emit(False, f"[Reset] Command 0x{cmd:04X} sent")

    # ------------------------------------------- 앱 다운로드 / 검증 (DFU)
    def _download_app(self, cmd: int, data: bytes):
        """C++ downloadApp : DFU/VERIFY 패킷 -> downloadImage -> 상태 패킷 판정."""
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
        """C++ downloadImage : SCI8 이미지를 블록 단위로 전송하며 커널이 회신하는
        러닝 체크섬(2바이트)을 검증한다. (에코 없음)

        커널과의 핸드셰이크는 체크섬 회신 시점에만 존재하므로 체크섬 지점
        사이의 바이트들은 한 번에 write 해도 와이어 상 동일하다."""
        total = len(data)
        pos = 0
        checksum = 0

        def send_range(nbytes: int):
            nonlocal pos, checksum
            if pos + nbytes > total:
                raise RuntimeError("Image file is shorter than expected (format error)")
            chunk = data[pos : pos + nbytes]
            self._write(chunk)
            checksum = (checksum + sum(chunk)) & 0xFFFF
            pos += nbytes
            self.sig_progress_changed.emit(self._current_phase, pos, total)

        def recv_and_check_checksum():
            lsb = self._read_byte_with_ack()
            msb = self._read_byte_with_ack()
            rcv = ((msb << 8) | lsb) & 0xFFFF
            if rcv != checksum:
                raise RuntimeError(
                    f"Image checksum error @ {pos}/{total} "
                    f"(Calculated 0x{checksum:04X} / Received 0x{rcv:04X})")

        self.sig_progress_changed.emit(self._current_phase, 0, total)

        # 선두 22바이트 : 키값(2) + 예약(16) + 엔트리주소(4)
        send_range(22)
        recv_and_check_checksum()          # 커널이 즉시 체크섬 회신

        # 블록 반복 : [blockSize(2)] [destAddr(4)] [data words ...]
        while pos < total:
            self._check_abort()

            if pos + 2 > total:
                raise RuntimeError("Image file is truncated at block header (format error)")

            block_size = ((data[pos + 1] << 8) | data[pos]) & 0xFFFF

            if block_size == 0x0000:       # 종단 블록
                send_range(2)
                self.sig_progress_changed.emit(self._current_phase, total, total)
                break

            # 블록사이즈(2) + 주소(4) + 첫 구간(최대 128워드)을 일괄 전송
            first_words = min(block_size, BLOCK_WORDS)
            send_range(2 + 4 + first_words * 2)

            # 이후 128워드 구간마다 : 체크섬 수신 -> 다음 구간 전송
            sent_words = first_words
            while sent_words < block_size:
                self._check_abort()
                recv_and_check_checksum()  # 128워드마다 중간 체크섬 (C++ 동일)
                run_words = min(block_size - sent_words, BLOCK_WORDS)
                send_range(run_words * 2)
                sent_words += run_words

            # 블록 종료 체크섬
            recv_and_check_checksum()


# ============================================================================
#  외부 인터페이스 (UI 스레드에서 사용)
# ============================================================================
class FirmwareRunWorker(QObject):
    """펌웨어 워커의 외부 인터페이스. 한 번에 하나의 작업(버전 조회 또는 쓰기)만
    수행하며, 진행 중이면 start_* 가 False 를 반환한다.

    사용 예 (윈도우):
        worker = FirmwareRunWorker(self, log_source=self.win_name)
        worker.sig_version_list_finished.connect(self.handle_version_list_finished)
        worker.sig_write_phase_changed.connect(self.handle_write_phase_changed)
        worker.sig_write_progress_changed.connect(self.handle_write_progress_changed)
        worker.sig_write_finished.connect(self.handle_write_finished)
        worker.start_version_list()
        worker.start_write(FirmwareWriteJob(...))
        worker.abort()      # 실행 중 작업 중단 요청 -> sig_write_finished(False, ABORT_MESSAGE)
        worker.cleanup()    # 창 closeEvent 에서 — 중단 + 스레드 종료 대기

    [주의] 쓰기 작업은 지정 COM 포트를 직접 연다 — 같은 포트를 쓰는 ServicePort
    는 호출측이 먼저 닫아야 한다."""

    sig_version_list_finished = Signal(bool, list, str)      # ok, versions, message
    sig_write_phase_changed = Signal(FirmwarePhase)
    sig_write_progress_changed = Signal(FirmwarePhase, int, int)  # phase, done, total
    sig_write_finished = Signal(bool, str)                   # ok, message

    def __init__(self, parent=None, log_source: str = "FirmwareRunWorker"):
        super().__init__(parent)
        self._log = AppLogManager().get_logger(log_source)
        self._thread: _FirmwareThreadBase | None = None
        self._is_cleaned = False

        app = QCoreApplication.instance()
        if app is not None:
            app.aboutToQuit.connect(self.cleanup)
        self.destroyed.connect(self.cleanup)

    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.isRunning()

    # ------------------------------------------------------------ 작업 시작
    def start_version_list(self) -> bool:
        if self.is_running:
            return False

        thread = FirmwareVersionListThread(self)
        thread.sig_version_list_finished.connect(self.sig_version_list_finished)
        self._replace_thread(thread)
        thread.start()
        return True

    def start_write(self, job: FirmwareWriteJob) -> bool:
        if self.is_running:
            return False

        thread = FirmwareWriteThread(job, self)
        thread.sig_phase_changed.connect(self.sig_write_phase_changed)
        thread.sig_progress_changed.connect(self.sig_write_progress_changed)
        thread.sig_write_finished.connect(self.sig_write_finished)
        self._replace_thread(thread)
        self._log.info(f"[Start] adapter={job.adapter_type.name}, port={job.port_name}, "
                       f"version={job.network_version or 'local files'}")
        thread.start()
        return True

    def abort(self):
        """실행 중 작업 중단 요청. 블로킹 read 타임아웃(RW_TIMEOUT_S) 안에
        sig_write_finished(False, ABORT_MESSAGE) 로 끝난다."""
        if self.is_running:
            self._log.warning("[Abort] requested")
            self._thread.abort()

    # ------------------------------------------------------------ 내부
    def _replace_thread(self, thread: _FirmwareThreadBase):
        old = self._thread
        if old is not None:
            old.blockSignals(True)
            old.deleteLater()

        thread.sig_log.connect(self._handle_log)
        self._thread = thread

    def _handle_log(self, is_err: bool, msg: str):
        if is_err:
            self._log.error(msg)
        else:
            self._log.info(msg)

    # ------------------------------------------------------------ 종료
    def cleanup(self):
        """중단 요청 후 스레드 종료를 기다린다 (최대 RW_TIMEOUT_S 안팎 블로킹).
        창 closeEvent 에서 반드시 호출한다 — 실행 중 QThread 가 파괴되면 앱 전체가
        abort 된다 (ParameterRunWorker 와 같은 이유)."""
        if self._is_cleaned:
            return
        self._is_cleaned = True

        app = QCoreApplication.instance()
        if app is not None:
            try:
                app.aboutToQuit.disconnect(self.cleanup)
            except (TypeError, RuntimeError):
                pass

        if self._thread is not None:
            self._thread.blockSignals(True)
            if self._thread.isRunning():
                self._thread.abort()
                self._thread.wait()
            self._thread = None
