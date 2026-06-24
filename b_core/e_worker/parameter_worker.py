from b_core.b_datatype.general_enum import ParamDisplayType
from PySide6.QtCore import QTimer
from datetime import datetime

from b_core.c_manager.parameter_manager import ParamManager
from typing import Optional
from PySide6.QtWidgets import QMessageBox
from PySide6.QtCore import QThread, Signal, QObject, QCoreApplication, Slot, Qt

from b_core.b_datatype import param_enum as p_enum
from b_core.b_datatype.parameter import Parameter
from b_core.b_datatype.general_enum import ParamAccType, SvcPortErrType, ParamParseErrType
from b_core.d_dal.service_port import ServicePort

class ParameterThread(QObject):
    sig_read_result = Signal(str, str, object, SvcPortErrType)
    sig_write_result = Signal(str, str, object, SvcPortErrType)
    sig_monitor_result = Signal(str, str, object, SvcPortErrType)

    # sample code
    @Slot(str, object)
    def process_read_request(self, packet: str, param: Parameter):
        nv1_check = None
        if param.is_nv1_proto:
            nv1_check = param.nv1_read_res

        response, err_type = ServicePort().request_string(packet, nv1_check)
        if err_type != SvcPortErrType.NONE:
            QThread.msleep(100)
            
        self.sig_read_result.emit(packet, response, param, err_type)

    # sample code
    @Slot(str, object)
    def process_write_request(self, packet: str, param: Parameter):
        response, err_type = ServicePort().request_string(packet)
        if err_type != SvcPortErrType.NONE:
            QThread.msleep(100)
            
        self.sig_write_result.emit(packet, response, param, err_type)

    @Slot(str, object)
    def process_monitor_request(self, packet: str, param: Parameter):
        nv1_check = None
        if param.is_nv1_proto:
            nv1_check = param.nv1_read_res

        response, err_type = ServicePort().request_string(packet, nv1_check)
        if err_type != SvcPortErrType.NONE:
            QThread.msleep(100)
            
        self.sig_monitor_result.emit(packet, response, param, err_type)        

class ParameterWorker(QObject):
    sig_read_request = Signal(str, object)
    sig_write_request = Signal(str, object)
    sig_monitor_request = Signal(str, object)

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

    def __init__(self, win_name:str="Param Worker", monitor_tick=100, parent=None):
        super().__init__(parent)

        self.monitor_timer = QTimer(self)
        self.monitor_timer.setSingleShot(True)
        self.monitor_timer.timeout.connect(self._on_timeout_monitor)
        self.monitor_time_tick = monitor_tick

        self.win_name = win_name
        self._is_cleaned = False

        self._acc_mode_param: Parameter = ParamManager().get_by_full_path("System.Access Mode")

        self._thread = QThread()
        self._param_thread = ParameterThread()
        
        self._param_thread.moveToThread(self._thread)

        self.sig_read_request.connect(self._param_thread.process_read_request)
        self.sig_write_request.connect(self._param_thread.process_write_request)
        self.sig_monitor_request.connect(self._param_thread.process_monitor_request)
        
        self._param_thread.sig_read_result.connect(self.handle_read_result)
        self._param_thread.sig_write_result.connect(self.handle_write_result)
        self._param_thread.sig_monitor_result.connect(self.handle_monitor_result)

        self._is_working = False
        self._progress = 0 # 0 ~ 100 (단위 %)

        self._current_phase = ""  # "INIT", "READ", "STOP"
        self._current_index = 0
        self._current_param: Optional[Parameter] = None
        self._monitor_index = 0
        self._monitor_param: Optional[Parameter] = None
        self._processed_count = 0
        self._total_target_count = 0
        self._monitor_log_count = 0
        self._active_msg_box: Optional[QMessageBox] = None

        self.init_param_list: list[Parameter] = []
        self.read_param_list: list[Parameter] = []
        self.write_param_list: list[Parameter] = []
        self.write_param_proc_list: list[tuple[Parameter, str]] = []
        self.monitor_param_list: list[Parameter] = []

        # 메모리 해제 관련 시그널 연결
        self._thread.finished.connect(self._param_thread.deleteLater)
        self._thread.finished.connect(self._thread.deleteLater)

        app = QCoreApplication.instance()
        if app is not None:
            app.aboutToQuit.connect(self.cleanup)

        self.destroyed.connect(self.cleanup)

        self._thread.start()

    def add_init_param(self, param_full_path: str)->Parameter:
        param = ParamManager().get_by_full_path(param_full_path)
        if param is not None:
            self.init_param_list.append(param)
        return param
            
    def add_read_param(self, param_full_path: str)->Parameter:
        param = ParamManager().get_by_full_path(param_full_path)
        if param is not None:
            self.read_param_list.append(param)
        return param

    def add_read_param_ptr(self, param: Parameter):
        if param is not None:
            self.read_param_list.append(param)

    def add_write_param(self, param_full_path: str)->Parameter:
        param = ParamManager().get_by_full_path(param_full_path)
        if param is not None:
            self.write_param_list.append(param)
        return param

    def add_write_param_ptr(self, param: Parameter):
        if param is not None:
            self.write_param_list.append(param)

    def add_monitor_param(self, param_full_path: str):
        param = ParamManager().get_by_full_path(param_full_path)
        if param is not None:
            self.monitor_param_list.append(param)

    def add_monitor_param_ptr(self, param: Parameter):
        if param is not None:
            self.monitor_param_list.append(param)

    def clear_monitor_param(self):
        self.monitor_param_list.clear()

    def refresh(self):  
        if ServicePort().connect_info:
            is_connected = True
        else:
            is_connected = False

        self._close_active_msg_box()

        self.monitor_timer.stop()
        self._monitor_param = None
        self._monitor_index = 0
        self._current_param = None
        self._current_phase = "STOP" 
        self.is_working = False
        self._processed_count = 0
        self._current_index = 0
        self.progress = 0

        if not is_connected:
            self._show_warning_msgbox("Connection Error", "Communication is not connected. Please check the connection status.")
            return

        self._total_target_count = len(self.init_param_list) + len(self.read_param_list) + len(self.write_param_list)
        self._processed_count = 0
        
        self.is_working = True
        self.progress = 0
        
        self._current_phase = "INIT"
        self._current_index = 0
        
        self._request_read_next()
            
    def read(self):
        # 추후 구현
        pass

    def _on_timeout_monitor(self):
        if len(self.monitor_param_list) < 1:
            return

        if self._monitor_index >= len(self.monitor_param_list):
            self._monitor_log_count += 1
            
            if self._monitor_log_count > 30:
                self._monitor_log_count = 0

            self._monitor_index = 0        

        self._monitor_param = self.monitor_param_list[self._monitor_index]
        if self._monitor_param.is_nv1_proto:
            packet = self._monitor_param.nv1_read_req
        else:
            packet = f"p:0B{self._monitor_param.id}{self._monitor_param.index:02X}"
        self.sig_monitor_request.emit(packet, self._monitor_param)

    def write(self):
        if ServicePort().connect_info:
            is_connected = True
        else:
            is_connected = False

        if self.is_working:
            self._show_warning_msgbox("Warning", f"The '{self._current_phase}' phase is currently in progress. Please try again in a moment.")
            return

        is_only_local_acc: bool = False
        current_acc_mode: int = int(self._acc_mode_param.value) if str(self._acc_mode_param.value).isdigit() else -1 

        if not is_connected:
            self._show_warning_msgbox("Connection Error", "Communication is not connected. Please check the connection status.")
            return
        
        self.write_param_proc_list.clear()

        for param in self.write_param_list:
            if param.write_str_value:
                if param.is_only_local_acc:
                    is_only_local_acc = True

                packet = f"p:01{param.id}{param.index:02X}{param.write_str_value}"
                param.write_str_value = None
                self.write_param_proc_list.append((param, packet))
        
        if is_only_local_acc and current_acc_mode == p_enum.AccModeEnum.REMOTE_LOCKED.value:
            self._show_warning_msgbox("Access Denied", "Cannot modify local-only parameters while in Remote Lock mode.")
            return

        if is_only_local_acc and current_acc_mode == p_enum.AccModeEnum.REMOTE.value:
            reply = self._show_question_msgbox("Access Mode Change", "You are attempting to change a local-only parameter while in Remote mode.\nWould you like to switch to Local mode and continue?")
            
            if reply != QMessageBox.StandardButton.Yes:
                return
            else:
                packet = f"p:01{self._acc_mode_param.id}{self._acc_mode_param.index:02X}{p_enum.AccModeEnum.LOCAL.value}"
                self.write_param_proc_list.insert(0, (self._acc_mode_param, packet))

        self._total_target_count = len(self.read_param_list) + (len(self.write_param_proc_list) * 2)
        self._processed_count = 0

        self.is_working = True
        self.progress = 0
        
        self._current_phase = "WRITE"
        self._current_index = 0
        
        self.monitor_timer.stop()
        self._monitor_param = None
        self._monitor_index = 0
        self._request_write_next()        

    def _request_read_next(self):        
        if self._current_phase == "STOP":
            return

        if self._current_phase == "INIT":
            if self._current_index < len(self.init_param_list):
                param = self.init_param_list[self._current_index]
                self._send_read_request(param)
                return
            else:
                self._current_phase = "READ_WRITE_PARAM"
                self._current_index = 0

        if self._current_phase == "READ_WRITE_PARAM":
            if self._current_index < len(self.write_param_list):
                param = self.write_param_list[self._current_index]
                self._send_read_request(param)
                return
            else:                
                self._current_phase = "READ"
                self._current_index = 0     

        if self._current_phase == "WRITE_AFTER_READ":
            if self._current_index < len(self.write_param_proc_list):
                param = self.write_param_proc_list[self._current_index][0]

                if param.acc == ParamAccType.WO:
                    self._request_read_next_skip()
                else:
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

                self._current_phase = "STOP"
                self._current_index = 0     
                
                if len(self.monitor_param_list) > 0:
                    self.monitor_timer.stop()
                    self.monitor_timer.start(self.monitor_time_tick)
                      

        #if self._current_phase == "MONITOR":
        #    pass
            #if not self.monitor_param_list:
            #    return
            #if self._current_index >= len(self.monitor_param_list):
            #    self._current_index = 0
            #param = self.monitor_param_list[self._current_index]
            #self._send_read_request(param)

    def _request_read_next_skip(self):
        if self._current_phase in ["INIT", "READ_WRITE_PARAM", "WRITE_AFTER_READ", "READ"]:
            self._processed_count += 1
            if self._total_target_count > 0:
                self.progress = int((self._processed_count / self._total_target_count) * 100)

        self._current_index += 1
        self._request_read_next()


    def _send_read_request(self, param: Parameter):
        packet = f"p:0B{param.id}{param.index:02X}"
        self._current_param = param
        self.sig_read_request.emit(packet, param)

    def _request_write_next(self):        
        if self._current_phase != "WRITE":
            return

        if self._current_phase == "WRITE":
            if self._current_index < len(self.write_param_proc_list):
                param, packet = self.write_param_proc_list[self._current_index]
                self._send_write_request(param, packet)
                return
            else:                
                self._current_phase = "WRITE_AFTER_READ"
                self._current_index = 0
                self._request_read_next()

    def _send_write_request(self, param: Parameter, packet: str):
        self._current_param = param
        self.sig_write_request.emit(packet, param)

    @Slot(str, str, object, SvcPortErrType)
    def handle_read_result(self, req_msg:str, resp_msg: str, param: Parameter, err_type:SvcPortErrType):
        if self._current_param != param or self._current_phase == "STOP":
            return

        self._add_log(req_msg, resp_msg, param)

        param_err_type, need_retry = param.set_read_response_packet(resp_msg)

        if err_type != SvcPortErrType.NONE:
            self._add_log(req_msg, resp_msg, param, err_type.name, True)
            self._request_read_next()
            return

        if param_err_type != ParamParseErrType.NONE:
            self._add_log(req_msg, resp_msg, param, param_err_type.name, True)
            if need_retry:
                self._request_read_next()
                return

        if self._current_phase in ["INIT", "READ_WRITE_PARAM", "WRITE_AFTER_READ", "READ"]:
            self._processed_count += 1
            if self._total_target_count > 0:
                self.progress = int((self._processed_count / self._total_target_count) * 100)

        self._current_index += 1
        self._request_read_next()

    @Slot(str, str, object, SvcPortErrType)
    def handle_monitor_result(self, req_msg:str, resp_msg: str, param: Parameter, err_type:SvcPortErrType):
        if self._monitor_param != param:
            return

        self._add_log(req_msg=req_msg, resp_msg=resp_msg, param=param,is_monitor=True)

        if param.display_type == ParamDisplayType.NV1_GROUP:
            param_err_type, need_retry = param.set_read_response_nv1_group_packet(resp_msg)
        else:
            param_err_type, need_retry = param.set_read_response_packet(resp_msg)

        if err_type != SvcPortErrType.NONE:
            self._add_log(req_msg=req_msg, resp_msg=resp_msg, param=param, err_msg=err_type.name, is_monitor=True, is_error=True)
            self.monitor_timer.start(self.monitor_time_tick)   
            return

        if param_err_type != ParamParseErrType.NONE:
            self._add_log(req_msg=req_msg, resp_msg=resp_msg, param=param, err_msg=param_err_type.name, is_monitor=True, is_error=True)
            if need_retry:
                self.monitor_timer.start(self.monitor_time_tick)   
                return

        self._monitor_index += 1
        self.monitor_timer.start(self.monitor_time_tick)       

    @Slot(str, str, object, SvcPortErrType)
    def handle_write_result(self, req_msg:str, resp_msg: str, param: Parameter, err_type:SvcPortErrType):
        if self._current_param != param or self._current_phase == "STOP":
            return

        self._add_log(req_msg, resp_msg, param)

        param_err_type, need_retry = param.set_write_response_packet(resp_msg)

        if err_type != SvcPortErrType.NONE:
            self._add_log(req_msg, resp_msg, param, err_type.name, True)

        if param_err_type != ParamParseErrType.NONE:
            self._add_log(req_msg, resp_msg, param, param_err_type.name, True)

        if self._current_phase == "WRITE":
            self._processed_count += 1
            if self._total_target_count > 0:
                self.progress = int((self._processed_count / self._total_target_count) * 100)

        if param.is_need_reconnect:
            ServicePort().reconnect()
            
        self._current_index += 1
        self._request_write_next()     

    def _add_log(self, req_msg: str, resp_msg: str, param: Parameter, err_msg: str = "", is_monitor:bool = False, is_error: bool = False):
        if is_monitor:
            if self._monitor_log_count < 30:
                return

        now = datetime.now()
        time_str = now.strftime("%H:%M:%S.%f")[:-3]
        status = "ERROR" if is_error else "INFO"
        
        log_msg = (
            f"[{self.win_name}][{time_str}] [{status}] "
            f"Path: {param.path} | Name: {param.name} | Index: {param.index} | "
            f"Req: {req_msg} | Resp: {resp_msg} | ErrMsg: {err_msg}"
        )

        print(log_msg)
        
    def _show_warning_msgbox(self, title: str, message: str):
        self._close_active_msg_box()
        self._active_msg_box = QMessageBox(QMessageBox.Icon.Warning, title, message, QMessageBox.StandardButton.Ok, self.parent())
        self._active_msg_box.exec()
        self._active_msg_box = None

    def _show_question_msgbox(self, title: str, message: str) -> QMessageBox.StandardButton:
        self._close_active_msg_box()
        self._active_msg_box = QMessageBox(QMessageBox.Icon.Question, title, message, QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, self.parent())
        reply = self._active_msg_box.exec()
        self._active_msg_box = None
        return reply

    def _close_active_msg_box(self):
        if self._active_msg_box is not None:
            self._active_msg_box.reject()
            self._active_msg_box = None

    #def _destroyed(self):
    #    app = QCoreApplication.instance()
    #    if app is not None:
    #        try:
    #            app.aboutToQuit.disconnect(self._destroyed)
    #        except (TypeError, RuntimeError):
    #            pass
    #    if self._thread is not None and self._thread.isRunning():
    #        
    #        if self._param_thread:
    #            self._param_thread.blockSignals(True)
    #        
    #        self._thread.quit()  
    #        self._thread.wait()  
    #        
    #        self._thread = None       
    #        self._param_thread = None    

    def cleanup(self):
        # 이미 자원 해제가 진행되었거나 완료되었다면 무시 (충돌 방지 핵심)
        if self._is_cleaned:
            return
        self._is_cleaned = True

        # 1. aboutToQuit 시그널 연결 해제
        app = QCoreApplication.instance()
        if app is not None:
            try:
                app.aboutToQuit.disconnect(self.cleanup)
            except (TypeError, RuntimeError):
                pass

        self.monitor_timer.stop()

        # 2. 스레드 안전 종료
        if self._thread is not None and self._thread.isRunning():
            if self._param_thread:
                self._param_thread.blockSignals(True)
                # (옵션) ParameterThread 내부에 루프가 있다면 멈추는 플래그나 메서드를 여기서 호출
                # self._param_thread.stop() 
            
            self._thread.quit()  # 스레드의 이벤트 루프 종료 요청
            self._thread.wait()  # 스레드가 완전히 종료될 때까지 대기
            
            #self._thread = None       
            #self._param_thread = None            
    