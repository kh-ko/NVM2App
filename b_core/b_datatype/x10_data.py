from typing import NamedTuple

# 클래스 바깥이나 별도 파일에 정의
class X10Data(NamedTuple):
    timestamp: int
    act_posi_pfs: float
    act_pres_sfs: float
    target_posi_pfs_used: float
    target_pres_sfs_used: float
    speed: float
    access_mode: int
    control_mode: int
    pres_contoller_selector: int
    is_simulator_on: bool
    is_PFO_on: bool
    is_test_mode_on: bool
    is_field_bus_error: bool
    is_saving: bool
    is_id_missing: bool
    is_pfo_missing: bool
    is_firmware_error: bool
    is_unknow_interface: bool
    is_no_sensor_signal: bool
    is_no_analog_signal: bool
    is_sensor_error: bool
    is_isolation_valve: bool
    is_slave_offline: bool
    is_network_failure: bool
    is_svc_request: bool
    is_learn_not_present: bool
    is_air_not_ready: bool
    is_pfo_not_ready: bool