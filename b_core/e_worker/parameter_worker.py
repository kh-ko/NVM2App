from b_core.c_manager.parameter_manager import ParamManager
from typing import Optional
from PySide6.QtCore import QThread, Signal, QObject, QCoreApplication, Slot

from b_core.b_datatype.parameter import Parameter
from b_core.b_datatype.general_enum import LogType
from b_core.c_manager.log_manager import LogManager
from b_core.d_dal.service_port import ServicePort

class ParameterThread(QObject):
    sig_read_result = Signal(str, object)
    sig_write_result = Signal(str, object)

    # sample code
    @Slot(str, object)
    def process_read_request(self, packet: str, param: Parameter):
        response = ServicePort().request_string(packet, True, True)
        self.sig_read_result.emit(response, param)

    # sample code
    @Slot(str, object)
    def process_write_request(self, packet: str, param: Parameter):
        response = ServicePort().request_string(packet, True, True)
        self.sig_write_result.emit(response, param)

class ParameterWorker(QObject):
    sig_read_request = Signal(str, object)
    sig_write_request = Signal(str, object)

    sig_progress_changed = Signal(int)

    @property
    def progress(self) -> int:
        return self._progress

    @progress.setter
    def progress(self, progress: int):
        if self._progress != progress:
            self._progress = progress
            self.sig_progress_changed.emit(progress)

    sig_is_working_changed = Signal(bool)

    @property
    def is_working(self) -> bool:
        return self._is_working

    @is_working.setter
    def is_working(self, is_working: bool):
        if self._is_working != is_working:
            self._is_working = is_working
            self.sig_is_working_changed.emit(is_working)        

    def __init__(self, parent=None):
        super().__init__(parent)
        self._thread = QThread()
        self._param_thread = ParameterThread()
        
        self._param_thread.moveToThread(self._thread)

        self.sig_read_request.connect(self._param_thread.process_read_request)
        self.sig_write_request.connect(self._param_thread.process_write_request)
        
        self._param_thread.sig_read_result.connect(self.handle_read_result)
        self._param_thread.sig_write_result.connect(self.handle_write_result)

        self._is_working = False
        self._progress = 0 # 0 ~ 100 (단위 %)

        self._current_phase = ""  # "INIT", "READ", "MONITOR", "STOP"
        self._current_index = 0
        self._current_param: Optional[Parameter] = None
        self._processed_count = 0
        self._total_target_count = 0

        self.init_param_list: list[Parameter] = []
        self.read_param_list: list[Parameter] = []
        self.write_param_list: list[Parameter] = []
        self.monitor_param_list: list[Parameter] = []

        # 메모리 해제 관련 시그널 연결
        self._thread.finished.connect(self._param_thread.deleteLater)
        self._thread.finished.connect(self._thread.deleteLater)

        app = QCoreApplication.instance()
        if app is not None:
            app.aboutToQuit.connect(self._destroyed)

        self.destroyed.connect(self._destroyed)

        self._thread.start()

    def add_init_param(self, param_full_path: str):
        param = ParamManager().get_by_full_path(param_full_path)
        if param is not None:
            self.init_param_list.append(param)
            
    def add_read_param(self, param_full_path: str):
        param = ParamManager().get_by_full_path(param_full_path)
        if param is not None:
            self.read_param_list.append(param)

    def add_write_param(self, param_full_path: str):
        param = ParamManager().get_by_full_path(param_full_path)
        if param is not None:
            self.write_param_list.append(param)

    def add_monitor_param(self, param_full_path: str):
        param = ParamManager().get_by_full_path(param_full_path)
        if param is not None:
            self.monitor_param_list.append(param)

    def refresh(self):            
        self._total_target_count = len(self.init_param_list) + len(self.read_param_list)
        self._processed_count = 0
        
        self.is_working = True
        self.progress = 0
        
        self._current_phase = "INIT"
        self._current_index = 0
        
        self._request_read_next()
            
    def read(self):
        pass

    def write(self):
        pass

    def _request_read_next(self):        
        if self._current_phase == "STOP":
            return

        if self._current_phase == "INIT":
            if self._current_index < len(self.init_param_list):
                param = self.init_param_list[self._current_index]
                self._send_read_request(param)
                return
            else:
                self._current_phase = "READ"
                self._current_index = 0

        if self._current_phase == "READ":
            if self._current_index < len(self.read_param_list):
                param = self.read_param_list[self._current_index]
                self._send_read_request(param)
                return
            else:
                self.is_working = False
                self.progress = 0
                
                self._current_phase = "MONITOR"
                self._current_index = 0

        if self._current_phase == "MONITOR":
            if not self.monitor_param_list:
                return
            
            if self._current_index >= len(self.monitor_param_list):
                self._current_index = 0
                
            param = self.monitor_param_list[self._current_index]
            self._send_read_request(param)

    def _send_read_request(self, param: Parameter):
        packet = f"p:0B{param.id}{param.index:02X}"
        self._current_param = param
        self.sig_read_request.emit(packet, param)

    @Slot(str, object)
    def handle_read_result(self, resp_msg: str, param: Parameter):

        result = param.set_read_response_packet(resp_msg)

        if result is not None:
            LogManager().log(LogType.ERROR, result)
        
        if self._current_param != param:
            return

        if resp_msg is None: # 통신 오류 이므로 계속 재 시도 해야함
            self._request_read_next()
            return

        if self._current_phase in ["INIT", "READ"]:
            self._processed_count += 1
            if self._total_target_count > 0:
                self.progress = int((self._processed_count / self._total_target_count) * 100)

        self._current_index += 1
        self._request_read_next()

    @Slot(str, object)
    def handle_write_result(self, resp_msg: str, param: Parameter):
        pass     

    def _destroyed(self):
        app = QCoreApplication.instance()
        if app is not None:
            try:
                app.aboutToQuit.disconnect(self._destroyed)
            except (TypeError, RuntimeError):
                pass
        if self._thread is not None and self._thread.isRunning():
            
            if self._param_thread:
                self._param_thread.blockSignals(True)
            
            self._thread.quit()  
            self._thread.wait()  
            
            self._thread = None       
            self._param_thread = None    
    