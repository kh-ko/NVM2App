import atexit
from PySide6.QtCore import QCoreApplication, QObject, Signal, QIODevice, Property, QMutex, QMutexLocker, QElapsedTimer
from PySide6.QtSerialPort import QSerialPort

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

    def __init__(self, parent=None):
        if self._initialized:
            return

        super().__init__(parent)

        self._initialized = True
        self.serial_port: QSerialPort | None = None 
        self._connect_info : str = ""
        self._termination_chars = b"\r\n" # 기본값
        self._mutex = QMutex()
        self._timer = QElapsedTimer()

        app = QCoreApplication.instance()
        if app is not None:
            app.aboutToQuit.connect(self.close)
            
        atexit.register(self.close)

    @property
    def connect_info(self) -> str:
        with QMutexLocker(self._mutex):
            return self._connect_info

    def _set_connect_info(self, info: str):
        if self._connect_info != info:
            self._connect_info = info
            self.connect_info_changed.emit(info)

    def open(self,  port_name: str, baudrate: int, data_bits: int, parity: int, stop_bits: int, termination: int):
        locker = QMutexLocker(self._mutex)
        
        parity_map = {0: 'N', 2: 'E', 3: 'O', 4: 'S', 5: 'M'}
        stop_map = {1: '1', 2: '2', 3: '1.5'}
        term_map_bytes = {0: b"\r\n", 1: b"\n", 2: b"\r"}
        termination_map = {0: 'CR+LF', 1: 'LF', 2: 'CR'}

        if self.serial_port is not None:
            self._close_internal()

        try:
            self.serial_port = QSerialPort(port_name)
            self.serial_port.setBaudRate(baudrate)
            self.serial_port.setDataBits(QSerialPort.DataBits(data_bits))
            self.serial_port.setParity(QSerialPort.Parity(parity))
            self.serial_port.setStopBits(QSerialPort.StopBits(stop_bits))
            self.serial_port.setFlowControl(QSerialPort.FlowControl.NoFlowControl)

            if self.serial_port.open(QIODevice.OpenModeFlag.ReadWrite):
                self._termination_chars = term_map_bytes.get(termination, b"\r\n")
                p_str = parity_map.get(parity, 'N')
                s_str = stop_map.get(stop_bits, '1')
                t_str = termination_map.get(termination, 'CR+LF')

                self.serial_port.errorOccurred.connect(self._on_serial_error)

                new_info = f"{port_name}-{baudrate}-{data_bits}-{p_str}-{s_str}-{t_str}-{t_str}"
                self._set_connect_info(new_info)
                LogManager().log(LogType.INFO, f"[ServicePort] [{port_name}] 연결 성공: {new_info}")
                return True
            else:
                LogManager().log(LogType.ERROR, f"[ServicePort] [{port_name}] 연결 실패: {self.serial_port.errorString()}")
                self._close_internal()
                return False

        except ValueError as e:
            LogManager().log(LogType.ERROR, f"[ServicePort] 설정 값 오류: {e}")
            self._close_internal()
            return False

    def close(self):
        with QMutexLocker(self._mutex):
            self._close_internal()      

    def request_string(self, command: str) -> str | None:
        cmd_bytes = command.encode('utf-8')
        return self.request(cmd_bytes)

    def request(self, command: bytes, is_error_present: bool = True) -> str | None:
        with QMutexLocker(self._mutex):
            if self.serial_port is None or not self.serial_port.isOpen():
                if is_error_present:
                    LogManager().log(LogType.ERROR, f"[ServicePort] 시리얼 포트가 열려있지 않습니다: {command.decode('utf-8')}")
                return None
            
            if self.serial_port.bytesAvailable() > 0:
                self.serial_port.clear(QSerialPort.Direction.Input)
            
            full_command = command + self._termination_chars

            self.serial_port.write(full_command)
            if not self.serial_port.waitForBytesWritten(100):
                if is_error_present:
                    LogManager().log(LogType.ERROR, f"[ServicePort] 명령어 전송 실패: {command.decode('utf-8')}")
                return None

            self._timer.start()
            response = None
            
            while True:
                elapsed = self._timer.elapsed()
                remaining_ms = 100 - elapsed
                
                if remaining_ms <= 0:
                    if is_error_present:
                        LogManager().log(LogType.ERROR, f"[ServicePort] 응답 시간 초과: {command.decode('utf-8')},{elapsed}ms")
                    return None
                
                if self.serial_port.waitForReadyRead(remaining_ms):
                    chunk = self.serial_port.readAll().data()
                    
                    if response is None:
                        term_idx = chunk.find(self._termination_chars)
                        if term_idx != -1:
                            raw_payload = chunk[:term_idx]
                            try:
                                return raw_payload.decode('utf-8')
                            except UnicodeDecodeError:
                                if is_error_present:
                                    LogManager().log(LogType.ERROR, f"[ServicePort] 응답 디코딩 실패: {command.decode('utf-8')},{raw_payload.hex()}")
                                return None
                        
                        response = bytearray(chunk)
                    else:
                        response.extend(chunk)
                        term_idx = response.find(self._termination_chars)
                        if term_idx != -1:
                            raw_payload = bytes(response[:term_idx])
                            try:
                                return raw_payload.decode('utf-8')
                            except UnicodeDecodeError:
                                if is_error_present:
                                    LogManager().log(LogType.ERROR, f"[ServicePort] 응답 디코딩 실패: {command.decode('utf-8')},{raw_payload.hex()}")
                                return None
                else:
                    if is_error_present:
                        LogManager().log(LogType.ERROR, f"[ServicePort] 응답 시간 초과: {command.decode('utf-8')},{elapsed}ms")
                    return None

    def _close_internal(self):
        if self.serial_port is not None:
            if self.serial_port.isOpen():
                self.serial_port.close()
                LogManager().log(LogType.INFO, f"[ServicePort] 연결 해제")
            self.serial_port.deleteLater()
            self.serial_port = None
        
        self._set_connect_info("")

    def _on_serial_error(self, error: QSerialPort.SerialPortError):
        # ResourceError: 장치가 시스템에서 갑자기 제거되었을 때 (USB 뽑힘 등)
        if error == QSerialPort.SerialPortError.ResourceError:
            port_name = self.serial_port.portName() if self.serial_port else "Unknown"
            error_msg = self.serial_port.errorString() if self.serial_port else "장치 분리됨"
            
            LogManager().log(LogType.ERROR, f"[ServicePort] 치명적 에러 (USB 뽑힘 등): {port_name} - {error_msg}")
            
            # 좀비가 된 포트를 깔끔하게 닫아줌
            self.close()        