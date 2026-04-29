import threading
import math

from PySide6.QtCore import Signal, QObject

from b_core.b_datatype import param_enum as p_enum
from b_core.c_manager.parameter_manager import ParamManager

class PosiConverterManager(QObject):
    _instance = None
    _creation_lock = threading.Lock()

    sig_posi_range_changed = Signal()

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

        self.posi_unit = p_enum.RS232PositionUnitEnum.USER_SPECIFIC.value
        self.posi_min  = 0.0
        self.posi_max  = 100.0

        self.posi_unit_param = ParamManager().get_by_full_path("RS232/RS485 User interface.Scaling.Position.Position Unit"         )
        self.posi_min_param  = ParamManager().get_by_full_path("RS232/RS485 User interface.Scaling.Position.Value Closest Position")
        self.posi_max_param  = ParamManager().get_by_full_path("RS232/RS485 User interface.Scaling.Position.Value Open Position"   )     
        
        self.posi_unit_param.sig_value_changed.connect(self.handle_posi_range_changed)
        self.posi_min_param.sig_value_changed.connect(self.handle_posi_range_changed)
        self.posi_max_param.sig_value_changed.connect(self.handle_posi_range_changed)    

    def handle_posi_range_changed(self):
        if not self.posi_unit_param.str_value:
            return

        self.posi_unit = self.posi_unit_param.value

        if self.posi_unit == p_enum.RS232PositionUnitEnum.USER_SPECIFIC.value:
            if not self.posi_min_param.str_value or not self.posi_max_param.str_value:
                return
            self.posi_min  = self.posi_min_param.value
            self.posi_max  = self.posi_max_param.value
        elif self.posi_unit == p_enum.RS232PositionUnitEnum.ZERO_TO_1.value:
            self.posi_min = 0.0
            self.posi_max = 1.0
        elif self.posi_unit == p_enum.RS232PositionUnitEnum.ZERO_TO_10.value:
            self.posi_min = 0.0
            self.posi_max = 10.0
        elif self.posi_unit == p_enum.RS232PositionUnitEnum.ZERO_TO_90.value:
            self.posi_min = 0.0
            self.posi_max = 90.0
        elif self.posi_unit == p_enum.RS232PositionUnitEnum.ZERO_TO_100.value:
            self.posi_min = 0.0
            self.posi_max = 100.0
        elif self.posi_unit == p_enum.RS232PositionUnitEnum.ZERO_TO_1000.value:
            self.posi_min = 0.0
            self.posi_max = 1000.0
        elif self.posi_unit == p_enum.RS232PositionUnitEnum.ZERO_TO_10000.value:
            self.posi_min = 0.0
            self.posi_max = 10000.0            
        elif self.posi_unit == p_enum.RS232PositionUnitEnum.ZERO_TO_100000.value:
            self.posi_min = 0.0
            self.posi_max = 100000.0  
        else:
            self.posi_unit = -1

        self.sig_posi_range_changed.emit()

    def convert_posi_to_display_str_value(self, ori_value: float) -> str:
            
        if self.posi_unit == -1:
            return "Unknown Range"

        range_value = self.posi_max - self.posi_min

        if range_value == 0:
            return "0"
        else:
            converted_value = (ori_value - self.posi_min) / range_value * 100

            if converted_value == 0:
                return "0"

            magnitude = math.floor(math.log10(abs(converted_value)))
            round_digits = 6 - 1 - magnitude
            rounded_value = round(converted_value, round_digits)

            if round_digits > 0:
                formatted_value = f"{rounded_value:.{round_digits}f}"
                if '.' in formatted_value:
                    formatted_value = formatted_value.rstrip('0').rstrip('.')
                return formatted_value
            else:
                return f"{rounded_value:.0f}"

    def convert_posi_to_display_value(self, ori_value: float) -> float:
            
        if self.posi_unit == -1:
            return -999.999

        range_value = self.posi_max - self.posi_min

        if range_value == 0:
            return 0.0
        else:
            converted_value = (ori_value - self.posi_min) / range_value * 100

            return converted_value
        
