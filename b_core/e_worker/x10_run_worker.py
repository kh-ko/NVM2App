import time
from collections import deque
from PySide6.QtCore import QCoreApplication, QObject, QThread, QMutex, QMutexLocker

from b_core.d_dal.service_port import ServicePort
from b_core.b_datatype import param_enum as p_enum
from b_core.b_datatype.general_enum import LogType
from b_core.b_datatype.x10_data import X10Data

from b_core.c_manager.log_manager import LogManager

class X10WorkerThread(QThread):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._is_running : bool = False
        self.svc_port : ServicePort = ServicePort()
        self._cmd_bytes : bytes = b"x:10"
        self.data_queue = deque(maxlen=200)
        self.queue_mutex = QMutex()

    def run(self):
        self._is_running = True
        
        while self._is_running:
            response : str | None = self.svc_port.request(self._cmd_bytes, False, False)
            
            if response is not None and response.startswith("x:10") and len(response) >= 39:
                try:
                    start_idx = len("x:10")
                    current_ms              = int(time.time() * 1000)
                    act_posi_pfs            = float(response[start_idx:start_idx+6]) / 100000.0 ; start_idx += 6
                    act_pres_sfs            = float(response[start_idx:start_idx+8]) / 1000000.0; start_idx += 8
                    target_value            = int(response[start_idx:start_idx+8])              ; start_idx += 8
                    speed                   = float(response[start_idx:start_idx+4]) / 1000.0   ; start_idx += 4
                    start_idx += 1          #dummy = response[start_idx]                                                   
                    access_mode             = int(response[start_idx:start_idx+1], 36)          ; start_idx += 1
                    control_mode            = int(response[start_idx:start_idx+1], 36)          ; start_idx += 1
                    pres_contoller_selector = int(response[start_idx:start_idx+1], 36)          ; start_idx += 1
                    status_bitmap           = int(response[start_idx:start_idx+1], 36)          ; start_idx += 1
                    warning_bitmap          = int(response[start_idx:start_idx+1], 36)          ; start_idx += 1
                    warning_bitmap2         = int(response[start_idx:start_idx+1], 36)          ; start_idx += 1
                    warning_bitmap3         = int(response[start_idx:start_idx+1], 36)          ; start_idx += 1
                    warning_bitmap4         = int(response[start_idx:start_idx+1], 36)          ; start_idx += 1

                    is_simulator_on     = (status_bitmap  & 0x01) == 0x01
                    is_PFO_on           = (status_bitmap  & 0x02) == 0x02
                    is_test_mode_on     = (status_bitmap  & 0x04) == 0x04

                    is_field_bus_error  = (warning_bitmap & 0x01) == 0x01
                    is_saving           = (warning_bitmap & 0x02) == 0x02
                    is_id_missing       = (warning_bitmap & 0x04) == 0x04
                    is_pfo_missing      = (warning_bitmap & 0x08) == 0x08

                    is_firmware_error   = (warning_bitmap2 & 0x01) == 0x01
                    is_unknow_interface = (warning_bitmap2 & 0x02) == 0x02
                    is_no_sensor_signal = (warning_bitmap2 & 0x04) == 0x04
                    is_no_analog_signal = (warning_bitmap2 & 0x08) == 0x08

                    is_sensor_error     = (warning_bitmap3 & 0x01) == 0x01
                    is_isolation_valve  = (warning_bitmap3 & 0x02) == 0x02
                    is_slave_offline    = (warning_bitmap3 & 0x04) == 0x04
                    is_network_failure  = (warning_bitmap3 & 0x08) == 0x08
                    
                    is_svc_request      = (warning_bitmap4 & 0x01) == 0x01
                    is_learn_not_present= (warning_bitmap4 & 0x02) == 0x02
                    is_air_not_ready    = (warning_bitmap4 & 0x04) == 0x04
                    is_pfo_not_ready    = (warning_bitmap4 & 0x08) == 0x08

                    target_posi_pfs_used = 0.0
                    target_pres_sfs_used = 0.0

                    if control_mode == p_enum.ControlModeEnum.POSITION.value:
                        target_posi_pfs_used = target_value / 100000.0
                    elif control_mode == p_enum.ControlModeEnum.PRESSURE.value:
                        target_pres_sfs_used = target_value / 1000000.0
                    
                    parsed_data = X10Data(current_ms, act_posi_pfs, act_pres_sfs, target_posi_pfs_used, target_pres_sfs_used, speed, access_mode, control_mode, pres_contoller_selector, 
                                            is_simulator_on, is_PFO_on, is_test_mode_on, 
                                            is_field_bus_error, is_saving, is_id_missing, is_pfo_missing, 
                                            is_firmware_error, is_unknow_interface, is_no_sensor_signal, is_no_analog_signal, 
                                            is_sensor_error, is_isolation_valve, is_slave_offline, is_network_failure, 
                                            is_svc_request, is_learn_not_present, is_air_not_ready, is_pfo_not_ready)

                    # ★ 자물쇠를 채우고 안전하게 큐에 저장
                    with QMutexLocker(self.queue_mutex):
                        self.data_queue.append(parsed_data)
                    
                except Exception as e:
                    LogManager().log(LogType.ERROR, f"X10WorkerThread._run() Error: {str(e)}")
            else:
                self.msleep(1000)

    def stop(self):
        self._is_running = False

class X10RunWorker(QObject):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._thread = X10WorkerThread(self)

        app = QCoreApplication.instance()
        if app is not None:
            app.aboutToQuit.connect(self._destroyed)

        self.destroyed.connect(self._destroyed)

    def start(self):
        if self._thread is not None and not self._thread.isRunning():
            self._thread.start()

    def stop(self):
        if self._thread is not None and self._thread.isRunning():
            self._thread.stop()
            self._thread.wait()

    def pop_all_data(self):
        if self._thread is None:
            return []

        data_list = []
        with QMutexLocker(self._thread.queue_mutex):
            while self._thread.data_queue:
                data_list.append(self._thread.data_queue.popleft())
        return data_list

    def _destroyed(self):
        app = QCoreApplication.instance()
        if app is not None:
            try:
                app.aboutToQuit.disconnect(self._destroyed)
            except (TypeError, RuntimeError):
                pass

        self.stop()
        self._thread = None            