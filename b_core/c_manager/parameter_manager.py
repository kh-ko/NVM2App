
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
        self._param_map: Dict[tuple, Parameter] = {}  # (path, name) 검색용
        self._parameters: List[Parameter] = []         # 전체 리스트 보관용

        self._add_param(Parameter("System"                              , "Access Mode"            , "0F0B0000",  0, ParamDisplayType.ENUM    , ParamDataType.UINT32, ParamAccType.RW, False, False, ""   , int(0x0), int(0)         , p_enum.AccModeEnum          , "0: Local<br>1: Remote<br>2: Remote Locked"))
        self._add_param(Parameter("System"                              , "Control Mode"           , "0F020000",  0, ParamDisplayType.ENUM    , ParamDataType.UINT32, ParamAccType.RW, False, False, ""   , int(0x0), int(0)         , p_enum.ControlModeEnum      , "0: Init<br>1: Homing<br>2: Position<br>3: Close<br>4: Open<br>5: Pressure Control<br>6: Hold<br>7: Learn<br>8: Interlock Open<br>9: Interlock Close<br>12: Power Failure<br>13: Safety<br>14: Error"))
        self._add_param(Parameter("System.Identification"               , "Serial Number"          , "0F100100",  0, ParamDisplayType.TEXT    , ParamDataType.STR   , ParamAccType.RO, False, False, ""   , int(0x0), int(0)         , None                        , "Identification of the product"))
        self._add_param(Parameter("System.Identification.Configuration" , "Model"                  , "B0000100",  0, ParamDisplayType.ENUM    , ParamDataType.UINT32, ParamAccType.RW, False, False, ""   , int(0x0), int(0)         , p_enum.SysModelEnum         , "1: APC<br>2: Manual<br>3: Gate<br>4: UHV Gate<br>5: Low cost APC"))
        self._add_param(Parameter("System.Identification.Configuration" , "Valve Type"             , "B0000100",  1, ParamDisplayType.ENUM    , ParamDataType.UINT32, ParamAccType.RW, False, False, ""   , int(0x0), int(0)         , p_enum.SysValveTypeEnum     , "1: Butterfly<br>2: Pendulum<br>3: Circular"))
        self._add_param(Parameter("System.Identification.Configuration" , "Sealing type"           , "B0000100",  2, ParamDisplayType.ENUM    , ParamDataType.UINT32, ParamAccType.RW, False, False, ""   , int(0x0), int(0)         , p_enum.SysSealingTypeEnum   , "1: Non-Sealing<br>2: Sealing<br>3: FCup-Sealing<br>4: Pendulum-No Heating<br>5: Pendulum-Heating"))
        self._add_param(Parameter("System.Identification.Configuration" , "Flange Size"            , "B0000100",  3, ParamDisplayType.ENUM    , ParamDataType.UINT32, ParamAccType.RW, False, False, ""   , int(0x0), int(0)         , p_enum.SysFlangeSizeEnum    , "1: 040<br>2: 050<br>3: 063<br>4: 080<br>5: 100<br>6: 160<br>7: 200<br>8: 250<br>9: 025<br>10: 320<br>11: 350<br>12: 400"))
        self._add_param(Parameter("System.Identification.Configuration" , "Contract Method"        , "B0000100",  4, ParamDisplayType.ENUM    , ParamDataType.UINT32, ParamAccType.RW, False, False, ""   , int(0x0), int(0)         , p_enum.SysContractMethodEnum, "1: ISO KF<br>2: ISO F<br>3: CF-F<br>4: ISO K<br>5: Controller only<br>6: VF<br>7: JIS"))
        self._add_param(Parameter("System.Identification.Configuration" , "Body Material"          , "B0000100",  5, ParamDisplayType.ENUM    , ParamDataType.UINT32, ParamAccType.RW, False, False, ""   , int(0x0), int(0)         , p_enum.SysBodyMaterialEnum  , "1: AL-Blank-Butterfly<br>2: SUS304<br>3: SUS316L<br>4: Controller only<br>5: Aluminum-Hard-Anodized<br>6: Aluminum-Blank-Pendulum<br>7: Aluminum-Nickel Coated"))
        self._add_param(Parameter("System.Identification.Configuration" , "User Interface"         , "B0000100",  6, ParamDisplayType.ENUM    , ParamDataType.UINT32, ParamAccType.RW, False, False, ""   , int(0x0), int(0)         , p_enum.SysUserInterfaceEnum , "1: RS232<br>2: RS232(+ Analog Output)<br>3: RS485(+ Analog Output)<br>4: Logic<br>5: DeviceNet<br>6: Profibus<br>7: EtherNet<br>8: CC-LINK<br>9: EtherCAT<br>10: Logic(Legacy)<br>11: DeviceNet(Legacy, MKS)<br>12: DeviceNet(APSystem)<br>13: Logic(Retrofit)<br>14: DeviceNet(Norcal)<br>15: Cluster Slave"))
        self._add_param(Parameter("System.Identification.Configuration" , "Power Option"           , "B0000100",  7, ParamDisplayType.ENUM    , ParamDataType.UINT32, ParamAccType.RW, False, False, ""   , int(0x0), int(0)         , p_enum.SysPowerOptionEnum   , "1: Basic<br>2: SPS<br>3: PFO<br>4: SPS & PFO<br>5: UPS<br>6: SPS & UPS<br>7: Basic & VC master<br>8: SPS & VC master<br>9: PFO & VC master<br>10: SPS & PFO & VC master<br>11: UPS & VC master<br>12: SPS & UPS & VC master"))
        self._add_param(Parameter("System.Identification.Configuration" , "Sensor Number"          , "B0000100",  8, ParamDisplayType.ENUM    , ParamDataType.UINT32, ParamAccType.RW, False, False, ""   , int(0x0), int(0)         , p_enum.SysSensorNumberEnum  , "0: No Sensor<br>1: 1 Sensor<br>2: 2 Sensor"))
        self._add_param(Parameter("System.Identification.Configuration" , "Revision 1"             , "B0000100",  9, ParamDisplayType.ENUM    , ParamDataType.UINT32, ParamAccType.RW, False, False, ""   , int(0x0), int(0)         , p_enum.Base36Enum           , "Valve Hardware Revision 1"))
        self._add_param(Parameter("System.Identification.Configuration" , "Revision 2"             , "B0000100", 10, ParamDisplayType.ENUM    , ParamDataType.UINT32, ParamAccType.RW, False, False, ""   , int(0x0), int(0)         , p_enum.Base36Enum           , "Valve Hardware Revision 2"))
        self._add_param(Parameter("System.Identification.Configuration" , "Revision 3"             , "B0000100", 11, ParamDisplayType.ENUM    , ParamDataType.UINT32, ParamAccType.RW, False, False, ""   , int(0x0), int(0)         , p_enum.Base36Enum           , "Valve Hardware Revision 3"))
        self._add_param(Parameter("System.Identification.Configuration" , "Product Number"         , "B0000100", 12, ParamDisplayType.HEX     , ParamDataType.UINT32, ParamAccType.RW, False, False, ""   , int(0x0), int(0xFFFFFFFF), None                        , "Product number"))
        self._add_param(Parameter("System.Identification.Configuration" , "Product Number Ex"      , "B0000100", 13, ParamDisplayType.HEX     , ParamDataType.UINT32, ParamAccType.RW, False, False, ""   , int(0x0), int(0xFFFFFFFF), None                        , "Extended Product Number"))
        self._add_param(Parameter("System.Statistics"                   , "Power Up Counter"       , "0F200100",  0, ParamDisplayType.NUMBER  , ParamDataType.UINT32, ParamAccType.RO, False, False, ""   , int(0x0), int(0xFFFFFFFF), None                        , ""))
        self._add_param(Parameter("System.Statistics"                   , "Total Time Powered"     , "0F200200",  0, ParamDisplayType.NUMBER  , ParamDataType.UINT32, ParamAccType.RO, False, False, "sec", int(0x0), int(0xFFFFFFFF), None                        , ""))
        self._add_param(Parameter("System.Statistics"                   , "Time Since Power On"    , "0F200300",  0, ParamDisplayType.NUMBER  , ParamDataType.UINT32, ParamAccType.RO, False, False, "sec", int(0x0), int(0xFFFFFFFF), None                        , ""))
        self._add_param(Parameter("System.Warning/Error"                , "Warning Bitmap"         , "0F300100",  0, ParamDisplayType.BITMAP  , ParamDataType.UINT32, ParamAccType.RO, False, False, ""   , int(0x0), int(0xFFFFFFFF), p_enum.SysWarningBitmap     , "0: No Learn Data<br>1: Isolation valve does not work<br>2: No Sensor Active<br>3: PFO Not Ready<br>4: Cluster Slave Offline<br>6: Fieldbus Data Not Valid<br>7: Network failure<br>8: Compressed Air Not Falling when valve close<br>9: Compressed Air Too Low<br>10: Compressed Air Too High<br>12: Fan stall alarm<br>15: Storing in NV Memory"))
        self._add_param(Parameter("System.Warning/Error"                , "Error Bitmap"           , "0F300500",  0, ParamDisplayType.BITMAP  , ParamDataType.UINT32, ParamAccType.RO, False, False, ""   , int(0x0), int(0xFFFFFFFF), p_enum.SysErrorBitmap       , "0: Homing Position Error<br>1: Homing Not Running<br>2: Homing Error State<br>3: Operation Position Error<br>4: Operation Not Running<br>5: Operation Error State<br>12: Other Component<br>30: General<br>31: Internal"))
        digiparam = ParameterDigi("System.Warning/Error"                , "Error Number"           , "0F300600",  0, ParamDisplayType.DIGI_NUM, ParamDataType.UINT32, ParamAccType.RO, False, False, ""   , int(0x0), int(0xFFFFFFFF)                              , "(XYZ)<br>[X]<br>0: No Error<br>1: All Motor Units<br>2: Motor Unit 1<br>3: Motor Unit 2<br>4: Motor Unit 3<br>8: Other<br>[Y]<br>0: Homing<br>2: Operation Mode<br>8: Other<br>[Z]<br>0: Position Error<br>1: Not running: No communication with component x<br>2: Error State: component x is running but in Status Error<br>8: Other")
        digiparam.add_ref_list(p_enum.SysErrorNumberComponent)
        digiparam.add_ref_list(p_enum.SysErrorNumberMode)
        digiparam.add_ref_list(p_enum.SysErrorNumberType)
        self._add_param(digiparam)
        self._add_param(Parameter("System.Warning/Error"                , "Error Code"             , "0F300700",  0, ParamDisplayType.ENUM    , ParamDataType.UINT32, ParamAccType.RO, False, False, ""   , int(0x0), int(0)         , p_enum.SysErrorCodeEnum     , "0:No error<br>1:No valve connected<br>2:Nonvolatile memory failure<br>3:Analog digital converter of sensor input failure<br>4:Initialization of motion controller failed<br>5:Encoder index pulse not found<br>6:Initialization of interface module failed<br>7:Initialization of external drive EEProm failed<br>10:Closing position can not be reached<br>11:Homing position can not be reached<br>12:Motion controller (Internal voltage error)<br>13:Motion controller (Internal error temperature)<br>14:Motion controller (Unexpected behavior)<br>15:Motion controller (Target position can not be reached)<br>16:Motion controller (Position minimal conductance cannot be reached)<br>17:Motion controller (Position to push back the Differential Plate cannot be reached)<br>18:Motion controller (Minimal isolation position cannot be reached)<br>20:Break slippery detected<br>30:SFV (Motion controller failure in master-slave communication)<br>40:Compressed air error<br>42:Power supply (low voltage detected)<br>96:SFV (Position deviation axis1 to axis2 at homing procedure)<br>97:SFV (Position deviation axis1 to axis2 at operating)<br>98:Position error during closing procedure<br>99:Position error at operating<br>200:Valve configuration error (not possible to operate the valve with these configuration)<br>701:Wrong ident code axis 1<br>702:Wrong ident code axis 2<br>703:Wrong ident code axis 2 AND axis 1<br>704:Wrong ident code axis 3<br>705:Wrong ident code axis 3 AND axis 1<br>706:Wrong ident code axis 3 AND axis 2<br>707:Wrong ident code axis 3 AND axis 2 AND axis 1"))
        self._add_param(Parameter("System.Services"                     , "Restart Controller"     , "0F500100",  0, ParamDisplayType.ENUM    , ParamDataType.UINT32, ParamAccType.RW, False, False, ""   , int(0x0), int(0)         , p_enum.FalseTrueEnum        , "Emulates a power cycle"))
        self._add_param(Parameter("System.Services"                     , "Configuration Lock Mode", "0F500500",  0, ParamDisplayType.ENUM    , ParamDataType.UINT32, ParamAccType.RW, False, False, ""   , int(0x0), int(0)         , p_enum.FalseTrueEnum        , "Locking the valve settings.<br>If true, no changes to the settings are possible."))

    def _add_param(self, param: Parameter):
        self._parameters.append(param)
        self._param_map[(param.path, param.name)] = param

    def get(self, path: str, name: str) -> Optional[Parameter]:
        return self._param_map.get((path, name))

    def get_all(self) -> List[Parameter]:
        """전체 파라미터 리스트를 가져옵니다."""
        return self._parameters
        
