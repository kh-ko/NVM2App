import time
import serial
from PySide6.QtCore import QCoreApplication, QObject, Signal, QMutex, QRecursiveMutex, QMutexLocker

from b_core.b_datatype.general_enum import SvcPortErrType
from b_core.c_manager.app_log_manager import AppLogManager

class ServicePort(QObject):
    _instance = None
    _creation_mutex = QMutex()

    connect_info_changed = Signal(str)

    def __new__(cls, *args, **kwargs):
        # 멀티스레드 환경에서 동시에 생성되는 것을 방지 (Thread-Safe Singleton)
        with QMutexLocker(cls._creation_mutex):
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self):
        if self._initialized:
            return

        super().__init__(parent=None)

        self._initialized = True
        self._log = AppLogManager().get_logger("ServicePort", is_global=True)
        self._is_trace_mode = False
        self.trace_buffer = []
        self.serial_port: serial.Serial | None = None
        self._connect_info : str = ""
        self._termination_chars = b"\r\n" # 기본값
        self.port_name = ""
        self.baudrate = 0
        self.data_bits = 0
        self.parity = 0
        self.stop_bits = 0
        self.termination = 0
        self._mutex = QRecursiveMutex()

        # 뮤텍스 안에서 확정된 connect_info 변경들 — 락 해제 후 순서대로 emit 한다.
        # (락을 잡은 채 emit 하면 수신 슬롯이 open/close/request 로 재진입해
        #  임계 구역 한가운데서 상태를 바꿀 수 있는 취약한 구조가 되기 때문)
        self._pending_infos: list[str] = []

        app = QCoreApplication.instance()
        if app is not None:
            app.aboutToQuit.connect(self.close)

    @property
    def connect_info(self) -> str:
        with QMutexLocker(self._mutex):
            return self._connect_info

    def _set_connect_info(self, info: str):
        """반드시 _mutex 안에서 호출. 시그널은 락 해제 후 _flush_connect_signals() 가 발화."""
        if self._connect_info == info:
            return

        self._connect_info = info
        self._pending_infos.append(info)

    def _flush_connect_signals(self):
        """락 해제 후 호출 — 뮤텍스 안에서 쌓인 connect_info 변경을 순서대로 emit."""
        while True:
            try:
                info = self._pending_infos.pop(0)
            except IndexError:
                return
            self.connect_info_changed.emit(info)

    def set_trace_mode(self, mode: bool):
        with QMutexLocker(self._mutex):
            self._is_trace_mode = mode
            self.trace_buffer.clear()

    def get_trace_buffer(self) -> list[str]:
        with QMutexLocker(self._mutex):
            data = list(self.trace_buffer)
            self.trace_buffer.clear()
            return data

    def open(self,  port_name: str, baudrate: int, data_bits: int, parity: int, stop_bits: int, termination: int) -> bool:
        self.set_trace_mode(False)

        with QMutexLocker(self._mutex):
            self.port_name = port_name
            self.baudrate = baudrate
            self.data_bits = data_bits
            self.parity = parity
            self.stop_bits = stop_bits
            self.termination = termination
            parity_map = {0: serial.PARITY_NONE, 2: serial.PARITY_EVEN, 3: serial.PARITY_ODD, 4: serial.PARITY_SPACE, 5: serial.PARITY_MARK}
            stop_map = {1: serial.STOPBITS_ONE, 2: serial.STOPBITS_TWO, 3: serial.STOPBITS_ONE_POINT_FIVE}
            term_map_bytes = {0: b"\r\n", 1: b"\n", 2: b"\r"}
            termination_map = {0: 'CR+LF', 1: 'LF', 2: 'CR'}

            self._close_internal()

            try:
                p_val = parity_map.get(parity, serial.PARITY_NONE)
                s_val = stop_map.get(stop_bits, serial.STOPBITS_ONE)

                self.serial_port = serial.Serial(port=port_name, baudrate=baudrate, bytesize=data_bits, parity=p_val, stopbits=s_val, timeout=0.5, write_timeout=0.5)

                self._termination_chars = term_map_bytes.get(termination, b"\r\n")

                p_str = p_val
                s_str = str(s_val)
                t_str = termination_map.get(termination, 'CR+LF')

                new_info = f"{port_name}-{baudrate}-{data_bits}-{p_str}-{s_str}-{t_str}"
                self._set_connect_info(new_info)
                self._log.info(f"port opened: {new_info}")
                success = True

            except serial.SerialException as e:
                self._log.error(f"port open failed: {port_name} ({e})")
                self._close_internal()
                success = False

        self._flush_connect_signals()
        return success

    def close(self):
        with QMutexLocker(self._mutex):
            self._close_internal()
            self.port_name = ""
            self.baudrate = 0
            self.data_bits = 0
            self.parity = 0
            self.stop_bits = 0
            self.termination = 0

        self._flush_connect_signals()

    def request_string(self, command: str, nv1_check: str = None) -> tuple[str | None, SvcPortErrType]:
        cmd_bytes = command.encode('utf-8')
        return self.request(cmd_bytes, nv1_check)

    def request(self, command: bytes, nv1_check: str = None) -> tuple[str | None, SvcPortErrType]:
        with QMutexLocker(self._mutex):
            result = self._request_locked(command, nv1_check)

        # 통신 오류로 포트가 닫힌 경우의 connect_info 변경 시그널 발화
        self._flush_connect_signals()
        return result

    def _request_locked(self, command: bytes, nv1_check: str = None) -> tuple[str | None, SvcPortErrType]:
        if self.serial_port is None or not self.serial_port.is_open:
            return None, SvcPortErrType.OPEN_ERROR

        try:
            self.serial_port.reset_input_buffer()
            full_command = command + self._termination_chars
            self.serial_port.write(full_command)
            self.serial_port.flush()

            if self._is_trace_mode:
                start_time = time.perf_counter()

                while (time.perf_counter() - start_time) < 1:
                    response_bytes = self.serial_port.read_until(self._termination_chars)

                    if not response_bytes:
                        break
                    elif nv1_check and response_bytes.startswith(nv1_check.encode('utf-8')):
                        break
                    elif nv1_check and response_bytes.startswith(b"E:"):
                        break
                    elif not nv1_check and response_bytes.startswith(b"p:"):
                        break
                    elif self._is_trace_mode:
                        # 터미네이터 없이 끊긴(타임아웃 부분 수신) 라인은 그대로 보존
                        if response_bytes.endswith(self._termination_chars):
                            raw_payload = response_bytes[:-len(self._termination_chars)]
                        else:
                            raw_payload = response_bytes
                        response_bytes = None
                        try:
                            if len(self.trace_buffer) < 200:
                                self.trace_buffer.append(raw_payload.decode('utf-8'))
                        except UnicodeDecodeError:
                            pass
            else:
                response_bytes = self.serial_port.read_until(self._termination_chars)

            if not response_bytes:
                return None, SvcPortErrType.READ_TIMEOUT_ERROR

            if response_bytes.endswith(self._termination_chars):
                raw_payload = response_bytes[:-len(self._termination_chars)]
                try:
                    ret_str = raw_payload.decode('utf-8')
                    return ret_str, SvcPortErrType.NONE
                except UnicodeDecodeError:
                    return None, SvcPortErrType.DECODING_ERROR
            else:
                return None, SvcPortErrType.UN_COMPLETED_DATA

        except serial.SerialTimeoutException:
            return None, SvcPortErrType.READ_TIMEOUT_ERROR
        except serial.SerialException as e:
            self._close_internal()
            return None, SvcPortErrType.DEVICE_ERR
        except Exception as e:
            return None, SvcPortErrType.UNKNOWN_ERR

    def get_port_name(self)-> str | None:
        with QMutexLocker(self._mutex):
            if self.serial_port is None or not self.serial_port.is_open:
                return None
            return self.serial_port.port

    def _close_internal(self):
        if self.serial_port is not None:
            if self.serial_port.is_open:
                self.serial_port.close()
                self._log.info("port closed")

            self.serial_port = None

        self._set_connect_info("")
