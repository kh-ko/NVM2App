import serial
from PySide6.QtCore import QCoreApplication, QObject, Signal, QIODevice, Property, QMutex, QRecursiveMutex, QMutexLocker

from b_core.b_datatype.general_enum import LogType
from b_core.c_manager.log_manager import LogManager

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
        self.serial_port: serial.Serial | None = None
        self._connect_info : str = ""
        self._termination_chars = b"\r\n" # 기본값
        self._mutex = QRecursiveMutex()

        app = QCoreApplication.instance()
        if app is not None:
            app.aboutToQuit.connect(self.close)

    @property
    def connect_info(self) -> str:
        with QMutexLocker(self._mutex):
            return self._connect_info

    def _set_connect_info(self, info: str):
        self._connect_info = info
        self.connect_info_changed.emit(info)

    def open(self,  port_name: str, baudrate: int, data_bits: int, parity: int, stop_bits: int, termination: int):
        with QMutexLocker(self._mutex): 
            parity_map = {0: serial.PARITY_NONE, 2: serial.PARITY_EVEN, 3: serial.PARITY_ODD, 4: serial.PARITY_SPACE, 5: serial.PARITY_MARK}
            stop_map = {1: serial.STOPBITS_ONE, 2: serial.STOPBITS_TWO, 3: serial.STOPBITS_ONE_POINT_FIVE}
            term_map_bytes = {0: b"\r\n", 1: b"\n", 2: b"\r"}
            termination_map = {0: 'CR+LF', 1: 'LF', 2: 'CR'}

            self._close_internal()

            try:
                p_val = parity_map.get(parity, serial.PARITY_NONE)
                s_val = stop_map.get(stop_bits, serial.STOPBITS_ONE)

                self.serial_port = serial.Serial(port=port_name, baudrate=baudrate, bytesize=data_bits, parity=p_val, stopbits=s_val, timeout=0.1)
                
                self._termination_chars = term_map_bytes.get(termination, b"\r\n")

                p_str = p_val
                s_str = str(s_val)
                t_str = termination_map.get(termination, 'CR+LF')

                new_info = f"{port_name}-{baudrate}-{data_bits}-{p_str}-{s_str}-{t_str}"
                self._set_connect_info(new_info)
                LogManager().log(LogType.INFO, f"[ServicePort] [{port_name}] 연결 성공: {new_info}")
                return True

            except serial.SerialException as e:
                LogManager().log(LogType.ERROR, f"[ServicePort] 연결 실패: {e}")
                self._close_internal()
                return False

    def close(self):
        with QMutexLocker(self._mutex):
            self._close_internal()      

    def request_string(self, command: str, is_error_present: bool = True, is_logging: bool = True) -> str | None:
        cmd_bytes = command.encode('utf-8')
        return self.request(cmd_bytes, is_error_present, is_logging)

    def request(self, command: bytes, is_error_present: bool = True, is_logging: bool = True) -> str | None:
        with QMutexLocker(self._mutex):
            if self.serial_port is None or not self.serial_port.is_open:
                if is_error_present:
                    LogManager().log(LogType.ERROR, f"[ServicePort] 시리얼 포트가 열려있지 않습니다: {command.decode('utf-8')}")
                return None
            
            try:
                self.serial_port.reset_input_buffer()
                full_command = command + self._termination_chars
                self.serial_port.write(full_command)
                self.serial_port.flush()

                if is_logging:
                    LogManager().log(LogType.TX, f"[ServicePort]{command.decode('utf-8')}")

                response_bytes = self.serial_port.read_until(self._termination_chars)

                if not response_bytes:
                    if is_error_present:
                        LogManager().log(LogType.ERROR, f"[ServicePort] 응답 시간 초과: {command.decode('utf-8')}")
                    return None

                if response_bytes.endswith(self._termination_chars):
                    raw_payload = response_bytes[:-len(self._termination_chars)]
                    try:
                        ret_str = raw_payload.decode('utf-8')
                        if is_logging:
                            LogManager().log(LogType.RX, f"[ServicePort]{ret_str}")
                        return ret_str
                    except UnicodeDecodeError:
                        if is_error_present:
                            LogManager().log(LogType.ERROR, f"[ServicePort] 응답 디코딩 실패: {command.decode('utf-8')},{raw_payload.hex()}")
                        return None
                else:
                    if is_error_present:
                        LogManager().log(LogType.ERROR, f"[ServicePort] 불완전한 데이터 수신: {response_bytes.hex()}")
                    return None

            except serial.SerialTimeoutException:
                if is_error_present:
                    LogManager().log(LogType.ERROR, f"[ServicePort] 명령어 전송/수신 타임아웃: {command.decode('utf-8')}")
                return None
            except serial.SerialException as e:
                LogManager().log(LogType.ERROR, f"[ServicePort] 치명적 통신 에러 (장치 분리 의심): {e}")
                self._close_internal() 
                return None
            except Exception as e:
                if is_error_present:
                    LogManager().log(LogType.ERROR, f"[ServicePort] 통신 에러: {e}")
                return None

    def get_port_name(self)-> str | None:
        with QMutexLocker(self._mutex):
            if self.serial_port is None or not self.serial_port.is_open:
                return None
            return self.serial_port.port

    def _close_internal(self):
        if self.serial_port is not None:
            if self.serial_port.is_open:
                self.serial_port.close()
                LogManager().log(LogType.INFO, "[ServicePort] 연결 해제")
            self.serial_port = None
        
        self._set_connect_info("")    