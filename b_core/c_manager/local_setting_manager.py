import threading
import math

from PySide6.QtCore import Signal, QObject

from b_core.b_datatype import param_enum as p_enum

class LocalSettingManager(QObject):
    _instance = None
    _creation_lock = threading.Lock()

    sig_pres_unit_changed = Signal()

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

        self._pres_unit = p_enum.SensUnitEnum.TORR.value

    @property
    def pres_unit(self) -> int:
        return self._pres_unit

    @pres_unit.setter
    def pres_unit(self, new_val: int):
        if self._pres_unit != new_val:
            self._pres_unit = new_val
            self.sig_pres_unit_changed.emit()
