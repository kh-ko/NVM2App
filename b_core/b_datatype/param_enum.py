from inspect import CO_COROUTINE
from enum import Enum

class DescriptionEnum(Enum):
    def __new__(cls, value, description):
        obj = object.__new__(cls)
        obj._value_ = value
        obj.description = description
        return obj

    @classmethod
    def get_desc(cls, value, default="Unknown"):
        try:
            return cls(value).description
        except ValueError:
            return default

    @classmethod
    def from_desc(cls, description, default=None):
        for member in cls:
            if member.description == description:
                return member
        return default

class ChartRangeModeEnum(DescriptionEnum):
    # LocalSettingManager 의 *_chart_range_mode 값 (차트 축 범위 결정 방식)
    AUTO          = (0, "Auto")
    FULL          = (1, "Full")
    CUSTOM        = (2, "Custom")

class ChartXWindowEnum(DescriptionEnum):
    # LocalSettingManager 의 chart_x_window_sec 값 (차트 X축 시간창, 초)
    SEC_30        = (30, "30 sec")
    MIN_1         = (60, "1 min")
    MIN_2         = (120, "2 min")
    MIN_5         = (300, "5 min")
    MIN_10        = (600, "10 min")

class OffOnEnum(DescriptionEnum):
    OFF           = (0, "Off")
    ON            = (1, "On")

class FalseTrueEnum(DescriptionEnum):
    FALSE           = (0, "False")
    TRUE            = (1, "True")

class DisableEnableEnum(DescriptionEnum):
    DISABLE         = (0, "Disable")
    ENABLE          = (1, "Enable")    

class NotDisableEnableEnum(DescriptionEnum):
    NOT_DISABLED    = (0, "Not Disabled")
    NOT_ENABLED     = (1, "Not Enabled")        

class OkNotOkEnum(DescriptionEnum):
    OK              = (0, "Ok")
    NOT_OK          = (1, "Not Ok")        

class DeactiveActiveEnum(DescriptionEnum):
    DEACTIVE        = (0, "Deactive")
    ACTIVE          = (1, "Active")   

class NotAvailAvailEnum(DescriptionEnum):
    NOT_AVAILABLE   = (0, "Not available")
    AVAILABLE       = (1, "Available")   

class NotUsedUsed(DescriptionEnum):
    NOT_USED        = (0, "Not Used")
    USED            = (1, "Used")

class OnlineOfflineEnum(DescriptionEnum):
    ONLINE  = (0, "Online")
    OFFLINE = (1, "Offline")    

class StopStartEnum(DescriptionEnum):
    STOP = (0, "Stop")
    START = (1, "Start")

class Base36Enum(DescriptionEnum):
    ZERO  = (0, "0")
    ONE   = (1, "1")
    TWO   = (2, "2")
    THREE = (3, "3")
    FOUR  = (4, "4")
    FIVE  = (5, "5")
    SIX   = (6, "6")
    SEVEN = (7, "7")
    EIGHT = (8, "8")
    NINE  = (9, "9")
    A     = (10, "A")
    B     = (11, "B")
    C     = (12, "C")
    D     = (13, "D")
    E     = (14, "E")
    F     = (15, "F")
    G     = (16, "G")
    H     = (17, "H")
    I     = (18, "I")
    J     = (19, "J")
    K     = (20, "K")
    L     = (21, "L")
    M     = (22, "M")
    N     = (23, "N")
    O     = (24, "O")
    P     = (25, "P")
    Q     = (26, "Q")
    R     = (27, "R")
    S     = (28, "S")
    T     = (29, "T")
    U     = (30, "U")
    V     = (31, "V")
    W     = (32, "W")
    X     = (33, "X")
    Y     = (34, "Y")
    Z     = (35, "Z")
    
class AccModeEnum(DescriptionEnum):
    LOCAL           = (0, "Local")
    REMOTE          = (1, "Remote")
    REMOTE_LOCKED   = (2, "Remote Locked")

class ControlModeEnum(DescriptionEnum):
    INIT                = (0, "Init")
    HOMING              = (1, "Homing")
    POSITION            = (2, "Position")
    CLOSE               = (3, "Close")
    OPEN                = (4, "Open")
    PRESSURE            = (5, "Pressure")
    HOLD                = (6, "Hold")
    LEARN               = (7, "Learn")
    INTERLOCK_OPEN      = (8, "Interlock Open")
    INTERLOCK_CLOSE     = (9, "Interlock Close")
    POWER_FAILURE       = (12, "Power Failure")
    SAFETY              = (13, "Safety")
    ERROR               = (14, "Error")

class ControlModeSetpointEnum(DescriptionEnum):
    POSITION            = (2, "Position")
    CLOSE               = (3, "Close")
    OPEN                = (4, "Open")
    PRESSURE            = (5, "Pressure")
    HOLD                = (6, "Hold")
    LEARN               = (7, "Learn") 

class SysModelEnum(DescriptionEnum):
    APC                 = (1, "APC")
    MANUAL              = (2, "Manual")
    GATE                = (3, "Gate")
    UHV_GATE            = (4, "UHV Gate")
    LOW_COST_APC        = (5, "Low cost APC")

class SysValveTypeEnum(DescriptionEnum):
    BUTTERFLY           = (1, "Butterfly")
    PENDULUM            = (2, "Pendulum")
    CIRCULAR            = (3, "Circular")

class SysSealingTypeEnum(DescriptionEnum):
    NON_SEALING         = (1, "Non-Sealing")
    SEALING             = (2, "Sealing")
    FCUP_SEALING        = (3, "FCup-Sealing")
    PENDULUM_NO_HEATING = (4, "Pendulum-No Heating")
    PENDULUM_HEATING    = (5, "Pendulum-Heating")

class SysFlangeSizeEnum(DescriptionEnum):
    SIZE_040            = (1, "040")
    SIZE_050            = (2, "050")
    SIZE_063            = (3, "063")
    SIZE_080            = (4, "080")
    SIZE_100            = (5, "100")
    SIZE_160            = (6, "160")
    SIZE_200            = (7, "200")
    SIZE_250            = (8, "250")
    SIZE_025            = (9, "025")
    SIZE_320            = (10, "320")
    SIZE_350            = (11, "350")
    SIZE_400            = (12, "400")

class SysContractMethodEnum(DescriptionEnum):
    ISO_KF              = (1, "ISO KF")
    ISO_F               = (2, "ISO F")
    CF_F                = (3, "CF-F")
    ISO_K               = (4, "ISO K")
    CONTROLLER_ONLY     = (5, "Controller only")
    VF                  = (6, "VF")
    JIS                 = (7, "JIS")

class SysBodyMaterialEnum(DescriptionEnum):
    AL_BLANK_BUTTERFLY      = (1, "AL-Blank-Butterfly")
    SUS304                  = (2, "SUS304")
    SUS316L                 = (3, "SUS316L")
    CONTROLLER_ONLY         = (4, "Controller only")
    ALUMINUM_HARD_ANODIZED  = (5, "Aluminum-Hard-Anodized")
    ALUMINUM_BLANK_PENDULUM = (6, "Aluminum-Blank-Pendulum")
    ALUMINUM_NICKEL_COATED  = (7, "Aluminum-Nickel Coated")

class SysUserInterfaceEnum(DescriptionEnum):
    RS232                   = (1, "RS232")
    RS232_ANALOG_OUTPUT     = (2, "RS232(+ Analog Output)")
    RS485_ANALOG_OUTPUT     = (3, "RS485(+ Analog Output)")
    LOGIC                   = (4, "Logic")
    DEVICENET               = (5, "DeviceNet")
    PROFIBUS                = (6, "Profibus")
    ETHERNET                = (7, "EtherNet")
    CC_LINK                 = (8, "CC-LINK")
    ETHERCAT                = (9, "EtherCAT")
    LOGIC_LEGACY            = (10, "Logic(Legacy)")
    DEVICENET_LEGACY_MKS    = (11, "DeviceNet(Legacy, MKS)")
    DEVICENET_APSYSTEM      = (12, "DeviceNet(APSystem)")
    LOGIC_RETROFIT          = (13, "Logic(Retrofit)")
    DEVICENET_NORCAL        = (14, "DeviceNet(Norcal)")
    CLUSTER_SLAVE           = (15, "Cluster Slave")

class SysPowerOptionEnum(DescriptionEnum):
    BASIC                 = (1, "Basic")
    SPS                   = (2, "SPS")
    PFO                   = (3, "PFO")
    SPS_PFO               = (4, "SPS & PFO")
    UPS                   = (5, "UPS")
    SPS_UPS               = (6, "SPS & UPS")
    BASIC_VC_MASTER       = (7, "Basic & VC master")
    SPS_VC_MASTER         = (8, "SPS & VC master")
    PFO_VC_MASTER         = (9, "PFO & VC master")
    SPS_PFO_VC_MASTER     = (10, "SPS & PFO & VC master")
    UPS_VC_MASTER         = (11, "UPS & VC master")
    SPS_UPS_VC_MASTER     = (12, "SPS & UPS & VC master")
    
class SysSensorNumberEnum(DescriptionEnum):
    NO_SENSOR           = (0, "No Sensor")
    ONE_SENSOR          = (1, "1 Sensor")
    TWO_SENSOR          = (2, "2 Sensor")
       
class SysWarningBitmap(DescriptionEnum):
    NO_LEARN_DATA                   = (0, "No Learn Data")
    ISOLATION_VALVE_DOES_NOT_WORK   = (1, "Isolation Valve Dose Not Work")
    NO_SENSOR_ACTIVE                = (2, "No Sensor Active")
    PFO_NOT_READY                   = (3, "PFO Not Ready")
    CLUSTER_SLAVE_OFFLINE           = (4, "Cluster Slave Offline")
    FIELDBUS_DATA_NOT_VALID         = (6, "Fieldbus Data Not Valid")
    NETWORK_FAILURE                 = (7, "Network Failure")
    COMPRESSED_AIR_NOT_FALLING      = (8, "Compressed Air Not Falling When Valve Close")
    COMPRESSED_AIR_TOO_LOW          = (9, "Compressed Air Too Low")
    COMPRESSED_AIR_TOO_HIGH         = (10, "Compressed Air Too High")
    FAN_STALL_ALARM                 = (12, "Fan Stall Alarm")
    STORING_IN_NV_MEMORY            = (15, "Storing in NV Memory")

class SysErrorBitmap(DescriptionEnum):
    HOMING_POSITION_ERROR       = (0, "Homing Position Error")
    HOMING_NOT_RUNNING          = (1, "Homing Not Running")
    HOMING_ERROR_STATE          = (2, "Homing Error State")
    OPERATION_POSITION_ERROR    = (3, "Operation Position Error")
    OPERATION_NOT_RUNNING       = (4, "Operation Not Running")
    OPERATION_ERROR_STATE       = (5, "Operation Error State")
    OTHER_COMPONENT             = (12, "Other Component Error")
    GENERAL                     = (30, "General Error")
    INTERNAL                    = (31, "Internal Error")

         
class SysErrorNumberComponent(DescriptionEnum):
    ALL_MOTOR_UNITS = (1, "All Motor Units")
    MOTOR_UNIT_1    = (2, "Motor Unit 1")
    MOTOR_UNIT_2    = (3, "Motor Unit 2")
    MOTOR_UNIT_3    = (4, "Motor Unit 3")
    OTHER_COMPONENT = (8, "Other")

class SysErrorNumberMode(DescriptionEnum):
    HOMING          = (0, "Homing")
    OPERATION_MODE  = (2, "Operation Mode")
    OTHER           = (8, "Other")
    NO_ERROR        = (10, "No Error")

class SysErrorNumberType(DescriptionEnum):
    POSITION_ERROR  = (0, "Position Error")
    NOT_RUNNING     = (1, "Not running: No communication with component x")
    ERROR_STATE     = (2, "Error State: component x is running but in Status Error")
    OTHER           = (8, "Other")   
    NO_ERROR        = (10, "No Error") 
         
class SysErrorCodeEnum(DescriptionEnum):
    NO_ERROR                                                                            = (  0, "(0) No error")
    NO_VALVE_CONNECTED                                                                  = (  1, "(1) No valve connected")
    NONVOLATILE_MEMORY_FAILURE                                                          = (  2, "(2) Nonvolatile memory failure")
    ANALOG_DIGITAL_CONVERTER_OF_SENSOR_INPUT_FAILURE                                    = (  3, "(3) Analog digital converter of sensor input failure")
    INITIALIZATION_OF_MOTION_CONTROLLER_FAILED                                          = (  4, "(4) Initialization of motion controller failed")
    ENCODER_INDEX_PULSE_NOT_FOUND                                                       = (  5, "(5) Encoder index pulse not found")
    INITIALIZATION_OF_INTERFACE_MODULE_FAILED                                           = (  6, "(6) Initialization of interface module failed")
    INITIALIZATION_OF_EXTERNAL_DRIVE_EEPROM_FAILED                                      = (  7, "(7) Initialization of external drive EEProm failed")
    CLOSING_POSITION_CAN_NOT_BE_REACHED                                                 = ( 10, "(10) Closing position can not be reached")
    HOMING_POSITION_CAN_NOT_BE_REACHED                                                  = ( 11, "(11) Homing position can not be reached")
    MOTION_CONTROLLER_INTERNAL_VOLTAGE_ERROR                                            = ( 12, "(12) Motion controller (Internal voltage error)")
    MOTION_CONTROLLER_INTERNAL_ERROR_TEMPERATURE                                        = ( 13, "(13) Motion controller (Internal error temperature)")
    MOTION_CONTROLLER_UNEXPECTED_BEHAVIOR                                               = ( 14, "(14) Motion controller (Unexpected behavior)")
    MOTION_CONTROLLER_TARGET_POSITION_CAN_NOT_BE_REACHED                                = ( 15, "(15) Motion controller (Target position can not be reached)")
    MOTION_CONTROLLER_POSITION_MINIMAL_CONDUCTANCE_CAN_NOT_BE_REACHED                   = ( 16, "(16) Motion controller (Position minimal conductance cannot be reached)")
    MOTION_CONTROLLER_POSITION_TO_PUSH_BACK_THE_DIFFERENTIAL_PLATE_CAN_NOT_BE_REACHED   = ( 17, "(17) Motion controller (Position to push back the Differential Plate cannot be reached)")
    MOTION_CONTROLLER_MINIMAL_ISOLATION_POSITION_CAN_NOT_BE_REACHED                     = ( 18, "(18) Motion controller (Minimal isolation position cannot be reached)")
    BREAK_SLIPPERY_DETECTED                                                             = ( 20, "(20) Break slippery detected")
    SFV_MOTION_CONTROLLER_FAILURE_IN_MASTER_SLAVE_COMMUNICATION                         = ( 30, "(30) SFV (Motion controller failure in master-slave communication)")
    COMPRESSED_AIR_ERROR                                                                = ( 40, "(40) Compressed air error")
    POWER_SUPPLY_LOW_VOLTAGE_DETECTED                                                   = ( 42, "(42) Power supply (low voltage detected)")
    SFV_POSITION_DEVIATION_AXIS1_TO_AXIS2_AT_HOMING_PROCEDURE                           = ( 96, "(96) SFV (Position deviation axis1 to axis2 at homing procedure)")
    SFV_POSITION_DEVIATION_AXIS1_TO_AXIS2_AT_OPERATING                                  = ( 97, "(97) SFV (Position deviation axis1 to axis2 at operating)")
    POSITION_ERROR_DURING_CLOSING_PROCEDURE                                             = ( 98, "(98) Position error during closing procedure")
    POSITION_ERROR_AT_OPERATING                                                         = ( 99, "(99) Position error at operating")
    VALVE_CONFIGURATION_ERROR                                                           = (200, "(200) Valve configuration error (not possible to operate the valve with these configuration)")
    WRONG_IDENT_CODE_AXIS_1                                                             = (701, "(701) Wrong ident code axis 1")
    WRONG_IDENT_CODE_AXIS_2                                                             = (702, "(702) Wrong ident code axis 2")
    WRONG_IDENT_CODE_AXIS_2_AND_AXIS_1                                                  = (703, "(703) Wrong ident code axis 2 AND axis 1")
    WRONG_IDENT_CODE_AXIS_3                                                             = (704, "(704) Wrong ident code axis 3")
    WRONG_IDENT_CODE_AXIS_3_AND_AXIS_1                                                  = (705, "(705) Wrong ident code axis 3 AND axis 1")
    WRONG_IDENT_CODE_AXIS_3_AND_AXIS_2                                                  = (706, "(706) Wrong ident code axis 3 AND axis 2")
    WRONG_IDENT_CODE_AXIS_3_AND_AXIS_2_AND_AXIS_1                                       = (707, "(707) Wrong ident code axis 3 AND axis 2 AND axis 1")

class ValveEndCtrlModeEnum(DescriptionEnum):
    POSI        = (2, "Position" )
    CLOSE       = (3, "Close"    )
    OPEN        = (4, "Open"     )
    PRESS       = (5, "Pressure Control")

class ValveStartConditionEnum(DescriptionEnum):
    STD            = (0, "Standard"             )
    OPEN_CMD       = (1, "Open Command"         )
    MOVE_CMD       = (2, "Move Command"         )
    AT_STARTUP     = (3, "At Startup"           )  
    HOME_CMD       = (4, "Homing Command"       )
    MOVE_CMD_STD   = (5, "Move Command/Standard")

class ValveHomingStatusEnum(DescriptionEnum):
    NOT_STARTED    = (0, "Not Started")
    IN_PROGRESS    = (1, "In Progress")
    COMPLETED      = (2, "Completed Successfully")
    ERROR          = (3, "Error Occurred")

class ValveIsolStateEnum(DescriptionEnum):
    NOT_ISOL    = (0, "Not Isolated")
    ISOL        = (1, "Isolated"    )

class ValvePosiStateEnum(DescriptionEnum):
    INTERMEDIATE= (0, "Intermediate")
    CLOSED      = (1, "Closed"      )    
    OPEN        = (2, "OPEN"        )    

class ValvePosiAdapModeEnum(DescriptionEnum):
    OFFSET      = (0, "Offset")

class ValvePosiActPosiEnum(DescriptionEnum):
    REAL        = (0, "Real(with added offset value)")
    ADAPTED     = (1, "Adapted(without added offset value)")

class SensZeroExeEnum(DescriptionEnum):
    NONE            = (0, "None")
    ZERO_ADJUST     = (1, "Execute Zero Adjust")
    CLEAR_OFFSET    = (2, "Clear Offset Value")

class SensZeroSelEnum(DescriptionEnum):
    SEN_1_AND_2     = (0, "Sensor 1+2")
    SEN_1           = (1, "Sensor 1")
    SEN_2           = (2, "Sensor 2")
    NONE            = (3, "None")

class SensInSrcEnum(DescriptionEnum):
    ANALOG      = (0, "Analog")
    DIGITAL     = (1, "Digital")
    SIMULATION  = (2, "Simulation")

class SensorScaleEnum(DescriptionEnum):
    LINEAR      = (0, "Linear")
    LOGARITHMIC = (1, "Logarithmic")

class SensUnitEnum(DescriptionEnum):
    PA      = (0, "Pa")
    KPA     = (1, "kPa")
    BAR     = (2, "bar")
    MBAR    = (3, "mbar")
    TORR    = (4, "Torr")
    MTORR   = (5, "mTorr")
    PSIA    = (6, "psia")
    PSIG    = (7, "psig")

class SensCrossModeEnum(DescriptionEnum):
    SOFT_SWITCH     = (0, "Soft Switch")
    HARD_SWITCH     = (1, "Hard Switch")
    TARGET_PRESSURE = (2, "Target Pressure")

class SensLogPresOnIFace(DescriptionEnum):
    LINEAR      = (0, "Linear signal") # Linear signal is used on Interface
    LOGARITHMIC = (1, "Logarithmic signal") # Logarithmic signal is used on Interface

class PosiRampModeEnum(DescriptionEnum):
    USE_RAMP_TIME   = (0, "Use Ramp Time")
    USE_RAMP_SLOPE  = (1, "Use Ramp Slope")

class RampTypeEnum(DescriptionEnum):
    LINEAR          = (0, "Linear")
    LOGARITHMIC     = (1, "Logarithmic")
    EXPONENTIAL     = (2, "Exponential")

class PresCtrlSelEnum(DescriptionEnum):
    NONE            = (0, "None")
    CONTROLLER_1    = (1, "Controller 1")
    CONTROLLER_2    = (2, "Controller 2")
    CONTROLLER_3    = (3, "Controller 3")
    CONTROLLER_4    = (4, "Controller 4")

class MFCFlowUnitEnum(DescriptionEnum):
    SLM     = (0, "slm")
    SCCM    = (1, "sccm")
    MBAR_LS = (2, "mbar l/s")
    PA_M3_S = (3, "Pa m^3/s")

class PresCtrlAlgoEnum(DescriptionEnum):
    ADAPTIVE    = (0, "Adaptive")
    PI          = (1, "PI")
    SOFT_PUMP   = (2, "Soft Pump")

class LearnDataSelEnum(DescriptionEnum):
    LEARN_BANK_1 = (0, "Learn Bank 1")
    LEARN_BANK_2 = (1, "Learn Bank 2")
    LEARN_BANK_3 = (2, "Learn Bank 3")
    LEARN_BANK_4 = (3, "Learn Bank 4")

class LearnStatusEnum(DescriptionEnum):
    NOT_STARTED      = (0, "Not Started")
    IN_PROGRESS      = (1, "In Progress")
    COMPLETED_SUCCESS= (2, "Completed Successfully")
    ABORTED          = (3, "Aborted")
    FAILED           = (4, "Failed")

class LearnBankStatusEnum(DescriptionEnum):
    NOT_USED            = (0, "Not Used")
    AVAILABLE           = (1, "Available")
    AVAILABLE_WARNING   = (2, "Available with Warnings")

class LearnWarnInfoBitmap(DescriptionEnum):
    RUNNING                = (0, "Running")
    CHECKSUM_ERROR         = (1, "Checksum error")
    TERM_BY_USER           = (2, "Terminated by user")
    UNSUITABLE_COND_HIGH   = (3, "Unsuitable learn condition / pressure too high")
    UNSUITABLE_COND_LOW    = (4, "Unsuitable learn condition / pressure too low")
    PRESSURE_DECREASING    = (5, "Pressure decreasing instead of rising")
    PRESSURE_UNSTABILITY   = (6, "Pressure unstability")
    TERM_BY_PROGRAM        = (7, "Terminated by program")
    NEGATIVE_OPEN_PRESSURE = (8, "Negative open pressure")    

class LearnBankType(DescriptionEnum):
    STANDARD    = (0, "Standard")
    SHORT       = (1, "Short")
    CALCULATED  = (2, "Calculated")

class CtrlDirEnum(DescriptionEnum):
    DOWNSTREAM = (0, "Downstream")
    UPSTREAM   = (1, "Upstream")

class PresScalerEnum(DescriptionEnum):
    LINEAR      = (0, "Linear")
    LOGARITHMIC = (1, "Logarithmic")

class PresRampModeEnum(DescriptionEnum):
    USE_RAMP_TIME   = (0, "Use Ramp Time")
    USE_RAMP_SLOPE  = (1, "Use Ramp Slope")

class PresRampStartValueEnum(DescriptionEnum):
    PREVIOUS_RAMP_VALUE = (0, "Previous Ramp Value")
    ACTUAL_PRESSURE_VALUE = (1, "Actual Pressure Value")

class AutoCtrlModeEnum(DescriptionEnum):
    THRESHOLD        = (0, "Threshold")
    PRESSURE_DIRECTION = (1, "Pressure Direction")

class PresCtrlSelBitmap(DescriptionEnum):
    CONTROLLER_1    = (0, "Controller 1")
    CONTROLLER_2    = (1, "Controller 2")
    CONTROLLER_3    = (2, "Controller 3")
    CONTROLLER_4    = (3, "Controller 4")

class PresCtrlSegSelBitmap(DescriptionEnum):
    SEG_1         = (0, "Segment 1")
    SEG_2         = (1, "Segment 2")
    SEG_3         = (2, "Segment 3")
    SEG_4         = (3, "Segment 4")
    SEG_5         = (4, "Segment 5")
    SEG_6         = (5, "Segment 6")
    SEG_7         = (6, "Segment 7")
    SEG_8         = (7, "Segment 8")
    SEG_9         = (8, "Segment 9")
    SEG_10        = (9, "Segment 10")

class PresCtrlThresCondEnum(DescriptionEnum):
    LOWER_OR_EQUAL    = (0, "Lower Or Equal")
    EQUAL             = (1, "Equal")

class PresCtrlRampThresModeEnum(DescriptionEnum):
    ACTUAL_PRESSURE = (0, "Actual Pressure")
    TARGET_PRESSURE = (1, "Target Pressure Used")

class PfoFuncEnum(DescriptionEnum):
    OPEN    = (0, "Open")
    CLOSE   = (1, "Close")

class PfoStateEnum(DescriptionEnum):
    BATTERY_IS_CHARGING = (0, "Battery is Charging")
    READY_TO_USE        = (1, "Ready To Use")
    ACTIVE              = (2, "Active")
    FAILURE             = (3, "Failure")

class DigitalInFuncEnum(DescriptionEnum):
    INTERLOCK_OPEN    = (0, "Interlock Open")
    INTERLOCK_CLOSE   = (1, "Interlock Close")
    HOLD              = (2, "Hold")

class DigitalOutFuncEnum(DescriptionEnum):
    OPEN    = (0, "Open")
    CLOSE   = (1, "Close")
    HOLD    = (2, "Hold")    

class DigitalIOInvertEnum(DescriptionEnum):
    NOT_INVERTED    = (0, "Not inverted")
    INVERTED        = (1, "inverted")

class RS232OpModeEnum(DescriptionEnum):
    RS232 = (0, "RS232")
    RS485 = (1, "RS485")
    SERVICE_INTERFACE_OVER_RS232 = (2, "Service Interface Over RS232")

class RS232BaudRateEnum(DescriptionEnum):
    BAUD_1200    = (0, "1200")
    BAUD_2400    = (1, "2400")
    BAUD_4800    = (2, "4800")
    BAUD_9600    = (3, "9600")
    BAUD_19200   = (4, "19200")
    BAUD_38400   = (5, "38400")
    BAUD_57600   = (6, "57600")
    BAUD_115200  = (7, "115200")
    BAUD_230400  = (8, "230400")
    BAUD_460800  = (9, "460800")
    BAUD_921600  = (10, "921600")
    BAUD_1000000 = (11, "1000000")

class RS232CommandSetEnum(DescriptionEnum):
    NV1 = (0, "NV 1")
    NV2 = (1, "NV 2")

class RS232CommandTerminationEnum(DescriptionEnum):
    CR = (0, "CR")
    LF = (1, "LF")
    CR_LF = (2, "CR+LF")

class RS232DataBitLengthEnum(DescriptionEnum):
    DATA_BITS_7 = (0, "7 Data Bits")
    DATA_BITS_8 = (1, "8 Data Bits")

class RS232NetworkEnum(DescriptionEnum):
    MULTIPLE_DEVICES = (0, "Multiple Devices")
    POINT_TO_POINT   = (1, "Point to Point")

class RS232ParityBitEnum(DescriptionEnum):
    NONE = (0, "None")
    ODD = (1, "Even")
    EVEN = (2, "Odd")

class RS232StopBitEnum(DescriptionEnum):
    STOP_BIT_1 = (0, "1 Stop Bit")
    STOP_BIT_2 = (1, "2 Stop Bits")

class RS232TopologyEnum(DescriptionEnum):
    FULL_DUPLEX = (0, "Full Duplex")
    HALF_DUPLEX = (1, "Half Duplex")

class RS232PositionUnitEnum(DescriptionEnum):
    ZERO_TO_1 = (0, "0-1")
    ZERO_TO_10 = (1, "0-10")
    ZERO_TO_90 = (2, "0-90")
    ZERO_TO_100 = (3, "0-100")
    ZERO_TO_1000 = (4, "0-1000")
    ZERO_TO_10000 = (5, "0-10000")
    ZERO_TO_100000 = (6, "0-100000")
    USER_SPECIFIC = (7, "User specific")

class RS232PressureUnitEnum(DescriptionEnum):
    PA = (0, "Pa")
    KPA = (1, "kPa")
    BAR = (2, "bar")
    MBAR = (3, "mbar")
    TORR = (4, "Torr")
    MTORR = (5, "mTorr")
    PSI = (6, "psi")
    USER_SPECIFIC = (7, "User specific")

class DeviceNetDevTypeEnum(DescriptionEnum):
    GENERIC_DEVICE            = (0x0 , "Generic Device")
    COMMUNICATIONS_ADAPTER    = (0xC , "Communications Adapter")
    PROCESS_CONTROL_DEVICE    = (0x1D, "Process Control Device")
    GENERIC_DEVICE_2          = (0x2B, "Generic Device")
    PRESSURE_CONTROL_VALVE    = (0x64, "Pressure Control Valve")

class DeviceNetBaudRateEnum(DescriptionEnum):
    BAUD_125K = (0, "125k")
    BAUD_250K = (1, "250k")
    BAUD_500K = (2, "500k")
    AUTO      = (3, "Auto")    

class DeviceNetProfileTypeEnum(DescriptionEnum):
    PROCESS_CONTROL_DEVICE = (0, "Process Control Device")
    GENERIC_DEVICE_C       = (1, "Generic Device C (new)")
    GENERIC_DEVICE_B       = (2, "Generic Device B (old)")    

class DeviceNetDataTypeEnum(DescriptionEnum):
    INT16   = (195, "INT16")
    FLOAT32 = (202, "FLOAT32")

class DeviceNetOutputConsumedAssy(DescriptionEnum):
    CUSTOMIZED = (0,   "(0)CUSTOMIZED")
    NUM_7      = (7,   "(7)SETPOINT/SETPOINT TYPE")
    NUM_8      = (8,   "(8)CONTROL MODE/SETPOINT/SETPOINT TYPE")
    NUM_23     = (23,  "(23)SETPOINT/SETPOINT TYPE")
    NUM_24     = (24,  "(24)CONTROL MODE/SETPOINT/SETPOINT TYPE")
    NUM_32     = (32,  "(32)CONTROL MODE/SETPOINT/KP(GAIN FACTOR)/KI(DLETA FACTOR)/RAMP TIME")
    NUM_102    = (102, "(102)CONTROL MODE/SETPOINT/SETPOINT TYPE/LEARN/LEARN PRES. LIMIT/ZERO")
    NUM_103    = (103, "(103)CONTROL MODE/SETPOINT/SETPOINT TYPE/CLUSTER ADDR./CLUSTER ACTION")
    NUM_107    = (107, "(107)CONTROL MODE/SETPOINT/SETPOINT TYPE/LEARN/LEARN PRES. LIMIT/ZERO")
    NUM_108    = (108, "(108)CONTROL MODE/SETPOINT/SETPOINT TYPE/CLUSTER ADDR./CLUSTER ACTION")
    NUM_110    = (110, "(110)CONTROL MODE/SETPOINT PRESSURE/SETPOINT POSITION/SETPOINT TYPE/LEARN/LEARN PRES. LIMIT/ZERO/CLUSTER ADDR./CLUSTER ACTION")
    NUM_112    = (112, "(112)CONTROL MODE/SETPOINT PRESSURE/SETPOINT POSITION/SETPOINT TYPE/LEARN/LEARN PRES. LIMIT/ZERO/CLUSTER ADD./CLUSTER ACTION")
    NUM_151    = (151, "(151)CONTROL MODE/SETPOINT PRESSURE/SETPOINT POSITION/SETPOINT TYPE/CLUSTER ADDR./CLUSTER ACTION")

class DeviceNetInputProducedAssy(DescriptionEnum):
    CUSTOMIZED = (0,   "(0)CUSTOMIZE"                                                                                                                              )
    NUM_1      = (1,   "(1)PRESSURE"                                                                                                                               )
    NUM_2      = (2,   "(2)EXCEPTION STATUS/PRESSURE"                                                                                                              )
    NUM_3      = (3,   "(3)EXCEPTION STATUS/PRESSURE/POSITION"                                                                                                     )
    NUM_4      = (4,   "(4)EXCEPTION STATUS/PRESSURE/SETPOINT"                                                                                                     )
    NUM_5      = (5,   "(5)EXCEPTION STATUS/PRESSURE/SETPOINT/POSITION"                                                                                            )
    NUM_6      = (6,   "(6)EXCEPTION STATUS/PRESSURE/SETPOINT/CONTROL MODE/POSITION"                                                                               )
    NUM_10     = (10,  "(10)EXCEPTION STATUS"                                                                                                                      )
    NUM_11     = (11,  "(11)EXCEPTION STATUS/PRESSURE/POSITION/CLOSE OPEN CHECK"                                                                                   )
    NUM_13     = (13,  "(13)EXCEPTION STATUS/EXCEPTION DETAIL ALARM"                                                                                               )
    NUM_14     = (14,  "(14)EXCEPTION STATUS/PRESSURE/POSITION/CLOSE OPEN CHECK"                                                                                   )
    NUM_17     = (17,  "(17)PRESSURE"                                                                                                                              )
    NUM_18     = (18,  "(18)EXCEPTION STATUS/PRESSURE"                                                                                                             )
    NUM_19     = (19,  "(19)EXCEPTION STATUS/PRESSURE/POSITION"                                                                                                    )
    NUM_20     = (20,  "(20)EXCEPTION STATUS/PRESSURE/SETPOINT"                                                                                                    )
    NUM_21     = (21,  "(21)EXCEPTION STATUS/PRESSURE/SETPOINT/POSITION"                                                                                           )
    NUM_22     = (22,  "(22)EXCEPTION STATUS/PRESSURE/SETPOINT/CONTROL MODE/POSITION"                                                                              )
    NUM_26     = (26,  "(26)EXCEPTION STATUS/PRESSURE/POSITION/CLOSE OPEN CHECK"                                                                                   )
    NUM_100    = (100, "(100)EXCEPTION STATUS/PRESSURE/POSITION/DEVICE STATUS 2/ACCESS MODE"                                                                       )
    NUM_101    = (101, "(101)EXCEPTION STATUS/PRESSURE/POSITION/CLOSE OPEN CHECK/DEVICE STATUS 2"                                                                  )
    NUM_104    = (104, "(104)EXCEPTION STATUS/PRESSURE/SENSOR 2 READING/POSITION/ACCESS MODE/DEVICE STATUS 2/CLUSTER INFOMATION"                                   )
    NUM_105    = (105, "(105)EXCEPTION STATUS/PRESSURE/POSITION/DEVICE STATUS 2/ACCESS MODE"                                                                       )
    NUM_106    = (106, "(106)EXCEPTION STATUS/PRESSURE/POSITION/SETPOINT/DEVICE STATUS 2"                                                                          )
    NUM_109    = (109, "(109)EXCEPTION STATUS/PRESSURE/SENSOR 2 READING/POSITION/ACCESS MODE/DEVICE STATUS 2/CLUSTER INFOMATION"                                   )
    NUM_111    = (111, "(111)EXCEPTION STATUS/PRESSURE/POSITION/SENSOR 1 READING/SENSOR 2 READING/CLOSE OPEN CHECK/DEVICE STATUTS2/ACCESS MODE/CLUSTER INFORMATION")
    NUM_113    = (113, "(113)EXCEPTION STATUS/PRESSURE/POSITION/SENSOR 1 READING/SENSOR 2 READING/CLOSE OPEN CHECK/DEVICE STATUTS2/ACCESS MODE/CLUSTER INFORMATION")
    NUM_150    = (150, "(150)EXCEPTION STATUS/SENSOR 1 READING/SENSOR 2 READING/POSITION/READING SENSOR/CLOSE OPEN CHECK"                                          )


class DeviceNetOutOldBitmap(DescriptionEnum):
    CTRL_MODE              = (0 , "Control Mode [Length: 1]")
    SETPOINT_INT           = (1 , "Setpoint(INT) [Length: 2]")
    SETPOINT_FLOAT         = (2 , "Setpoint(FLOAT) [Length: 4]")
    SETPOINT_TYPE          = (3 , "Setpoint Type [Length: 1]")
    LEARN                  = (4 , "Learn [Length: 1]")
    LEARN_PRES_LIMIT_INT   = (5 , "Learn Pressure Limit(INT) [Length: 2]")
    LEARN_PRES_LIMIT_FLOAT = (6 , "Learn Pressure Limit(FLOAT) [Length: 4]")
    ZERO                   = (7 , "Zero [Length: 1]")
    CONTROLLER_CTRL_MODE   = (8 , "Controller Control Mode [Length: 1]")
    CONTROLLER_SELECTOR    = (9 , "Controller Selector [Length: 1]")
    CTRL_GAIN              = (10, "Control Gain(P-Gain) [Length: 4]")
    SENSOR_DELAY           = (11, "Sensor Delay [Length: 4]")
    RAMP_TIME              = (12, "Ramp Time [Length: 4]")
    RAMP_MODE              = (13, "Ramp Mode [Length: 1]")
    DIRECTION_MODE         = (18, "Direction Mode(Fixed Control) [Length: 1]")
    CTRL_DELTA_GAIN        = (19, "Control Delta Gain(I-Gain) [Length: 4]")
    CALIBRATION            = (20, "Calibration [Length: 1]")
    DUMMY                  = (21, "Dummy [Length: 1]")

class DeviceNetInOldBitmap(DescriptionEnum):
    EXCEPTION_STATUS       = (0 , "Exception Status [Length: 1]")
    PRES_INT               = (1 , "Pressure(INT) [Length: 2]")
    PRES_FLOAT             = (2 , "Pressure(FLOAT) [Length: 4]")
    SETPOINT_INT           = (3 , "Setpoint(INT) [Length: 2]")
    SETPOINT_FLOAT         = (4 , "Setpoint(FLOAT) [Length: 4]")
    POSITION_INT           = (5 , "Position(INT) [Length: 2]")
    POSITION_FLOAT         = (6 , "Position(FLOAT) [Length: 4]")
    EXCEPTION_DETAIL_ALARM = (7 , "Exception Detail Alarm [Length: 15]")
    EXCEPTION_DETAIL_WARN  = (8 , "Exception Detail Warning [Length: 15]")
    CLOSE_OPEN_CHECK       = (9 , "Valve Close/Open Check [Length: 1]")
    DEVICE_STATUS_2        = (10, "Device Status 2 [Length: 1]")
    ACCESS_MODE            = (11, "Access Mode [Length: 1]")
    CONTROLLER_CTRL_MODE   = (12, "Controller Control Mode [Length: 1]")
    CONTROLLER_SELECTOR    = (13, "Controller Selector [Length: 1]")
    CTRL_GAIN              = (14, "Control Gain(P-Gain) [Length: 4]")
    SENSOR_DELAY           = (15, "Sensor Delay [Length: 4]")
    RAMP_TIME              = (16, "Ramp Time [Length: 4]")
    RAMP_MODE              = (17, "Ramp Mode [Length: 1]")
    DIRECTION_MODE         = (22, "Direction Mode(Fixed Control) [Length: 1]")
    CTRL_DELTA_GAIN        = (23, "Control Delta Gain(I-Gain) [Length: 4]")
    SENSOR1_READ_INT       = (24, "Sensor 1 Reading(INT) [Length: 2]")
    SENSOR1_READ_FLOAT     = (25, "Sensor 1 Reading(FLOAT) [Length: 4]")
    SENSOR2_READ_INT       = (26, "Sensor 2 Reading(INT) [Length: 2]")
    SENSOR2_READ_FLOAT     = (27, "Sensor 2 Reading(FLOAT) [Length: 4]")
    DUMMY                  = (28, "Dummy [Length: 1]")


class DeviceNetOutSelector(DescriptionEnum):
    NONE                   = (0, "NONE")
    CTRL_MODE              = (1, "CONTROL MODE")
    SETPOINT               = (2, "SETPOINT")
    SETPOINT_PRESSURE      = (3, "SETPOINT PRESSURE")
    SETPOINT_POSITION      = (4, "SETPOINT POSITION")
    SETPOINT_TYPE          = (5, "SETPOINT TYPE")
    LEARN                  = (6, "LEARN")
    LEARN_PRESSURE_LIMIT   = (7, "LEARN PRESSURE LIMIT")
    ZERO                   = (8, "ZERO")
    KP                     = (9, "KP (Gain Factor)")
    KI                     = (10, "KI (Delta Factor)")
    KD                     = (11, "KD (Ramp Time)")
    CLUSTER_ADDRESS        = (12, "CLUSTER ADDRESS")
    CLUSTER_ACTION         = (13, "CLUSTER ACTION")

class DeviceNetInSelector(DescriptionEnum):
    NONE                   = (0, "NONE")
    EXCEPTION_STATUS       = (1, "EXCEPTION STATUS")
    EXCEPTION_DETAIL_ALARM = (2, "EXCEPTION DETAIL ALARM")
    EXCEPTION_DETAIL_WARN  = (3, "EXCEPTION DETAIL WARNING")
    PRESSURE               = (4, "PRESSURE")
    POSITION               = (5, "POSITION")
    CLOSE_OPEN_CHECK       = (6, "CLOSE/OPEN CHECK")
    DEVICE_STATUS_2        = (7, "DEVICE STATUS 2")
    SENSOR1_READING        = (8, "SENSOR 1 READING")
    SENSOR2_READING        = (9, "SENSOR 2 READING")
    READING_SENSOR         = (10, "READING SENSOR")
    CTRL_MODE              = (11, "CONTROL MODE")
    SETPOINT               = (12, "SETPOINT")
    SETPOINT_PRESSURE      = (13, "SETPOINT PRESSURE")
    SETPOINT_POSITION      = (14, "SETPOINT POSITION")
    SETPOINT_TYPE          = (15, "SETPOINT TYPE")
    ACCESS_MODE            = (16, "ACCESS MODE")
    CLUSTER_INFORMATION    = (17, "CLUSTER INFORMATION")
    CLUSTER_ACTION         = (18, "CLUSTER ACTION")

class DeviceNetPositionUnitEnum(DescriptionEnum):
    COUNT   = (4097, "Count")
    PERCENT = (4103, "Percnet")
    DEGREE  = (5891, "Degree")

class DeviceNetPressureUnitEnum(DescriptionEnum):
    COUNTS    = (4097, "Counts")
    PERCENT   = (4103, "Percent")
    PSI       = (4864, "PSI")
    TORR      = (4865, "Torr")
    MTORR     = (4866, "mTorr")
    BAR       = (4871, "Bar")
    MBAR      = (4872, "mBar")
    PA        = (4873, "Pa")
    ATM       = (4875, "atm")

class DeviceNetLossFunEnum(DescriptionEnum):
    OPEN = (0, "Open")
    CLOSE = (1, "Close")
    KEEP_POSITION = (2, "Keep Position")    

class EtherCATStateEnum(DescriptionEnum):
    ERROR        = (0, "Error")
    INIT         = (1, "Init")
    PRE_OP       = (2, "Pre-Op")
    BOOTSTRAP    = (3, "Bootstrap")
    SAFE_OP      = (4, "Safe-Op")
    OP           = (8, "OP")

class EtherCATXmlVerEnum(DescriptionEnum):
    VER_1        = (0, "V1")
    VER_2        = (1, "V2")    

class EtherCATDataTypeEnum(DescriptionEnum):
    INT     = (0, "INT32")
    FLOAT   = (1, "FLOAT32")

class SlaveLossFunEnum(DescriptionEnum):
    CLOSE = (0, "Close")
    OPEN = (1, "Open")
    KEEP_POSITION = (2, "Keep Position")        

class ClusterUnfreezeFreezeEnum(DescriptionEnum):
    UNFREEZE = (0, "Unfreeze")
    FREEZE   = (1, "Freeze") 

class ClusterHomingEndPosiEnum(DescriptionEnum):
    CLOSE = (0, "Close")
    OPEN  = (1, "Open") 

class ClusterHomingStartConditionEnum(DescriptionEnum):
    DEFAULT_NOT_SEALED = (0, "Default[not sealed]")
    SELECTED_COMMAND   = (1, "Selected Command") 
    OPEN_COMMAND       = (2, "Open Command") 
    ANY_COMMAND        = (3, "Any Command") 

class ClusterHomingModeEnum(DescriptionEnum):
    SHORT    = (0, "Short")
    EXTENDED = (1, "Extended")   

class ClusterPowerFailOptEnum(DescriptionEnum):
    CLOSE = (0, "Close")
    OPEN  = (1, "Open") 

class ClusterNetworkFailOptEnum(DescriptionEnum):
    CLOSE         = (0, "Close")
    OPEN          = (1, "Open")      
    KEEP_POSITION = (2, "Keep Position") 
    