import threading
import math

from decimal import Decimal

from PySide6.QtCore import Signal, QObject

from b_core.b_datatype import param_enum as p_enum
from b_core.c_manager.parameter_manager import ParamManager
from b_core.c_manager.local_setting_manager import LocalSettingManager


# 압력을 나타내는 단위는 3가지 이다.
# 1. 통신에서 사용하는 압력 단위
# 2. GUI 표시할 압력 단위
# 3. Full Scale값으로 압력 표시 단위( 0.0 ~ 1.0 : 1.0일때 압력센서의 Max값이 된다.)

class PresConverterManager(QObject):
    _instance = None
    _creation_lock = threading.Lock()

    sig_pres_range_changed = Signal()

    PA_FACTORS = {
        p_enum.SensUnitEnum.PA.value: 1.0,            # Pa
        p_enum.SensUnitEnum.KPA.value: 1000.0,         # kPa
        p_enum.SensUnitEnum.BAR.value: 100000.0,       # bar
        p_enum.SensUnitEnum.MBAR.value: 100.0,          # mbar
        p_enum.SensUnitEnum.TORR.value: 133.322368,     # Torr
        p_enum.SensUnitEnum.MTORR.value: 0.133322368,    # mTorr
        p_enum.SensUnitEnum.PSIA.value: 6894.757,       # psia
        p_enum.SensUnitEnum.PSIG.value: 6894.757        # psig
    }

    ATM_PA = 101325.0

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

        self.slope = 1.0
        self.intercept = 0.0
        self.unit_gain = 0.0
        self.unit_offset = 0.0

        self.iface_unit_param       = ParamManager().get_by_full_path("RS232/RS485 User interface.Scaling.Pressure.Pressure Unit"                   )
        self.iface_min_param        = ParamManager().get_by_full_path("RS232/RS485 User interface.Scaling.Pressure.Value Pressure 0"                )
        self.iface_max_param        = ParamManager().get_by_full_path("RS232/RS485 User interface.Scaling.Pressure.Value Pressure Sensor Full Scale")   

        self.sens1_avail_param     = ParamManager().get_by_full_path("Sensor.Sensor 1.Basic.Available"                                             )
        self.sens1_enable_param    = ParamManager().get_by_full_path("Sensor.Sensor 1.Basic.Enable"                                                )
        self.sens1_unit_param      = ParamManager().get_by_full_path("Sensor.Sensor 1.Range.Data Unit"                                             )
        self.sens1_min_value_param = ParamManager().get_by_full_path("Sensor.Sensor 1.Range.Lower Limit Data Value"                                )
        self.sens1_max_value_param = ParamManager().get_by_full_path("Sensor.Sensor 1.Range.Upper Limit Data Value"                                )

        self.sens2_avail_param     = ParamManager().get_by_full_path("Sensor.Sensor 2.Basic.Available"                                             )
        self.sens2_enable_param    = ParamManager().get_by_full_path("Sensor.Sensor 2.Basic.Enable"                                                )
        self.sens2_unit_param      = ParamManager().get_by_full_path("Sensor.Sensor 2.Range.Data Unit"                                             )
        self.sens2_min_value_param = ParamManager().get_by_full_path("Sensor.Sensor 2.Range.Lower Limit Data Value"                                )
        self.sens2_max_value_param = ParamManager().get_by_full_path("Sensor.Sensor 2.Range.Upper Limit Data Value"                                )
        
        LocalSettingManager().sig_pres_unit_changed.connect (self.handle_sens_cfg_changed )

        self.iface_unit_param.sig_value_changed.connect      (self.handle_sens_cfg_changed )
        self.iface_min_param.sig_value_changed.connect       (self.handle_sens_cfg_changed )
        self.iface_max_param.sig_value_changed.connect       (self.handle_sens_cfg_changed )    

        self.sens1_avail_param.sig_value_changed.connect    (self.handle_sens_cfg_changed )
        self.sens1_enable_param.sig_value_changed.connect   (self.handle_sens_cfg_changed )
        self.sens1_unit_param.sig_value_changed.connect     (self.handle_sens_cfg_changed )
        self.sens1_min_value_param.sig_value_changed.connect(self.handle_sens_cfg_changed )
        self.sens1_max_value_param.sig_value_changed.connect(self.handle_sens_cfg_changed )

        self.sens2_avail_param.sig_value_changed.connect    (self.handle_sens_cfg_changed )
        self.sens2_enable_param.sig_value_changed.connect   (self.handle_sens_cfg_changed )
        self.sens2_unit_param.sig_value_changed.connect     (self.handle_sens_cfg_changed )
        self.sens2_min_value_param.sig_value_changed.connect(self.handle_sens_cfg_changed )
        self.sens2_max_value_param.sig_value_changed.connect(self.handle_sens_cfg_changed )    

    def handle_sens_cfg_changed(self):
        params = [
            self.iface_unit_param, self.iface_min_param, self.iface_max_param,
            self.sens1_avail_param, self.sens1_enable_param, self.sens1_unit_param, self.sens1_min_value_param, self.sens1_max_value_param,
            self.sens2_avail_param, self.sens2_enable_param, self.sens2_unit_param, self.sens2_min_value_param, self.sens2_max_value_param
        ]

        if any(p.value is None for p in params):
            return

        if self.iface_unit_param.value == p_enum.RS232PressureUnitEnum.USER_SPECIFIC.value:
            iface_min = self.iface_min_param.value
            iface_max = self.iface_max_param.value

            s1_max_pa = self._convert_pressure(self.sens1_max_value_param.value, self.sens1_unit_param.value, p_enum.SensUnitEnum.PA.value)
            s2_max_pa = self._convert_pressure(self.sens2_max_value_param.value, self.sens2_unit_param.value, p_enum.SensUnitEnum.PA.value)

            s1_active = self.sens1_avail_param.value and self.sens1_enable_param.value
            s2_active = self.sens2_avail_param.value and self.sens2_enable_param.value

            if s1_active and s2_active:
                if s1_max_pa >= s2_max_pa:
                    sens_unit = self.sens1_unit_param.value
                    sens_min = self.sens1_min_value_param.value
                    sens_max = self.sens1_max_value_param.value
                else:
                    sens_unit = self.sens2_unit_param.value
                    sens_min = self.sens2_min_value_param.value
                    sens_max = self.sens2_max_value_param.value
            elif s1_active:
                sens_unit = self.sens1_unit_param.value
                sens_min = self.sens1_min_value_param.value
                sens_max = self.sens1_max_value_param.value
            elif s2_active:
                sens_unit = self.sens2_unit_param.value
                sens_min = self.sens2_min_value_param.value
                sens_max = self.sens2_max_value_param.value
            else:
                sens_unit = p_enum.SensUnitEnum.TORR.value
                sens_min = 0.0
                sens_max = 1.0

            if iface_max == iface_min or sens_max == sens_min:
                self.slope = 1.0
                self.intercept = 0.0
                self.unit_gain = 0.0
                self.unit_offset = 0.0
            else:
                self.slope = (sens_max - sens_min) / (iface_max - iface_min)
                self.intercept = sens_min - (self.slope * iface_min)
                self.unit_gain, self.unit_offset = self._get_unit_conversion(sens_unit, LocalSettingManager().pres_unit)
        else:
            self.slope = 1
            self.intercept = 0
            iface_unit = self._convert_iface_unit_to_sens_unit(self.iface_unit_param.value)
            self.unit_gain, self.unit_offset = self._get_unit_conversion(iface_unit, LocalSettingManager().pres_unit)
                    
        # UI 갱신 등을 위한 시그널 발생
        self.sig_pres_range_changed.emit()

    def get_dp_max_pres(self) -> float:
        if self.iface_max_param.value:
            return self.convert_iface_pres_to_dp_pres(self.iface_max_param.value)
        else:
            return 1.0

    def convert_iface_pres_to_dp_pres(self, ori_value: float) -> float:
        real_pres_in_sens_unit = (ori_value * self.slope) + self.intercept
        return (real_pres_in_sens_unit * self.unit_gain) + self.unit_offset

    def convert_dp_pres_to_iface_pres_str(self, value: float) -> str:
        if self.slope == 0:
            return ""
            
        real_pres_in_sens_unit = (value - self.unit_offset) / self.unit_gain
        result_value = (real_pres_in_sens_unit - self.intercept) / self.slope
        return format(Decimal(str(result_value)), 'f')

    def convert_sfs_to_dp_pres(self, value: float) -> float:
        pres_max = self.get_dp_max_pres()
        return pres_max * value

    def convert_dp_pres_to_sfs(self, value: float) -> float:
        pres_max = self.get_dp_max_pres()
        if pres_max == 0: return 0.0
        return value / pres_max        

    def _convert_pressure(self, value: float, from_unit_idx: int, to_unit_idx: int) -> float:
        gain, offset = self._get_unit_conversion(from_unit_idx, to_unit_idx)
        return (value * gain) + offset

    def _get_unit_conversion(self, from_unit_idx: int, to_unit_idx: int) -> tuple[float, float]:
        from_factor = self.PA_FACTORS.get(from_unit_idx, 1.0)
        to_factor = self.PA_FACTORS.get(to_unit_idx, 1.0)
        
        gain = from_factor / to_factor
        offset = 0.0

        if from_unit_idx == p_enum.SensUnitEnum.PSIG.value and to_unit_idx != p_enum.SensUnitEnum.PSIG.value:
            offset = self.ATM_PA / to_factor
        elif from_unit_idx != p_enum.SensUnitEnum.PSIG.value and to_unit_idx == p_enum.SensUnitEnum.PSIG.value:
            offset = -self.ATM_PA / to_factor
            
        return gain, offset

    def _convert_iface_unit_to_sens_unit(self, unit:int)->int :
        if unit == p_enum.RS232PressureUnitEnum.PA.value:
            return p_enum.SensUnitEnum.PA.value
        elif unit == p_enum.RS232PressureUnitEnum.KPA.value:
            return p_enum.SensUnitEnum.KPA.value
        elif unit == p_enum.RS232PressureUnitEnum.BAR.value:
            return p_enum.SensUnitEnum.BAR.value
        elif unit == p_enum.RS232PressureUnitEnum.MBAR.value:
            return p_enum.SensUnitEnum.MBAR.value
        elif unit == p_enum.RS232PressureUnitEnum.TORR.value:
            return p_enum.SensUnitEnum.TORR.value
        elif unit == p_enum.RS232PressureUnitEnum.MTORR.value:
            return p_enum.SensUnitEnum.MTORR.value
        elif unit == p_enum.RS232PressureUnitEnum.PSI.value:
            return p_enum.SensUnitEnum.PSIA.value
        else:
            return p_enum.SensUnitEnum.PA.value
            
        