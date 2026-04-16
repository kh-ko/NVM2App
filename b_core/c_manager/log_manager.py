from collections import deque
from PySide6.QtCore import QObject, QMutex, QMutexLocker
from b_core.b_datatype.general_enum import LogType

class LogManager(QObject):
    _instance = None
    _creation_mutex = QMutex()

    def __new__(cls, *args, **kwargs):
        # 멀티스레드 환경에서 동시에 생성되는 것을 방지 (Thread-Safe Singleton)
        with QMutexLocker(cls._creation_mutex):
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
        return cls._instance

    def __init__(self, parent=None):
        # QObject.__init__ 중복 호출 방어
        if self._initialized:
            return

        super().__init__(parent)
        self._initialized = True

        # 초기화 로직 (여기서 한 번만 실행됨)
        self._max_size = 1000
        self._log_queue = deque(maxlen=self._max_size)
        self._queue_mutex = QMutex()  # 내부 큐 접근 제어용 락도 QMutex로 통일
        
        print(f"LogManager Initialized (Ring Buffer size: {self._max_size})")

    def log(self, msg_type: LogType, message: str):
        """
        로그를 큐에 추가. maxlen을 초과하면 가장 오래된 로그가 자동 삭제됨.
        """
        print(f"{message}")

        with QMutexLocker(self._queue_mutex):
            self._log_queue.append((msg_type, message))

    def get_all_logs(self):
        """
        현재 쌓여있는 모든 로그를 가져오고 큐를 비웁니다.
        """
        with QMutexLocker(self._queue_mutex):
            if not self._log_queue:
                return []
            
            # 현재까지 쌓인 것들을 리스트로 복사 후 비우기
            logs = list(self._log_queue)
            self._log_queue.clear()
            return logs