import time
from datetime import datetime

from typing import List, Tuple
from collections import deque
from PySide6.QtCore import QCoreApplication, QObject, QThread, QMutex, QMutexLocker, Signal

from b_core.d_dal.service_port import ServicePort
from b_core.b_datatype import param_enum as p_enum
from b_core.b_datatype.general_enum import SvcPortErrType
from b_core.b_datatype.compound_data import CompoundData
from b_core.b_datatype.parameter import Parameter

from b_core.c_manager.log_manager import LogManager
from b_core.c_manager.parameter_manager import ParamManager

class CompoundsWorkerThread(QThread):
    sig_log = Signal(bool, str, str, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._loop_log_count : int = 0
        self._is_running : bool = False
        self._is_not_connected : bool = True
        self.svc_port : ServicePort = ServicePort()
        self._cmd_bytes : bytes = b"x:10"
        self.data_queue = deque(maxlen=200)
        self.queue_mutex = QMutex()
        self.compound_write_cmds : List[bytes] = []
        self.compound_read_bytes : bytes = b""

    def set_compound_pairs(self, pairs: list[tuple[Parameter, Parameter | None]]):
        self.compound_write_cmds.clear()
        self.compound_read_bytes = b""

        if not pairs:
            return

        for param1, param2 in pairs:
            idx_str = f"{param1.index:02X}" 
            p2_id = param2.id if param2 is not None else "00000000"
            cmd_str = f"p:01{param1.id}{idx_str}{int(p2_id, 16)}"
            self.compound_write_cmds.append(cmd_str.encode('utf-8'))

        first_param_id = pairs[0][0].id
        read_str = f"p:29{first_param_id}00"
        self.compound_read_bytes = read_str.encode('utf-8')

    # self.svc_port.connect_info 값이 존재할때 serial port가 연결되어있는 상태이다.
    # 최초 연결되면 compound_write_cmds를 모두 실행한다. wirte 된 항목에서 대해서 추후 compound_read_bytes의 응답으로 values가 반환된다.
    # 모든 통신은 성공이후 sleep없이 바로 다음 동작을수행한다. 어차피 Serial 통신이므로 self.svc_port 내부에서 적절하게 대기 하도록 된다.
    def run(self):
        self._is_running = True

        response: str | None = None
        err_type: SvcPortErrType | None = None
        
        while self._is_running:
            if self.svc_port.connect_info:
                if self._is_not_connected: 
                    for cmd in self.compound_write_cmds: 
                        if not self._is_running:
                            break

                        response, err_type = self.svc_port.request(cmd)

                        if err_type != SvcPortErrType.NONE:
                            self.sig_log.emit(True, cmd.hex(), response, f"Write Compound Fail : {err_type}")
                            self.msleep(100) 
                            break
                        
                        if not response.startswith("p:0001"):
                            self.sig_log.emit(True, cmd.hex(), response, "Write Compound Fail")
                            self.msleep(100) 
                            break

                        self.sig_log.emit(False, cmd.hex(), response, "Write Compound Success")
                    else:
                        self._is_not_connected = False
            else:
                self._is_not_connected = True
                self.msleep(100)
                continue

            if self._is_not_connected:
                self.msleep(100)
                continue

            if not self.compound_read_bytes:
                self.sig_log.emit(True, "TX : Not Set", "", "[Compound Read Command] is not set")
                self.msleep(100)
                continue

            response, err_type = self.svc_port.request(self.compound_read_bytes)
            
            if err_type == SvcPortErrType.NONE and response.startswith("p:0029"):
                try:
                    self._loop_log_count += 1

                    if self._loop_log_count % 100 == 0:
                        self.sig_log.emit(False, self.compound_read_bytes.hex(), response, "Read Compound Success")

                    payload = response[16:]
                    values = payload.split(';')
                    
                    if len(values) >= 12:
                        current_ms = int(time.time() * 1000)
                        
                        parsed_data = CompoundData(
                            current_ms,
                            int(values[0]),   # access_mode
                            int(values[1]),   # control_mode
                            float(values[2]),     # act_posi
                            float(values[3]),     # act_pres
                            float(values[4]),     # target_posi
                            float(values[5]),     # target_pres
                            float(values[6]),     # speed
                            int(values[7]),   # pres_contoller_selector
                            int(values[8]),   # warning_bitmap
                            int(values[9]),   # error_bitmap
                            int(values[10]),  # error_number
                            int(values[11])   # error_code
                        )
                        
                        with QMutexLocker(self.queue_mutex):
                            self.data_queue.append(parsed_data)

                    else:
                        self.sig_log.emit(True, self.compound_read_bytes.hex(), response, "Response is short")
                        
                except Exception as e:
                    self.sig_log.emit(True, self.compound_read_bytes.hex(), response, f"Error: {str(e)}")
            else:
                self.msleep(1000)

    def stop(self):
        self._is_running = False

class CompoundsRunWorker(QObject):

    def __init__(self, parent=None):
        super().__init__(parent)

        param_mapping = [
            ("System.Access Mode", 0),
            ("System.Control Mode", 1),
            ("Position Control.Basic.Actual Position", 2),
            ("Position Control.Basic.Target Position Used", 3),
            ("Pressure Control.Basic.Actual Pressure", 4),
            ("Pressure Control.Basic.Target Pressure Used", 5),
            ("Position Control.Basic.Position Control Speed", 6),
            ("Pressure Control.Basic.Controller Selector Used", 7),
            ("System.Warning/Error.Warning Bitmap", 8),
            ("System.Warning/Error.Error Bitmap", 9),
            ("System.Warning/Error.Error Number", 10),
            ("System.Warning/Error.Error Code", 11)
        ]

        self._thread = CompoundsWorkerThread(self)
        self._thread.sig_log.connect(self.handle_log_event)

        self.compound_pairs : List[Tuple[Parameter, Parameter | None]] = []

        for ref_path, index in param_mapping:
            compound_path = f"Compound Commands.NVM For Sevice.Compound Commands 1.[{index}]"
            compound = ParamManager().get_by_full_path(compound_path)
            ref_param = ParamManager().get_by_full_path(ref_path)
            self.compound_pairs.append((compound, ref_param))

        # 마지막 12번 인덱스 (None 처리)
        compound_12 = ParamManager().get_by_full_path("Compound Commands.NVM For Sevice.Compound Commands 1.[12]")
        self.compound_pairs.append((compound_12, None))

        app = QCoreApplication.instance()
        if app is not None:
            app.aboutToQuit.connect(self._destroyed)

        self.destroyed.connect(self._destroyed)

    def start(self):
        if self._thread is not None and not self._thread.isRunning():
            self._thread.set_compound_pairs(self.compound_pairs)
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

        if data_list:
            last_data = data_list[-1]
            
            # __init__ 에서 구성한 param_mapping 인덱스(0~11) 순서와 동일하게 매핑
            # (CompoundData의 실제 속성명이 다를 경우, 해당 클래스에 맞춰 수정 필요)
            latest_values = [
                last_data.access_mode,               # 0
                last_data.control_mode,              # 1
                last_data.act_posi,                  # 2
                last_data.act_pres,                  # 3
                last_data.target_posi,               # 4
                last_data.target_pres,               # 5
                last_data.speed,                     # 6
                last_data.pres_contoller_selector,   # 7
                last_data.warning_bitmap,            # 8
                last_data.error_bitmap,              # 9
                last_data.error_number,              # 10
                last_data.error_code                 # 11
            ]
            
            for index, val in enumerate(latest_values):
                # compound_pairs는 (compound, ref_param) 형태
                compound, ref_param = self.compound_pairs[index]
                
                # 12번 인덱스처럼 ref_param이 None인 경우를 방어
                if ref_param is not None:
                    ref_param.set_force_value(str(val))

        return data_list

    def handle_log_event(self, is_err: bool, tx: str, rx: str, msg: str):
        now = datetime.now()
        time_str = now.strftime("%H:%M:%S.%f")[:-3]
        status = "ERROR" if is_err else "INFO"
        
        log_msg = (
            f"[Compound Worker][{time_str}] [{status}] "
            f"Tx: {tx} "
            f"Rx: {rx} "
            f"Message: {msg}"
        )

        print(log_msg)

    def _destroyed(self):
        app = QCoreApplication.instance()
        if app is not None:
            try:
                app.aboutToQuit.disconnect(self._destroyed)
            except (TypeError, RuntimeError):
                pass

        self.stop()
        self._thread = None            