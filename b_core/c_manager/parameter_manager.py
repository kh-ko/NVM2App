
import json
import threading

from typing import Union, List, Dict, Optional
from PySide6.QtCore import QFile, QIODevice

from b_core.a_define import file_folder_path as path_def
from b_core.b_datatype import param_enum as p_enum
from b_core.b_datatype.general_enum import LogType, ParamDataType, ParamAccType, ParamDisplayType
from b_core.c_manager.log_manager import LogManager
from b_core.b_datatype.parameter_digi import ParameterDigi
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
        self._add_param_enum  ("System.Access Mode"                                                                         , "0F0B0000",  0, ParamAccType.RW, p_enum.AccModeEnum          , False, False, None)
        self._add_param_enum  ("System.Control Mode"                                                                        , "0F020000",  0, ParamAccType.RW, p_enum.ControlModeEnum      , False, False, None)
        self._add_param_text  ("System.Identification.Serial Number"                                                        , "0F100100",  0, ParamAccType.RO,                               False, False, "Identification of the product")
        self._add_param_enum  ("System.Identification.Configuration.Model"                                                  , "B0000100",  0, ParamAccType.RW, p_enum.SysModelEnum         , False, False, None)
        self._add_param_enum  ("System.Identification.Configuration.Valve Type"                                             , "B0000100",  1, ParamAccType.RW, p_enum.SysValveTypeEnum     , False, False, None)
        self._add_param_enum  ("System.Identification.Configuration.Sealing Type"                                           , "B0000100",  2, ParamAccType.RW, p_enum.SysSealingTypeEnum   , False, False, None)
        self._add_param_enum  ("System.Identification.Configuration.Flange Size"                                            , "B0000100",  3, ParamAccType.RW, p_enum.SysFlangeSizeEnum    , False, False, None)
        self._add_param_enum  ("System.Identification.Configuration.Contract Method"                                        , "B0000100",  4, ParamAccType.RW, p_enum.SysContractMethodEnum, False, False, None)
        self._add_param_enum  ("System.Identification.Configuration.Body Material"                                          , "B0000100",  5, ParamAccType.RW, p_enum.SysBodyMaterialEnum  , False, False, None)
        self._add_param_enum  ("System.Identification.Configuration.User Interface"                                         , "B0000100",  6, ParamAccType.RW, p_enum.SysUserInterfaceEnum , False, False, None)
        self._add_param_enum  ("System.Identification.Configuration.Power Option"                                           , "B0000100",  7, ParamAccType.RW, p_enum.SysPowerOptionEnum   , False, False, None)
        self._add_param_enum  ("System.Identification.Configuration.Sensor Number"                                          , "B0000100",  8, ParamAccType.RW, p_enum.SysSensorNumberEnum  , False, False, None)
        self._add_param_enum  ("System.Identification.Configuration.Revision 1"                                             , "B0000100",  9, ParamAccType.RW, p_enum.Base36Enum           , False, False, "Valve Hardware Revision 1")
        self._add_param_enum  ("System.Identification.Configuration.Revision 2"                                             , "B0000100", 10, ParamAccType.RW, p_enum.Base36Enum           , False, False, "Valve Hardware Revision 2")
        self._add_param_enum  ("System.Identification.Configuration.Revision 3"                                             , "B0000100", 11, ParamAccType.RW, p_enum.Base36Enum           , False, False, "Valve Hardware Revision 3")
        self._add_param_hex   ("System.Identification.Configuration.Product Number"                                         , "B0000100", 12, ParamAccType.RW,                               False, False, "Product number")
        self._add_param_hex   ("System.Identification.Configuration.Product Number Ex"                                      , "B0000100", 13, ParamAccType.RW,                               False, False, "Extended Product Number")
        self._add_param_num   ("System.Statistics.Power Up Counter"                                                         , "0F200100",  0, ParamAccType.RO, un_min, un_max, ""          , False, False, "")
        self._add_param_real  ("System.Statistics.Total Time Powered"                                                       , "0F200200",  0, ParamAccType.RO, f_min, f_max, "sec"         , False, False, "")
        self._add_param_real  ("System.Statistics.Time Since Power On"                                                      , "0F200300",  0, ParamAccType.RO, f_min, f_max, "sec"         , False, False, "")
        self._add_param_bitmap("System.Warning/Error.Warning Bitmap"                                                        , "0F300100",  0, ParamAccType.RO, p_enum.SysWarningBitmap     , False, False, None)
        self._add_param_bitmap("System.Warning/Error.Error Bitmap"                                                          , "0F300500",  0, ParamAccType.RO, p_enum.SysErrorBitmap       , False, False, None)
        self._add_param_3digi ("System.Warning/Error.Error Number"                                                          , "0F300600",  0, ParamAccType.RO, p_enum.SysErrorNumberComponent, p_enum.SysErrorNumberMode, p_enum.SysErrorNumberType, False, False, None)
        self._add_param_enum  ("System.Warning/Error.Error Code"                                                            , "0F300700",  0, ParamAccType.RO, p_enum.SysErrorCodeEnum     , False, False, None)
        self._add_param_enum  ("System.Services.Restart Controller"                                                         , "0F500100",  0, ParamAccType.RW, p_enum.FalseTrueEnum        , False, False, "Emulates a power cycle")
        self._add_param_enum  ("System.Services.Configuration Lock Mode"                                                    , "0F500500",  0, ParamAccType.RW, p_enum.FalseTrueEnum        , False, False, "Locking the valve settings.<br>If true, no changes to the settings are possible.")
       
        '''       
        Sensor       
        '''       
        self._add_param_pres  ("Sensor.Sensor 1.Basic.Actual Pressure Valuee"                                               , "12010A00",  0, ParamAccType.RO,                               False, False, "Pressure value of the sensor")
        self._add_param_enum  ("Sensor.Sensor 1.Basic.Available"                                                            , "12010100",  0, ParamAccType.RW, p_enum.FalseTrueEnum        , True , True , None)
        self._add_param_enum  ("Sensor.Sensor 1.Basic.Enable"                                                               , "12010200",  0, ParamAccType.RW, p_enum.FalseTrueEnum        , True , True , None)
        self._add_param_enum  ("Sensor.Sensor 1.Basic.Input Source"                                                         , "12010600",  0, ParamAccType.RW, p_enum.SensInSrcEnum        , True , True , None)
        self._add_param_enum  ("Sensor.Sensor 1.Basic.Scale"                                                                , "12010310",  0, ParamAccType.RW, p_enum.SensorScaleEnum      , True , True , None)
        self._add_param_enum  ("Sensor.Sensor 1.Range.Data Unit"                                                            , "12010301",  0, ParamAccType.RW, p_enum.SensUnitEnum         , True , True , None)
        self._add_param_real  ("Sensor.Sensor 1.Range.Upper Limit Data Value"                                               , "12010302",  0, ParamAccType.RW, f_min, f_max, ""            , True , True, "Define the range of the pressure sensor.")
        self._add_param_real  ("Sensor.Sensor 1.Range.Lower Limit Data Value"                                               , "12010303",  0, ParamAccType.RW, f_min, f_max, ""            , True , True, "Define the range of the pressure sensor.")
        self._add_param_real  ("Sensor.Sensor 1.Range.Upper Limit Voltage Value"                                            , "12010304",  0, ParamAccType.RW, f_min, f_max, "V"           , True , True, "Defines the voltage range of the sensor.")
        self._add_param_real  ("Sensor.Sensor 1.Range.Lower Limit Voltage Value"                                            , "12010305",  0, ParamAccType.RW, f_min, f_max, "V"           , True , True, "Defines the voltage range of the sensor.")
        self._add_param_real  ("Sensor.Sensor 1.Range.Voltage Per Decade"                                                   , "12010311",  0, ParamAccType.RW, f_min, f_max, "V"           , True , True, "E.g.: Logarithmic Sensor with 1000Torr SFS at 9.0V and 1V/Decade:<br>Upper Limit Data Value = 1000,<br>Upper Limit Voltage Value = 9,<br>Voltage Per Decade := 1")
        self._add_param_enum  ("Sensor.Sensor 1.Zero Adjust.Enable"                                                         , "12010401",  0, ParamAccType.RW, p_enum.FalseTrueEnum        , True , True , None)
        self._add_param_real  ("Sensor.Sensor 1.Zero Adjust.Offset Value [SFS]"                                             , "12010402",  0, ParamAccType.RW, 0.0  , 1.0  , "SFS"         , True , True , "Value 1.0 means sensor full scale. For example for a 0-10 Volt gauge the value 0.1 means 1 Volt")
        self._add_param_enum  ("Sensor.Sensor 1.Filter.Enable"                                                              , "12010501",  0, ParamAccType.RW, p_enum.FalseTrueEnum        , True , True , None)
        self._add_param_real  ("Sensor.Sensor 1.Filter.Time"                                                                , "12010502",  0, ParamAccType.RW, 0.0  , 1.0  , "sec"         , True , True , "")
        self._add_param_pres  ("Sensor.Sensor 1.Analog Sensor Input.Value"                                                  , "12011101",  0, ParamAccType.RO,                               False, False, "Pressure value of the sensor")
        self._add_param_pres  ("Sensor.Sensor 1.Digital Sensor Input.Value"                                                 , "1201100A",  0, ParamAccType.RO,                               False, False, "Pressure value of the sensor")
        
        self._add_param_pres  ("Sensor.Sensor 2.Basic.Actual Pressure Valuee"                                               , "12020A00",  0, ParamAccType.RO,                               False, False, "Pressure value of the sensor")
        self._add_param_enum  ("Sensor.Sensor 2.Basic.Available"                                                            , "12020100",  0, ParamAccType.RW, p_enum.FalseTrueEnum        , True , True , None)
        self._add_param_enum  ("Sensor.Sensor 2.Basic.Enable"                                                               , "12020200",  0, ParamAccType.RW, p_enum.FalseTrueEnum        , True , True , None)
        self._add_param_enum  ("Sensor.Sensor 2.Basic.Input Source"                                                         , "12020600",  0, ParamAccType.RW, p_enum.SensInSrcEnum        , True , True , None)
        self._add_param_enum  ("Sensor.Sensor 2.Basic.Scale"                                                                , "12020310",  0, ParamAccType.RW, p_enum.SensorScaleEnum      , True , True , None)
        self._add_param_enum  ("Sensor.Sensor 2.Range.Data Unit"                                                            , "12020301",  0, ParamAccType.RW, p_enum.SensUnitEnum         , True , True , None)
        self._add_param_real  ("Sensor.Sensor 2.Range.Upper Limit Data Value"                                               , "12020302",  0, ParamAccType.RW, f_min, f_max, ""            , True , True, "Define the range of the pressure sensor.")
        self._add_param_real  ("Sensor.Sensor 2.Range.Lower Limit Data Value"                                               , "12020303",  0, ParamAccType.RW, f_min, f_max, ""            , True , True, "Define the range of the pressure sensor.")
        self._add_param_real  ("Sensor.Sensor 2.Range.Upper Limit Voltage Value"                                            , "12020304",  0, ParamAccType.RW, f_min, f_max, "V"           , True , True, "Defines the voltage range of the sensor.")
        self._add_param_real  ("Sensor.Sensor 2.Range.Lower Limit Voltage Value"                                            , "12020305",  0, ParamAccType.RW, f_min, f_max, "V"           , True , True, "Defines the voltage range of the sensor.")
        self._add_param_real  ("Sensor.Sensor 2.Range.Voltage Per Decade"                                                   , "12020311",  0, ParamAccType.RW, f_min, f_max, "V"           , True , True, "E.g.: Logarithmic Sensor with 1000Torr SFS at 9.0V and 1V/Decade:<br>Upper Limit Data Value = 1000,<br>Upper Limit Voltage Value = 9,<br>Voltage Per Decade := 1")
        self._add_param_enum  ("Sensor.Sensor 2.Zero Adjust.Enable"                                                         , "12020401",  0, ParamAccType.RW, p_enum.FalseTrueEnum        , True , True , None)
        self._add_param_real  ("Sensor.Sensor 2.Zero Adjust.Offset Value [SFS]"                                             , "12020402",  0, ParamAccType.RW, 0.0  , 1.0  , "SFS"         , True , True , "Value 1.0 means sensor full scale. For example for a 0-10 Volt gauge the value 0.1 means 1 Volt")
        self._add_param_enum  ("Sensor.Sensor 2.Filter.Enable"                                                              , "12020501",  0, ParamAccType.RW, p_enum.FalseTrueEnum        , True , True , None)
        self._add_param_real  ("Sensor.Sensor 2.Filter.Time"                                                                , "12020502",  0, ParamAccType.RW, 0.0  , 1.0  , "sec"         , True , True , "")
        self._add_param_pres  ("Sensor.Sensor 2.Analog Sensor Input.Value"                                                  , "12021101",  0, ParamAccType.RO,                               False, False, "Pressure value of the sensor")
        self._add_param_pres  ("Sensor.Sensor 2.Digital Sensor Input.Value"                                                 , "1202100A",  0, ParamAccType.RO,                               False, False, "Pressure value of the sensor")
              
        self._add_param_enum  ("Sensor.Crossover.Crossover Mode"                                                            , "12050100",  0, ParamAccType.RW, p_enum.SensCrossModeEnum    , True , True , None)
        self._add_param_real  ("Sensor.Crossover.Threshold High [SFS low sensor]"                                           , "12050300",  0, ParamAccType.RW, 0.0  , 1.0  , "SFS"         , True , True , "Defines the transition area respectively the hysteresis limits")
        self._add_param_real  ("Sensor.Crossover.Threshold Low [SFS low sensor]"                                            , "12050200",  0, ParamAccType.RW, 0.0  , 1.0  , "SFS"         , True , True , "Defines the transition area respectively the hysteresis limits")
        self._add_param_real  ("Sensor.Crossover.Delay"                                                                     , "12050400",  0, ParamAccType.RW, 0.0  , f_max, "sec"         , True , True , "Only relevant in Crossover Mode = Hard Switch Delay start after reaching the hysteresis limit")
        
        '''
        Position Control
        '''
        self._add_param_posi  ("Position Control.Basic.Target Position Used"                                                , "10660600",  0, ParamAccType.RO,                               False, False, "")
        self._add_param_posi  ("Position Control.Basic.Actual Position"                                                     , "11010000",  0, ParamAccType.RO,                               False, False, "")
        self._add_param_real  ("Position Control.Basic.Position Control Speed"                                              , "11030000",  0, ParamAccType.RO, 0.0  , 1.0  , ""            , False, False, "Speed valid in Control Mode = Position 1.0 equals to full speed")
        self._add_param_posi  ("Position Control.Basic.Target Position"                                                     , "11020000",  0, ParamAccType.RW,                               False, False, "")
        self._add_param_enum  ("Position Control.Ramp.Enable"                                                               , "11620100",  0, ParamAccType.RW, p_enum.FalseTrueEnum        , True , True , None)
        self._add_param_enum  ("Position Control.Ramp.Mode"                                                                 , "11620400",  0, ParamAccType.RW, p_enum.PosiRampModeEnum     , True , True , None)
        self._add_param_posi  ("Position Control.Ramp.Slope"                                                                , "11620300",  0, ParamAccType.RW,                               True , True , "")
        self._add_param_real  ("Position Control.Ramp.Time"                                                                 , "11620200",  0, ParamAccType.RW, 0.0  , f_max, "sec"         , True , True , "")
        self._add_param_enum  ("Position Control.Ramp.Type"                                                                 , "11620500",  0, ParamAccType.RW, p_enum.RampTypeEnum         , True , True , None)
                      
        '''              
        Pressure Control              
        '''              
        self._add_param_pres  ("Pressure Control.Basic.Actual Pressure"                                                     , "07010000",  0, ParamAccType.RO,                               False, False, "")
        self._add_param_enum  ("Pressure Control.Basic.Controller Selector"                                                 , "07100000",  0, ParamAccType.RW, p_enum.PresCtrlSelEnum      , True , True , None)
        self._add_param_enum  ("Pressure Control.Basic.Controller Selector Used"                                            , "07100100",  0, ParamAccType.RO, p_enum.PresCtrlSelEnum      , False, False, None)
        self._add_param_real  ("Pressure Control.Basic.Conductance[l/s]"                                                    , "07100200",  0, ParamAccType.RO, 0.0  , f_max, "l/s"         , False, False, "")
        self._add_param_real  ("Pressure Control.Basic.MFC Flow"                                                            , "07100300",  0, ParamAccType.RO, 0.0  , f_max, ""            , False, False, "")
        self._add_param_enum  ("Pressure Control.Basic.MFC Flow Unit"                                                       , "07100400",  0, ParamAccType.RO, p_enum.MFCFlowUnitEnum      , False, False, None)
        self._add_param_real  ("Pressure Control.Basic.Chamber Volume [L]"                                                  , "07100800",  0, ParamAccType.RO, 0.0  , f_max, "L"           , False, False, "")
        self._add_param_real  ("Pressure Control.Basic.Adaptive Conductance gain"                                           , "07100500",  0, ParamAccType.RO, 0.0  , f_max, ""            , False, False, "")
        self._add_param_real  ("Pressure Control.Basic.Adaptive Flow gain"                                                  , "07100600",  0, ParamAccType.RO, 0.0  , f_max, ""            , False, False, "")
        self._add_param_real  ("Pressure Control.Basic.Adaptive Total gain"                                                 , "07100700",  0, ParamAccType.RO, 0.0  , f_max, ""            , False, False, "")
        self._add_param_real  ("Pressure Control.Basic.Pressure Control Speed"                                              , "07050000",  0, ParamAccType.RW, 0.001, 1.0  , ""            , True , True , "Speed valid in Control Mode = Pressure 1.0 equals to full speed")
        self._add_param_pres  ("Pressure Control.Basic.Target Pressure"                                                     , "07020000",  0, ParamAccType.RW,                               False, False, "")
        self._add_param_pres  ("Pressure Control.Basic.Target Pressure Used"                                                , "07030000",  0, ParamAccType.RO,                               False, False, "This value is set as pressure controller input.<br>It differs to the Target Pressure if a pressure ramp is used.")
        
        #self._add_param(Parameter("Pressure Control.General Settings", "Store Control Parameter Volatile", "07301100", 0, ParamDisplayType.ENUM     , ParamDataType.UINT32, ParamAccType.RW, False, False, ""   ,int(un_min), int(un_min), p_enum.FalseTrueEnum, "0: Store in NV Memory, 1: Do Not Store in NV Memory"))
        self._add_param_enum  ("Pressure Control.General Settings.Control Position Restriction.Enable"                      , "07301201",  0, ParamAccType.RW, p_enum.FalseTrueEnum        , True, True, None)   
        self._add_param_posi  ("Pressure Control.General Settings.Control Position Restriction.Maximum Control Position"    , "07301203",  0, ParamAccType.RW,                               True, True, "Limit the movement during pressure control") 
        self._add_param_posi  ("Pressure Control.General Settings.Control Position Restriction.Minimum Control Position"    , "07301202",  0, ParamAccType.RW,                               True, True, "Limit the movement during pressure control") 
        self._add_param_enum  ("Pressure Control.General Settings.Automated Controller Selector.Enable"                     , "07301701",  0, ParamAccType.RW, p_enum.FalseTrueEnum        , True, True, None) 
        self._add_param_enum  ("Pressure Control.General Settings.Automated Controller Selector.Mode"                       , "07301702",  0, ParamAccType.RW, p_enum.AutoCtrlModeEnum     , True, True, None) 
        self._add_param_enum  ("Pressure Control.General Settings.Automated Controller Selector.Controller Pressure Rising" , "07301720",  0, ParamAccType.RW, p_enum.PresCtrlSelEnum      , True, True, None) 
        self._add_param_enum  ("Pressure Control.General Settings.Automated Controller Selector.Controller Pressure Falling", "07301721",  0, ParamAccType.RW, p_enum.PresCtrlSelEnum      , True, True, None) 
        self._add_param_bitmap("Pressure Control.General Settings.Automated Controller Selector.Controller Selector Bitmap" , "07301703",  0, ParamAccType.RW, p_enum.PresCtrlSelBitmap    , True, True, None)
        self._add_param_enum  ("Pressure Control.General Settings.Automated Controller Selector.Threshold Condition"        , "07301710",  0, ParamAccType.RW, p_enum.PresCtrlThresCondEnum, True, True, None)  
        self._add_param_pres  ("Pressure Control.General Settings.Automated Controller Selector.Controller 1 Threshold"     , "07301704",  0, ParamAccType.RW,                               True, True, "Used if Mode = Threshold")
        self._add_param_pres  ("Pressure Control.General Settings.Automated Controller Selector.Controller 2 Threshold"     , "07301705",  0, ParamAccType.RW,                               True, True, "Used if Mode = Threshold")
        self._add_param_pres  ("Pressure Control.General Settings.Automated Controller Selector.Controller 3 Threshold"     , "07301706",  0, ParamAccType.RW,                               True, True, "Used if Mode = Threshold")
        self._add_param_pres  ("Pressure Control.General Settings.Automated Controller Selector.Controller 4 Threshold"     , "07301707",  0, ParamAccType.RW,                               True, True, "Used if Mode = Threshold")
        

        for i in range(1, 5):
            self._add_param_enum(f"Pressure Control.Controller {i}.Control Algorithm.Algorithm mode"                     , f"071{i}0100",  0, ParamAccType.RW, p_enum.PresCtrlAlgoEnum     , True, True, None)
            self._add_param_real(f"Pressure Control.Controller {i}.Adaptive Settings.Gain Factor"                        , f"071{i}0203",  0, ParamAccType.RW, 0.0001, 100.0, ""           , True, True, "")
            self._add_param_real(f"Pressure Control.Controller {i}.Adaptive Settings.Delta Factor"                       , f"071{i}0207",  0, ParamAccType.RW, 0.0001, 100.0, ""           , True, True, "")
            self._add_param_real(f"Pressure Control.Controller {i}.Adaptive Settings.Sensor Delay"                       , f"071{i}0204",  0, ParamAccType.RW, 0.0   , 1.0  , "sec"        , True, True, "")
            self._add_param_enum(f"Pressure Control.Controller {i}.Adaptive Settings.Learn Data Selection"               , f"071{i}0205",  0, ParamAccType.RW, p_enum.LearnDataSelEnum     , True, True, None)
            
            self._add_param_enum(f"Pressure Control.Controller {i}.PI/Soft Pump Settings.Control Direction"              , f"071{i}0206",  0, ParamAccType.RW, p_enum.CtrlDirEnum          , True, True, None)
            self._add_param_real(f"Pressure Control.Controller {i}.PI/Soft Pump Settings.P-Gain"                         , f"071{i}0201",  0, ParamAccType.RW, 0.001, 100.0, ""            , True, True, "Proportional Gain")
            self._add_param_real(f"Pressure Control.Controller {i}.PI/Soft Pump Settings.I-Gain"                         , f"071{i}0202",  0, ParamAccType.RW, 0.001, 100.0, ""            , True, True, "Integral Gain")
            self._add_param_enum(f"Pressure Control.Controller {i}.PI/Soft Pump Settings.Pressure Scaler"                , f"071{i}0223",  0, ParamAccType.RW, p_enum.PresScalerEnum       , True, True, None)
            
            self._add_param_enum(f"Pressure Control.Controller {i}.Ramp.Enable"                                          , f"071{i}0301", 0, ParamAccType.RW, p_enum.FalseTrueEnum         , True, True, None)
            self._add_param_real(f"Pressure Control.Controller {i}.Ramp.Time"                                            , f"071{i}0302", 0, ParamAccType.RW, 0, 1000000.0, "sec"          , True, True, "Target reach time")
            self._add_param_pres(f"Pressure Control.Controller {i}.Ramp.Slope"                                           , f"071{i}0303", 0, ParamAccType.RW                               , True, True, "")
            self._add_param_enum(f"Pressure Control.Controller {i}.Ramp.Mode"                                            , f"071{i}0304", 0, ParamAccType.RW, p_enum.PresRampModeEnum      , True, True, None)
            self._add_param_enum(f"Pressure Control.Controller {i}.Ramp.Start Value"                                     , f"071{i}0305", 0, ParamAccType.RW, p_enum.PresRampStartValueEnum, True, True, None)
            self._add_param_enum(f"Pressure Control.Controller {i}.Ramp.Type"                                            , f"071{i}0306", 0, ParamAccType.RW, p_enum.RampTypeEnum          , True, True, None)
        
        '''              
        RS232 User interface            
        '''   
        self._add_param_enum("RS232 User interface.Settings.Operation Mode"                                                 , "A1010000", 0, ParamAccType.RW, p_enum.RS232OpModeEnum            , True, True, None)
        self._add_param_num ("RS232 User interface.Settings.Address"                                                        , "A1110A00", 0, ParamAccType.RW, 0, 255, ""                        , True, True, "Only used if Operation Mode = RS485")
        self._add_param_enum("RS232 User interface.Settings.Baud Rate"                                                      , "A1110100", 0, ParamAccType.RW, p_enum.RS232BaudRateEnum          , True, True, None)
        self._add_param_enum("RS232 User interface.Settings.Command Set"                                                    , "A1110500", 0, ParamAccType.RW, p_enum.RS232CommandSetEnum        , True, True, None)
        self._add_param_enum("RS232 User interface.Settings.Command Termination"                                            , "A1110B00", 0, ParamAccType.RW, p_enum.RS232CommandTerminationEnum, True, True, None)
        self._add_param_enum("RS232 User interface.Settings.Data Bit Length"                                                , "A1110200", 0, ParamAccType.RW, p_enum.RS232DataBitLengthEnum     , True, True, None)
        self._add_param_enum("RS232 User interface.Settings.Network"                                                        , "A1110900", 0, ParamAccType.RW, p_enum.RS232NetworkEnum           , True, True, None)
        self._add_param_enum("RS232 User interface.Settings.Parity Bit"                                                     , "A1110400", 0, ParamAccType.RW, p_enum.RS232ParityBitEnum         , True, True, None)
        self._add_param_enum("RS232 User interface.Settings.Stop Bit"                                                       , "A1110300", 0, ParamAccType.RW, p_enum.RS232StopBitEnum           , True, True, None)
        self._add_param_enum("RS232 User interface.Settings.Topology"                                                       , "A1110800", 0, ParamAccType.RW, p_enum.RS232TopologyEnum          , True, True, None)

        self._add_param_enum("RS232 User interface.Scaling.Position.Position Unit"                                          , "A1120101", 0, ParamAccType.RW, p_enum.RS232PositionUnitEnum      , True, True, None)
        self._add_param_real("RS232 User interface.Scaling.Position.Value Closest Position"                                 , "A1120102", 0, ParamAccType.RW, f_min, f_max, "", True, True, "")
        self._add_param_real("RS232 User interface.Scaling.Position.Value Open Position"                                    , "A1120103", 0, ParamAccType.RW, f_min, f_max, "", True, True, "")
        self._add_param_enum("RS232 User interface.Scaling.Pressure.Pressure Unit"                                          , "A1120201", 0, ParamAccType.RW, p_enum.RS232PressureUnitEnum      , True, True, None)
        self._add_param_real("RS232 User interface.Scaling.Pressure.Value Pressure 0"                                       , "A1120202", 0, ParamAccType.RW, f_min, f_max, "", True, True, "")
        self._add_param_real("RS232 User interface.Scaling.Pressure.Value Pressure Sensor Full Scale"                       , "A1120203", 0, ParamAccType.RW, f_min, f_max, "", True, True, "")

        '''
        NVM for Compounds
        '''
        self._add_param_nvm_compound("Compound Commands.NVM For Sevice.Compound Commands 1.[0]" , "B10A0100",  0)#, "System.Access Mode")
        self._add_param_nvm_compound("Compound Commands.NVM For Sevice.Compound Commands 1.[1]" , "B10A0100",  1)#, "System.Control Mode")
        self._add_param_nvm_compound("Compound Commands.NVM For Sevice.Compound Commands 1.[2]" , "B10A0100",  2)#, "Position Control.Basic.Actual Position")
        self._add_param_nvm_compound("Compound Commands.NVM For Sevice.Compound Commands 1.[3]" , "B10A0100",  3)#, "Position Control.Basic.Target Position Used")
        self._add_param_nvm_compound("Compound Commands.NVM For Sevice.Compound Commands 1.[4]" , "B10A0100",  4)#, "Pressure Control.Basic.Actual Pressure")
        self._add_param_nvm_compound("Compound Commands.NVM For Sevice.Compound Commands 1.[5]" , "B10A0100",  5)#, "Pressure Control.Basic.Target Pressure Used")
        self._add_param_nvm_compound("Compound Commands.NVM For Sevice.Compound Commands 1.[6]" , "B10A0100",  6)#, "Position Control.Basic.Position Control Speed")
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

    def _add_param_enum(self, full_path: str, id: str, index: int, param_acc : ParamAccType, enum_class: type, is_nor_backup: bool, is_fu_backup: bool, description: str | None):
        path, name = full_path.rsplit(".", 1)

        if not description:
            items = [f"{item.value}: {item.description}" for item in enum_class]
            description = "<br>".join(items)

        self._add_param(Parameter(path, name, id, index, ParamDisplayType.ENUM, ParamDataType.UINT32, param_acc, is_nor_backup, is_fu_backup, "", int(0), int(0), enum_class, description))


    def _add_param_bitmap(self, full_path: str, id: str, index: int, param_acc : ParamAccType, enum_class: type, is_nor_backup: bool, is_fu_backup: bool, description: str | None):
        path, name = full_path.rsplit(".", 1)

        if not description:
            items = [f"{item.value}: {item.description}" for item in enum_class]
            description = "<br>".join(items)

        self._add_param(Parameter(path, name, id, index, ParamDisplayType.BITMAP, ParamDataType.UINT32, param_acc, is_nor_backup, is_fu_backup, "", int(0), int(4294967295), enum_class, description))


    def _add_param_3digi(self, full_path: str, id: str, index: int, param_acc : ParamAccType, enum_class1: type, enum_class2: type, enum_class3: type, is_nor_backup: bool, is_fu_backup: bool, description: str | None):
        path, name = full_path.rsplit(".", 1)

        if not description:
            items1 = [f"{item.value}: {item.description}" for item in enum_class1]
            items2 = [f"{item.value}: {item.description}" for item in enum_class2]
            items3 = [f"{item.value}: {item.description}" for item in enum_class3]
            description = "<br>".join(items1 + items2 + items3)

        digiparam = ParameterDigi(path, name, id, index, ParamDisplayType.DIGI_NUM , ParamDataType.UINT32, param_acc, is_nor_backup, is_fu_backup, "", int(0), int(4294967295), description)
        digiparam.add_ref_list(enum_class1) 
        digiparam.add_ref_list(enum_class2) 
        digiparam.add_ref_list(enum_class3) 

        self._add_param(digiparam)        


    def _add_param_text(self, full_path: str, id: str, index: int, param_acc : ParamAccType, is_nor_backup: bool, is_fu_backup: bool, description: str):
        path, name = full_path.rsplit(".", 1)
        self._add_param(Parameter(path, name, id, index, ParamDisplayType.TEXT, ParamDataType.STR, param_acc, is_nor_backup, is_fu_backup, "", int(0), int(0), None, description))


    def _add_param_hex(self, full_path: str, id: str, index: int, param_acc : ParamAccType, is_nor_backup: bool, is_fu_backup: bool, description: str):
        path, name = full_path.rsplit(".", 1)
        self._add_param(Parameter(path, name, id, index, ParamDisplayType.HEX, ParamDataType.UINT32, param_acc, is_nor_backup, is_fu_backup, "", int(0), int(4294967295), None, description))


    def _add_param_num(self, full_path: str, id: str, index: int, param_acc : ParamAccType, min_value: int, max_value: int, unit: str, is_nor_backup: bool, is_fu_backup: bool, description: str):
        path, name = full_path.rsplit(".", 1)
        self._add_param(Parameter(path, name, id, index, ParamDisplayType.NUMBER, ParamDataType.UINT32, param_acc, is_nor_backup, is_fu_backup, unit, min_value, max_value, None, description))

    def _add_param_pres(self, full_path: str, id: str, index: int, param_acc : ParamAccType, is_nor_backup: bool, is_fu_backup: bool, description: str):
        path, name = full_path.rsplit(".", 1)
        self._add_param(Parameter(path, name, id, index, ParamDisplayType.SENS_PRES, ParamDataType.FLOAT, param_acc, is_nor_backup, is_fu_backup, "", float(-3.4028235e+38), float(3.4028235e+38), None, description))

    def _add_param_posi(self, full_path: str, id: str, index: int, param_acc : ParamAccType, is_nor_backup: bool, is_fu_backup: bool, description: str):
        path, name = full_path.rsplit(".", 1)
        self._add_param(Parameter(path, name, id, index, ParamDisplayType.POSI, ParamDataType.FLOAT, param_acc, is_nor_backup, is_fu_backup, "", float(-3.4028235e+38), float(3.4028235e+38), None, description))

    def _add_param_real(self, full_path: str, id: str, index: int, param_acc : ParamAccType, min_value: float, max_value: float, unit: str, is_nor_backup: bool, is_fu_backup: bool, description: str):
        path, name = full_path.rsplit(".", 1)
        self._add_param(Parameter(path, name, id, index, ParamDisplayType.REAL, ParamDataType.FLOAT, param_acc, is_nor_backup, is_fu_backup, unit, min_value, max_value, None, description))   

    def _add_param_nvm_compound(self, full_path: str, id: str, index: int):
        path, name = full_path.rsplit(".", 1)
        self._add_param(Parameter(path, name, id, index, ParamDisplayType.HEX, ParamDataType.UINT32, ParamAccType.RW, False, False, "", int(0), int(4294967295), None, ""))

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

    def get_all(self) -> List[Parameter]:
        """전체 파라미터 리스트를 가져옵니다."""
        return self._parameters
        
