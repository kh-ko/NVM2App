import serial
from PySide6.QtCore import QCoreApplication, QObject, Signal, Qt, QThread, QMutex, QRecursiveMutex, QMutexLocker

from b_core.b_datatype.general_enum import SvcPortErrType
from b_core.c_manager.app_log_manager import AppLogManager
from b_core.d_dal.serial_setting import SerialSetting

class ServicePort(QObject):
    _instance = None
    _creation_mutex = QMutex()

    connect_info_changed = Signal(str)
    _sig_flush_requested = Signal()  # 내부용 — 대기 목록 비우기 요청 (항상 메인 스레드로 큐 배달)

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

        # 시그널 배달은 메인 스레드에서만 수행한다 (_emit_pending 참고).
        # 워커에서 먼저 싱글턴이 만들어지면 큐 슬롯을 돌릴 이벤트 루프가 없어
        # connect_info_changed 가 영영 발화되지 않으므로 생성 스레드를 강제한다.
        app = QCoreApplication.instance()
        assert app is not None and QThread.currentThread() == app.thread(), \
            "ServicePort must be created on the main thread after QApplication"

        self._initialized = True
        self._log = AppLogManager().get_logger("ServicePort", is_global=True)
        self.serial_port: serial.Serial | None = None
        self._connect_info : str = ""
        self._termination_chars = b"\r\n" # 기본값
        self._setting: SerialSetting | None = None  # 열려 있는 포트의 설정 (닫히면 None) — _info_mutex 아래

        # 락 2개의 역할 분리:
        # - _mutex      : 시리얼 I/O + 포트 상태(open/close/request). 왕복 내내 점유된다.
        # - _info_mutex : _connect_info / _pending_infos 전용. 아주 짧게만 잡는다.
        # 메인 스레드가 연결 정보를 읽거나 시그널을 배달할 때 _mutex 를 기다리면
        # 워커의 시리얼 왕복(최대 timeout 0.5s)마다 GUI 가 멈추므로 반드시 분리한다.
        # 락 순서 규칙: _mutex -> _info_mutex 순으로만 중첩한다.
        # (_info_mutex 를 잡은 채 _mutex 를 잡는 경로는 만들지 말 것)
        self._mutex = QRecursiveMutex()
        self._info_mutex = QMutex()

        # 뮤텍스 안에서 확정된 connect_info 변경들 — 락 해제 후 순서대로 emit 한다.
        # (락을 잡은 채 emit 하면 수신 슬롯이 open/close/request 로 재진입해
        #  임계 구역 한가운데서 상태를 바꿀 수 있는 취약한 구조가 되기 때문)
        self._pending_infos: list[str] = []
        self._sig_flush_requested.connect(self._emit_pending, Qt.QueuedConnection)

        app.aboutToQuit.connect(self.close)

    @property
    def connect_info(self) -> str:
        # _info_mutex 만 잡는다 — 워커의 시리얼 왕복(_mutex)을 기다리지 않는다
        with QMutexLocker(self._info_mutex):
            return self._connect_info

    def _set_connect_info(self, info: str):
        """반드시 _mutex 안에서 호출 (append 순서 = 포트 상태 변경 순서 보장).
        시그널은 락 해제 후 _flush_connect_signals() 가 발화."""
        with QMutexLocker(self._info_mutex):
            if self._connect_info == info:
                return

            self._connect_info = info
            self._pending_infos.append(info)

    def _flush_connect_signals(self):
        """_mutex 해제 후 호출 — 실제 emit 은 메인 스레드의 _emit_pending 이 수행한다.

        여기서 직접 emit 하지 않는 이유: 워커 스레드 발 emit 은 큐 배달, 메인
        스레드 발 emit 은 직접 배달이라 두 경로가 섞이면 먼저 쌓인 항목이
        나중에 도착할 수 있다. (예: 워커의 통신 오류로 쌓인 "" 가, 직후 사용자가
        open() 한 결과보다 늦게 슬롯에 도달해 열린 포트를 끊김으로 표시)
        emit 을 메인 스레드 한 곳으로 모으면 배달 순서가 append 순서와 같아진다.

        대기 항목이 없으면 요청하지 않는다 — request() 는 매 호출마다 여기를
        거치므로, 무조건 요청하면 폴링 속도로 메인 스레드 이벤트가 쌓인다."""
        with QMutexLocker(self._info_mutex):
            if not self._pending_infos:
                return
        self._sig_flush_requested.emit()

    def _emit_pending(self):
        """항상 메인 스레드에서 실행 — 대기 목록을 쌓인 순서대로 emit.

        pop 은 _info_mutex 안에서, emit 은 락 밖에서 한다 (슬롯이 open/close/
        request 로 재진입해 _mutex 를 잡아도 안전 — 여기서는 _mutex 를 잡지
        않는다). 재진입으로 추가된 항목은 이 루프가 이어서 처리하고, 그때
        함께 큐에 들어온 flush 요청은 빈 목록을 보고 바로 반환한다."""
        while True:
            with QMutexLocker(self._info_mutex):
                if not self._pending_infos:
                    return
                info = self._pending_infos.pop(0)
            self.connect_info_changed.emit(info)

    def open(self, setting: SerialSetting) -> bool:
        """setting 으로 포트를 연다 (열려 있던 포트는 먼저 닫는다).

        코드 → pyserial 값 변환과 코드 검증은 SerialSetting 몫 — 표에 없는 코드는 호출측이
        from_connection() 에서 미리 거른다 (여기서는 ValueError 가 그대로 올라온다)."""
        with QMutexLocker(self._mutex):
            self._close_internal()

            try:
                self.serial_port = serial.Serial(**setting.pyserial_kwargs(timeout=0.5))
                self._termination_chars = setting.term_bytes
                with QMutexLocker(self._info_mutex):
                    self._setting = setting

                new_info = setting.describe()
                self._set_connect_info(new_info)
                self._log.info(f"port opened: {new_info}")
                success = True

            except serial.SerialException as e:
                self._log.error(f"port open failed: {setting.port_name} ({e})")
                self._close_internal()
                success = False

        self._flush_connect_signals()
        return success

    def close(self):
        with QMutexLocker(self._mutex):
            self._close_internal()

        self._flush_connect_signals()

    def request_string(self, command: str) -> tuple[str | None, SvcPortErrType]:
        cmd_bytes = command.encode('utf-8')
        return self.request(cmd_bytes)

    def request(self, command: bytes) -> tuple[str | None, SvcPortErrType]:
        with QMutexLocker(self._mutex):
            result = self._request_locked(command)

        # 통신 오류로 포트가 닫힌 경우의 connect_info 변경 시그널 발화
        self._flush_connect_signals()
        return result

    def _request_locked(self, command: bytes) -> tuple[str | None, SvcPortErrType]:
        if self.serial_port is None or not self.serial_port.is_open:
            return None, SvcPortErrType.OPEN_ERROR

        try:
            self.serial_port.reset_input_buffer()
            full_command = command + self._termination_chars
            self.serial_port.write(full_command)
            self.serial_port.flush()

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

    def get_port_name(self) -> str | None:
        setting = self.setting
        return setting.port_name if setting is not None else None

    @property
    def setting(self) -> SerialSetting | None:
        """열려 있는 포트의 설정 (닫혀 있으면 None) — 재부팅 대기·펌웨어 업데이트가 재연결에 쓰는 스냅샷.
        _info_mutex 만 잡으므로 워커의 시리얼 왕복(_mutex)을 기다리지 않는다 (F016)."""
        with QMutexLocker(self._info_mutex):
            return self._setting

    def _close_internal(self):
        if self.serial_port is not None:
            if self.serial_port.is_open:
                self.serial_port.close()
                self._log.info("port closed")

            self.serial_port = None

        with QMutexLocker(self._info_mutex):
            self._setting = None
        self._set_connect_info("")
