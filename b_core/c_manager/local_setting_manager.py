import threading
import json
import os

from PySide6.QtCore import Signal, QObject

from b_core.a_define import file_folder_path as path_def

from b_core.b_datatype import param_enum as p_enum

class LocalSettingManager(QObject):
    _instance = None
    _creation_lock = threading.Lock()

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
        self._posi_decimal_places = 2
        self._pres_decimal_places = 3
        
        self._posi_setpoint01 = 1.0
        self._posi_setpoint02 = 0.9
        self._posi_setpoint03 = 0.8
        self._posi_setpoint04 = 0.7
        self._posi_setpoint05 = 0.6
        self._posi_setpoint06 = 0.5
        self._pres_setpoint01 = 1.0
        self._pres_setpoint02 = 0.9
        self._pres_setpoint03 = 0.8
        self._pres_setpoint04 = 0.7
        self._pres_setpoint05 = 0.6
        self._pres_setpoint06 = 0.5

        self._posi_chart_enable_actual = True
        self._posi_chart_enable_target = True
        self._posi_chart_range_mode = 1 # 0: Auto, 1: Full, 2: Custom
        self._posi_chart_range_custom_min = 0.0
        self._posi_chart_range_custom_max = 100.0
        self._pres_chart_enable_actual = True
        self._pres_chart_enable_target = True
        self._pres_chart_range_mode = 1 # 0: Auto, 1: Full, 2: Custom
        self._pres_chart_range_custom_min = 0.0
        self._pres_chart_range_custom_max = 100.0

        self._load_settings()

    @property
    def pres_unit(self) -> int:
        return self._pres_unit    

    @pres_unit.setter
    def pres_unit(self, new_val: int):
        if self._pres_unit != new_val:
            self._pres_unit = new_val
            self._save_settings()
            self.sig_pres_unit_changed.emit()
            
    @property
    def posi_decimal_places(self) -> int:
        return self._posi_decimal_places

    @posi_decimal_places.setter
    def posi_decimal_places(self, new_val: int):
        if self._posi_decimal_places != new_val:
            self._posi_decimal_places = new_val
            self._save_settings()
            self.sig_posi_decimal_places_changed.emit()

    @property
    def pres_decimal_places(self) -> int:
        return self._pres_decimal_places

    @pres_decimal_places.setter
    def pres_decimal_places(self, new_val: int):
        if self._pres_decimal_places != new_val:
            self._pres_decimal_places = new_val
            self._save_settings()
            self.sig_pres_decimal_places_changed.emit()
   

    @property
    def posi_setpoint01(self) -> float:
        return self._posi_setpoint01

    @posi_setpoint01.setter
    def posi_setpoint01(self, new_val: float):
        if self._posi_setpoint01 != new_val:
            self._posi_setpoint01 = new_val
            self._save_settings()
            self.sig_posi_setpoint01_changed.emit()

    @property
    def posi_setpoint02(self) -> float:
        return self._posi_setpoint02

    @posi_setpoint02.setter
    def posi_setpoint02(self, new_val: float):
        if self._posi_setpoint02 != new_val:
            self._posi_setpoint02 = new_val
            self._save_settings()
            self.sig_posi_setpoint02_changed.emit()

    @property
    def posi_setpoint03(self) -> float:
        return self._posi_setpoint03

    @posi_setpoint03.setter
    def posi_setpoint03(self, new_val: float):
        if self._posi_setpoint03 != new_val:
            self._posi_setpoint03 = new_val
            self._save_settings()
            self.sig_posi_setpoint03_changed.emit()

    @property
    def posi_setpoint04(self) -> float:
        return self._posi_setpoint04

    @posi_setpoint04.setter
    def posi_setpoint04(self, new_val: float):
        if self._posi_setpoint04 != new_val:
            self._posi_setpoint04 = new_val
            self._save_settings()
            self.sig_posi_setpoint04_changed.emit()

    @property
    def posi_setpoint05(self) -> float:
        return self._posi_setpoint05

    @posi_setpoint05.setter
    def posi_setpoint05(self, new_val: float):
        if self._posi_setpoint05 != new_val:
            self._posi_setpoint05 = new_val
            self._save_settings()
            self.sig_posi_setpoint05_changed.emit()

    @property
    def posi_setpoint06(self) -> float:
        return self._posi_setpoint06

    @posi_setpoint06.setter
    def posi_setpoint06(self, new_val: float):
        if self._posi_setpoint06 != new_val:
            self._posi_setpoint06 = new_val
            self._save_settings()
            self.sig_posi_setpoint06_changed.emit()

    @property
    def pres_setpoint01(self) -> float:
        return self._pres_setpoint01

    @pres_setpoint01.setter
    def pres_setpoint01(self, new_val: float):
        if self._pres_setpoint01 != new_val:
            self._pres_setpoint01 = new_val
            self._save_settings()
            self.sig_pres_setpoint01_changed.emit()

    @property
    def pres_setpoint02(self) -> float:
        return self._pres_setpoint02

    @pres_setpoint02.setter
    def pres_setpoint02(self, new_val: float):
        if self._pres_setpoint02 != new_val:
            self._pres_setpoint02 = new_val
            self._save_settings()
            self.sig_pres_setpoint02_changed.emit()

    @property
    def pres_setpoint03(self) -> float:
        return self._pres_setpoint03

    @pres_setpoint03.setter
    def pres_setpoint03(self, new_val: float):
        if self._pres_setpoint03 != new_val:
            self._pres_setpoint03 = new_val
            self._save_settings()
            self.sig_pres_setpoint03_changed.emit()

    @property
    def pres_setpoint04(self) -> float:
        return self._pres_setpoint04

    @pres_setpoint04.setter
    def pres_setpoint04(self, new_val: float):
        if self._pres_setpoint04 != new_val:
            self._pres_setpoint04 = new_val
            self._save_settings()
            self.sig_pres_setpoint04_changed.emit()

    @property
    def pres_setpoint05(self) -> float:
        return self._pres_setpoint05

    @pres_setpoint05.setter
    def pres_setpoint05(self, new_val: float):
        if self._pres_setpoint05 != new_val:
            self._pres_setpoint05 = new_val
            self._save_settings()
            self.sig_pres_setpoint05_changed.emit()

    @property
    def pres_setpoint06(self) -> float:
        return self._pres_setpoint06

    @pres_setpoint06.setter
    def pres_setpoint06(self, new_val: float):
        if self._pres_setpoint06 != new_val:
            self._pres_setpoint06 = new_val
            self._save_settings()
            self.sig_pres_setpoint06_changed.emit()

    @property
    def posi_chart_enable_actual(self) -> bool:
        return self._posi_chart_enable_actual

    @posi_chart_enable_actual.setter
    def posi_chart_enable_actual(self, new_val: bool):
        if self._posi_chart_enable_actual != new_val:
            self._posi_chart_enable_actual = new_val
            self._save_settings()
            self.sig_posi_chart_enable_actual_changed.emit()

    @property
    def posi_chart_enable_target(self) -> bool:
        return self._posi_chart_enable_target

    @posi_chart_enable_target.setter
    def posi_chart_enable_target(self, new_val: bool):
        if self._posi_chart_enable_target != new_val:
            self._posi_chart_enable_target = new_val
            self._save_settings()
            self.sig_posi_chart_enable_target_changed.emit()

    @property
    def posi_chart_range_mode(self) -> int:
        return self._posi_chart_range_mode

    @posi_chart_range_mode.setter
    def posi_chart_range_mode(self, new_val: int):
        if self._posi_chart_range_mode != new_val:
            self._posi_chart_range_mode = new_val
            self._save_settings()
            self.sig_posi_chart_range_mode_changed.emit()

    @property
    def posi_chart_range_custom_min(self) -> float:
        return self._posi_chart_range_custom_min

    @posi_chart_range_custom_min.setter
    def posi_chart_range_custom_min(self, new_val: float):
        if self._posi_chart_range_custom_min != new_val:
            self._posi_chart_range_custom_min = new_val
            self._save_settings()
            self.sig_posi_chart_range_custom_min_changed.emit()

    @property
    def posi_chart_range_custom_max(self) -> float:
        return self._posi_chart_range_custom_max

    @posi_chart_range_custom_max.setter
    def posi_chart_range_custom_max(self, new_val: float):
        if self._posi_chart_range_custom_max != new_val:
            self._posi_chart_range_custom_max = new_val
            self._save_settings()
            self.sig_posi_chart_range_custom_max_changed.emit()

    @property
    def pres_chart_enable_actual(self) -> bool:
        return self._pres_chart_enable_actual

    @pres_chart_enable_actual.setter
    def pres_chart_enable_actual(self, new_val: bool):
        if self._pres_chart_enable_actual != new_val:
            self._pres_chart_enable_actual = new_val
            self._save_settings()
            self.sig_pres_chart_enable_actual_changed.emit()

    @property
    def pres_chart_enable_target(self) -> bool:
        return self._pres_chart_enable_target

    @pres_chart_enable_target.setter
    def pres_chart_enable_target(self, new_val: bool):
        if self._pres_chart_enable_target != new_val:
            self._pres_chart_enable_target = new_val
            self._save_settings()
            self.sig_pres_chart_enable_target_changed.emit()

    @property
    def pres_chart_range_mode(self) -> int:
        return self._pres_chart_range_mode

    @pres_chart_range_mode.setter
    def pres_chart_range_mode(self, new_val: int):
        if self._pres_chart_range_mode != new_val:
            self._pres_chart_range_mode = new_val
            self._save_settings()
            self.sig_pres_chart_range_mode_changed.emit()

    @property
    def pres_chart_range_custom_min(self) -> float:
        return self._pres_chart_range_custom_min

    @pres_chart_range_custom_min.setter
    def pres_chart_range_custom_min(self, new_val: float):
        if self._pres_chart_range_custom_min != new_val:
            self._pres_chart_range_custom_min = new_val
            self._save_settings()
            self.sig_pres_chart_range_custom_min_changed.emit()

    @property
    def pres_chart_range_custom_max(self) -> float:
        return self._pres_chart_range_custom_max

    @pres_chart_range_custom_max.setter
    def pres_chart_range_custom_max(self, new_val: float):
        if self._pres_chart_range_custom_max != new_val:
            self._pres_chart_range_custom_max = new_val
            self._save_settings()
            self.sig_pres_chart_range_custom_max_changed.emit()

    def _load_settings(self):
        """JSON 파일로부터 설정값을 읽어옵니다."""
        # RSRC_LOCAL_SETTING_JSON_FILE 경로가 존재하는지 확인
        if os.path.exists(path_def.RSRC_LOCAL_SETTING_JSON_FILE):
            try:
                with open(path_def.RSRC_LOCAL_SETTING_JSON_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # 파일에 해당 키가 있으면 할당, 없으면 기본값 유지
                    self._pres_unit                   = data.get("pres_unit", self._pres_unit)
                    self._posi_decimal_places         = data.get("posi_decimal_places", self._posi_decimal_places)
                    self._pres_decimal_places         = data.get("pres_decimal_places", self._pres_decimal_places)
                    self._posi_setpoint01             = data.get("posi_setpoint01", self._posi_setpoint01)
                    self._posi_setpoint02             = data.get("posi_setpoint02", self._posi_setpoint02)
                    self._posi_setpoint03             = data.get("posi_setpoint03", self._posi_setpoint03)
                    self._posi_setpoint04             = data.get("posi_setpoint04", self._posi_setpoint04)
                    self._posi_setpoint05             = data.get("posi_setpoint05", self._posi_setpoint05)
                    self._posi_setpoint06             = data.get("posi_setpoint06", self._posi_setpoint06)
                    self._pres_setpoint01             = data.get("pres_setpoint01", self._pres_setpoint01)
                    self._pres_setpoint02             = data.get("pres_setpoint02", self._pres_setpoint02)
                    self._pres_setpoint03             = data.get("pres_setpoint03", self._pres_setpoint03)
                    self._pres_setpoint04             = data.get("pres_setpoint04", self._pres_setpoint04)
                    self._pres_setpoint05             = data.get("pres_setpoint05", self._pres_setpoint05)
                    self._pres_setpoint06             = data.get("pres_setpoint06", self._pres_setpoint06)
                    self._posi_chart_enable_actual    = data.get("posi_chart_enable_actual", self._posi_chart_enable_actual)
                    self._posi_chart_enable_target    = data.get("posi_chart_enable_target", self._posi_chart_enable_target)
                    self._posi_chart_range_mode       = data.get("posi_chart_range_mode", self._posi_chart_range_mode)
                    self._posi_chart_range_custom_min = data.get("posi_chart_range_custom_min", self._posi_chart_range_custom_min)
                    self._posi_chart_range_custom_max = data.get("posi_chart_range_custom_max", self._posi_chart_range_custom_max)
                    self._pres_chart_enable_actual    = data.get("pres_chart_enable_actual", self._pres_chart_enable_actual)
                    self._pres_chart_enable_target    = data.get("pres_chart_enable_target", self._pres_chart_enable_target)
                    self._pres_chart_range_mode       = data.get("pres_chart_range_mode", self._pres_chart_range_mode)
                    self._pres_chart_range_custom_min = data.get("pres_chart_range_custom_min", self._pres_chart_range_custom_min)
                    self._pres_chart_range_custom_max = data.get("pres_chart_range_custom_max", self._pres_chart_range_custom_max)
            except Exception as e:
                print(f"[LocalSettingManager] 로드 실패: {e}")

    def _save_settings(self):
        """현재 모든 설정값을 JSON 파일로 저장합니다."""
        try:
            # 저장할 데이터 구성 (설정값이 늘어나면 여기에 추가)
            save_data = {
                "pres_unit"                   : self._pres_unit,
                "posi_decimal_places"         : self._posi_decimal_places,
                "pres_decimal_places"         : self._pres_decimal_places,
                "posi_setpoint01"             : self._posi_setpoint01,
                "posi_setpoint02"             : self._posi_setpoint02,
                "posi_setpoint03"             : self._posi_setpoint03,
                "posi_setpoint04"             : self._posi_setpoint04,
                "posi_setpoint05"             : self._posi_setpoint05,
                "posi_setpoint06"             : self._posi_setpoint06,
                "pres_setpoint01"             : self._pres_setpoint01,
                "pres_setpoint02"             : self._pres_setpoint02,
                "pres_setpoint03"             : self._pres_setpoint03,
                "pres_setpoint04"             : self._pres_setpoint04,
                "pres_setpoint05"             : self._pres_setpoint05,
                "pres_setpoint06"             : self._pres_setpoint06,
                "posi_chart_enable_actual"    : self._posi_chart_enable_actual,
                "posi_chart_enable_target"    : self._posi_chart_enable_target,
                "posi_chart_range_mode"       : self._posi_chart_range_mode,
                "posi_chart_range_custom_min" : self._posi_chart_range_custom_min,
                "posi_chart_range_custom_max" : self._posi_chart_range_custom_max,
                "pres_chart_enable_actual"    : self._pres_chart_enable_actual,
                "pres_chart_enable_target"    : self._pres_chart_enable_target,
                "pres_chart_range_mode"       : self._pres_chart_range_mode,
                "pres_chart_range_custom_min" : self._pres_chart_range_custom_min,
                "pres_chart_range_custom_max" : self._pres_chart_range_custom_max,
            }

            # 폴더가 없으면 생성
            os.makedirs(os.path.dirname(path_def.RSRC_LOCAL_SETTING_JSON_FILE), exist_ok=True)

            with open(path_def.RSRC_LOCAL_SETTING_JSON_FILE, 'w', encoding='utf-8') as f:
                json.dump(save_data, f, indent=4)
        except Exception as e:
            print(f"[LocalSettingManager] 저장 실패: {e}")
