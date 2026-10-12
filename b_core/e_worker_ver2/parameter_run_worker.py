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
- 재부팅 대기 중 refresh()/write()/capture()/raw_write() 는 BUSY 를 반환한다 (대기를 중단시키지
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
- write() 는 param.write_str_value 를 내부에서 읽지 않는다. 호출측이
  [(param, value), ...] 쌍을 인자로 넘긴다 — write_str_value 는 누구나 접근
  가능한 공유 필드라, 팝업이 떠 있는 동안 다른 UI 가 같은 param 을 건드릴
  구조적 여지가 있다. 값은 호출 시점에 스냅샷으로 확정한다.

2026-09-10 PacketSpec 도입 (1단계, 동작 변화 없음):
- 작업 단위가 param 에서 패킷(spec)으로 바뀌었다: _Job(op, spec, values).
  요청 문자열은 spec.build_request(), 응답 반영은 spec.apply_response() —
  워커는 NV2/NV1 을 구분하지 않고 "p:" 를 모른다.
- 읽기 목록은 spec 기준으로 중복을 제거한다. NV2 는 param 마다 spec 이 달라
  지금과 1:1 이고, 여러 param 이 한 패킷을 공유하는 NV1(2단계)에서 요청이 줄어든다.
- spec 은 작업 큐를 만드는 시점에 SpecRegistry 에서 param 으로 찾는다
  (조건부 프로토콜 선택은 NV1 단계). 찾은 spec 은 _Job 에 담기므로 응답 처리와
  모니터링 라운드에서는 다시 조회하지 않는다. 등록부에 없으면 그 param 은
  요청 없이 Not Support 로 두고 건너뛴다.
- 쓰기는 pending 을 write spec 기준으로 묶어 spec 당 요청 1건을 만든다.

2026-09-11 도메인 중립화 (3단계):
- write() 의 값은 도메인 값(백분율, Torr 등 — 숫자 또는 그 문자열)이고 선로 문자열은
  spec 의 codec 이 만든다. 요청을 만들 수 없으면(BuildFailure) 그 작업은 건너뛴다 —
  건너뛴 param 은 시퀀스 종료 시 sig_write_skipped 로 한 번에 알린다 (창이 대화상자로 표시,
  2026-09-14 사용자 결정: 기능 처리는 그대로 두고 GUI 안내만 보강).
- 문맥이 바뀌어도 값은 재디코드하지 않는다 (결정 E).

2026-09-14 기준 워커 조정 (문맥 선행 읽기 대체, 사용자 결정):
- codec 문맥 param(Interface.Scaling.*, Sensor 1/2.*)은 MainWin 워커(is_primary)가 init
  목록으로 읽는다. 기준 워커의 refresh 가 진행 중이면 다른 워커의 refresh() 는 예약만 하고
  (StartResult.PENDING) 기준 시퀀스가 끝난 뒤 이어서 시작한다 — 연결/재연결 직후 자식 창이
  문맥 없이(또는 이전 장비 문맥으로) decode 하는 경합을 막는다. 요청 목록 자체는 구 워커와
  같다 (문맥 param 을 큐에 끼워 넣지 않는다).
- 대기(PENDING)는 창 입장에서 refresh 진행 중과 같아야 한다: 진행 중이던 시퀀스/모니터링을
  중단하고(구 refresh 와 동일) is_working 을 올려 창 본문을 잠그며, write() 는 BUSY 를 돌려준다.
  잠금은 지연 refresh 가 _finish_sequence 에 닿을 때(또는 끊김/cleanup) 풀린다 — 재연결 직후
  이전 값이 편집 가능한 채 남거나, 그 사이 시작된 쓰기가 지연 refresh 에 잘리는 일을 막는다.

2026-10-12 결과 계약 (6위 본안):
- spec.apply_response() 는 Outcome(verdict, reason) — 판정(spec 의 _judge)과 적용(플래그·값, PacketSpec 기본 클래스)이
  분리됐다. 워커는 need_retry(= 부류 TRANSIENT) 만으로 재시도를 정하고 reason 은 로그에만 쓴다.
- spec.build_request() 는 만들 수 없으면 BuildFailure(값 없음/문맥 미준비/형식 불량/폭 초과) — 그 작업은 건너뛰고 사유를
  로그에 남긴다. 창에는 종전처럼 sig_write_skipped 로 한 번에 알린다 (사유는 LogView 에만, 2026-10-12 사용자 결정).

2026-10-12 백업·복원을 시퀀스로 (data-protocol-2, F085/F086/F087):
- capture(params, max_retry) 는 읽기 spec 으로 CAPTURE 시퀀스를, raw_write([(tag, 패킷)], max_retry) 는 완성된 패킷
  (raw_packet_spec) 으로 RAW 시퀀스를 돈다. 둘 다 보통 시퀀스처럼 is_working 으로 창을 잠그고 모니터링을 멈추며, 끝나면
  sig_sequence_report(SequenceReport) 로 작업별 Outcome 과 끝난 이유(완료 / abort_sequence() / 끊김)를 한 번 보고한다.
- _Job.max_retry: TRANSIENT 재시도 상한. refresh·쓰기 read-back 은 None(무제한, F028), CAPTURE/RAW 는 호출측 값.
  통신 오류는 빈 응답으로 spec 에 들어가 TRANSIENT 이므로 같은 상한에 든다. 상한을 넘기면 실패로 기록하고 다음 작업으로.
- 상태 머신 밖에서 돌던 단건 읽기(single_read_request)·raw 쓰기(raw_write_request)와 그 시그널은 없앴다 — 창이 응답을
  판정하지 않고, 재시도·누락·중단이 워커 한 곳에서 정해진다.
"""

from enum import Enum, auto
from typing import NamedTuple, Optional

from PySide6.QtCore import QCoreApplication, QObject, QThread, QTimer, Signal, Slot

from b_core.b_datatype import param_enum as p_enum
from b_core.b_datatype.general_enum import (ParamAccType, ParamParseErrType,
                                            SvcPortErrType)
from b_core.b_datatype.parameter import Parameter
from b_core.c_manager.app_log_manager import AppLogManager
from b_core.c_manager.parameter_manager import ParamManager
from b_core.d_dal.serial_setting import SerialSetting, probe_once
from b_core.d_dal.service_port import ServicePort
from b_core.g_protocol.packet_spec import BuildFailure, Outcome, PacketSpec, Verdict
from b_core.g_protocol.raw_packet_spec import raw_write_spec_of
from b_core.g_protocol.spec_registry import SpecRegistry


class StartResult(Enum):
    """refresh()/write()/capture()/raw_write() 시작 결과. OK 외의 사유 표시는 윈도우 몫."""
    OK = auto()
    NOT_CONNECTED = auto()
    EMPTY = auto()              # 처리할 param 없음
    BUSY = auto()               # write·capture·raw_write: 시퀀스/재부팅/기준 refresh 대기 중, refresh: 재부팅 대기 중
    LOCAL_BLOCKED = auto()      # Remote Lock 상태에서 local 전용 param 쓰기 시도
    NEED_LOCAL_SWITCH = auto()  # Remote 상태 — Local 전환 여부를 사용자에게 물어볼 것
    PENDING = auto()            # refresh: 기준(MainWin) refresh 완료 후 자동 시작 예약됨
                                #          (대기 중에도 is_working=True 로 창이 잠기고 write 는 BUSY)


class _JobOp(Enum):
    READ = auto()
    WRITE = auto()
    RAW = auto()       # 완성된 패킷 1건 (RawPacketSpec) — 복원


class _Job(NamedTuple):
    op: _JobOp
    spec: PacketSpec
    values: dict | None = None    # WRITE: {param: 도메인 값 (숫자 또는 문자열)}
    max_retry: int | None = None  # TRANSIENT 재시도 상한. None = 무제한 (refresh·쓰기 read-back — F028 결정)
    tag: str | None = None        # RAW: 창이 항목을 식별하는 꼬리표 — 보고에 그대로 실린다


class SequenceKind(Enum):
    REFRESH = auto()   # refresh(): 등록 param 전체 읽기 → 완료 시 sig_finish_refresh
    WRITE = auto()     # write(): 쓰기 + read-back
    CAPTURE = auto()   # capture(): 백업 — 읽기 spec 으로 읽고 보고
    RAW = auto()       # raw_write(): 복원 — 완성된 패킷을 보내고 보고


class SequenceEnd(Enum):
    COMPLETED = auto()     # 작업을 전부 돌았다 (실패한 작업이 있어도 완료)
    ABORTED = auto()       # abort_sequence() — 사용자 취소
    DISCONNECTED = auto()  # 연결 끊김 — handle_disconnected()


class JobResult(NamedTuple):
    tag: str | None        # RAW 작업의 꼬리표 (CAPTURE 는 None)
    params: tuple          # 그 작업이 실은 param (CAPTURE: 읽기 spec 의 params, RAW: ())
    outcome: Outcome       # 마지막 시도의 결과 — verdict 가 OK 가 아니면 실패 (재시도 소진 / 거부 / 미지원)
    lines: dict            # CAPTURE 성공: {param: 읽은 선로 원문} — 읽은 그 자리에서 떠 둔 사본 (공유 str_value 는 다른 읽기가 바꿀 수 있다)


class SequenceReport(NamedTuple):
    kind: SequenceKind
    results: list          # JobResult, 끝난 작업 순서대로 — 중단되면 그때까지
    total: int             # 시퀀스의 작업 수 (중단 시 "k/n" 표시용)
    end: SequenceEnd


class _WorkerState(Enum):
    IDLE = auto()          # 최초 refresh() 이전 / 중단됨
    SEQUENCE = auto()      # 작업 큐 처리 중 (refresh/write/capture/raw_write — 종류는 _seq_kind: SequenceKind)
    MONITOR = auto()       # 유휴 — read_param_list round-robin 읽기
    REBOOT = auto()        # 밸브 재부팅 대기 (임시 raw serial 연결로 SN probe 폴링)
    DISCONNECTED = auto()  # 연결 끊김으로 전 동작 중단 — 재연결 refresh 대기
    PENDING = auto()       # 기준(MainWin) refresh 완료 대기 — 창 잠금(is_working) 유지, write 는 BUSY


class ParameterThread(QObject):
    """요청 1건을 처리하고 결과를 되돌려주는 워커 스레드 슬롯 모음.

    transport: request_string(packet) -> (response, SvcPortErrType) 을 가진 객체. 앱에서는 ServicePort 싱글턴이고,
    테스트 하네스는 {요청: 응답} 스크립트 객체를 꽂아 장비 없이 상태 전이를 확인한다 (F110).
    시퀀스 요청은 모두 이 한 지점을 지난다 (백업·복원도 시퀀스). 재부팅 probe 는 임시 raw 포트라 별도."""

    sig_result = Signal(int, str, str, object, SvcPortErrType)         # seq, packet, response, spec, err
    sig_reboot_probe_result = Signal(int, bool, str)                   # seq, success, detail

    ERROR_DELAY_MS = 100  # 통신 오류 시 인위적 지연 (즉시 실패 경로의 부하 방지)

    def __init__(self, transport=None, parent=None):
        super().__init__(parent)
        self._transport = transport if transport is not None else ServicePort()

    @Slot(int, str, object)
    def process_request(self, seq: int, packet: str, spec):
        response, err_type = self._transport.request_string(packet)
        if err_type != SvcPortErrType.NONE:
            QThread.msleep(self.ERROR_DELAY_MS)

        self.sig_result.emit(seq, packet, response, spec, err_type)

    @Slot(int, str, object, str)
    def process_reboot_probe(self, seq: int, packet: str, setting: SerialSetting, expected_prefix: str):
        """재부팅 확인 probe — ServicePort 는 닫힌 채, 임시 raw 포트 1왕복(probe_once)으로 장비 응답
        여부만 확인한다 (ComportScan 과 같은 경로). 판정은 spec 이 준 정상 응답 접두로 한다 (F026)."""
        try:
            response = probe_once(setting, packet, timeout=0.5)
        except Exception as e:  # 포트 열기 실패(아직 재부팅 중), 쓰기 타임아웃 등
            self.sig_reboot_probe_result.emit(seq, False, f"{type(e).__name__}: {e}")
            return

        detail = response.decode("utf-8", errors="ignore").strip()
        if response.startswith(expected_prefix.encode("utf-8")):
            self.sig_reboot_probe_result.emit(seq, True, detail)
        else:
            self.sig_reboot_probe_result.emit(seq, False, detail or "no response")


class ParameterRunWorker(QObject):
    # 내부 요청 (워커 스레드로)
    sig_request = Signal(int, str, object)
    sig_reboot_probe_request = Signal(int, str, object, str)  # seq, packet, SerialSetting, 정상 응답 접두

    # 외부 공개
    sig_sequence_report = Signal(object)  # SequenceReport — CAPTURE/RAW 시퀀스가 끝날 때 1회 (완료·중단·끊김 모두)
    sig_reboot_started = Signal()
    sig_reboot_finished = Signal(bool)  # True=재부팅 후 통신 복구, False=취소됨
    sig_progress_changed = Signal(int)
    sig_is_working_changed = Signal(bool)
    sig_finish_refresh = Signal()
    sig_write_skipped = Signal(list)  # 시퀀스 종료 시: 요청을 만들 수 없어(BuildFailure) 건너뛴 쓰기 param 목록 — 사유는 로그에

    MONITOR_LOG_ROUNDS = 30   # 모니터링 정상 로그는 30 라운드당 1 라운드만 기록
    REBOOT_TICK_MS = 1000

    # 기준 워커 조정 — MainWin 워커(is_primary)의 refresh 가 진행 중이면 다른 워커의
    # refresh 는 예약만 하고, 기준 시퀀스가 끝난 뒤 이어서 시작한다. codec 문맥 param
    # (Interface.Scaling.*, Sensor 1/2.*)은 MainWin 이 init 목록으로 읽으므로
    # "기준 refresh 완료" 가 곧 "문맥 최신" 이다 (3단계 결정 E: 재디코드 없음).
    _primary: "ParameterRunWorker | None" = None
    _pending_refresh: list["ParameterRunWorker"] = []

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

    def __init__(self, parent=None, log_source: str = "ParameterRunWorker", monitor_tick: int = 100,
                 is_primary: bool = False, transport=None):
        """transport: 테스트용 통신 대역(ParameterThread 참고). None 이면 ServicePort — 앱은 항상 None."""
        super().__init__(parent)

        self._log = AppLogManager().get_logger(log_source)

        if is_primary:
            ParameterRunWorker._primary = self

        self._acc_mode_param: Optional[Parameter] = ParamManager().get_by_full_path("System.Access Mode")

        self._registry = SpecRegistry()  # param -> spec 바인딩 (ParamManager 가 채운다)

        # 상태 (문자열 phase 대신 enum + 작업 큐 + 시퀀스 번호)
        self._state = _WorkerState.IDLE
        self._seq = 0
        self._jobs: list[_Job] = []
        self._job_index = 0
        self._seq_kind = SequenceKind.REFRESH   # 현재 시퀀스의 종류 (완료 시그널·보고 구분용)
        self._seq_results: list[JobResult] = []  # CAPTURE/RAW: 끝난 작업의 결과 (보고용)
        self._job_retry = 0                      # 현재 작업의 TRANSIENT 재시도 횟수 (max_retry 와 비교)
        self._skipped_write_params: list[Parameter] = []  # 이번 시퀀스에서 요청을 만들 수 없어(BuildFailure) 건너뛴 쓰기
        self._is_working = False
        self._progress = 0
        self._is_cleaned = False

        # 등록 param 목록
        # write_param_list: 실제 쓰기값은 write() 호출 시 인자로 받는다 —
        # 이 목록은 refresh() 가 [쓰기 가능한 RW param 을 읽어 초기값을 채우는] 데만 쓰인다.
        self.init_param_list: list[Parameter] = []
        self.read_param_list: list[Parameter] = []
        self.write_param_list: list[Parameter] = []

        # 모니터링 (유휴 시 read_param_list 의 spec 들을 round-robin)
        self.monitor_time_tick = monitor_tick
        self._monitor_specs: list[PacketSpec] = []  # 라운드 시작 때 read_param_list 에서 다시 만든다
        self._monitor_index = 0
        self._monitor_round = 0
        self.monitor_timer = QTimer(self)
        self.monitor_timer.setSingleShot(True)
        self.monitor_timer.timeout.connect(self._on_timeout_monitor)

        # 재부팅 대기
        self._reboot_probe_packet: str = ""
        self._reboot_port_setting: SerialSetting | None = None
        self._reboot_expected_prefix: str = ""
        self.reboot_timer = QTimer(self)
        self.reboot_timer.setSingleShot(True)
        self.reboot_timer.timeout.connect(self._on_timeout_reboot)

        # 워커 스레드 구성
        self._thread = QThread()
        self._param_thread = ParameterThread(transport)
        self._param_thread.moveToThread(self._thread)

        self.sig_request.connect(self._param_thread.process_request)
        self.sig_reboot_probe_request.connect(self._param_thread.process_reboot_probe)

        self._param_thread.sig_result.connect(self._handle_result)
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
        self._monitor_specs = []
        self._monitor_index = 0

    def clear_write_param(self, start_index: Optional[int] = None):
        if start_index is None:
            self.write_param_list.clear()
        else:
            del self.write_param_list[start_index:]

    # ------------------------------------------------------------ spec 해석
    def _read_specs_of(self, params: list[Parameter]) -> list[PacketSpec]:
        """param 목록 -> 읽기 spec 목록 (등장 순서 유지, 같은 spec 은 한 번만).
        spec 이 없는 param 은 요청 없이 Not Support 로 두고 건너뛴다."""
        seen: set[int] = set()
        specs: list[PacketSpec] = []
        for param in params:
            spec = self._registry.get_read_spec(param)
            if spec is None:
                if not param.is_not_support:
                    self._log.error(f"no read spec: {param.path}.{param.name} — marked as not supported")
                    param.is_not_support = True
                continue
            if id(spec) in seen:
                continue
            seen.add(id(spec))
            specs.append(spec)
        return specs

    def _write_jobs_of(self, pending: list[tuple[Parameter, str]]) -> list[_Job]:
        """[(param, 값), ...] -> 쓰기 작업 목록. 같은 write spec 을 쓰는 param 들은
        한 작업으로 묶인다 (NV2 는 항상 1:1)."""
        jobs: list[_Job] = []
        job_by_spec: dict[int, _Job] = {}
        for param, value in pending:
            spec = self._registry.get_write_spec(param)
            if spec is None:
                self._log.error(f"no write spec: {param.path}.{param.name} — write skipped")
                param.is_not_support = True
                continue
            job = job_by_spec.get(id(spec))
            if job is None:
                job = _Job(_JobOp.WRITE, spec, {})
                job_by_spec[id(spec)] = job
                jobs.append(job)
            job.values[param] = value
        return jobs

    # ------------------------------------------------------------ 시퀀스 시작
    @property
    def _is_refreshing(self) -> bool:
        return self._state == _WorkerState.SEQUENCE and self._seq_kind is SequenceKind.REFRESH

    def refresh(self) -> StartResult:
        """등록 param 전체 읽기 시퀀스 시작. 완료 후 모니터링으로 전환된다.

        기준 워커(MainWin)의 refresh 가 진행 중이면 PENDING 을 반환하고 예약한다 —
        기준 시퀀스가 끝나면 워커가 스스로 refresh() 를 다시 호출한다 (클래스 주석 참고).
        대기 중에도 창은 refresh 중과 같이 잠긴다 (is_working=True, write 는 BUSY).

        진행 중이던 시퀀스/모니터링은 무조건 중단하고 다시 시작한다.
        단, 재부팅 대기 중에는 BUSY 를 반환한다 — 외부의 refresh 호출이
        재부팅 대기를 중단시키지 않기 위한 안전망.
        (재부팅 대기 중단은 cancel_reboot() 로만 가능)"""
        if self._state == _WorkerState.REBOOT:
            return StartResult.BUSY

        primary = ParameterRunWorker._primary
        if primary is not None and primary is not self and primary._is_refreshing:
            if self not in ParameterRunWorker._pending_refresh:
                ParameterRunWorker._pending_refresh.append(self)
            # 대기 시작: 진행 중이던 동작을 중단하고 창을 잠근다. 이미 대기 중이면 그대로 둔다
            # (잠금 해제는 지연 refresh 의 _finish_sequence, 끊김(handle_disconnected), cleanup 에서)
            if self._state != _WorkerState.PENDING:
                self._stop_all()
                self._state = _WorkerState.PENDING
                self.is_working = True
                self._log.info("refresh pending - waiting for primary refresh to finish")
            return StartResult.PENDING

        self._stop_all()

        params: list[Parameter] = []
        params += self.init_param_list
        params += [p for p in self.write_param_list if p.acc != ParamAccType.WO]
        params += self.read_param_list

        jobs = [_Job(_JobOp.READ, spec) for spec in self._read_specs_of(params)]

        if not jobs:
            return StartResult.EMPTY

        if not ServicePort().connect_info:
            return StartResult.NOT_CONNECTED

        self._start_sequence(jobs, SequenceKind.REFRESH)
        return StartResult.OK

    def write(self, pairs: list[tuple[Parameter, float | int | str]], switch_to_local: bool = False) -> StartResult:
        """전달받은 [(param, value), ...] 쌍들의 쓰기 시퀀스 시작.

        값은 도메인 값(숫자 또는 문자열)이며 호출측이 스냅샷으로 넘긴다 — 워커는
        param.write_str_value 같은 공유 필드를 직접 참조하지 않는다 (모듈 docstring 참고).
        선로 문자열은 전송 직전에 spec 의 codec 이 만든다 — 호출측이 미리 문자열화하지
        않아야 유효숫자 절단이 한 번만 일어난다.

        NEED_LOCAL_SWITCH 반환 시 윈도우가 사용자에게 물어본 뒤 동일 pairs 로
        write(pairs, switch_to_local=True) 를 다시 호출한다.
        쓰기 후에는 [쓴 param 읽기(RW만) -> read_param_list 읽기] 가 이어진다."""
        # PENDING 도 BUSY — 대기 중 시작된 쓰기가 지연 refresh 의 _stop_all 에 잘리는 것을 막는다
        if self._state in (_WorkerState.SEQUENCE, _WorkerState.REBOOT, _WorkerState.PENDING):
            return StartResult.BUSY

        if not ServicePort().connect_info:
            return StartResult.NOT_CONNECTED

        # 값 없음(None / 빈 문자열)만 거른다 — 숫자 0 은 유효한 쓰기 값이다
        pending = [(param, value) for param, value in pairs if value is not None and value != ""]
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
            jobs += self._write_jobs_of([(self._acc_mode_param, str(p_enum.AccModeEnum.LOCAL.value))])

        jobs += self._write_jobs_of(pending)

        # 쓰기 후 read-back: 쓴 param(RW) -> 등록 읽기 목록. spec 기준으로 한 번씩만
        readback = [param for param, _ in pending if param.acc != ParamAccType.WO]
        jobs += [_Job(_JobOp.READ, spec) for spec in self._read_specs_of(readback + self.read_param_list)]

        self._stop_all()
        self._start_sequence(jobs, SequenceKind.WRITE)
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

        report = None
        if self._state == _WorkerState.SEQUENCE:
            self._log.info(f"disconnected - sequence aborted ({self._job_index}/{len(self._jobs)} jobs done)")
            report = self._take_report(SequenceEnd.DISCONNECTED)
        elif self._state == _WorkerState.PENDING:
            self._log.info("disconnected - pending refresh cancelled")

        self._stop_all()  # PENDING 이었다면 여기서 is_working=False 로 창 잠금이 풀린다
        self._state = _WorkerState.DISCONNECTED

        # 예약된 refresh 는 취소한다 — 재연결 시 창이 다시 refresh() 를 호출한다.
        # 기준 워커가 끊기면 대기자 전부를 비운다 (대기자도 각자 끊김 처리를 받는다)
        self._discard_pending_refresh()
        if self is ParameterRunWorker._primary:
            ParameterRunWorker._pending_refresh.clear()

        if report is not None:
            self.sig_sequence_report.emit(report)  # 상태 전환을 모두 마친 뒤 — 창의 슬롯이 대화상자를 띄워도 워커는 이미 정리됐다

    # ------------------------------------------------------------ 백업·복원 시퀀스 (보고형)
    def capture(self, params: list[Parameter], max_retry: int = 3) -> StartResult:
        """param 들의 읽기 spec 으로 읽기 시퀀스(CAPTURE)를 시작한다 — 백업.

        성공한 param 은 값·str_value(선로 원문)·플래그가 보통 읽기와 똑같이 갱신되므로, 창은 str_value 로 파일 행을 만든다.
        같은 spec 을 쓰는 param 은 한 작업이고, spec 없는 param 은 Not Support 로 두고 작업을 만들지 않는다 — 창은
        '체크한 param − 성공한 param' 으로 누락을 센다. TRANSIENT 는 max_retry 까지 같은 작업을 재시도하고, 소진하면 실패로
        기록하고 다음으로 간다. 시퀀스 중에는 is_working 이 켜져 창이 잠기고 모니터링은 멈춘다. 끝나면 sig_sequence_report.
        반환: SEQUENCE/PENDING/REBOOT 중 BUSY, 미연결 NOT_CONNECTED, 작업 없음 EMPTY, 시작 OK."""
        if self._state in (_WorkerState.SEQUENCE, _WorkerState.REBOOT, _WorkerState.PENDING):
            return StartResult.BUSY

        if not ServicePort().connect_info:
            return StartResult.NOT_CONNECTED

        jobs = [_Job(_JobOp.READ, spec, max_retry=max_retry) for spec in self._read_specs_of(params)]
        if not jobs:
            return StartResult.EMPTY

        self._stop_all()
        self._start_sequence(jobs, SequenceKind.CAPTURE)
        return StartResult.OK

    def raw_write(self, jobs: list[tuple[str, str]], max_retry: int = 3) -> StartResult:
        """(tag, 완성된 패킷) 목록을 순서대로 보내는 RAW 시퀀스를 시작한다 — 복원 (Local 전환 패킷도 목록의 한 항목).

        판정은 raw_write_spec_of(packet) 의 spec: NV2 쓰기 패킷은 장비 오류 코드를 REJECTED/NOT_SUPPORT 로 판정해 재시도하지
        않고 실패로 기록하며, 잡음(접두 불일치·빈 응답)만 max_retry 까지 재시도한다. 실패해도 다음 항목으로 진행한다.
        반환은 capture() 와 같다."""
        if self._state in (_WorkerState.SEQUENCE, _WorkerState.REBOOT, _WorkerState.PENDING):
            return StartResult.BUSY

        if not ServicePort().connect_info:
            return StartResult.NOT_CONNECTED

        raw_jobs = [_Job(_JobOp.RAW, raw_write_spec_of(packet), max_retry=max_retry, tag=tag) for tag, packet in jobs]
        if not raw_jobs:
            return StartResult.EMPTY

        self._stop_all()
        self._start_sequence(raw_jobs, SequenceKind.RAW)
        return StartResult.OK

    def abort_sequence(self) -> bool:
        """사용자 취소 — CAPTURE/RAW 시퀀스를 끊고 그때까지의 결과를 SequenceEnd.ABORTED 로 보고한다.
        보내 둔 요청의 응답은 seq 로 폐기된다. REFRESH/WRITE 시퀀스에는 쓰지 않는다 (False)."""
        if self._state != _WorkerState.SEQUENCE or self._seq_kind not in (SequenceKind.CAPTURE, SequenceKind.RAW):
            return False

        report = self._take_report(SequenceEnd.ABORTED)
        self._log.info(f"{self._seq_kind.name.lower()} aborted by user ({len(report.results)}/{report.total} jobs done)")
        self._stop_all()
        self._enter_idle()
        self.sig_sequence_report.emit(report)
        return True

    def _take_report(self, end: SequenceEnd) -> SequenceReport | None:
        """CAPTURE/RAW 시퀀스면 지금까지의 결과로 보고서를 만들고 결과를 비운다 — 그 밖의 시퀀스는 None.
        보고는 _finish_sequence(COMPLETED) / abort_sequence(ABORTED) / handle_disconnected(DISCONNECTED) 세 곳에서만 낸다.
        _stop_all() 자체는 보고하지 않는다 (refresh/write/재부팅/cleanup 경로 — CAPTURE/RAW 가 돌 때는 창이 잠겨 들어오지
        않고, cleanup 은 창이 닫히는 중이라 보고할 곳이 없다)."""
        if self._seq_kind not in (SequenceKind.CAPTURE, SequenceKind.RAW):
            return None
        report = SequenceReport(self._seq_kind, self._seq_results, len(self._jobs), end)
        self._seq_results = []
        return report

    # ------------------------------------------------------------ 재부팅
    def cancel_reboot(self):
        """재부팅 대기 취소. 포트는 닫힌 상태로 둔다 (단선과 동일 취급).

        호출측(윈도우)은 취소 후 해당 윈도우를 닫아 동작을 마무리한다."""
        if self._state != _WorkerState.REBOOT:
            return

        self._stop_all()
        self.sig_reboot_finished.emit(False)

    def start_reboot_wait(self, port_setting: SerialSetting) -> bool:
        """워커 밖의 요인(펌웨어 업데이트 등)으로 장비가 재부팅될 때 재부팅 대기를
        외부에서 시작한다. 이후 흐름은 reconnect param 쓰기에 의한 재부팅과 같다
        (sig_reboot_started -> SN probe 폴링 -> 응답 시 ServicePort.open ->
        sig_reboot_finished(True) -> 재연결 refresh 는 윈도우 경로).

        port_setting: 재연결에 쓸 SerialSetting — 호출측이 ServicePort 를 닫기 전에
        svc.setting 으로 스냅샷해 둔 값. ServicePort 가 아직 열려 있으면 여기서 닫는다 (probe 는 임시 raw
        serial 연결로만 수행하므로 같은 포트가 열려 있으면 안 된다).
        이미 재부팅 대기 중이면 False."""
        if self._state == _WorkerState.REBOOT:
            return False

        ServicePort().close()
        return self._start_reboot(port_setting)

    def reconnect(self) -> bool:
        """재부팅 없이 즉시 재접속 — 포트를 닫았다 같은 설정으로 다시 연다.

        워커 밖의 요인(백업 복원 등)으로 장비 param 이 바뀌었을 때 쓴다. 재접속과 같은 경로
        (connect_info_changed → 창마다 refresh, 기준 워커 먼저)로 열린 창 전부가 다시 읽는다 —
        start_reboot_wait 의 '재부팅 없는' 형제이며, 창이 ServicePort 를 직접 여닫지 않게 하는 단일 지점.
        열려 있지 않으면(재부팅 대기 중 포함) False 로 아무것도 하지 않고, 다시 열기 실패도 False —
        끊김 상태로 남아 상태바·로그에 드러난다 (N077, 2026-10-06 결정)."""
        svc = ServicePort()
        setting = svc.setting  # close() 가 지우므로 먼저 스냅샷
        if setting is None:
            return False

        self._log.info("reconnect requested - reopening the port so every window refreshes")
        svc.close()
        return svc.open(setting)

    def _start_reboot(self, port_setting: SerialSetting | None = None) -> bool:
        """port_setting 이 None 이면(쓰기 경로) 현재 ServicePort 설정을 백업한 뒤
        닫는다. 주어지면(외부 시작 경로) 그 값을 재연결에 쓴다."""
        sn = ParamManager().get_by_full_path("System.Identification.Serial Number")
        sn_spec = self._registry.get_read_spec(sn) if sn is not None else None
        if sn_spec is None:
            self._log.error("reboot: Serial Number param (or its read spec) not found - abort")
            self._stop_all()
            self.sig_reboot_finished.emit(False)
            return False

        self._reboot_probe_packet = sn_spec.build_request()
        self._reboot_expected_prefix = sn_spec.expected_response_prefix  # probe 판정 기준 (F026)

        if port_setting is None:
            # 포트 설정을 백업한 뒤 닫는다. 재부팅 대기 동안 ServicePort 는 닫힌 채
            # 유지되고, 확인은 임시 raw serial 연결(probe)로만 수행한다.
            svc = ServicePort()
            port_setting = svc.setting
            svc.close()

        if port_setting is None:
            # 쓰기 응답과 재부팅 진입 사이에 끊긴 경우 — 빈 설정으로 영원히 probe 하지 않는다
            self._log.error("reboot: port setting unavailable (disconnected) - abort")
            self._stop_all()
            self.sig_reboot_finished.emit(False)
            return False

        self._reboot_port_setting = port_setting

        # 진행 중이던 쓰기 시퀀스는 여기서 명시적으로 정리한다.
        # close() 의 끊김 시그널은 큐 배달이라 REBOOT 진입 후에 도착하고,
        # handle_disconnected 는 REBOOT 를 무시하므로 (의도된 동작) 시퀀스 정리를
        # 시그널 경로에 기대면 안 된다.
        self._stop_all()

        self._state = _WorkerState.REBOOT
        self.sig_reboot_started.emit()
        self.reboot_timer.start(self.REBOOT_TICK_MS)
        return True

    def _on_timeout_reboot(self):
        if self._state != _WorkerState.REBOOT:
            return

        self.sig_reboot_probe_request.emit(self._seq, self._reboot_probe_packet,
                                           self._reboot_port_setting, self._reboot_expected_prefix)

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
        ServicePort().open(setting)

    # ------------------------------------------------------------ 작업 큐 처리
    def _start_sequence(self, jobs: list[_Job], kind: SequenceKind):
        self._seq += 1
        self._jobs = jobs
        self._job_index = 0
        self._job_retry = 0
        self._seq_kind = kind
        self._seq_results = []
        self._skipped_write_params = []
        self._state = _WorkerState.SEQUENCE
        self.is_working = True
        self.progress = 0
        self._send_current_job()

    def _send_current_job(self):
        # 쓰기 요청을 만들 수 없으면(BuildFailure — 값 없음/문맥 미준비/형식 불량/폭 초과) 그 작업은 건너뛰고 사유를 로그에 남긴다
        while self._job_index < len(self._jobs):
            job = self._jobs[self._job_index]
            packet = job.spec.build_request(job.values)
            if not isinstance(packet, BuildFailure):
                self.sig_request.emit(self._seq, packet, job.spec)
                return

            self._log.error(f"request not built ({packet.name}) - write skipped: "
                            f"{job.spec.describe()} values={job.values}")
            self._skipped_write_params += list(job.values) if job.values else []
            self._job_index += 1
            self.progress = int((self._job_index / len(self._jobs)) * 100)

        self._finish_sequence()

    @Slot(int, str, str, object, SvcPortErrType)
    def _handle_result(self, seq: int, packet: str, response: str,
                       spec: PacketSpec, err_type: SvcPortErrType):
        # 이전 시퀀스의 늦은 응답은 폐기
        if seq != self._seq:
            return

        if self._state == _WorkerState.SEQUENCE:
            self._handle_sequence_result(packet, response, spec, err_type)
        elif self._state == _WorkerState.MONITOR:
            self._handle_monitor_result(packet, response, spec, err_type)
        # REBOOT 상태는 ServicePort 요청을 보내지 않으므로 (probe 전용) 여기로 오지 않는다

    def _handle_sequence_result(self, packet, response, spec: PacketSpec, err_type):
        job = self._jobs[self._job_index]
        outcome = spec.apply_response(response)   # 통신 오류는 빈 응답으로 들어가 TRANSIENT(COMMUNICATION_ERR)

        is_error = err_type != SvcPortErrType.NONE or outcome.reason is not ParamParseErrType.NONE
        err_msg = err_type.name if err_type != SvcPortErrType.NONE else outcome.reason.name
        self._log_transaction(packet, response, spec, err_msg if is_error else "", is_error=is_error)
        # UNCHECKED(RW 쓰기)는 reason NONE 이라 정상 로그

        if job.op is _JobOp.WRITE:
            # 쓰기 — 실패해도 로그만 남기고 계속 진행. 재접속 param 이면 결과와 무관하게 재부팅 대기 (N045 결정)
            if any(param.is_need_reconnect for param in spec.params):
                self._start_reboot()
                return
        else:  # READ / RAW
            if outcome.need_retry and (job.max_retry is None or self._job_retry < job.max_retry):
                # 부류 TRANSIENT — 같은 작업 재시도 (refresh 는 무제한, CAPTURE/RAW 는 상한까지)
                self._job_retry += 1
                self._send_current_job()
                return

            if self._seq_kind in (SequenceKind.CAPTURE, SequenceKind.RAW):
                # 성공이든 실패(소진/거부/미지원)든 기록. 선로 원문은 지금 떠 둔다 — apply_response 직후라 다른 읽기가 끼어들 틈이 없다
                lines = {p: p.str_value for p in spec.params} if outcome.verdict is Verdict.OK else {}
                self._seq_results.append(JobResult(job.tag, spec.params, outcome, lines))
            elif self._seq_kind is SequenceKind.REFRESH and outcome.reason is ParamParseErrType.NONE:
                # refresh 읽기 성공 = 장비 값으로 동기화 확정 → 값이 안 변해도 통지하여
                # UI 의 dirty 를 클리어하게 한다. write 후 read-back 은 제외 —
                # 값이 그대로면 쓰기가 반영되지 않은 것이므로 dirty 가 유지되어야 한다.
                for param in spec.params:
                    param.notify_synced()

        # 다음 작업으로
        self._job_retry = 0
        self._job_index += 1
        self.progress = int((self._job_index / len(self._jobs)) * 100)

        if self._job_index < len(self._jobs):
            self._send_current_job()
        else:
            self._finish_sequence()

    def _finish_sequence(self):
        was_refresh = self._seq_kind is SequenceKind.REFRESH
        report = self._take_report(SequenceEnd.COMPLETED)   # CAPTURE/RAW 만 — 비우기 전에

        self.is_working = False
        self.progress = 0
        self._jobs = []
        self._job_index = 0
        self._enter_idle()

        # refresh 시퀀스 완료만 알린다 (write 완료에는 발화하지 않음) —
        # 윈도우가 이 시그널을 받아 CompoundRunWorker.start_polling() 등을 수행
        if was_refresh:
            self.sig_finish_refresh.emit()

        # 기준 워커의 시퀀스가 끝나면(refresh 든, refresh 를 끊고 들어온 write 든)
        # 예약된 다른 워커의 refresh 를 이어서 시작한다
        if self is ParameterRunWorker._primary:
            self._release_pending_refresh()

        # 건너뛴 쓰기 안내는 상태 전환을 모두 마친 뒤 마지막에 — 창의 슬롯이 모달 대화상자를
        # 띄워 이벤트 루프가 안에서 돌더라도 워커는 이미 유휴/모니터링 상태다
        if self._skipped_write_params:
            skipped, self._skipped_write_params = self._skipped_write_params, []
            self.sig_write_skipped.emit(skipped)

        if report is not None:
            self.sig_sequence_report.emit(report)

    def _enter_idle(self):
        """시퀀스가 끝난 뒤의 유휴 상태 — read_param_list 가 있으면 모니터링, 없으면 IDLE."""
        if self.read_param_list:
            self._state = _WorkerState.MONITOR
            self._monitor_specs = []
            self._monitor_index = 0
            self._monitor_round = 0
            self.monitor_timer.start(self.monitor_time_tick)
        else:
            self._state = _WorkerState.IDLE

    # ------------------------------------------------------------ 기준 워커 조정
    @classmethod
    def _release_pending_refresh(cls) -> None:
        waiting, cls._pending_refresh = cls._pending_refresh, []
        for worker in waiting:
            QTimer.singleShot(0, worker._resume_pending_refresh)  # 기준 워커 슬롯 밖에서 시작

    def _resume_pending_refresh(self) -> None:
        if self._is_cleaned:
            return
        result = self.refresh()
        if result not in (StartResult.OK, StartResult.PENDING):
            self._log.info(f"pending refresh not started: {result.name}")

    def _discard_pending_refresh(self) -> None:
        ParameterRunWorker._pending_refresh = [w for w in ParameterRunWorker._pending_refresh if w is not self]

    # ------------------------------------------------------------ 모니터링
    def _on_timeout_monitor(self):
        if self._state != _WorkerState.MONITOR:
            return

        # 리스트가 비어 있어도 타이머는 계속 돌린다 —
        # clear 후 add_read_param 으로 다시 채워지면 자동으로 재개되도록
        if not self.read_param_list:
            self.monitor_timer.start(self.monitor_time_tick)
            return

        # 라운드 시작마다 read_param_list 에서 spec 목록을 다시 만든다 —
        # 목록 변경(clear/add)과 조건부 spec 전환이 다음 라운드에 반영된다
        if self._monitor_index >= len(self._monitor_specs):
            self._monitor_specs = self._read_specs_of(self.read_param_list)
            self._monitor_index = 0
            # 정상 로그 샘플링용 라운드 카운트 (MONITOR_LOG_ROUNDS 라운드당 1 라운드 기록)
            self._monitor_round += 1
            if self._monitor_round > self.MONITOR_LOG_ROUNDS:
                self._monitor_round = 0

            if not self._monitor_specs:
                self.monitor_timer.start(self.monitor_time_tick)
                return

        spec = self._monitor_specs[self._monitor_index]
        self.sig_request.emit(self._seq, spec.build_request(), spec)

    def _handle_monitor_result(self, packet, response, spec: PacketSpec, err_type):
        outcome = spec.apply_response(response)

        if err_type != SvcPortErrType.NONE:
            self._log_transaction(packet, response, spec, err_type.name, is_error=True, is_monitor=True)
            self.monitor_timer.start(self.monitor_time_tick)  # 같은 spec 재시도
            return

        if outcome.reason is not ParamParseErrType.NONE:
            self._log_transaction(packet, response, spec, outcome.reason.name, is_error=True, is_monitor=True)
            if outcome.need_retry:   # 부류 TRANSIENT — 다음 틱에 같은 spec
                self.monitor_timer.start(self.monitor_time_tick)
                return
        else:
            self._log_transaction(packet, response, spec, is_monitor=True)

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
        self._job_retry = 0
        self._seq_results = []
        self._skipped_write_params = []
        self._state = _WorkerState.IDLE
        self.is_working = False
        self.progress = 0

    def _log_transaction(self, req: str, resp: str, spec: PacketSpec,
                         err_msg: str = "", is_error: bool = False, is_monitor: bool = False):
        # 모니터링 로그는 오류 포함 샘플링 라운드에서만 기록
        # (미연결 상태의 100ms 무한 재시도가 로그를 홍수시키는 것을 방지 — ver1 동일)
        if is_monitor and self._monitor_round != self.MONITOR_LOG_ROUNDS:
            return

        msg = f"Spec: {spec.describe()} | Req: {req} | Resp: {resp}"
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

        self._discard_pending_refresh()
        if self is ParameterRunWorker._primary:
            ParameterRunWorker._primary = None
            # 기준 워커가 사라지면 대기자를 잠긴 채 두지 않고 이어서 시작시킨다
            # (대기자 자신도 cleanup 됐다면 _resume_pending_refresh 가 _is_cleaned 로 무시)
            self._release_pending_refresh()

        self._stop_all()

        if self._thread is not None and self._thread.isRunning():
            if self._param_thread:
                self._param_thread.blockSignals(True)
            self._thread.quit()
            self._thread.wait()
