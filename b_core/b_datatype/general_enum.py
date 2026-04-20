from enum import Enum, auto

class LogType(Enum):
    INFO = auto()
    ERROR = auto()
    WARNING = auto()
    MONITOR = auto()
    TX = auto()
    RX = auto()

class ParamAccType(Enum):
    RO = auto()
    RW = auto()
    WO = auto()
    
class ParamDisplayType(Enum):
    ENUM      = auto()
    TEXT      = auto()
    NUMBER    = auto()
    HEX       = auto()
    BITMAP    = auto()
    DIGI_NUM  = auto()
    SENS_PRES = auto()
    H_SFS     = auto()
    L_SFS     = auto()
    REAL      = auto()
    POSI      = auto()

class ParamDataType(Enum):
    INT8   = auto()
    UINT8  = auto()
    INT16  = auto()
    UINT16 = auto()
    INT32  = auto()
    UINT32 = auto()
    FLOAT  = auto()
    DOUBLE = auto()
    STR    = auto()