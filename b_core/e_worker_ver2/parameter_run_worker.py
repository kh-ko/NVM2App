"""Parameter 읽기/쓰기/모니터링 워커 (기존 e_worker/parameter_worker.py 대응).

ver1 에서 달라진 점:
- UI(QMessageBox, RebootWaitDialog)를 완전히 제거 — 워커는 시그널/반환값만 낸다.
  경고/질문/재부팅 대기 표시는 윈도우 레이어 몫이다. (refresh/write 는
  StartResult 를 반환하고, 재부팅은 sig_reboot_started/finished 로 알린다)
- 재부팅 대기: ServicePort 는 닫아둔 채, 임시 raw serial 연결(probe)로 1초마다
  SN 읽기를 시도한다. 장비 응답이 확인된 뒤에야 ServicePort 를 다시 열므로
  connect_info_changed 는 "통신 가능한 연결"이 생겼을 때만 발화한다.
  -> 재부팅 완료 처리는 윈도우의 일반 재연결 refresh 경로가 겸한다
     (워커가 내부에서 refresh 를 호출하지 않는다).
- 재부팅 대기 중 refresh()/write() 는 BUSY 를 반환한다 (대기를 중단시키지
  않기 위한 안전망). 재부팅 대기 중단은 cancel_reboot() 로만 가능하다.
- 문자열 phase 상태 머신 제거 — 시퀀스 시작 시 작업 큐(list[_Job])를 만들어
  인덱스 하나로 순회한다. 진행률 = 처리 수 / 큐 길이.
- 요청-응답 상관관계를 param 객체 동일성 대신 시퀀스 번호(seq)로 검증한다.
  (refresh 재진입/중단 시 이전 시퀀스의 늦은 응답이 자동 폐기됨)
- monitor_param_list 제거 — 시퀀스가 끝나 유휴 상태가 되면 read_param_list 를
  round-robin 으로 계속 읽는다. (최초 refresh() 이전에는 동작하지 않음)
- 읽기 통신 오류 시 무한 재시도는 의도된 동작이다: 연결이 안 되면 GUI 를 구성할
  수 없으므로 계속 재시도하고, 윈도우는 is_working/progress 로 상황을 표시하며
  중단은 윈도우 닫기(cleanup)로 한다. 단 이것은 연결된 상태의 일시적 오류에만
  적용된다 — 연결 끊김 시에는 윈도우가 handle_disconnected() 를 호출해
  REBOOT 를 제외한 모든 동작을 중단시킨다. (재연결 refresh 가 전체를 다시 읽음)
- 쓰기 실패는 로그만 남기고 다음 작업으로 진행한다. (로그 뷰로 확인)
- acc mode 를 LOCAL 로 전환한 뒤 REMOTE 로 복원하지 않는 것은 의도된 동작이다.
- print -> AppLogManager. (log_source 에 담당 윈도우 이름을 넘길 것)
- NV1 프로토콜 처리(is_nv1_proto / NV1_GROUP)는 복잡도를 낮추기 위해 일단 제거
  — 추후 별도 처리 예정. (ver1 parameter_worker.py 참고)
- write() 는 param.write_str_value 를 내부에서 읽지 않는다. 호출측이
  [(param, value), ...] 쌍을 인자로 넘긴다 — write_str_value 는 누구나 접근
  가능한 공유 필드라, 팝업이 떠 있는 동안 다른 UI 가 같은 param 을 건드릴
  구조적 여지가 있다. 값은 호출 시점에 스냅샷으로 확정한다.
"""

from enum import Enum, auto
from typing import NamedTuple, Optional

import serial
from PySide6.QtCore import QCoreApplication, QObject, QThread, QTimer, Signal, Slot

from b_core.b_datatype import param_enum as p_enum
from b_core.b_datatype.general_enum import (ParamAccType, ParamParseErrType,
                                            SvcPortErrType)
from b_core.b_datatype.parameter import Parameter
from b_core.c_manager.app_log_manager import AppLogManager
from b_core.c_manager.parameter_manager import ParamManager
from b_core.d_dal.service_port import ServicePort


class StartResult(Enum):
    """refresh()/write() 시작 결과. OK 외의 사유 표시는 윈도우 몫."""
    OK = auto()
    NOT_CONNECTED = auto()
    EMPTY = auto()              # 처리할 param 없음
    BUSY = auto()               # write: 시퀀스/재부팅 진행 중, refresh: 재부팅 대기 중
    LOCAL_BLOCKED = auto()      # Remote Lock 상태에서 local 전용 param 쓰기 시도
    NEED_LOCAL_SWITCH = auto()  # Remote 상태 — Local 전환 여부를 사용자에게 물어볼 것


class _JobOp(Enum):
    READ = auto()
    WRITE = auto()


class _Job(NamedTuple):
    op: _JobOp
    param: Parameter
    packet: str


class _WorkerState(Enum):
    IDLE = auto()          # 최초 refresh() 이전 / 중단됨
    SEQUENCE = auto()      # 작업 큐 처리 중 (refresh/write)
    MONITOR = auto()       # 유휴 — read_param_list round-robin 읽기
    REBOOT = auto()        # 밸브 재부팅 대기 (임시 raw serial 연결로 SN probe 폴링)
    DISCONNECTED = auto()  # 연결 끊김으로 전 동작 중단 — 재연결 refresh 대기


class ParameterThread(QObject):
    """요청 1건을 처리하고 결과를 되돌려주는 워커 스레드 슬롯 모음."""

    sig_result = Signal(int, str, str, object, SvcPortErrType)         # seq, packet, response, param, err
    sig_single_read_result = Signal(str, str, object, SvcPortErrType)  # packet, response, param, err
    sig_raw_write_result = Signal(str, str, str, SvcPortErrType)       # tag, packet, response, err
    sig_reboot_probe_result = Signal(int, bool, str)                   # seq, success, detail

    ERROR_DELAY_MS = 100  # 통신 오류 시 인위적 지연 (즉시 실패 경로의 부하 방지)

    @Slot(int, str, object)
    def process_request(self, seq: int, packet: str, param):
        response, err_type = ServicePort().request_string(packet)
        if err_type != SvcPortErrType.NONE:
            QThread.msleep(self.ERROR_DELAY_MS)

        self.sig_result.emit(seq, packet, response, param, err_type)

    @Slot(str, object)
    def process_single_read(self, packet: str, param):
        response, err_type = ServicePort().request_string(packet, None)
        if err_type != SvcPortErrType.NONE:
            QThread.msleep(self.ERROR_DELAY_MS)

        self.sig_single_read_result.emit(packet, response, param, err_type)

    @Slot(str, str)
    def process_raw_write(self, tag: str, packet: str):
        response, err_type = ServicePort().request_string(packet, None)
        if err_type != SvcPortErrType.NONE:
            QThread.msleep(self.ERROR_DELAY_MS)

        self.sig_raw_write_result.emit(tag, packet, response, err_type)

    @Slot(int, str, object)
    def process_reboot_probe(self, seq: int, packet: str, setting: tuple):
        """재부팅 확인 probe — ServicePort 는 닫힌 채, 임시 raw serial 연결로
        요청을 보내 장비 응답 여부만 확인한다. (ComportScanRunWorker 와 같은 패턴)"""
        port_name, baudrate, data_bits, parity, stop_bits, termination = setting

        parity_map = {0: serial.PARITY_NONE, 2: serial.PARITY_EVEN, 3: serial.PARITY_ODD,
                      4: serial.PARITY_SPACE, 5: serial.PARITY_MARK}
        stop_map = {1: serial.STOPBITS_ONE, 2: serial.STOPBITS_TWO, 3: serial.STOPBITS_ONE_POINT_FIVE}
        term_map_bytes = {0: b"\r\n", 1: b"\n", 2: b"\r"}
        term = term_map_bytes.get(termination, b"\r\n")

        try:
            with serial.Serial(port=port_name, baudrate=baudrate, bytesize=data_bits,
                               parity=parity_map.get(parity, serial.PARITY_NONE),
                               stopbits=stop_map.get(stop_bits, serial.STOPBITS_ONE),
                               timeout=0.5, write_timeout=0.5) as ser:
                ser.reset_input_buffer()
                ser.write(packet.encode('utf-8') + term)
                ser.flush()
                response = ser.read_until(term)

            if response.startswith(b"p:"):
                detail = response.decode('utf-8', errors='ignore').strip()
                self.sig_reboot_probe_result.emit(seq, True, detail)
            else:
                detail = response.decode('utf-8', errors='ignore').strip() or "no response"
                self.sig_reboot_probe_result.emit(seq, False, detail)

        except serial.SerialException as e:
            self.sig_reboot_probe_result.emit(seq, False, str(e))
        except Exception as e:
            self.sig_reboot_probe_result.emit(seq, False, str(e))


class ParameterRunWorker(QObject):
    # 내부 요청 (워커 스레드로)
    sig_request = Signal(int, str, object)
    sig_single_read_request = Signal(str, object)
    sig_raw_write_request = Signal(str, str)
    sig_reboot_probe_request = Signal(int, str, object)

    # 외부 공개
    sig_single_read_result = Signal(str, str, object, SvcPortErrType)  # packet, response, param, err
    sig_raw_write_result = Signal(str, str, str, SvcPortErrType)       # tag, packet, response, err
    sig_reboot_started = Signal()
    sig_reboot_finished = Signal(bool)  # True=재부팅 후 통신 복구, False=취소됨
    sig_progress_changed = Signal(int)
    sig_is_working_changed = Signal(bool)
    sig_finish_refresh = Signal()

    MONITOR_LOG_ROUNDS = 30   # 모니터링 정상 로그는 30 라운드당 1 라운드만 기록
    REBOOT_TICK_MS = 1000

    @property
    def progress(self) -> int:
        return self._progress

    @progress.setter
    def progress(self, progress: int):
        if self._progress != progress:
            self._progress = progress
            self.sig_progress_changed.emit(progress)

    @property
    def is_working(self) -> bool:
        return self._is_working

    @is_working.setter
    def is_working(self, is_working: bool):
        if self._is_working != is_working:
            self._is_working = is_working
            self.sig_is_working_changed.emit(is_working)

    def __init__(self, parent=None, log_source: str = "ParameterRunWorker", monitor_tick: int = 100):
        super().__init__(parent)

        self._log = AppLogManager().get_logger(log_source)

        self._acc_mode_param: Optional[Parameter] = ParamManager().get_by_full_path("System.Access Mode")

        # 상태 (문자열 phase 대신 enum + 작업 큐 + 시퀀스 번호)
        self._state = _WorkerState.IDLE
        self._seq = 0
        self._jobs: list[_Job] = []
        self._job_index = 0
        self._seq_is_refresh = False  # 현재 시퀀스가 refresh 인지 (완료 시그널 구분용)
        self._is_working = False
        self._progress = 0
        self._is_cleaned = False

        # 등록 param 목록
        # write_param_list: 실제 쓰기값은 write() 호출 시 인자로 받는다 —
        # 이 목록은 refresh() 가 [쓰기 가능한 RW param 을 읽어 초기값을 채우는] 데만 쓰인다.
        self.init_param_list: list[Parameter] = []
        self.read_param_list: list[Parameter] = []
        self.write_param_list: list[Parameter] = []

        # 모니터링 (유휴 시 read_param_list round-robin)
        self.monitor_time_tick = monitor_tick
        self._monitor_index = 0
        self._monitor_round = 0
        self.monitor_timer = QTimer(self)
        self.monitor_timer.setSingleShot(True)
        self.monitor_timer.timeout.connect(self._on_timeout_monitor)

        # 재부팅 대기
        self._reboot_probe_packet: str = ""
        self._reboot_port_setting: tuple = ()
        self.reboot_timer = QTimer(self)
        self.reboot_timer.setSingleShot(True)
        self.reboot_timer.timeout.connect(self._on_timeout_reboot)

        # 워커 스레드 구성
        self._thread = QThread()
        self._param_thread = ParameterThread()
        self._param_thread.moveToThread(self._thread)

        self.sig_request.connect(self._param_thread.process_request)
        self.sig_single_read_request.connect(self._param_thread.process_single_read)
        self.sig_raw_write_request.connect(self._param_thread.process_raw_write)
        self.sig_reboot_probe_request.connect(self._param_thread.process_reboot_probe)

        self._param_thread.sig_result.connect(self._handle_result)
        self._param_thread.sig_single_read_result.connect(self.sig_single_read_result)
        self._param_thread.sig_raw_write_result.connect(self.sig_raw_write_result)
        self._param_thread.sig_reboot_probe_result.connect(self._handle_reboot_probe_result)

        self._thread.finished.connect(self._param_thread.deleteLater)
        self._thread.finished.connect(self._thread.deleteLater)

        app = QCoreApplication.instance()
        if app is not None:
            app.aboutToQuit.connect(self.cleanup)
        self.destroyed.connect(self.cleanup)

        self._thread.start()

    # ------------------------------------------------------------ param 등록
    def add_init_param(self, param_full_path: str) -> Optional[Parameter]:
        param = ParamManager().get_by_full_path(param_full_path)
        if param is not None:
            self.init_param_list.append(param)
        else:
            self._log.error(f"init param not found: {param_full_path}")
        return param

    def add_init_param_ptr(self, param: Parameter):
        if param is not None:
            self.init_param_list.append(param)

    def add_read_param(self, param_full_path: str) -> Optional[Parameter]:
        param = ParamManager().get_by_full_path(param_full_path)
        if param is not None:
            self.read_param_list.append(param)
        else:
            self._log.error(f"read param not found: {param_full_path}")
        return param

    def add_read_param_ptr(self, param: Parameter):
        if param is not None:
            self.read_param_list.append(param)

    def add_write_param(self, param_full_path: str) -> Optional[Parameter]:
        """refresh() 시 초기값을 읽어올 쓰기 가능 param 등록. 실제 쓰기값은 write() 인자로 전달한다."""
        param = ParamManager().get_by_full_path(param_full_path)
        if param is not None:
            self.write_param_list.append(param)
        else:
            self._log.error(f"write param not found: {param_full_path}")
        return param

    def add_write_param_ptr(self, param: Parameter):
        if param is not None:
            self.write_param_list.append(param)

    def clear_read_param(self, start_index: Optional[int] = None):
        if start_index is None:
            self.read_param_list.clear()
        else:
            del self.read_param_list[start_index:]
        self._monitor_index = 0

    def clear_write_param(self, start_index: Optional[int] = None):
        if start_index is None:
            self.write_param_list.clear()
        else:
            del self.write_param_list[start_index:]

    # ------------------------------------------------------------ 시퀀스 시작
    def refresh(self) -> StartResult:
        """등록 param 전체 읽기 시퀀스 시작. 완료 후 모니터링으로 전환된다.

        진행 중이던 시퀀스/모니터링은 무조건 중단하고 다시 시작한다.
        단, 재부팅 대기 중에는 BUSY 를 반환한다 — 외부의 refresh 호출이
        재부팅 대기를 중단시키지 않기 위한 안전망.
        (재부팅 대기 중단은 cancel_reboot() 로만 가능)"""
        if self._state == _WorkerState.REBOOT:
            return StartResult.BUSY

        self._stop_all()

        jobs: list[_Job] = []
        for param in self.init_param_list:
            jobs.append(self._build_read_job(param))
        for param in self.write_param_list:
            if param.acc != ParamAccType.WO:
                jobs.append(self._build_read_job(param))
        for param in self.read_param_list:
            jobs.append(self._build_read_job(param))

        if not jobs:
            return StartResult.EMPTY

        if not ServicePort().connect_info:
            return StartResult.NOT_CONNECTED

        self._start_sequence(jobs, is_refresh=True)
        return StartResult.OK

    def write(self, pairs: list[tuple[Parameter, str]], switch_to_local: bool = False) -> StartResult:
        """전달받은 [(param, value), ...] 쌍들의 쓰기 시퀀스 시작.

        값은 호출측이 스냅샷으로 넘긴다 — 워커는 param.write_str_value 같은
        공유 필드를 직접 참조하지 않는다 (모듈 docstring 참고).

        NEED_LOCAL_SWITCH 반환 시 윈도우가 사용자에게 물어본 뒤 동일 pairs 로
        write(pairs, switch_to_local=True) 를 다시 호출한다.
        쓰기 후에는 [쓴 param 읽기(RW만) -> read_param_list 읽기] 가 이어진다."""
        if self._state in (_WorkerState.SEQUENCE, _WorkerState.REBOOT):
            return StartResult.BUSY

        if not ServicePort().connect_info:
            return StartResult.NOT_CONNECTED

        pending = [(param, value) for param, value in pairs if value]
        if not pending:
            return StartResult.EMPTY

        # local 전용 param 쓰기 가능 여부 (값 소비 전에 판정)
        is_only_local_acc = any(param.is_only_local_acc for param, _ in pending)
        acc_mode_value = -1
        if self._acc_mode_param is not None and str(self._acc_mode_param.value).isdigit():
            acc_mode_value = int(self._acc_mode_param.value)

        if is_only_local_acc and acc_mode_value == p_enum.AccModeEnum.REMOTE_LOCKED.value:
            return StartResult.LOCAL_BLOCKED

        if is_only_local_acc and acc_mode_value == p_enum.AccModeEnum.REMOTE.value and not switch_to_local:
            return StartResult.NEED_LOCAL_SWITCH

        jobs: list[_Job] = []

        # Local 전환 쓰기를 맨 앞에 (전환 후 REMOTE 복원하지 않는 것은 의도된 동작)
        if is_only_local_acc and acc_mode_value == p_enum.AccModeEnum.REMOTE.value and switch_to_local:
            acc = self._acc_mode_param
            packet = f"p:01{acc.id}{acc.index:02X}{p_enum.AccModeEnum.LOCAL.value}"
            jobs.append(_Job(_JobOp.WRITE, acc, packet))

        for param, value in pending:
            packet = f"p:01{param.id}{param.index:02X}{value}"
            jobs.append(_Job(_JobOp.WRITE, param, packet))

        for param, _ in pending:
            if param.acc != ParamAccType.WO:
                jobs.append(self._build_read_job(param))
        for param in self.read_param_list:
            jobs.append(self._build_read_job(param))

        self._stop_all()
        self._start_sequence(jobs, is_refresh=False)
        return StartResult.OK

    def handle_disconnected(self) -> None:
        """연결 끊김 처리 — 윈도우가 connect_info_changed("") 수신 시 호출한다.

        REBOOT 를 제외한 모든 동작(SEQUENCE/MONITOR)을 중단하고
        DISCONNECTED 상태로 전환한다. 재개는 재연결 시 윈도우의 refresh() 로.
        - SEQUENCE 중단 근거: 포트가 닫힌 동안 재시도는 성공할 수 없고,
          재연결 시 refresh() 가 어차피 전체를 다시 읽는다. (무한 재시도 유지는
          연결된 상태의 일시적 통신 오류에만 적용)
        - REBOOT 예외 근거: 재부팅 대기는 워커 스스로 포트를 닫으며 시작되므로
          그때 발화되는 끊김 시그널이 대기를 죽이면 안 된다."""
        if self._state == _WorkerState.REBOOT:
            return

        if self._state == _WorkerState.SEQUENCE:
            self._log.info(f"disconnected — sequence aborted ({self._job_index}/{len(self._jobs)} jobs done)")

        self._stop_all()
        self._state = _WorkerState.DISCONNECTED

    # ------------------------------------------------------------ 단발 요청
    def single_read_request(self, param: Parameter):
        packet = f"p:0B{param.id}{param.index:02X}"
        self.sig_single_read_request.emit(packet, param)

    def raw_write_request(self, tag: str, packet: str):
        """완성된 패킷을 그대로 전송. 결과는 sig_raw_write_result(tag, ...) 로."""
        self.sig_raw_write_request.emit(tag, packet)

    # ------------------------------------------------------------ 재부팅
    def cancel_reboot(self):
        """재부팅 대기 취소. 포트는 닫힌 상태로 둔다 (단선과 동일 취급).

        호출측(윈도우)은 취소 후 해당 윈도우를 닫아 동작을 마무리한다."""
        if self._state != _WorkerState.REBOOT:
            return

        self._stop_all()
        self.sig_reboot_finished.emit(False)

    def _start_reboot(self):
        sn = ParamManager().get_by_full_path("System.Identification.Serial Number")
        if sn is None:
            self._log.error("reboot: Serial Number param not found — abort")
            self._stop_all()
            self.sig_reboot_finished.emit(False)
            return

        self._reboot_probe_packet = f"p:0B{sn.id}{sn.index:02X}"

        # 포트 설정을 백업한 뒤 닫는다. 재부팅 대기 동안 ServicePort 는 닫힌 채
        # 유지되고, 확인은 임시 raw serial 연결(probe)로만 수행한다.
        svc = ServicePort()
        self._reboot_port_setting = (svc.port_name, svc.baudrate, svc.data_bits,
                                     svc.parity, svc.stop_bits, svc.termination)
        svc.close()

        self._state = _WorkerState.REBOOT
        self.sig_reboot_started.emit()
        self.reboot_timer.start(self.REBOOT_TICK_MS)

    def _on_timeout_reboot(self):
        if self._state != _WorkerState.REBOOT:
            return

        self.sig_reboot_probe_request.emit(self._seq, self._reboot_probe_packet,
                                           self._reboot_port_setting)

    def _handle_reboot_probe_result(self, seq: int, success: bool, detail: str):
        if seq != self._seq or self._state != _WorkerState.REBOOT:
            return

        # 1초 주기 폴링이라 스팸 우려가 없으므로 항상 기록
        if success:
            self._log.info(f"reboot probe ok: {detail}")
        else:
            self._log.info(f"reboot probe waiting: {detail}")

        if not success:
            self.reboot_timer.start(self.REBOOT_TICK_MS)
            return

        # 장비 응답 확인 — REBOOT 해제 후 정식 연결.
        # ServicePort.open() 의 connect_info_changed 시그널이 윈도우의 일반
        # 재연결 경로(refresh)를 태우므로, 여기서 refresh 를 직접 호출하지 않는다.
        setting = self._reboot_port_setting
        self._stop_all()
        self.sig_reboot_finished.emit(True)  # 윈도우가 대기 다이얼로그를 닫는다
        ServicePort().open(*setting)

    # ------------------------------------------------------------ 작업 큐 처리
    def _build_read_job(self, param: Parameter) -> _Job:
        packet = f"p:0B{param.id}{param.index:02X}"
        return _Job(_JobOp.READ, param, packet)

    def _start_sequence(self, jobs: list[_Job], is_refresh: bool):
        self._seq += 1
        self._jobs = jobs
        self._job_index = 0
        self._seq_is_refresh = is_refresh
        self._state = _WorkerState.SEQUENCE
        self.is_working = True
        self.progress = 0
        self._send_current_job()

    def _send_current_job(self):
        job = self._jobs[self._job_index]
        self.sig_request.emit(self._seq, job.packet, job.param)

    @Slot(int, str, str, object, SvcPortErrType)
    def _handle_result(self, seq: int, packet: str, response: str,
                       param: Parameter, err_type: SvcPortErrType):
        # 이전 시퀀스의 늦은 응답은 폐기
        if seq != self._seq:
            return

        if self._state == _WorkerState.SEQUENCE:
            self._handle_sequence_result(packet, response, param, err_type)
        elif self._state == _WorkerState.MONITOR:
            self._handle_monitor_result(packet, response, param, err_type)
        # REBOOT 상태는 ServicePort 요청을 보내지 않으므로 (probe 전용) 여기로 오지 않는다

    def _handle_sequence_result(self, packet, response, param, err_type):
        job = self._jobs[self._job_index]

        if job.op is _JobOp.READ:
            param_err_type, need_retry = param.set_read_response_packet(response)

            if err_type != SvcPortErrType.NONE:
                # 읽기 통신 오류 — 같은 작업 무한 재시도 (의도된 동작, 모듈 주석 참고)
                self._log_transaction(packet, response, param, err_type.name, is_error=True)
                self._send_current_job()
                return

            if param_err_type != ParamParseErrType.NONE:
                self._log_transaction(packet, response, param, param_err_type.name, is_error=True)
                if need_retry:
                    self._send_current_job()
                    return
            else:
                self._log_transaction(packet, response, param)

                # refresh 읽기 성공 = 장비 값으로 동기화 확정 → 값이 안 변해도 통지하여
                # UI 의 dirty 를 클리어하게 한다. write 후 read-back 은 제외 —
                # 값이 그대로면 쓰기가 반영되지 않은 것이므로 dirty 가 유지되어야 한다.
                if self._seq_is_refresh:
                    param.notify_synced()

        else:  # WRITE — 실패해도 로그만 남기고 계속 진행
            param_err_type, _ = param.set_write_response_packet(response)

            if err_type != SvcPortErrType.NONE:
                self._log_transaction(packet, response, param, err_type.name, is_error=True)
            elif param_err_type != ParamParseErrType.NONE:
                self._log_transaction(packet, response, param, param_err_type.name, is_error=True)
            else:
                self._log_transaction(packet, response, param)

            if param.is_need_reconnect:
                self._start_reboot()
                return

        # 다음 작업으로
        self._job_index += 1
        self.progress = int((self._job_index / len(self._jobs)) * 100)

        if self._job_index < len(self._jobs):
            self._send_current_job()
        else:
            self._finish_sequence()

    def _finish_sequence(self):
        was_refresh = self._seq_is_refresh

        self.is_working = False
        self.progress = 0
        self._jobs = []
        self._job_index = 0

        # 유휴 -> read_param_list 모니터링 시작
        if self.read_param_list:
            self._state = _WorkerState.MONITOR
            self._monitor_index = 0
            self._monitor_round = 0
            self.monitor_timer.start(self.monitor_time_tick)
        else:
            self._state = _WorkerState.IDLE

        # refresh 시퀀스 완료만 알린다 (write 완료에는 발화하지 않음) —
        # 윈도우가 이 시그널을 받아 CompoundRunWorker.start_polling() 등을 수행
        if was_refresh:
            self.sig_finish_refresh.emit()

    # ------------------------------------------------------------ 모니터링
    def _on_timeout_monitor(self):
        if self._state != _WorkerState.MONITOR:
            return

        # 리스트가 비어 있어도 타이머는 계속 돌린다 —
        # clear 후 add_read_param 으로 다시 채워지면 자동으로 재개되도록
        if not self.read_param_list:
            self.monitor_timer.start(self.monitor_time_tick)
            return

        if self._monitor_index >= len(self.read_param_list):
            self._monitor_index = 0
            # 정상 로그 샘플링용 라운드 카운트 (MONITOR_LOG_ROUNDS 라운드당 1 라운드 기록)
            self._monitor_round += 1
            if self._monitor_round > self.MONITOR_LOG_ROUNDS:
                self._monitor_round = 0

        job = self._build_read_job(self.read_param_list[self._monitor_index])
        self.sig_request.emit(self._seq, job.packet, job.param)

    def _handle_monitor_result(self, packet, response, param, err_type):
        param_err_type, need_retry = param.set_read_response_packet(response)

        if err_type != SvcPortErrType.NONE:
            self._log_transaction(packet, response, param, err_type.name, is_error=True, is_monitor=True)
            self.monitor_timer.start(self.monitor_time_tick)  # 같은 param 재시도
            return

        if param_err_type != ParamParseErrType.NONE:
            self._log_transaction(packet, response, param, param_err_type.name, is_error=True, is_monitor=True)
            if need_retry:
                self.monitor_timer.start(self.monitor_time_tick)
                return
        else:
            self._log_transaction(packet, response, param, is_monitor=True)

        self._monitor_index += 1
        self.monitor_timer.start(self.monitor_time_tick)

    # ------------------------------------------------------------ 내부 공통
    def _stop_all(self):
        """진행 중인 모든 동작 중단. seq 를 올려 늦은 응답을 무효화한다."""
        self._seq += 1
        self.monitor_timer.stop()
        self.reboot_timer.stop()
        self._jobs = []
        self._job_index = 0
        self._state = _WorkerState.IDLE
        self.is_working = False
        self.progress = 0

    def _log_transaction(self, req: str, resp: str, param: Parameter,
                         err_msg: str = "", is_error: bool = False, is_monitor: bool = False):
        # 모니터링 로그는 오류 포함 샘플링 라운드에서만 기록
        # (미연결 상태의 100ms 무한 재시도가 로그를 홍수시키는 것을 방지 — ver1 동일)
        if is_monitor and self._monitor_round != self.MONITOR_LOG_ROUNDS:
            return

        msg = (f"Path: {param.path} | Name: {param.name} | Index: {param.index} | "
               f"Req: {req} | Resp: {resp}")
        if is_error:
            self._log.error(f"{msg} | ErrMsg: {err_msg}")
        else:
            self._log.info(msg)

    # ------------------------------------------------------------ 종료
    def cleanup(self):
        if self._is_cleaned:
            return
        self._is_cleaned = True

        app = QCoreApplication.instance()
        if app is not None:
            try:
                app.aboutToQuit.disconnect(self.cleanup)
            except (TypeError, RuntimeError):
                pass

        self._stop_all()

        if self._thread is not None and self._thread.isRunning():
            if self._param_thread:
                self._param_thread.blockSignals(True)
            self._thread.quit()
            self._thread.wait()
