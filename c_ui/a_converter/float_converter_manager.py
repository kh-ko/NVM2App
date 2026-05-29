import threading

from decimal import Decimal
from PySide6.QtCore import QObject

class FloatConverterManager(QObject):
    _instance = None
    _creation_lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        # 멀티스레드 환경에서 동시에 생성되는 것을 방지
        with cls._creation_lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        # 중복 초기화 방어
        if self._initialized:
            return
        super().__init__()
        self._initialized = True

    def to_str(self, ori_value: float) -> str:
        if ori_value is None:
            return None

        try:
            s = f"{ori_value:.6g}"
            str_value = f"{Decimal(s):f}" if 'e' in s else s
            return str_value
        except Exception:
            return None

    def to_str_with_decimal_places(self, ori_value: float, decimal_places: int) -> str | None:
        if ori_value is None:
            return None

        try:
            str_value = f"{ori_value:.{decimal_places}f}"
            return str_value
        except Exception:
            return None
