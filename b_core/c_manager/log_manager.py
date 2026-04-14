import threading

from collections import deque
from PySide6.QtCore import QObject

from b_core.b_datatype.general_enum import LogType

class LogManager(QObject):
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            with cls._lock:
                if not cls._instance:
                    cls._instance = super().__new__(cls)
                    super(LogManager, cls._instance).__init__()
                    cls._instance._init_manager()
        return cls._instance

    def _init_manager(self):
        # 최대 1000개까지만 보관하는 링 버퍼 생성
        self._max_size = 1000
        self._log_queue = deque(maxlen=self._max_size)
        self._queue_lock = threading.Lock()  # 큐 접근 제어용 락
        print(f"LogManager Initialized (Ring Buffer size: {self._max_size})")

    def log(self, msg_type: LogType, message: str):
        """
        로그를 큐에 추가. maxlen을 초과하면 가장 오래된 로그가 자동 삭제됨.
        """
        print(f"{message}")

        with self._queue_lock:
            self._log_queue.append((msg_type, message))

    def get_all_logs(self):
        """
        현재 쌓여있는 모든 로그를 가져오고 큐를 비웁니다.
        """
        with self._queue_lock:
            if not self._log_queue:
                return []
            
            # 현재까지 쌓인 것들을 리스트로 복사 후 비우기
            logs = list(self._log_queue)
            self._log_queue.clear()
            return logs