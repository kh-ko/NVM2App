
import os
import json
import threading

from typing import Union, List, Dict, Optional
from PySide6.QtCore import QFile, QIODevice

from b_core.a_define import file_folder_path as path_def
from b_core.b_datatype import param_enum as p_enum
from b_core.b_datatype.general_enum import LogType, ParamDataType, ParamAccType, ParamDisplayType, PARAM_DISPLAY_TYPE_MAP
from b_core.c_manager.log_manager import LogManager
from b_core.b_datatype.parameter import Parameter


class ParamManager:
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

        self._initialized = True
        self._init_manager()     

    def _init_manager(self):
        self._param_map: Dict[tuple, Parameter] = {}  # (path, name) 검색용
        self._parameters: List[Parameter] = []         # 전체 리스트 보관용

        if os.path.exists(path_def.RSRC_PARAM_SCHEMA_JSON_FILE):
            try:
                with open(path_def.RSRC_PARAM_SCHEMA_JSON_FILE, 'r', encoding='utf-8') as f:
                    param_list = json.load(f)
            except Exception as e:
                print(f"[ParamManager] 로드 실패: {e}")

        for param in param_list:
            param_type = param.get("type", "")

            display_type = PARAM_DISPLAY_TYPE_MAP.get(param_type)
            self._add_param(param, display_type)

    def _add_param(self, param_json, param_display_type: ParamDisplayType):
        param = Parameter(param_json, param_display_type)
        self._parameters.append(param)
        self._param_map[(param.path, param.name)] = param

    def get_by_full_path(self, full_path: str) -> Optional[Parameter]:
        path, name = full_path.rsplit(".", 1)
        ret_param = self._param_map.get((path, name))
        if ret_param is None:
            LogManager().log(LogType.ERROR, f"[ParameterManager] 파라미터를 찾을 수 없습니다: {full_path}")
        return ret_param

    def get(self, path: str, name: str) -> Optional[Parameter]:
        ret_param = self._param_map.get((path, name))
        if ret_param is None:
            LogManager().log(LogType.ERROR, f"[ParameterManager] 파라미터를 찾을 수 없습니다: {path}, {name}")
        return ret_param

    def get_params_in_folder(self, folder_path: str) -> List[Parameter]:
        ret_params: List[Parameter] = []
        for param in self._parameters:
            if param.path == folder_path:
                ret_params.append(param)
        return ret_params

    def get_all(self) -> List[Parameter]:
        """전체 파라미터 리스트를 가져옵니다."""
        return self._parameters
        
