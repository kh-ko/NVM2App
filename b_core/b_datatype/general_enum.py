from enum import Enum, auto

from b_core.b_datatype.param_enum import DescriptionEnum

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
    NV1_GROUP = auto()
    ENUM      = auto()
    TEXT      = auto()
    NUMBER    = auto()
    HEX       = auto()
    BITMAP    = auto()
    ERR_NUM   = auto()
    SENS_PRES = auto()
    H_SFS     = auto()
    L_SFS     = auto()
    REAL      = auto()
    SCALE     = auto()
    POSI      = auto()
    BTN       = auto()
    SENS1_PRES = auto()
    SENS2_PRES = auto()
    PRESS_SLOPE = auto()
    IFACE_GAIN = auto()
    ENUM_36   = auto()

PARAM_DISPLAY_TYPE_MAP = {
    "nv1_group": ParamDisplayType.NV1_GROUP,
    "enum": ParamDisplayType.ENUM,
    "btn": ParamDisplayType.BTN,
    "bitmap": ParamDisplayType.BITMAP,
    "errnum": ParamDisplayType.ERR_NUM,
    "text": ParamDisplayType.TEXT,
    "hex": ParamDisplayType.HEX,
    "num": ParamDisplayType.NUMBER,
    "real": ParamDisplayType.REAL,
    "scale": ParamDisplayType.SCALE,
    "posi": ParamDisplayType.POSI,
    "ifgain": ParamDisplayType.IFACE_GAIN,
    "pres": ParamDisplayType.SENS_PRES,
    "s1pres": ParamDisplayType.SENS1_PRES,
    "s2pres": ParamDisplayType.SENS2_PRES,
    "presslope": ParamDisplayType.PRESS_SLOPE,
    "compound": ParamDisplayType.HEX,
    "enum36": ParamDisplayType.ENUM_36,
}    

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
    BASE_36= auto()

class SvcPortErrType(Enum):
    NONE                = auto()
    OPEN_ERROR          = auto()
    READ_TIMEOUT_ERROR  = auto()
    WRITE_TIMEOUT_ERROR = auto()
    DECODING_ERROR      = auto()
    UN_COMPLETED_DATA   = auto()
    DEVICE_ERR          = auto()
    UNKNOWN_ERR         = auto()

class ParamParseErrType(Enum):
    NONE                = auto()
    COMMUNICATION_ERR   = auto()
    WRONG_FORMAT        = auto()
    WRONG_PREFIX        = auto()
    WRONG_PARAM_LENGTH  = auto()
    WRONG_SVC_CODE      = auto()
    WRONG_ID_OR_INDEX   = auto()
    UNKNOWN_ERROR_CODE  = auto()
    DATA_TYPE_ERROR     = auto()

    ERR_0C_WRONG_CMD_LEN                                   = auto() # "0C": "wrong command length"
    ERR_1C_WRONG_CMD_LEN                                   = auto() # "1C": "value too low", 
    ERR_1D_VALUE_TOO_LOW                                   = auto() # "1D": "value too high",
    ERR_20_RESULTING_ZERO_ADJUST_OFFSET_VALUE_OUT_OF_RANGE = auto() # "20": "resulting zero adjust offset value out of range", 
    ERR_21_NOT_VALID_BECAUSE_NO_SENSOR_ENABLED             = auto() # "21": "not valid because no sensor enabled",
    ERR_50_WRONG_ACCESS_MODE                               = auto() # "50": "wrong access mode",
    ERR_51_TIMEOUT                                         = auto() # "51": "timeout", 
    ERR_6D_EEPROM_NOT_READY                                = auto() # "6D": "EEProm not ready",
    ERR_6E_WRONG_PARAMETER_ID                              = auto() # "6E": "wrong parameter ID", 
    ERR_6F_SET_TO_DEFAULT_VALUE_NOT_ALLOWED                = auto() # "6F": "set to default value not allowed",
    ERR_70_PARAMETER_NOT_SETTABLE                          = auto() # "70": "parameter not settable", 
    ERR_71_PARAMETER_NOT_READABLE                          = auto() # "71": "parameter not readable", 
    ERR_72_SET_TO_INITIAL_VALUE_NOT_ALLOWED                = auto() # "72": "set to initial value not allowed",
    ERR_73_WRONG_PARAMETER_INDEX                           = auto() # "73": "wrong parameter index", 
    ERR_74_INITIAL_VALUE_OUT_OF_RANGE                      = auto() # "74": "initial value out of range", 
    ERR_76_WRONG_VALUE                                     = auto() # "76": "wrong value",
    ERR_77_WRONG_VALUE_ONLY_RESET_POSSIBLE                 = auto() # "77": "wrong value, only reset possible", 
    ERR_78_NOT_ALLOWED_IN_THIS_STATE                       = auto() # "78": "not allowed in this state", 
    ERR_7A_WRONG_SERVICE                                   = auto() # "7A": "wrong service",
    ERR_7B_PARAMETER_NOT_ACTIVE                            = auto() # "7B": "parameter not active", 
    ERR_7C_PARAMETER_SYSTEM_ERROR                          = auto() # "7C": "parameter system error", 
    ERR_7D_COMMUNICATION_ERROR                             = auto() # "7D": "communication error",
    ERR_7E_UNKNOWN_SERVICE                                 = auto() # "7E": "unknown service", 
    ERR_7F_UNEXPECTED_CHARACTER                            = auto() # "7F": "unexpected character", 
    ERR_80_NO_ACCESS_RIGHTS                                = auto() # "80": "no access rights",
    ERR_81_NO_ADEQUATELY_HARDWARE                          = auto() # "81": "no adequately hardware", 
    ERR_82_WRONG_OBJECT_STATE                              = auto() # "82": "wrong object state", 
    ERR_84_NO_SLAVE_COMMAND                                = auto() # "84": "no slave command",
    ERR_85_COMMAND_TO_UNKNOWN_SLAVE                        = auto() # "85": "command to unknown slave", 
    ERR_87_COMMAND_TO_MASTER_ONLY                          = auto() # "87": "command to master only", 
    ERR_88_ONLY_G_COMMAND_ALLOWED                          = auto() # "88": "only G command allowed",
    ERR_89_NOT_SUPPORTED                                   = auto() # "89": "not supported", 
    ERR_A0_FUNCTION_IS_DISABLED                            = auto() # "A0": "function is disabled", 
    ERR_A1_ALREADY_DONE                                    = auto() # "A1": "already done"

class MainChartRangeModeEnum(DescriptionEnum):
    AUTO            = (0, "AUTO")
    FULL            = (1, "FULL")
    CUSTOM          = (2, "CUSTOM")

class MainChartTimeRangeEnum(DescriptionEnum):
    SEC_30          = (30000, "30초")
    MIN_1           = (60000, "1분")
    MIN_2           = (120000, "2분")
    MIN_3           = (180000, "3분")
    MIN_5           = (300000, "5분")
    MIN_10          = (600000, "10분")

class ConnectionNetworkEnum(DescriptionEnum):
    RS232           = (0,"RS232" )
    RS485           = (1,"RS485" )
    TCP_IP          = (2,"TCP/IP")  
    
class ConnectionBaudRateEnum(DescriptionEnum):
    BAUDRATE_9600   = (9600  , "9600"  )
    BAUDRATE_19200  = (19200 , "19200" )
    BAUDRATE_38400  = (38400 , "38400" )
    BAUDRATE_57600  = (57600 , "57600" )  
    BAUDRATE_115200 = (115200, "115200")  

class ConnectionDataBitsEnum(DescriptionEnum):
    DATABITS_5      = (5, "5")
    DATABITS_6      = (6, "6")
    DATABITS_7      = (7, "7")
    DATABITS_8      = (8, "8")          

class ConnectionParityEnum(DescriptionEnum):
    NO_PARITY       = (0, "NoParity"   )
    EVEN_PARITY     = (2, "EvenParity" )
    ODD_PARITY      = (3, "OddParity"  )
    SPACE_PARITY    = (4, "SpaceParity")
    MARK_PARITY     = (5, "MarkParity" )

class ConnectionStopBitsEnum(DescriptionEnum):
    ONE_STOP          = (1, "OneStop"       )
    TWO_STOP          = (2, "TwoStop"       )
    ONE_AND_HALF_STOP = (3, "OneAndHalfStop")

class ConnectionTerminationEnum(DescriptionEnum):
    CR_LF           = (0, "CR_LF")
    LF              = (1, "LF"   )
    CR              = (2, "CR"   )    

class DecimalPlacesEnum(DescriptionEnum):
    DECIAML_PLACES_0 = (0, "0")
    DECIAML_PLACES_1 = (1, "1")
    DECIAML_PLACES_2 = (2, "2")
    DECIAML_PLACES_3 = (3, "3")
    DECIAML_PLACES_4 = (4, "4")
    DECIAML_PLACES_5 = (5, "5")
    DECIAML_PLACES_6 = (6, "6")

class PositionUnitEnum(DescriptionEnum):
    POSI_UNIT_PERCENT = (0, "Percent(%)")     

class EtherCATRangeSettingOptEnum(DescriptionEnum):
    BASIC         = (0, "Basic")  
    ADVENCED      = (1, "Advanced")