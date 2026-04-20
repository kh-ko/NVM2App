import json
import threading

from typing import Union, List, Dict, Optional
from PySide6.QtCore import QFile, QIODevice, QObject, Signal  # QObject, Signal 임포트 추가

from b_core.a_define import file_folder_path as path_def
from b_core.b_datatype import param_enum as p_enum
from b_core.b_datatype.general_enum import LogType, ParamDataType, ParamAccType, ParamDisplayType
from b_core.c_manager.log_manager import LogManager
from b_core.b_datatype.parameter_digi import ParameterDigi
from b_core.b_datatype.parameter import Parameter


# 전역 변수 관리자
class GvManager(QObject):
    _instance = None
    _creation_lock = threading.Lock()

    serial_number_changed = Signal(str)
    
    @property
    def serial_number(self) -> str:
        with self._data_lock:
            return self._serial_number

    @serial_number.setter
    def serial_number(self, value: str):
        with self._data_lock:
            if self._serial_number != value:
                self._serial_number = value
                self.serial_number_changed.emit(value)                

    def __new__(cls, *args, **kwargs):
        with cls._creation_lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
        return cls._instance

    def __init__(self, parent=None):
        if self._initialized:
            return

        super().__init__(parent)

        self._initialized = True
        
        self._data_lock = threading.Lock()
        self._serial_number = "-"
        
        self._init_manager()

    def _init_manager(self):
        pass

