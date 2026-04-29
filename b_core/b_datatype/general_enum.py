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
    COMMUNICATION_ERROR = auto()
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
    