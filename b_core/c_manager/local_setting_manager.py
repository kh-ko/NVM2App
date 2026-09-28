"""로컬 설정(local_setting.json) 관리자.

장비(param)가 아니라 이 PC 의 앱에만 저장되는 사용자 설정을 관리한다.
(압력 단위, 소수점 자리수, setpoint 버튼 값, 차트 표시 설정 등)

설정 항목 추가는 두 줄이면 된다:
    sig_<설정명>_changed = Signal()     # 1. 시그널 선언
    <설정명> = _Setting(기본값)         # 2. 설정 선언
_Setting 디스크립터가 [property + 변경 검사 + 저장 + 시그널 발화 + load/save 키]
를 전부 담당한다. 시그널 선언이 누락되면 클래스 생성 시점에 TypeError 로
즉시 검출된다. (ver1 은 항목당 5곳을 수정해야 해서 누락 잠복 버그 위험이 있었음)

- 값 변경 시마다 전체 설정이 local_setting.json 에 저장된다(임시 파일 + os.replace 원자 교체).
  저장 실패는 로그만 남기고 메모리 값·시그널은 유지한다(화면과 메모리는 일치, 파일만 뒤처짐).
- 로드 시 파일이 깨졌으면 '.corrupt-일시' 로 보관하고 기본값으로, 항목 값의 종류가
  기본값과 다르면(bool/int/float 구분, int→float 허용) 그 항목만 기본값으로 둔다.
- setter 는 UI 스레드 전용이다. (락 없음 — 워커 스레드에서 호출 금지)
- 최초 로드는 시그널을 발화하지 않는다. 컨트롤은 생성 시 property 를
  직접 읽어 초기값을 잡아야 한다.
"""

import threading

from PySide6.QtCore import Signal, QObject

from b_core.a_define import file_folder_path as path_def
from b_core.c_manager.app_log_manager import AppLogManager
from b_core.f_helper.json_file_helper import JsonLoadError, load_json, save_json_atomic, quarantine_corrupt

from b_core.b_datatype import param_enum as p_enum


class _Setting:
    """LocalSettingManager 전용 설정 디스크립터.

    값은 인스턴스의 _<설정명> 속성에 저장되고, 변경되면
    [_save_settings() 호출 -> sig_<설정명>_changed 발화] 를 수행한다.
    기본값은 bool/int/float 리터럴로 둔다(Enum 은 .value, None 금지) — 로드 시 종류 검사의 기준."""

    def __init__(self, default):
        self.default = default
        self.name = ""

    def __set_name__(self, owner, name):
        self.name = name

        # 시그널 선언 누락을 클래스 생성 시점에 검출
        if not hasattr(owner, f"sig_{name}_changed"):
            raise TypeError(f"LocalSettingManager: sig_{name}_changed 시그널 선언이 없습니다")

        owner._settings[name] = self  # load/save 자동화용 레지스트리 등록

    def __get__(self, obj, objtype=None):
        if obj is None:
            return self
        return getattr(obj, "_" + self.name, self.default)

    def __set__(self, obj, value):
        if getattr(obj, "_" + self.name, self.default) == value:
            return

        setattr(obj, "_" + self.name, value)
        obj._save_settings()
        getattr(obj, f"sig_{self.name}_changed").emit()


class LocalSettingManager(QObject):
    _instance = None
    _creation_lock = threading.Lock()

    # ------------------------------------------------------------ 시그널
    sig_pres_unit_changed = Signal()
    sig_posi_decimal_places_changed = Signal()
    sig_pres_decimal_places_changed = Signal()
    sig_posi_setpoint01_changed = Signal()
    sig_posi_setpoint02_changed = Signal()
    sig_posi_setpoint03_changed = Signal()
    sig_posi_setpoint04_changed = Signal()
    sig_posi_setpoint05_changed = Signal()
    sig_posi_setpoint06_changed = Signal()
    sig_pres_setpoint01_changed = Signal()
    sig_pres_setpoint02_changed = Signal()
    sig_pres_setpoint03_changed = Signal()
    sig_pres_setpoint04_changed = Signal()
    sig_pres_setpoint05_changed = Signal()
    sig_pres_setpoint06_changed = Signal()

    sig_posi_chart_enable_actual_changed = Signal()
    sig_posi_chart_enable_target_changed = Signal()
    sig_posi_chart_range_mode_changed = Signal()
    sig_posi_chart_range_custom_min_changed = Signal()
    sig_posi_chart_range_custom_max_changed = Signal()
    sig_pres_chart_enable_actual_changed = Signal()
    sig_pres_chart_enable_target_changed = Signal()
    sig_pres_chart_range_mode_changed = Signal()
    sig_pres_chart_range_custom_min_changed = Signal()
    sig_pres_chart_range_custom_max_changed = Signal()
    sig_chart_x_window_sec_changed = Signal()

    # ------------------------------------------------------------ 설정 선언
    _settings: dict = {}  # _Setting.__set_name__ 이 채우는 레지스트리 (직접 수정 금지)

    pres_unit = _Setting(p_enum.SensUnitEnum.TORR.value)
    posi_decimal_places = _Setting(2)
    pres_decimal_places = _Setting(3)

    posi_setpoint01 = _Setting(1.0)
    posi_setpoint02 = _Setting(0.9)
    posi_setpoint03 = _Setting(0.8)
    posi_setpoint04 = _Setting(0.7)
    posi_setpoint05 = _Setting(0.6)
    posi_setpoint06 = _Setting(0.5)
    pres_setpoint01 = _Setting(1.0)
    pres_setpoint02 = _Setting(0.9)
    pres_setpoint03 = _Setting(0.8)
    pres_setpoint04 = _Setting(0.7)
    pres_setpoint05 = _Setting(0.6)
    pres_setpoint06 = _Setting(0.5)

    posi_chart_enable_actual = _Setting(True)
    posi_chart_enable_target = _Setting(True)
    posi_chart_range_mode = _Setting(1)  # 0: Auto, 1: Full, 2: Custom
    posi_chart_range_custom_min = _Setting(0.0)
    posi_chart_range_custom_max = _Setting(100.0)
    pres_chart_enable_actual = _Setting(True)
    pres_chart_enable_target = _Setting(True)
    pres_chart_range_mode = _Setting(1)  # 0: Auto, 1: Full, 2: Custom
    pres_chart_range_custom_min = _Setting(0.0)
    pres_chart_range_custom_max = _Setting(100.0)
    chart_x_window_sec = _Setting(60)    # X축 시간창(초) — 30/60/120/300/600

    # ------------------------------------------------------------ 생성/초기화
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

        self._log = AppLogManager().get_logger("LocalSettingManager", is_global=True)

        # 기본값으로 초기화한 뒤 파일 값으로 덮어쓴다
        for name, setting in self._settings.items():
            setattr(self, "_" + name, setting.default)

        self._load_settings()

    # ------------------------------------------------------------ 파일 IO
    def _load_settings(self):
        """JSON 파일에서 설정값을 읽어온다. (없는 키·종류가 다른 값은 기본값 유지, 시그널 미발화)"""
        try:
            data = load_json(path_def.RSRC_LOCAL_SETTING_JSON_FILE, expect=dict)
        except JsonLoadError as e:
            moved = quarantine_corrupt(path_def.RSRC_LOCAL_SETTING_JSON_FILE)
            kept = f"손상 파일은 {moved} 로 보관" if moved else "손상 파일 보관 실패(다음 저장이 덮어씀)"
            self._log.error(f"local_setting.json 로드 실패 — 기본값 사용, {kept}: {e}")
            return
        if data is None:
            return

        for name, setting in self._settings.items():
            if name not in data:
                continue
            value = data[name]
            if not _is_same_kind(value, setting.default):
                self._log.warning(f"local_setting.json '{name}' 값 형식이 맞지 않아 기본값 사용: {value!r}")
                continue
            if isinstance(setting.default, float):
                value = float(value)  # int 로 적힌 값도 메모리·다음 저장에서는 float
            # 디스크립터를 거치지 않고 직접 저장 (로드 중 저장/시그널 발화 방지)
            setattr(self, "_" + name, value)

    def _save_settings(self) -> bool:
        """현재 모든 설정값을 JSON 파일로 저장한다. 실패해도 메모리 값·시그널은 유지된다."""
        try:
            save_data = {name: getattr(self, "_" + name) for name in self._settings}
            save_json_atomic(path_def.RSRC_LOCAL_SETTING_JSON_FILE, save_data)
            return True
        except Exception as e:
            self._log.error(f"local_setting.json 저장 실패 (메모리 값은 유지): {e}")
            return False


def _is_same_kind(value, default) -> bool:
    """기본값과 같은 종류인지 — bool/int/float 를 구분하고 int → float 만 허용한다."""
    if isinstance(default, bool):
        return isinstance(value, bool)
    if isinstance(default, int):
        return isinstance(value, int) and not isinstance(value, bool)
    if isinstance(default, float):
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    return isinstance(value, type(default))
