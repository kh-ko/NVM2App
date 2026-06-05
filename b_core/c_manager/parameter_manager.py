
import json
import threading

from typing import Union, List, Dict, Optional
from PySide6.QtCore import QFile, QIODevice

from b_core.a_define import file_folder_path as path_def
from b_core.b_datatype import param_enum as p_enum
from b_core.b_datatype.general_enum import LogType, ParamDataType, ParamAccType, ParamDisplayType
from b_core.c_manager.log_manager import LogManager
from b_core.b_datatype.parameter_errnum import ParameterErrNum 
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
        f_min = -3.4028235e+38
        f_max = 3.4028235e+38
        n_min = -2147483648
        n_max = 2147483647
        un_min = 0
        un_max = 4294967295

        self._param_map: Dict[tuple, Parameter] = {}  # (path, name) 검색용
        self._parameters: List[Parameter] = []         # 전체 리스트 보관용

        '''
        System
        '''
        self._add_param_enum  ("System.Access Mode"                                                                         , "0F0B0000",  0, ParamAccType.RW, p_enum.AccModeEnum          , False, False, False, None)
        self._add_param_enum  ("System.Control Mode"                                                                        , "0F020000",  0, ParamAccType.RW, p_enum.ControlModeEnum      , True , False, False, None)
        self._add_param_text  ("System.Identification.Serial Number"                                                        , "0F100100",  0, ParamAccType.RO,                               False, False, False, "Identification of the product")
        self._add_param_enum  ("System.Identification.Configuration.Model"                                                  , "B0000100",  0, ParamAccType.RW, p_enum.SysModelEnum         , False, True , False, None)
        self._add_param_enum  ("System.Identification.Configuration.Valve Type"                                             , "B0000100",  1, ParamAccType.RW, p_enum.SysValveTypeEnum     , False, True , False, None)
        self._add_param_enum  ("System.Identification.Configuration.Sealing Type"                                           , "B0000100",  2, ParamAccType.RW, p_enum.SysSealingTypeEnum   , False, True , False, None)
        self._add_param_enum  ("System.Identification.Configuration.Flange Size"                                            , "B0000100",  3, ParamAccType.RW, p_enum.SysFlangeSizeEnum    , False, True , False, None)
        self._add_param_enum  ("System.Identification.Configuration.Contract Method"                                        , "B0000100",  4, ParamAccType.RW, p_enum.SysContractMethodEnum, False, True , False, None)
        self._add_param_enum  ("System.Identification.Configuration.Body Material"                                          , "B0000100",  5, ParamAccType.RW, p_enum.SysBodyMaterialEnum  , False, True , False, None)
        self._add_param_enum  ("System.Identification.Configuration.User Interface"                                         , "B0000100",  6, ParamAccType.RW, p_enum.SysUserInterfaceEnum , False, True , False, None)
        self._add_param_enum  ("System.Identification.Configuration.Power Option"                                           , "B0000100",  7, ParamAccType.RW, p_enum.SysPowerOptionEnum   , False, True , False, None)
        self._add_param_enum  ("System.Identification.Configuration.Sensor Number"                                          , "B0000100",  8, ParamAccType.RW, p_enum.SysSensorNumberEnum  , False, True , False, None)
        self._add_param_enum  ("System.Identification.Configuration.Revision 1"                                             , "B0000100",  9, ParamAccType.RW, p_enum.Base36Enum           , False, True , False, "Valve Hardware Revision 1")
        self._add_param_enum  ("System.Identification.Configuration.Revision 2"                                             , "B0000100", 10, ParamAccType.RW, p_enum.Base36Enum           , False, True , False, "Valve Hardware Revision 2")
        self._add_param_enum  ("System.Identification.Configuration.Revision 3"                                             , "B0000100", 11, ParamAccType.RW, p_enum.Base36Enum           , False, True , False, "Valve Hardware Revision 3")
        self._add_param_hex   ("System.Identification.Configuration.Product Number"                                         , "B0000100", 12, ParamAccType.RW,                               False, True , False, "Product number")
        self._add_param_hex   ("System.Identification.Configuration.Product Number Ex"                                      , "B0000100", 13, ParamAccType.RW,                               False, True , False, "Extended Product Number")
        self._add_param_text  ("System.Identification.Firmware.Firmware ID"                                                 , "0F100301",  0, ParamAccType.RO,                               False, False, False, "Firmware ID")
        self._add_param_text  ("System.Identification.Firmware.Firmware Version"                                            , "0F100302",  0, ParamAccType.RO,                               False, False, False, "Firmware Version")
        self._add_param_text  ("System.Identification.Firmware.Interface Version"                                           , "0F100303",  0, ParamAccType.RO,                               False, False, False, "Interface Version")
        self._add_param_num   ("System.Statistics.Power Up Counter"                                                         , "0F200100",  0, ParamAccType.RO, un_min, un_max, ""          , False, False, False, "")
        self._add_param_real  ("System.Statistics.Total Time Powered [sec]"                                                 , "0F200200",  0, ParamAccType.RO, f_min, f_max, "sec"         , False, False, False, "")
        self._add_param_real  ("System.Statistics.Time Since Power On [sec]"                                                , "0F200300",  0, ParamAccType.RO, f_min, f_max, "sec"         , False, False, False, "")
        self._add_param_bitmap("System.Warning/Error.Warning Bitmap"                                                        , "0F300100",  0, ParamAccType.RO, p_enum.SysWarningBitmap     , False, False, False, None)
        self._add_param_bitmap("System.Warning/Error.Error Bitmap"                                                          , "0F300500",  0, ParamAccType.RO, p_enum.SysErrorBitmap       , False, False, False, None)
        self._add_param_errnum("System.Warning/Error.Error Number"                                                          , "0F300600",  0, ParamAccType.RO, p_enum.SysErrorNumberComponent, "Component", p_enum.SysErrorNumberMode, "Mode", p_enum.SysErrorNumberType, "Type", False, False, False, None)
        self._add_param_enum  ("System.Warning/Error.Error Code"                                                            , "0F300700",  0, ParamAccType.RO, p_enum.SysErrorCodeEnum     , False, False, False, None)
        self._add_param_btn   ("System.Services.Restart Controller"                                                         , "0F500100",  0, ParamAccType.WO, "1"                         , True , False, False, "Emulates a power cycle")
        self._add_param_btn   ("System.Services.Error Recover"                                                              , "0F506600",  0, ParamAccType.WO, "1"                         , True , False, False, "Clear error status")
        self._add_param_btn   ("System.Services.Restore Factory Parameters"                                                 , "0F500205",  0, ParamAccType.WO, "1"                         , True , False, False, "Factory reset")
        self._add_param_enum  ("System.Services.Test Mode"                                                                  , "0F030000",  0, ParamAccType.RW, p_enum.OffOnEnum            , True , False, False, "Test mode on/off")

        '''       
        Valve       
        '''     
        self._add_param_posi  ("Valve.Basic.Actual Position"                                                                , "10010000",  0, ParamAccType.RO,                               False, False, False, "Show position of the valve plate")
        self._add_param_enum  ("Valve.Basic.Isolation State"                                                                , "10110000",  0, ParamAccType.RO, p_enum.ValveIsolStateEnum   , False, False, False, None)
        self._add_param_enum  ("Valve.Basic.Position State"                                                                 , "10100000",  0, ParamAccType.RO, p_enum.ValvePosiStateEnum   , False, False, False, None)
        
        self._add_param_num   ("Valve.Cycle Counter.Control Cycles"                                                         , "10300100",  0, ParamAccType.RO, un_min, un_max, ""          , False, False, False, "The valve movement is summarized.<br>The distance open > close > open is 1 Control Cycle.<br>This value can be manipulated by the customer<br>(set to 0 after service, for example)")
        self._add_param_num   ("Valve.Cycle Counter.Control Cycles Total"                                                   , "10300200",  0, ParamAccType.RO, un_min, un_max, ""          , False, False, False, "This value is the number of Control Cycles in valve lifespan")
        self._add_param_btn   ("Valve.Cycle Counter.Reset Control Cycles"                                                   , "10300100",  0, ParamAccType.WO, "0"                         , False, False, False, "Reset Control Cycles")
        self._add_param_num   ("Valve.Cycle Counter.Isolation Cycles"                                                       , "10300300",  0, ParamAccType.RO, un_min, un_max, ""          , False, False, False, "A Isolation Cycle is done if the valve has reached the sealed state.<br>This value can be manipulated by the customer.<br>(set to 0 after service, for example)")
        self._add_param_num   ("Valve.Cycle Counter.Isolation Cycles Total"                                                 , "10300400",  0, ParamAccType.RO, un_min, un_max, ""          , False, False, False, "This value is the number of Isolation Cycles in valve lifespan")
        self._add_param_btn   ("Valve.Cycle Counter.Reset Isolation Cycles"                                                 , "10300300",  0, ParamAccType.WO, "0"                         , False, False, False, "Reset Isolation Cycles")
        
        self._add_param_enum  ("Valve.Compressed Air.Error Enable"                                                          , "10A90000",  0, ParamAccType.RW, p_enum.DisableEnableEnum    , False, True , False, None)
        self._add_param_enum  ("Valve.Compressed Air.Pressure"                                                              , "10A40000",  0, ParamAccType.RO, p_enum.OkNotOkEnum          , False, False, False, None)
        self._add_param_enum  ("Valve.Homing.End Control Mode"                                                              , "10200300",  0, ParamAccType.RW, p_enum.ValveEndCtrlModeEnum , False, True , False, None)
        self._add_param_posi  ("Valve.Homing.End Position"                                                                  , "10200400",  0, ParamAccType.RW,                               False, True , False, "Position to End Control Mode (2: Position)")
        self._add_param_enum  ("Valve.Homing.Start Condition"                                                               , "10200100",  0, ParamAccType.RW, p_enum.ValveStartConditionEnum, False, True , False, None)
        self._add_param_enum  ("Valve.Homing.Status"                                                                        , "10201100",  0, ParamAccType.RO, p_enum.ValveHomingStatusEnum, False, False, False, None)
        self._add_param_enum  ("Valve.Position Restriction.Enable"                                                          , "10640100",  0, ParamAccType.RW, p_enum.DisableEnableEnum    , False, True , False, None)
        self._add_param_posi  ("Valve.Position Restriction.Maximum Position"                                                , "10640300",  0, ParamAccType.RW,                               False, True , False, "High position limit Limit the valve movement in Control Mode<br>Pressure,<br>Position,<br>Open,<br>Interlock Open")
        self._add_param_enum  ("Valve.Position Restriction.Restriction Active"                                              , "10640400",  0, ParamAccType.RW, p_enum.DeactiveActiveEnum   , False, True , False, None)
        self._add_param_enum  ("Valve.Position Adaption.Enable"                                                             , "10660100",  0, ParamAccType.RW, p_enum.DisableEnableEnum    , False, True , False, None)
        self._add_param_enum  ("Valve.Position Adaption.Mode"                                                               , "10660200",  0, ParamAccType.RW, p_enum.ValvePosiAdapModeEnum, False, True , False, None)
        self._add_param_enum  ("Valve.Position Adaption.Actual Position"                                                    , "10660300",  0, ParamAccType.RW, p_enum.ValvePosiActPosiEnum , False, True , False, None)
        self._add_param_posi  ("Valve.Position Adaption.Offset"                                                             , "10660400",  0, ParamAccType.RW,                               False, True , False, "Amount of displacement of the position")
        self._add_param_posi  ("Valve.Position Adaption.Target Position In"                                                 , "10660500",  0, ParamAccType.RO,                               False, False, False, "Same Value as Target Position under Position Control")
        self._add_param_posi  ("Valve.Position Adaption.Target Position Used"                                               , "10660600",  0, ParamAccType.RO,                               False, False, False, "Target Position In value added with offset value")
        self._add_param_posi  ("Valve.Position Adaption.Actual Position Real"                                               , "10660700",  0, ParamAccType.RO,                               False, False, False, "Actual Position with offset value")
        self._add_param_posi  ("Valve.Position Adaption.Actual Position Adapted"                                            , "10660800",  0, ParamAccType.RO,                               False, False, False, "Actual Position without offset value")
        
        '''       
        Sensor       
        '''       
        self._add_param_pres  ("Sensor.Basic.Actual Pressure"                                                               , "12100000", 0, ParamAccType.RO,                                False, False, False, "")
        self._add_param_enum  ("Sensor.Zero Adjust.Sensor Selection"                                                        , "12040100", 0, ParamAccType.RW, p_enum.SensZeroSelEnum       , False, False, False, None)
        self._add_param_pres  ("Sensor.Zero Adjust.Target Pressure"                                                         , "12040300", 0, ParamAccType.RO,                                False, False, False, "")
        self._add_param_enum  ("Sensor.Zero Adjust.Execute"                                                                 , "12040400", 0, ParamAccType.RW, p_enum.SensZeroExeEnum       , False, False, False, None)

        self._add_param_pres  ("Sensor.Sensor 1.Basic.Actual Pressure Valuee"                                               , "12010A00",  0, ParamAccType.RO,                               False, False, False, "Pressure value of the sensor")
        self._add_param_enum  ("Sensor.Sensor 1.Basic.Available"                                                            , "12010100",  0, ParamAccType.RW, p_enum.NotAvailAvailEnum    , False, True , True , None)
        self._add_param_enum  ("Sensor.Sensor 1.Basic.Enable"                                                               , "12010200",  0, ParamAccType.RW, p_enum.DisableEnableEnum    , False, True , True , None)
        self._add_param_enum  ("Sensor.Sensor 1.Basic.Input Source"                                                         , "12010600",  0, ParamAccType.RW, p_enum.SensInSrcEnum        , False, True , True , None)
        self._add_param_enum  ("Sensor.Sensor 1.Basic.Scale"                                                                , "12010310",  0, ParamAccType.RW, p_enum.SensorScaleEnum      , False, True , True , None)
        self._add_param_enum  ("Sensor.Sensor 1.Range.Data Unit"                                                            , "12010301",  0, ParamAccType.RW, p_enum.SensUnitEnum         , False, True , True , None)
        self._add_param_real  ("Sensor.Sensor 1.Range.Upper Limit Data Value"                                               , "12010302",  0, ParamAccType.RW, f_min, f_max, ""            , False, True , True , "Define the range of the pressure sensor.")
        self._add_param_real  ("Sensor.Sensor 1.Range.Lower Limit Data Value"                                               , "12010303",  0, ParamAccType.RW, f_min, f_max, ""            , False, True , True , "Define the range of the pressure sensor.")
        self._add_param_real  ("Sensor.Sensor 1.Range.Upper Limit Voltage Value [V]"                                        , "12010304",  0, ParamAccType.RW, f_min, f_max, "V"           , False, True , True , "Defines the voltage range of the sensor.")
        self._add_param_real  ("Sensor.Sensor 1.Range.Lower Limit Voltage Value [V]"                                        , "12010305",  0, ParamAccType.RW, f_min, f_max, "V"           , False, True , True , "Defines the voltage range of the sensor.")
        self._add_param_real  ("Sensor.Sensor 1.Range.Voltage Per Decade [V]"                                               , "12010311",  0, ParamAccType.RW, f_min, f_max, "V"           , False, True , True , "E.g.: Logarithmic Sensor with 1000Torr SFS at 9.0V and 1V/Decade:<br>Upper Limit Data Value = 1000,<br>Upper Limit Voltage Value = 9,<br>Voltage Per Decade := 1")
        self._add_param_enum  ("Sensor.Sensor 1.Zero Adjust.Enable"                                                         , "12010401",  0, ParamAccType.RW, p_enum.DisableEnableEnum    , False, True , True , None)
        self._add_param_real  ("Sensor.Sensor 1.Zero Adjust.Offset Value [SFS]"                                             , "12010402",  0, ParamAccType.RW, 0.0  , 1.0  , "SFS"         , False, True , True , "Value 1.0 means sensor full scale. For example for a 0-10 Volt gauge the value 0.1 means 1 Volt")
        self._add_param_enum  ("Sensor.Sensor 1.Filter.Enable"                                                              , "12010501",  0, ParamAccType.RW, p_enum.DisableEnableEnum    , False, True , True , None)
        self._add_param_real  ("Sensor.Sensor 1.Filter.Time [sec]"                                                          , "12010502",  0, ParamAccType.RW, 0.0  , 1.0  , "sec"         , False, True , True , "")
        self._add_param_pres  ("Sensor.Sensor 1.Analog Sensor Input.Value"                                                  , "12011101",  0, ParamAccType.RO,                               False, False, False, "Pressure value of the sensor")
        self._add_param_pres  ("Sensor.Sensor 1.Digital Sensor Input.Value"                                                 , "1201100A",  0, ParamAccType.RW,                               False, False, False, "Pressure value of the sensor")
        
        self._add_param_pres  ("Sensor.Sensor 2.Basic.Actual Pressure Valuee"                                               , "12020A00",  0, ParamAccType.RO,                               False, False, False, "Pressure value of the sensor")
        self._add_param_enum  ("Sensor.Sensor 2.Basic.Available"                                                            , "12020100",  0, ParamAccType.RW, p_enum.FalseTrueEnum        , False, True , True , None)
        self._add_param_enum  ("Sensor.Sensor 2.Basic.Enable"                                                               , "12020200",  0, ParamAccType.RW, p_enum.FalseTrueEnum        , False, True , True , None)
        self._add_param_enum  ("Sensor.Sensor 2.Basic.Input Source"                                                         , "12020600",  0, ParamAccType.RW, p_enum.SensInSrcEnum        , False, True , True , None)
        self._add_param_enum  ("Sensor.Sensor 2.Basic.Scale"                                                                , "12020310",  0, ParamAccType.RW, p_enum.SensorScaleEnum      , False, True , True , None)
        self._add_param_enum  ("Sensor.Sensor 2.Range.Data Unit"                                                            , "12020301",  0, ParamAccType.RW, p_enum.SensUnitEnum         , False, True , True , None)
        self._add_param_real  ("Sensor.Sensor 2.Range.Upper Limit Data Value"                                               , "12020302",  0, ParamAccType.RW, f_min, f_max, ""            , False, True , True , "Define the range of the pressure sensor.")
        self._add_param_real  ("Sensor.Sensor 2.Range.Lower Limit Data Value"                                               , "12020303",  0, ParamAccType.RW, f_min, f_max, ""            , False, True , True , "Define the range of the pressure sensor.")
        self._add_param_real  ("Sensor.Sensor 2.Range.Upper Limit Voltage Value [V]"                                        , "12020304",  0, ParamAccType.RW, f_min, f_max, "V"           , False, True , True , "Defines the voltage range of the sensor.")
        self._add_param_real  ("Sensor.Sensor 2.Range.Lower Limit Voltage Value [V]"                                        , "12020305",  0, ParamAccType.RW, f_min, f_max, "V"           , False, True , True , "Defines the voltage range of the sensor.")
        self._add_param_real  ("Sensor.Sensor 2.Range.Voltage Per Decade [V]"                                               , "12020311",  0, ParamAccType.RW, f_min, f_max, "V"           , False, True , True , "E.g.: Logarithmic Sensor with 1000Torr SFS at 9.0V and 1V/Decade:<br>Upper Limit Data Value = 1000,<br>Upper Limit Voltage Value = 9,<br>Voltage Per Decade := 1")
        self._add_param_enum  ("Sensor.Sensor 2.Zero Adjust.Enable"                                                         , "12020401",  0, ParamAccType.RW, p_enum.FalseTrueEnum        , False, True , True , None)
        self._add_param_real  ("Sensor.Sensor 2.Zero Adjust.Offset Value [SFS]"                                             , "12020402",  0, ParamAccType.RW, 0.0  , 1.0  , "SFS"         , False, True , True , "Value 1.0 means sensor full scale. For example for a 0-10 Volt gauge the value 0.1 means 1 Volt")
        self._add_param_enum  ("Sensor.Sensor 2.Filter.Enable"                                                              , "12020501",  0, ParamAccType.RW, p_enum.FalseTrueEnum        , False, True , True , None)
        self._add_param_real  ("Sensor.Sensor 2.Filter.Time [sec]"                                                          , "12020502",  0, ParamAccType.RW, 0.0  , 1.0  , "sec"         , False, True , True , "")
        self._add_param_pres  ("Sensor.Sensor 2.Analog Sensor Input.Value"                                                  , "12021101",  0, ParamAccType.RO,                               False, False, False, "Pressure value of the sensor")
        self._add_param_pres  ("Sensor.Sensor 2.Digital Sensor Input.Value"                                                 , "1202100A",  0, ParamAccType.RW,                               False, False, False, "Pressure value of the sensor")
              
        self._add_param_enum  ("Sensor.Crossover.Crossover Mode"                                                            , "12050100",  0, ParamAccType.RW, p_enum.SensCrossModeEnum    , False, True , True , None)
        self._add_param_real  ("Sensor.Crossover.Threshold High [SFS low sensor]"                                           , "12050300",  0, ParamAccType.RW, 0.0  , 1.0  , "SFS"         , False, True , True , "Defines the transition area respectively the hysteresis limits")
        self._add_param_real  ("Sensor.Crossover.Threshold Low [SFS low sensor]"                                            , "12050200",  0, ParamAccType.RW, 0.0  , 1.0  , "SFS"         , False, True , True , "Defines the transition area respectively the hysteresis limits")
        self._add_param_real  ("Sensor.Crossover.Delay [sec]"                                                               , "12050400",  0, ParamAccType.RW, 0.0  , f_max, "sec"         , False, True , True , "Only relevant in Crossover Mode = Hard Switch Delay start after reaching the hysteresis limit")

        self._add_param_real  ("Sensor.General Setting.Logarithmic Pressure.Actual Logarithmic Value"                       , "12A10101",  0, ParamAccType.RO, 0.0  , f_max, ""            , False, False, False , "")
        self._add_param_pres  ("Sensor.General Setting.Logarithmic Pressure.Lowest Pressure"                                , "12A10107",  0, ParamAccType.RW,                               False, False, False, "Limitation of the lowest pressure<br>if a linear sensor is connected that become <= 0")
        self._add_param_real  ("Sensor.General Setting.Logarithmic Pressure.Percent Per Decade [%]"                         , "12A10104",  0, ParamAccType.RW, 0.0  , f_max, "%"           , False, True , True , "Defines the logarithmic scaling")
        self._add_param_enum  ("Sensor.General Setting.Logarithmic Pressure.Pressure on on Interface"                       , "12A10105",  0, ParamAccType.RW, p_enum.SensLogPresOnIFace   , False, True , True , None)
        self._add_param_real  ("Sensor.General Setting.Logarithmic Pressure.Upper Limit Value"                              , "12A10103",  0, ParamAccType.RO, 0.0  , f_max, ""            , False, False, False, "Corresponds to the SFS according to the sensor settings")
        self._add_param_real  ("Sensor.General Setting.Logarithmic Pressure.Use Logarithmic from Sensor"                    , "12A10106",  0, ParamAccType.RW, 0.0  , f_max, ""            , False, True , True , "If a logarithmic sensor is connected,<br>the sensor signal can be used directly.")
        
        '''
        Position Control
        '''
        self._add_param_posi  ("Position Control.Basic.Target Position Used"                                                , "10660600",  0, ParamAccType.RO,                               False, False, False, "")
        self._add_param_posi  ("Position Control.Basic.Actual Position"                                                     , "11010000",  0, ParamAccType.RO,                               False, False, False, "")
        self._add_param_real  ("Position Control.Basic.Position Control Speed Used"                                         , "11030000",  0, ParamAccType.RO, 0.0  , 1.0  , ""            , False, False, False, "Speed valid in Control Mode = Position 1.0 equals to full speed")
        self._add_param_real  ("Position Control.Basic.Position Control Speed"                                              , "11030000",  0, ParamAccType.RW, 0.0  , 1.0  , ""            , False, False, False, "Speed valid in Control Mode = Position 1.0 equals to full speed")
        self._add_param_posi  ("Position Control.Basic.Target Position"                                                     , "11020000",  0, ParamAccType.RW,                               False, False, False, "")
        self._add_param_enum  ("Position Control.Ramp.Enable"                                                               , "11620100",  0, ParamAccType.RW, p_enum.FalseTrueEnum        , False, True , True , None)
        self._add_param_enum  ("Position Control.Ramp.Mode"                                                                 , "11620400",  0, ParamAccType.RW, p_enum.PosiRampModeEnum     , False, True , True , None)
        self._add_param_posi  ("Position Control.Ramp.Slope"                                                                , "11620300",  0, ParamAccType.RW,                               False, True , True , "")
        self._add_param_real  ("Position Control.Ramp.Time [sec]"                                                           , "11620200",  0, ParamAccType.RW, 0.0  , f_max, "sec"         , False, True , True , "")
        self._add_param_enum  ("Position Control.Ramp.Type"                                                                 , "11620500",  0, ParamAccType.RW, p_enum.RampTypeEnum         , False, True , True , None)
                      
        '''              
        Pressure Control              
        '''              
        self._add_param_pres  ("Pressure Control.Basic.Actual Pressure"                                                     , "07010000",  0, ParamAccType.RO,                               False, False, False, "")
        self._add_param_enum  ("Pressure Control.Basic.Controller Selector"                                                 , "07100000",  0, ParamAccType.RW, p_enum.PresCtrlSelEnum      , False, True , True , None)
        self._add_param_enum  ("Pressure Control.Basic.Controller Selector Used"                                            , "07100100",  0, ParamAccType.RO, p_enum.PresCtrlSelEnum      , False, False, False, None)
        self._add_param_real  ("Pressure Control.Basic.Conductance[l/s]"                                                    , "07100200",  0, ParamAccType.RO, 0.0  , f_max, "l/s"         , False, False, False, "")
        self._add_param_real  ("Pressure Control.Basic.MFC Flow"                                                            , "07100300",  0, ParamAccType.RO, 0.0  , f_max, ""            , False, False, False, "")
        self._add_param_enum  ("Pressure Control.Basic.MFC Flow Unit"                                                       , "07100400",  0, ParamAccType.RO, p_enum.MFCFlowUnitEnum      , False, False, False, None)
        self._add_param_real  ("Pressure Control.Basic.Chamber Volume [L]"                                                  , "07100800",  0, ParamAccType.RO, 0.0  , f_max, "L"           , False, False, False, "")
        self._add_param_real  ("Pressure Control.Basic.Adaptive Conductance gain"                                           , "07100500",  0, ParamAccType.RO, 0.0  , f_max, ""            , False, False, False, "")
        self._add_param_real  ("Pressure Control.Basic.Adaptive Flow gain"                                                  , "07100600",  0, ParamAccType.RO, 0.0  , f_max, ""            , False, False, False, "")
        self._add_param_real  ("Pressure Control.Basic.Adaptive Total gain"                                                 , "07100700",  0, ParamAccType.RO, 0.0  , f_max, ""            , False, False, False, "")
        self._add_param_real  ("Pressure Control.Basic.Pressure Control Speed"                                              , "07050000",  0, ParamAccType.RW, 0.001, 1.0  , ""            , False, True , True , "Speed valid in Control Mode = Pressure 1.0 equals to full speed")
        self._add_param_pres  ("Pressure Control.Basic.Target Pressure"                                                     , "07020000",  0, ParamAccType.RW,                               False, False, False, "")
        self._add_param_pres  ("Pressure Control.Basic.Target Pressure Used"                                                , "07030000",  0, ParamAccType.RO,                               False, False, False, "This value is set as pressure controller input.<br>It differs to the Target Pressure if a pressure ramp is used.")
        
        #self._add_param(Parameter("Pressure Control.General Settings", "Store Control Parameter Volatile", "07301100", 0, ParamDisplayType.ENUM     , ParamDataType.UINT32, ParamAccType.RW, False, False, ""   ,int(un_min), int(un_min), p_enum.FalseTrueEnum, "0: Store in NV Memory, 1: Do Not Store in NV Memory"))
        self._add_param_enum  ("Pressure Control.General Settings.Control Position Restriction.Enable"                      , "07301201",  0, ParamAccType.RW, p_enum.FalseTrueEnum        , False, True, True, None)   
        self._add_param_posi  ("Pressure Control.General Settings.Control Position Restriction.Maximum Control Position"    , "07301203",  0, ParamAccType.RW,                               False, True, True, "Limit the movement during pressure control") 
        self._add_param_posi  ("Pressure Control.General Settings.Control Position Restriction.Minimum Control Position"    , "07301202",  0, ParamAccType.RW,                               False, True, True, "Limit the movement during pressure control") 
        self._add_param_enum  ("Pressure Control.General Settings.Automated Controller Selector.Enable"                     , "07301701",  0, ParamAccType.RW, p_enum.FalseTrueEnum        , False, True, True, None) 
        self._add_param_enum  ("Pressure Control.General Settings.Automated Controller Selector.Mode"                       , "07301702",  0, ParamAccType.RW, p_enum.AutoCtrlModeEnum     , False, True, True, None) 
        self._add_param_enum  ("Pressure Control.General Settings.Automated Controller Selector.Controller Pressure Rising" , "07301720",  0, ParamAccType.RW, p_enum.PresCtrlSelEnum      , False, True, True, None) 
        self._add_param_enum  ("Pressure Control.General Settings.Automated Controller Selector.Controller Pressure Falling", "07301721",  0, ParamAccType.RW, p_enum.PresCtrlSelEnum      , False, True, True, None) 
        self._add_param_bitmap("Pressure Control.General Settings.Automated Controller Selector.Controller Selector Bitmap" , "07301703",  0, ParamAccType.RW, p_enum.PresCtrlSelBitmap    , False, True, True, None)
        self._add_param_enum  ("Pressure Control.General Settings.Automated Controller Selector.Threshold Condition"        , "07301710",  0, ParamAccType.RW, p_enum.PresCtrlThresCondEnum, False, True, True, None)  
        self._add_param_pres  ("Pressure Control.General Settings.Automated Controller Selector.Controller 1 Threshold"     , "07301704",  0, ParamAccType.RW,                               False, True, True, "Used if Mode = Threshold")
        self._add_param_pres  ("Pressure Control.General Settings.Automated Controller Selector.Controller 2 Threshold"     , "07301705",  0, ParamAccType.RW,                               False, True, True, "Used if Mode = Threshold")
        self._add_param_pres  ("Pressure Control.General Settings.Automated Controller Selector.Controller 3 Threshold"     , "07301706",  0, ParamAccType.RW,                               False, True, True, "Used if Mode = Threshold")
        self._add_param_pres  ("Pressure Control.General Settings.Automated Controller Selector.Controller 4 Threshold"     , "07301707",  0, ParamAccType.RW,                               False, True, True, "Used if Mode = Threshold")

        self._add_param_enum  ("Pressure Control.General Settings.Profile Ramp.Enable"                                      , "07301801", 0, ParamAccType.RW, p_enum.DisableEnableEnum     , False, True , True , None)  
        self._add_param_enum  ("Pressure Control.General Settings.Profile Ramp.Threshold Mode"                              , "07301802", 0, ParamAccType.RW, p_enum.PresCtrlRampThresModeEnum, False, True, True, None)  
        self._add_param_enum  ("Pressure Control.General Settings.Profile Ramp.Ramp Type"                                   , "07301840", 0, ParamAccType.RW, p_enum.RampTypeEnum          , False, True , True , None)  
        self._add_param_pres  ("Pressure Control.General Settings.Profile Ramp.Actual Slope"                                , "07301841", 0, ParamAccType.RW,                                False, True , True , "")
        self._add_param_bitmap("Pressure Control.General Settings.Profile Ramp.Controller Selector Bitmap"                  , "07301811", 0, ParamAccType.RW, p_enum.PresCtrlSelBitmap     , False, True , True , None)
        self._add_param_bitmap("Pressure Control.General Settings.Profile Ramp.Segment Selector Bitmap"                     , "07301810", 0, ParamAccType.RW, p_enum.PresCtrlSegSelBitmap  , False, True , True , None)

        for i in range(0, 10):
            self._add_param_pres(f"Pressure Control.General Settings.Profile Ramp.Segment Slope [{i+1}]"                    , "07301830", i, ParamAccType.RW                               , False, True, True, "Define the slope in the segment")
            self._add_param_pres(f"Pressure Control.General Settings.Profile Ramp.Segment Threshold [{i+1}]"                , "07301820", i, ParamAccType.RW                               , False, True, True, "Defines the upper limit of a segment 10 Segments are available")


        for i in range(1, 5):
            self._add_param_enum(f"Pressure Control.Controller {i}.Control Algorithm.Algorithm mode"                     , f"071{i}0100",  0, ParamAccType.RW, p_enum.PresCtrlAlgoEnum     , False, True, True, None)
            self._add_param_real(f"Pressure Control.Controller {i}.Adaptive Settings.Gain Factor"                        , f"071{i}0203",  0, ParamAccType.RW, 0.0001, 100.0, ""           , False, True, True, "")
            self._add_param_real(f"Pressure Control.Controller {i}.Adaptive Settings.Delta Factor"                       , f"071{i}0207",  0, ParamAccType.RW, 0.0001, 100.0, ""           , False, True, True, "")
            self._add_param_real(f"Pressure Control.Controller {i}.Adaptive Settings.Sensor Delay [sec]"                 , f"071{i}0204",  0, ParamAccType.RW, 0.0   , 1.0  , "sec"        , False, True, True, "")
            self._add_param_enum(f"Pressure Control.Controller {i}.Adaptive Settings.Learn Data Selection"               , f"071{i}0205",  0, ParamAccType.RW, p_enum.LearnDataSelEnum     , False, True, True, None)
            
            self._add_param_enum(f"Pressure Control.Controller {i}.PI/Soft Pump Settings.Control Direction"              , f"071{i}0206",  0, ParamAccType.RW, p_enum.CtrlDirEnum          , False, True, True, None)
            self._add_param_real(f"Pressure Control.Controller {i}.PI/Soft Pump Settings.P-Gain"                         , f"071{i}0201",  0, ParamAccType.RW, 0.001, 100.0, ""            , False, True, True, "Proportional Gain")
            self._add_param_real(f"Pressure Control.Controller {i}.PI/Soft Pump Settings.I-Gain"                         , f"071{i}0202",  0, ParamAccType.RW, 0.001, 100.0, ""            , False, True, True, "Integral Gain")
            self._add_param_enum(f"Pressure Control.Controller {i}.PI/Soft Pump Settings.Pressure Scaler"                , f"071{i}0223",  0, ParamAccType.RW, p_enum.PresScalerEnum       , False, True, True, None)
            
            self._add_param_enum(f"Pressure Control.Controller {i}.Ramp.Enable"                                          , f"071{i}0301", 0, ParamAccType.RW, p_enum.FalseTrueEnum         , False, True, True, None)
            self._add_param_real(f"Pressure Control.Controller {i}.Ramp.Time [sec]"                                      , f"071{i}0302", 0, ParamAccType.RW, 0, 1000000.0, "sec"          , False, True, True, "Target reach time")
            self._add_param_pres(f"Pressure Control.Controller {i}.Ramp.Slope"                                           , f"071{i}0303", 0, ParamAccType.RW                               , False, True, True, "")
            self._add_param_enum(f"Pressure Control.Controller {i}.Ramp.Mode"                                            , f"071{i}0304", 0, ParamAccType.RW, p_enum.PresRampModeEnum      , False, True, True, None)
            self._add_param_enum(f"Pressure Control.Controller {i}.Ramp.Start Value"                                     , f"071{i}0305", 0, ParamAccType.RW, p_enum.PresRampStartValueEnum, False, True, True, None)
            self._add_param_enum(f"Pressure Control.Controller {i}.Ramp.Type"                                            , f"071{i}0306", 0, ParamAccType.RW, p_enum.RampTypeEnum          , False, True, True, None)
        
        '''              
        RS232/RS485 User interface            1
        '''   
        self._add_param_enum("RS232/RS485 User interface.Settings.Operation Mode"                                        , "A1010000", 0, ParamAccType.RW, p_enum.RS232OpModeEnum            , False, True, True, None)
        self._add_param_num ("RS232/RS485 User interface.Settings.Address"                                               , "A1110A00", 0, ParamAccType.RW, 0, 255, ""                        , False, True, True, "Only used if Operation Mode = RS485")
        self._add_param_enum("RS232/RS485 User interface.Settings.Baud Rate"                                             , "A1110100", 0, ParamAccType.RW, p_enum.RS232BaudRateEnum          , False, True, True, None)
        self._add_param_enum("RS232/RS485 User interface.Settings.Command Set"                                           , "A1110500", 0, ParamAccType.RW, p_enum.RS232CommandSetEnum        , False, True, True, None)
        self._add_param_enum("RS232/RS485 User interface.Settings.Command Termination"                                   , "A1110B00", 0, ParamAccType.RW, p_enum.RS232CommandTerminationEnum, False, True, True, None)
        self._add_param_enum("RS232/RS485 User interface.Settings.Data Bit Length"                                       , "A1110200", 0, ParamAccType.RW, p_enum.RS232DataBitLengthEnum     , False, True, True, None)
        self._add_param_enum("RS232/RS485 User interface.Settings.Network"                                               , "A1110900", 0, ParamAccType.RW, p_enum.RS232NetworkEnum           , False, True, True, None)
        self._add_param_enum("RS232/RS485 User interface.Settings.Parity Bit"                                            , "A1110400", 0, ParamAccType.RW, p_enum.RS232ParityBitEnum         , False, True, True, None)
        self._add_param_enum("RS232/RS485 User interface.Settings.Stop Bit"                                              , "A1110300", 0, ParamAccType.RW, p_enum.RS232StopBitEnum           , False, True, True, None)
        self._add_param_enum("RS232/RS485 User interface.Settings.Topology"                                              , "A1110800", 0, ParamAccType.RW, p_enum.RS232TopologyEnum          , False, True, True, None)

        self._add_param_enum("RS232/RS485 User interface.Scaling.Position.Position Unit"                                 , "A1120101", 0, ParamAccType.RW, p_enum.RS232PositionUnitEnum      , False, True, True, None)
        self._add_param_real("RS232/RS485 User interface.Scaling.Position.Value Closest Position"                        , "A1120102", 0, ParamAccType.RW, f_min, f_max, ""                  , False, True, True, "")
        self._add_param_real("RS232/RS485 User interface.Scaling.Position.Value Open Position"                           , "A1120103", 0, ParamAccType.RW, f_min, f_max, ""                  , False, True, True, "")
        self._add_param_enum("RS232/RS485 User interface.Scaling.Pressure.Pressure Unit"                                 , "A1120201", 0, ParamAccType.RW, p_enum.RS232PressureUnitEnum      , False, True, True, None)
        self._add_param_real("RS232/RS485 User interface.Scaling.Pressure.Value Pressure 0"                              , "A1120202", 0, ParamAccType.RW, f_min, f_max, ""                  , False, True, True, "")
        self._add_param_real("RS232/RS485 User interface.Scaling.Pressure.Value Pressure Sensor Full Scale"              , "A1120203", 0, ParamAccType.RW, f_min, f_max, ""                  , False, True, True, "")

        '''
        NVM for Compounds
        '''
        self._add_param_nvm_compound("Compound Commands.NVM For Sevice.Compound Commands 1.[0]" , "B10A0100",  0)#, "System.Access Mode")
        self._add_param_nvm_compound("Compound Commands.NVM For Sevice.Compound Commands 1.[1]" , "B10A0100",  1)#, "System.Control Mode")
        self._add_param_nvm_compound("Compound Commands.NVM For Sevice.Compound Commands 1.[2]" , "B10A0100",  2)#, "Position Control.Basic.Actual Position")
        self._add_param_nvm_compound("Compound Commands.NVM For Sevice.Compound Commands 1.[3]" , "B10A0100",  3)#, "Position Control.Basic.Target Position Used")
        self._add_param_nvm_compound("Compound Commands.NVM For Sevice.Compound Commands 1.[4]" , "B10A0100",  4)#, "Pressure Control.Basic.Actual Pressure")
        self._add_param_nvm_compound("Compound Commands.NVM For Sevice.Compound Commands 1.[5]" , "B10A0100",  5)#, "Pressure Control.Basic.Target Pressure Used")
        self._add_param_nvm_compound("Compound Commands.NVM For Sevice.Compound Commands 1.[6]" , "B10A0100",  6)#, "Position Control.Basic.Position Control Speed Used")
        self._add_param_nvm_compound("Compound Commands.NVM For Sevice.Compound Commands 1.[7]" , "B10A0100",  7)#, "Pressure Control.Basic.Controller Selector Used")
        self._add_param_nvm_compound("Compound Commands.NVM For Sevice.Compound Commands 1.[8]" , "B10A0100",  8)#, "System.Warning/Error.Warning Bitmap")
        self._add_param_nvm_compound("Compound Commands.NVM For Sevice.Compound Commands 1.[9]" , "B10A0100",  9)#, "System.Warning/Error.Error Bitmap")
        self._add_param_nvm_compound("Compound Commands.NVM For Sevice.Compound Commands 1.[10]", "B10A0100", 10)#, "System.Warning/Error.Error Number")
        self._add_param_nvm_compound("Compound Commands.NVM For Sevice.Compound Commands 1.[11]", "B10A0100", 11)#, "System.Warning/Error.Error Code")
        self._add_param_nvm_compound("Compound Commands.NVM For Sevice.Compound Commands 1.[12]", "B10A0100", 12)
        self._add_param_nvm_compound("Compound Commands.NVM For Sevice.Compound Commands 1.[13]", "B10A0100", 13)
        self._add_param_nvm_compound("Compound Commands.NVM For Sevice.Compound Commands 1.[14]", "B10A0100", 14)
        self._add_param_nvm_compound("Compound Commands.NVM For Sevice.Compound Commands 1.[15]", "B10A0100", 15)
        self._add_param_nvm_compound("Compound Commands.NVM For Sevice.Compound Commands 1.[16]", "B10A0100", 16)
        self._add_param_nvm_compound("Compound Commands.NVM For Sevice.Compound Commands 1.[17]", "B10A0100", 17)
        self._add_param_nvm_compound("Compound Commands.NVM For Sevice.Compound Commands 1.[18]", "B10A0100", 18)
        self._add_param_nvm_compound("Compound Commands.NVM For Sevice.Compound Commands 1.[19]", "B10A0100", 19)

        #for i in range(0, 20):
        #    self._add_param_nvm_compound(f"Compound Commands.NVM For Sevice.Compound Commands 2.2 [{i}]", "B10A0200", i, ParamAccType.RW, False, False, None)

    def _add_param_btn(self, full_path: str, id: str, index: int, param_acc : ParamAccType, write_str: str, is_only_local_acc:bool, is_nor_backup: bool, is_fu_backup: bool, description: str | None):
        path, name = full_path.rsplit(".", 1)

        self._add_param(Parameter(path, name, id, index, ParamDisplayType.BTN, ParamDataType.UINT32, param_acc, is_only_local_acc, is_nor_backup, is_fu_backup, "", int(0), int(0), None, description, write_str))


    def _add_param_enum(self, full_path: str, id: str, index: int, param_acc : ParamAccType, enum_class: type, is_only_local_acc:bool, is_nor_backup: bool, is_fu_backup: bool, description: str | None):
        path, name = full_path.rsplit(".", 1)

        if not description:
            items = [f"{item.value}: {item.description}" for item in enum_class]
            description = "<br>".join(items)

        self._add_param(Parameter(path, name, id, index, ParamDisplayType.ENUM, ParamDataType.UINT32, param_acc, is_only_local_acc, is_nor_backup, is_fu_backup, "", int(0), int(0), enum_class, description))


    def _add_param_bitmap(self, full_path: str, id: str, index: int, param_acc : ParamAccType, enum_class: type, is_only_local_acc:bool, is_nor_backup: bool, is_fu_backup: bool, description: str | None):
        path, name = full_path.rsplit(".", 1)

        if not description:
            items = [f"{item.value}: {item.description}" for item in enum_class]
            description = "<br>".join(items)

        self._add_param(Parameter(path, name, id, index, ParamDisplayType.BITMAP, ParamDataType.UINT32, param_acc, is_only_local_acc, is_nor_backup, is_fu_backup, "", int(0), int(4294967295), enum_class, description))


    def _add_param_errnum(self, full_path: str, id: str, index: int, param_acc : ParamAccType, enum_class1: type, name1: str, enum_class2: type, name2: str, enum_class3: type, name3: str, is_only_local_acc:bool, is_nor_backup: bool, is_fu_backup: bool, description: str | None):
        path, name = full_path.rsplit(".", 1)

        if not description:
            items1 = [f"{item.value}: {item.description}" for item in enum_class1]
            items2 = [f"{item.value}: {item.description}" for item in enum_class2]
            items3 = [f"{item.value}: {item.description}" for item in enum_class3]
            description = "<br>".join(items1 + items2 + items3)

        errnumparam = ParameterErrNum(path, name, id, index, ParamDisplayType.ERR_NUM , ParamDataType.UINT32, param_acc, is_only_local_acc, is_nor_backup, is_fu_backup, "", int(0), int(4294967295), description)
        errnumparam.add_ref_list(name1, enum_class1) 
        errnumparam.add_ref_list(name2, enum_class2) 
        errnumparam.add_ref_list(name3, enum_class3) 

        self._add_param(errnumparam)        


    def _add_param_text(self, full_path: str, id: str, index: int, param_acc : ParamAccType, is_only_local_acc:bool, is_nor_backup: bool, is_fu_backup: bool, description: str):
        path, name = full_path.rsplit(".", 1)
        self._add_param(Parameter(path, name, id, index, ParamDisplayType.TEXT, ParamDataType.STR, param_acc, is_only_local_acc, is_nor_backup, is_fu_backup, "", int(0), int(0), None, description))


    def _add_param_hex(self, full_path: str, id: str, index: int, param_acc : ParamAccType, is_only_local_acc:bool, is_nor_backup: bool, is_fu_backup: bool, description: str):
        path, name = full_path.rsplit(".", 1)
        self._add_param(Parameter(path, name, id, index, ParamDisplayType.HEX, ParamDataType.UINT32, param_acc, is_only_local_acc, is_nor_backup, is_fu_backup, "", int(0), int(4294967295), None, description))


    def _add_param_num(self, full_path: str, id: str, index: int, param_acc : ParamAccType, min_value: int, max_value: int, unit: str, is_only_local_acc:bool, is_nor_backup: bool, is_fu_backup: bool, description: str):
        path, name = full_path.rsplit(".", 1)
        self._add_param(Parameter(path, name, id, index, ParamDisplayType.NUMBER, ParamDataType.UINT32, param_acc, is_only_local_acc, is_nor_backup, is_fu_backup, unit, min_value, max_value, None, description))

    def _add_param_pres(self, full_path: str, id: str, index: int, param_acc : ParamAccType, is_only_local_acc:bool, is_nor_backup: bool, is_fu_backup: bool, description: str):
        path, name = full_path.rsplit(".", 1)
        self._add_param(Parameter(path, name, id, index, ParamDisplayType.SENS_PRES, ParamDataType.FLOAT, param_acc, is_only_local_acc, is_nor_backup, is_fu_backup, "", float(-3.4028235e+38), float(3.4028235e+38), None, description))

    def _add_param_posi(self, full_path: str, id: str, index: int, param_acc : ParamAccType, is_only_local_acc:bool, is_nor_backup: bool, is_fu_backup: bool, description: str):
        path, name = full_path.rsplit(".", 1)
        self._add_param(Parameter(path, name, id, index, ParamDisplayType.POSI, ParamDataType.FLOAT, param_acc, is_only_local_acc, is_nor_backup, is_fu_backup, "", float(-3.4028235e+38), float(3.4028235e+38), None, description))

    def _add_param_real(self, full_path: str, id: str, index: int, param_acc : ParamAccType, min_value: float, max_value: float, unit: str, is_only_local_acc:bool, is_nor_backup: bool, is_fu_backup: bool, description: str):
        path, name = full_path.rsplit(".", 1)
        self._add_param(Parameter(path, name, id, index, ParamDisplayType.REAL, ParamDataType.FLOAT, param_acc, is_only_local_acc, is_nor_backup, is_fu_backup, unit, min_value, max_value, None, description))   

    def _add_param_nvm_compound(self, full_path: str, id: str, index: int):
        path, name = full_path.rsplit(".", 1)
        self._add_param(Parameter(path, name, id, index, ParamDisplayType.HEX, ParamDataType.UINT32, ParamAccType.RW, False, False, False, "", int(0), int(4294967295), None, ""))

    def _add_param(self, param: Parameter):
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
        
