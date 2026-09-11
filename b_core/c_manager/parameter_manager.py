
import os
import json
import threading

from typing import Union, List, Dict, Optional

from b_core.a_define import file_folder_path as path_def
from b_core.b_datatype.general_enum import ParamDisplayType, PARAM_DISPLAY_TYPE_MAP
from b_core.c_manager.app_log_manager import AppLogManager
from b_core.b_datatype.parameter import Parameter
from b_core.g_protocol import spec_loader
from b_core.g_protocol.spec_registry import SpecRegistry


class ParamManager:
    """Parameter 저장소 (싱글턴).

    로드 순서 (2026-09-11 PacketSpec 도입 1단계):
      1. params.json   -> Parameter 생성 (값 정의만, 전송 정보 없음)
      2. nv2_spec.json -> SpecRegistry 에 param 별 NV2 읽기/쓰기 spec 등록
      3. (NV1 단계) nv1_spec.json
      4. 검증: 어느 스펙에도 없는 param 은 오류 로그 + Not Support (결정 9)
    창은 지금처럼 get_by_full_path() 로 찾을 뿐 프로토콜을 모른다. spec 이
    필요한 쪽(워커, 백업/복원 창, Compound)은 SpecRegistry() 에서 param 으로 찾는다."""

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
        self._log = AppLogManager().get_logger("ParamManager", is_global=True)
        self._param_map: Dict[tuple, Parameter] = {}  # (path, name) 검색용
        self._parameters: List[Parameter] = []         # 전체 리스트 보관용
        self._spec_registry = SpecRegistry()

        # 스키마 파일이 없거나 로드에 실패해도 빈 목록으로 기동한다
        # (param 을 못 찾는 오류는 이후 get 계열 호출에서 개별 로그로 남음)
        param_list = []

        if os.path.exists(path_def.RSRC_PARAMS_JSON_FILE):
            try:
                with open(path_def.RSRC_PARAMS_JSON_FILE, 'r', encoding='utf-8') as f:
                    param_list = json.load(f)
            except Exception as e:
                self._log.error(f"params 스키마 로드 실패: {e}")
        else:
            self._log.error(f"params 스키마 파일 없음: {path_def.RSRC_PARAMS_JSON_FILE}")

        for param in param_list:
            param_type = param.get("type", "")

            display_type = PARAM_DISPLAY_TYPE_MAP.get(param_type)
            self._add_param(param, display_type)

        # 전송 규약 부착 — 경로 조회는 오류 로그 없이 (누락은 로더가 자기 문구로 기록)
        count = spec_loader.load_nv2_specs(path_def.RSRC_NV2_SPEC_JSON_FILE,
                                           self._find_quiet, self._spec_registry)
        missing = spec_loader.validate_specs(self._parameters, self._spec_registry)
        self._log.info(f"params {len(self._parameters)} / nv2 spec {count} / spec 없음 {missing}")

    def _add_param(self, param_json, param_display_type: ParamDisplayType):
        param = Parameter(param_json, param_display_type)
        self._parameters.append(param)
        self._param_map[(param.path, param.name)] = param

    def _find_quiet(self, full_path: str) -> Optional[Parameter]:
        path, sep, name = full_path.rpartition(".")
        if not sep:
            return None
        return self._param_map.get((path, name))

    def get_param_list(self):
        return self._parameters

    def get_by_full_path(self, full_path: str) -> Optional[Parameter]:
        path, name = full_path.rsplit(".", 1)
        ret_param = self._param_map.get((path, name))
        if ret_param is None:
            self._log.error(f"파라미터를 찾을 수 없습니다: {full_path}")
        return ret_param

    def get(self, path: str, name: str) -> Optional[Parameter]:
        ret_param = self._param_map.get((path, name))
        if ret_param is None:
            self._log.error(f"파라미터를 찾을 수 없습니다: {path}, {name}")
        return ret_param

    def get_all_folder_paths(self, root_path: str = "") -> List[str]:
        """root_path 하위(자신 포함)에서 파라미터를 직접 담고 있는 폴더 경로 목록.

        폴더는 스키마에 별도 노드가 없고 param.path 로만 존재하므로,
        파라미터가 직접 속한 path 의 중복 제거 목록이 곧 폴더 목록이다
        (파라미터 없이 하위 폴더만 가진 중간 폴더는 나오지 않는다).
        순서는 스키마(json) 등장 순서를 따른다. root_path 가 빈 문자열이면
        전체 폴더를 반환한다.
        """
        prefix = root_path + "." if root_path else ""
        seen = set()
        folder_paths: List[str] = []

        for param in self._parameters:
            if param.path in seen:
                continue
            # root 자신이거나 root 의 하위 경로만 통과 ("System" 이 "SystemX" 에 걸리지 않도록)
            if root_path and param.path != root_path and not param.path.startswith(prefix):
                continue
            seen.add(param.path)
            folder_paths.append(param.path)

        return folder_paths

    def get_params_grouped(self, root_path: str = "",
                           filter_param_paths: Optional[List[str]] = None) -> Dict[str, List[Parameter]]:
        """root_path 하위의 폴더별 param 목록을 한 번의 순회로 그룹핑해 반환.

        [get_all_folder_paths() + 폴더별 get_params_in_folder() 반복] 은
        O(폴더수 x 전체 param) 이라 넓은 경로에서 창 생성이 느려진다 — 이 API 는
        전체 param 을 1회만 훑는다. 폴더/param 순서는 스키마(json) 등장 순서
        (dict 삽입 순서) 그대로다. filter_param_paths 는 full path 제외 목록."""
        prefix = root_path + "." if root_path else ""
        filter_set = set(filter_param_paths) if filter_param_paths else None
        grouped: Dict[str, List[Parameter]] = {}

        for param in self._parameters:
            # root 자신이거나 root 의 하위 경로만 통과 (get_all_folder_paths 와 동일 규칙)
            if root_path and param.path != root_path and not param.path.startswith(prefix):
                continue
            if filter_set is not None and f"{param.path}.{param.name}" in filter_set:
                continue
            grouped.setdefault(param.path, []).append(param)

        return grouped

    def get_params_in_folder(self, folder_path: str, filter_param_paths: Optional[List[str]] = None) -> List[Parameter]:
        ret_params: List[Parameter] = []
        for param in self._parameters:
            if param.path == folder_path:
                param_full_path = f"{folder_path}.{param.name}"
                if filter_param_paths is not None and param_full_path in filter_param_paths:
                    continue
                ret_params.append(param)
        return ret_params

    def get_all(self) -> List[Parameter]:
        """전체 파라미터 리스트를 가져옵니다."""
        return self._parameters
