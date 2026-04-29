from enum import Enum

class DescriptionEnum(Enum):
    def __new__(cls, value, description):
        obj = object.__new__(cls)
        obj._value_ = value
        obj.description = description
        return obj

class FalseTrueEnum(DescriptionEnum):
    FALSE           = (0, "False")
    TRUE            = (1, "True")

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
    ISOLATION_VALVE_DOES_NOT_WORK   = (1, "Isolation valve does not work")
    NO_SENSOR_ACTIVE                = (2, "No Sensor Active")
    PFO_NOT_READY                   = (3, "PFO Not Ready")
    CLUSTER_SLAVE_OFFLINE           = (4, "Cluster Slave Offline")
    FIELDBUS_DATA_NOT_VALID         = (6, "Fieldbus Data Not Valid")
    NETWORK_FAILURE                 = (7, "Network failure")
    COMPRESSED_AIR_NOT_FALLING      = (8, "Compressed Air Not Falling when valve close")
    COMPRESSED_AIR_TOO_LOW          = (9, "Compressed Air Too Low")
    COMPRESSED_AIR_TOO_HIGH         = (10, "Compressed Air Too High")
    FAN_STALL_ALARM                 = (12, "Fan stall alarm")
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
    NO_ERROR        = (0, "No Error")
    ALL_MOTOR_UNITS = (1, "All Motor Units")
    MOTOR_UNIT_1    = (2, "Motor Unit 1")
    MOTOR_UNIT_2    = (3, "Motor Unit 2")
    MOTOR_UNIT_3    = (4, "Motor Unit 3")
    OTHER_COMPONENT = (8, "Other")

class SysErrorNumberMode(DescriptionEnum):
    HOMING          = (0, "Homing")
    OPERATION_MODE  = (2, "Operation Mode")
    OTHER           = (8, "Other")

class SysErrorNumberType(DescriptionEnum):
    POSITION_ERROR          = (0, "Position Error")
    NOT_RUNNING             = (1, "Not running: No communication with component x")
    ERROR_STATE             = (2, "Error State: component x is running but in Status Error")
    OTHER                   = (8, "Other")    
         
class SysErrorCodeEnum(DescriptionEnum):
    NO_ERROR                                                                            = (0, "No error")
    NO_VALVE_CONNECTED                                                                  = (1, "No valve connected")
    NONVOLATILE_MEMORY_FAILURE                                                          = (2, "Nonvolatile memory failure")
    ANALOG_DIGITAL_CONVERTER_OF_SENSOR_INPUT_FAILURE                                    = (3, "Analog digital converter of sensor input failure")
    INITIALIZATION_OF_MOTION_CONTROLLER_FAILED                                          = (4, "Initialization of motion controller failed")
    ENCODER_INDEX_PULSE_NOT_FOUND                                                       = (5, "Encoder index pulse not found")
    INITIALIZATION_OF_INTERFACE_MODULE_FAILED                                           = (6, "Initialization of interface module failed")
    INITIALIZATION_OF_EXTERNAL_DRIVE_EEPROM_FAILED                                      = (7, "Initialization of external drive EEProm failed")
    CLOSING_POSITION_CAN_NOT_BE_REACHED                                                 = (10, "Closing position can not be reached")
    HOMING_POSITION_CAN_NOT_BE_REACHED                                                  = (11, "Homing position can not be reached")
    MOTION_CONTROLLER_INTERNAL_VOLTAGE_ERROR                                            = (12, "Motion controller (Internal voltage error)")
    MOTION_CONTROLLER_INTERNAL_ERROR_TEMPERATURE                                        = (13, "Motion controller (Internal error temperature)")
    MOTION_CONTROLLER_UNEXPECTED_BEHAVIOR                                               = (14, "Motion controller (Unexpected behavior)")
    MOTION_CONTROLLER_TARGET_POSITION_CAN_NOT_BE_REACHED                                = (15, "Motion controller (Target position can not be reached)")
    MOTION_CONTROLLER_POSITION_MINIMAL_CONDUCTANCE_CAN_NOT_BE_REACHED                   = (16, "Motion controller (Position minimal conductance cannot be reached)")
    MOTION_CONTROLLER_POSITION_TO_PUSH_BACK_THE_DIFFERENTIAL_PLATE_CAN_NOT_BE_REACHED   = (17, "Motion controller (Position to push back the Differential Plate cannot be reached)")
    MOTION_CONTROLLER_MINIMAL_ISOLATION_POSITION_CAN_NOT_BE_REACHED                     = (18, "Motion controller (Minimal isolation position cannot be reached)")
    BREAK_SLIPPERY_DETECTED                                                             = (20, "Break slippery detected")
    SFV_MOTION_CONTROLLER_FAILURE_IN_MASTER_SLAVE_COMMUNICATION                         = (30, "SFV (Motion controller failure in master-slave communication)")
    COMPRESSED_AIR_ERROR                                                                = (40, "Compressed air error")
    POWER_SUPPLY_LOW_VOLTAGE_DETECTED                                                   = (42, "Power supply (low voltage detected)")
    SFV_POSITION_DEVIATION_AXIS1_TO_AXIS2_AT_HOMING_PROCEDURE                           = (96, "SFV (Position deviation axis1 to axis2 at homing procedure)")
    SFV_POSITION_DEVIATION_AXIS1_TO_AXIS2_AT_OPERATING                                  = (97, "SFV (Position deviation axis1 to axis2 at operating)")
    POSITION_ERROR_DURING_CLOSING_PROCEDURE                                             = (98, "Position error during closing procedure")
    POSITION_ERROR_AT_OPERATING                                                         = (99, "Position error at operating")
    VALVE_CONFIGURATION_ERROR                                                           = (200, "Valve configuration error (not possible to operate the valve with these configuration)")
    WRONG_IDENT_CODE_AXIS_1                                                             = (701, "Wrong ident code axis 1")
    WRONG_IDENT_CODE_AXIS_2                                                             = (702, "Wrong ident code axis 2")
    WRONG_IDENT_CODE_AXIS_2_AND_AXIS_1                                                  = (703, "Wrong ident code axis 2 AND axis 1")
    WRONG_IDENT_CODE_AXIS_3                                                             = (704, "Wrong ident code axis 3")
    WRONG_IDENT_CODE_AXIS_3_AND_AXIS_1                                                  = (705, "Wrong ident code axis 3 AND axis 1")
    WRONG_IDENT_CODE_AXIS_3_AND_AXIS_2                                                  = (706, "Wrong ident code axis 3 AND axis 2")
    WRONG_IDENT_CODE_AXIS_3_AND_AXIS_2_AND_AXIS_1                                       = (707, "Wrong ident code axis 3 AND axis 2 AND axis 1")

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

class PresCtrlThresCondEnum(DescriptionEnum):
    LOWER_OR_EQUAL    = (0, "Lower Or Equal")
    EQUAL             = (1, "Equal")

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



