'''
from enum import Enum

from PySide6.QtCore import QCoreApplication, QT_TRANSLATE_NOOP

class ParamId(Enum):
    def __new__(cls, value, full_path_key):
        obj = object.__new__(cls)
        obj._value_ = value
        obj.full_path_key = full_path_key
        return obj

    @property
    def full_path(self):
        # UI에 텍스트를 표시해야 할 때(런타임) 이 프로퍼티를 호출하면,
        # 현재 적용된 언어팩에 맞춰 동적으로 번역된 텍스트를 반환합니다.
        return QCoreApplication.translate("ParamId", self.path_key)

class ParamIds(ParamId):
    SYSTEM_ACC_MODE                 = (  0, QT_TRANSLATE_NOOP("ParamId", "System.Access Mode"                                   ))
    SYSTEM_CTRL_MODE                = (  1, QT_TRANSLATE_NOOP("ParamId", "System.Control Mode"                                  ))
    SYSTEM_ID_SN                    = (  2, QT_TRANSLATE_NOOP("ParamId", "System.Identification.Serial Number"                  ))
    SYSTEM_ID_CFG_MODEL             = (  3, QT_TRANSLATE_NOOP("ParamId", "System.Identification.Configuration.Model"            ))
    SYSTEM_ID_CFG_VALVE_TYPE        = (  4, QT_TRANSLATE_NOOP("ParamId", "System.Identification.Configuration.Valve Type"       ))
    SYSTEM_ID_CFG_SEALING_TYPE      = (  5, QT_TRANSLATE_NOOP("ParamId", "System.Identification.Configuration.Sealing Type"     ))
    SYSTEM_ID_CFG_FLANGE_SIZE       = (  6, QT_TRANSLATE_NOOP("ParamId", "System.Identification.Configuration.Flange Size"      ))
    SYSTEM_ID_CFG_CONTRACT_METHOD   = (  7, QT_TRANSLATE_NOOP("ParamId", "System.Identification.Configuration.Contract Method"  ))
    SYSTEM_ID_CFG_BODY_MATERIAL     = (  8, QT_TRANSLATE_NOOP("ParamId", "System.Identification.Configuration.Body Material"    ))
    SYSTEM_ID_CFG_USER_IFACE        = (  9, QT_TRANSLATE_NOOP("ParamId",  "System.Identification.Configuration.User Interface"  ))
    SYSTEM_ID_CFG_POWER_OPT         = ( 10, QT_TRANSLATE_NOOP("ParamId", "System.Identification.Configuration.Power Option"     ))
    SYSTEM_ID_CFG_SENS_NUM          = ( 11, QT_TRANSLATE_NOOP("ParamId", "System.Identification.Configuration.Sensor Number"    ))
    SYSTEM_ID_CFG_REV_1             = ( 12, QT_TRANSLATE_NOOP("ParamId", "System.Identification.Configuration.Revision 1"       ))
    SYSTEM_ID_CFG_REV_2             = ( 13, QT_TRANSLATE_NOOP("ParamId", "System.Identification.Configuration.Revision 2"       ))
    SYSTEM_ID_CFG_REV_3             = ( 14, QT_TRANSLATE_NOOP("ParamId", "System.Identification.Configuration.Revision 3"       ))
    SYSTEM_ID_CFG_PRODUCT_NUM       = ( 15, QT_TRANSLATE_NOOP("ParamId", "System.Identification.Configuration.Product Number"   ))
    SYSTEM_ID_CFG_PRODUCT_NUM_EX    = ( 16, QT_TRANSLATE_NOOP("ParamId", "System.Identification.Configuration.Product Number Ex"))
    SYSTEM_STAT_POWER_UP_COUNTER    = ( 17, QT_TRANSLATE_NOOP("ParamId", "System.Statistics.Power Up Counter"                   ))
    SYSTEM_STAT_TOTAL_TIME_POWERED  = ( 18, QT_TRANSLATE_NOOP("ParamId", "System.Statistics.Total Time Powered"                 ))
    SYSTEM_STAT_TIME_SINCE_POWER_ON = ( 19, QT_TRANSLATE_NOOP("ParamId", "System.Statistics.Time Since Power On"                ))
    SYSTEM_WARN_ERR_WARN_BITMAP     = ( 20, QT_TRANSLATE_NOOP("ParamId", "System.Warning/Error.Warning Bitmap"                  ))
    SYSTEM_WARN_ERR_ERR_BITMAP      = ( 21, QT_TRANSLATE_NOOP("ParamId", "System.Warning/Error.Error Bitmap"                    ))
    SYSTEM_WARN_ERR_ERR_NUMBER      = ( 22, QT_TRANSLATE_NOOP("ParamId", "System.Warning/Error.Error Number"                    ))
    SYSTEM_WARN_ERR_ERR_CODE        = ( 23, QT_TRANSLATE_NOOP("ParamId", "System.Warning/Error.Error Code"                      ))
    SYSTEM_SVC_RESTART_CONTROLLER   = ( 24, QT_TRANSLATE_NOOP("ParamId", "System.Services.Restart Controller"                   ))
    SYSTEM_SVC_CFG_LOCK_MODE        = ( 25, QT_TRANSLATE_NOOP("ParamId", "System.Services.Configuration Lock Mode"              ))

    SENS_1_BASIC_ACT_PRES_VALUE     = ( 26, QT_TRANSLATE_NOOP("ParamId", "Sensor.Sensor 1.Basic.Actual Pressure Valuee"         ))
    SENS_1_BASIC_AVAILABLE          = ( 27, QT_TRANSLATE_NOOP("ParamId", "Sensor.Sensor 1.Basic.Available"                      ))
    SENS_1_BASIC_ENABLE             = ( 28, QT_TRANSLATE_NOOP("ParamId", "Sensor.Sensor 1.Basic.Enable"                         ))
    SENS_1_BASIC_IN_SRC             = ( 29, QT_TRANSLATE_NOOP("ParamId", "Sensor.Sensor 1.Basic.Input Source"                   ))
    SENS_1_BASIC_SCALE              = ( 30, QT_TRANSLATE_NOOP("ParamId", "Sensor.Sensor 1.Basic.Scale"                          ))
    SENS_1_RANGE_DATA_UNIT          = ( 31, QT_TRANSLATE_NOOP("ParamId", "Sensor.Sensor 1.Range.Data Unit"                      ))
    SENS_1_RANGE_UP_DATA_VAL        = ( 32, QT_TRANSLATE_NOOP("ParamId", "Sensor.Sensor 1.Range.Upper Limit Data Value"         ))
    SENS_1_RANGE_LOW_DATA_VAL       = ( 33, QT_TRANSLATE_NOOP("ParamId", "Sensor.Sensor 1.Range.Lower Limit Data Value"         ))
    SENS_1_RANGE_UP_VOLT_VAL        = ( 34, QT_TRANSLATE_NOOP("ParamId", "Sensor.Sensor 1.Range.Upper Limit Voltage Value"      ))
    SENS_1_RANGE_LOW_VOLT_VAL       = ( 35, QT_TRANSLATE_NOOP("ParamId", "Sensor.Sensor 1.Range.Lower Limit Voltage Value"      ))
    SENS_1_RANGE_VOLT_PER_DECADE    = ( 36, QT_TRANSLATE_NOOP("ParamId", "Sensor.Sensor 1.Range.Voltage Per Decade"             ))
    SENS_1_ZERO_ADJ_ENABLE          = ( 37, QT_TRANSLATE_NOOP("ParamId", "Sensor.Sensor 1.Zero Adjust.Enable"                   ))
    SENS_1_ZERO_ADJ_OFFSET_VAL_SFS  = ( 38, QT_TRANSLATE_NOOP("ParamId", "Sensor.Sensor 1.Zero Adjust.Offset Value [SFS]"       ))
    SENS_1_FILTER_ENABLE            = ( 39, QT_TRANSLATE_NOOP("ParamId", "Sensor.Sensor 1.Filter.Enable"                        ))
    SENS_1_FILTER_TIME_SEC          = ( 40, QT_TRANSLATE_NOOP("ParamId", "Sensor.Sensor 1.Filter.Time(sec)"                     ))
    SENS_1_ANALOG_SENS_IN_VAL       = ( 41, QT_TRANSLATE_NOOP("ParamId", "Sensor.Sensor 1.Analog Sensor Input.Value"            ))
    SENS_1_DIGI_SENS_IN_VAL         = ( 42, QT_TRANSLATE_NOOP("ParamId", "Sensor.Sensor 1.Digital Sensor Input.Value"           ))

    SENS_2_BASIC_ACT_PRES_VAL       = ( 43, QT_TRANSLATE_NOOP("ParamId", "Sensor.Sensor 2.Basic.Actual Pressure Valuee"         ))
    SENS_2_BASIC_AVAILABLE          = ( 44, QT_TRANSLATE_NOOP("ParamId", "Sensor.Sensor 2.Basic.Available"                      ))
    SENS_2_BASIC_ENABLE             = ( 45, QT_TRANSLATE_NOOP("ParamId", "Sensor.Sensor 2.Basic.Enable"                         ))
    SENS_2_BASIC_IN_SRC             = ( 46, QT_TRANSLATE_NOOP("ParamId", "Sensor.Sensor 2.Basic.Input Source"                   ))
    SENS_2_BASIC_SCALE              = ( 47, QT_TRANSLATE_NOOP("ParamId", "Sensor.Sensor 2.Basic.Scale"                          ))
    SENS_2_RANGE_DATA_UNIT          = ( 48, QT_TRANSLATE_NOOP("ParamId", "Sensor.Sensor 2.Range.Data Unit"                      ))
    SENS_2_RANGE_UP_DATA_VAL        = ( 49, QT_TRANSLATE_NOOP("ParamId", "Sensor.Sensor 2.Range.Upper Limit Data Value"         ))
    SENS_2_RANGE_LOW_DATA_VAL       = ( 50, QT_TRANSLATE_NOOP("ParamId", "Sensor.Sensor 2.Range.Lower Limit Data Value"         ))
    SENS_2_RANGE_UP_VOLT_VAL        = ( 51, QT_TRANSLATE_NOOP("ParamId", "Sensor.Sensor 2.Range.Upper Limit Voltage Value"      ))
    SENS_2_RANGE_LOW_VOLT_VAL       = ( 52, QT_TRANSLATE_NOOP("ParamId", "Sensor.Sensor 2.Range.Lower Limit Voltage Value"      ))
    SENS_2_RANGE_VOLT_PER_DECADE    = ( 53, QT_TRANSLATE_NOOP("ParamId", "Sensor.Sensor 2.Range.Voltage Per Decade"             ))
    SENS_2_ZERO_ADJ_ENABLE          = ( 54, QT_TRANSLATE_NOOP("ParamId", "Sensor.Sensor 2.Zero Adjust.Enable"                   ))
    SENS_2_ZERO_ADJ_OFFSET_VAL_SFS  = ( 55, QT_TRANSLATE_NOOP("ParamId", "Sensor.Sensor 2.Zero Adjust.Offset Value [SFS]"       ))
    SENS_2_FILTER_ENABLE            = ( 56, QT_TRANSLATE_NOOP("ParamId", "Sensor.Sensor 2.Filter.Enable"                        ))
    SENS_2_FILTER_TIME_SEC          = ( 57, QT_TRANSLATE_NOOP("ParamId", "Sensor.Sensor 2.Filter.Time(sec)"                     ))
    SENS_2_ANALOG_SENS_IN_VAL       = ( 58, QT_TRANSLATE_NOOP("ParamId", "Sensor.Sensor 2.Analog Sensor Input.Value"            ))
    SENS_2_DIGI_SENS_IN_VAL         = ( 59, QT_TRANSLATE_NOOP("ParamId", "Sensor.Sensor 2.Digital Sensor Input.Value"           ))

    SENS_CROSS_MODE                 = ( 60, QT_TRANSLATE_NOOP("ParamId", "Sensor.Crossover.Crossover Mode"                      ))
    SENS_CROSS_HIGH_THRES_LSFS      = ( 61, QT_TRANSLATE_NOOP("ParamId", "Sensor.Crossover.Threshold High [SFS low sensor]"     ))
    SENS_CROSS_LOW_THRES_LSFS       = ( 62, QT_TRANSLATE_NOOP("ParamId", "Sensor.Crossover.Threshold Low [SFS low sensor]"      ))
    SENS_CROSS_DELAY_SEC            = ( 63, QT_TRANSLATE_NOOP("ParamId", "Sensor.Crossover.Delay(sec)"                          ))

    POSICTRL_BASIC_TARGET_POSI_USED = ( 64, QT_TRANSLATE_NOOP("ParamId", "Position Control.Basic.Target Position Used"          ))
    POSICTRL_BASIC_ACT_POSI         = ( 65, QT_TRANSLATE_NOOP("ParamId", "Position Control.Basic.Actual Position"               ))
    POSICTRL_BASIC_POSI_CTRL_SPEED  = ( 66, QT_TRANSLATE_NOOP("ParamId", "Position Control.Basic.Position Control Speed"        ))
    POSICTRL_BASIC_TARGET_POSI      = ( 67, QT_TRANSLATE_NOOP("ParamId", "Position Control.Basic.Target Position"               ))
    POSICTRL_RAMP_ENABLE            = ( 68, QT_TRANSLATE_NOOP("ParamId", "Position Control.Ramp.Enable"                         ))
    POSICTRL_RAMP_MODE              = ( 69, QT_TRANSLATE_NOOP("ParamId", "Position Control.Ramp.Mode"                           ))
    POSICTRL_RAMP_SLOPE_POSI        = ( 70, QT_TRANSLATE_NOOP("ParamId", "Position Control.Ramp.Slope(Position(%)/sec)"         ))
    POSICTRL_RAMP_TIME_SEC          = ( 71, QT_TRANSLATE_NOOP("ParamId", "Position Control.Ramp.Time(sec)"                      ))
    POSICTRL_RAMP_TYPE              = ( 72, QT_TRANSLATE_NOOP("ParamId", "Position Control.Ramp.Type"                           ))


                                                      
         
'''