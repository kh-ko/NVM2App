"""Compound 슬롯 기록 + 고속 폴링 워커 (기존 e_worker/compounds_run_worker.py 대응).

ver1 에서 달라진 점:
- 슬롯 구성(12개 param 경로, "Compound Commands 1" 뱅크)이 워커에 하드코딩되어
  있던 것을 제거. 사용측(윈도우)이 configure() 로 주입한다 — 어떤 윈도우든
  자기 UI 기능 정의에 맞는 슬롯 구성으로 사용 가능.
- 응답 값의 형 변환도 워커가 모른다. 사용측이 주입한 sample_factory 가
  워커 스레드에서 호출되어 형 변환을 수행한다 (UI 스레드 부하 방지는 ver1 유지).
  미지정 시 원시 문자열 튜플(CompoundSample)을 큐에 쌓는다.
- 폴링 제어권은 윈도우 소유 — 워커는 연결 시그널을 구독하지 않는다.
  생성 직후에는 폴링 게이트가 비활성(idle)이며, 윈도우가 start_polling() 을
  호출해야 [슬롯 쓰기 -> 폴링] 이 시작된다. (보통 ParameterRunWorker 의
  sig_finish_refresh 수신 시점) stop_polling() 은 스레드를 유지한 채
  idle 루프로 되돌린다. (연결 끊김 시 윈도우가 호출)
- ref param 자동 갱신은 pop_all_data()(UI 스레드) 에서 마지막 샘플의
  원시 문자열로 수행한다 (ver1 의 형변환 -> str() 왕복 제거).

동작 흐름:
1. start_polling() 되면 configure() 된 슬롯 쓰기 명령("p:01...")을 일괄 전송한다.
2. 이후 "29" 서비스 코드("p:29...")로 지연 없이 최대 속도로 폴링한다.
   (시리얼 왕복 자체가 자연 지연이 된다)
3. 인위적 지연은 시리얼 왕복 없이 즉시 실패하는 경로에만 둔다:
   - 폴링 게이트 비활성 / 미연결 대기 / 설정 없음: IDLE_DELAY_MS
   - 슬롯 쓰기 실패 재시도: WRITE_RETRY_DELAY_MS
   - 읽기 통신 오류: ERROR_DELAY_MS
   파싱 예외·짧은 응답은 이미 시리얼 왕복이 발생한 뒤이므로 지연 없이
   로그만 남기고 다음 폴링을 진행한다.
"""

import time
from collections import deque
from typing import Callable, NamedTuple

from PySide6.QtCore import QCoreApplication, QMutex, QMutexLocker, QObject, QThread, Signal

from b_core.c_manager.app_log_manager import AppLogManager
from b_core.d_dal.service_port import ServicePort
from b_core.b_datatype.general_enum import SvcPortErrType
from b_core.b_datatype.parameter import Parameter


class CompoundSample(NamedTuple):
    """sample_factory 미지정 시의 기본 샘플 — 슬롯 순서 그대로의 원시 문자열."""
    timestamp_ms: int
    values: tuple[str, ...]


# 워커 스레드에서 호출된다: (timestamp_ms, values) -> 큐에 쌓을 샘플 객체
SampleFactory = Callable[[int, list[str]], object]


class CompoundPollThread(QThread):
    """슬롯 쓰기 -> "29" 폴링 -> 큐 적재만 아는 기계적 폴링 스레드.

    슬롯 구성/형 변환 등 도메인 지식은 전부 CompoundRunWorker.configure() 로
    주입받는다."""

    sig_log = Signal(bool, str, str, str)  # is_err, tx, rx, msg

    IDLE_DELAY_MS = 100         # 미연결 대기 / 설정 없음
    WRITE_RETRY_DELAY_MS = 100  # 슬롯 쓰기 실패 후 재시도 간격
    ERROR_DELAY_MS = 1000       # 읽기 통신 오류 후 대기
    LOOP_WARN_MS = 200          # 이 시간을 넘는 루프/요청은 진단 로그를 남긴다

    def __init__(self, parent=None):
        super().__init__(parent)
        self._is_running: bool = False
        self.svc_port: ServicePort = ServicePort()

        # 슬롯 구성 (configure 로 교체됨) — _config_mutex 로 보호
        self._config_mutex = QMutex()
        self._config_gen: int = 0            # 구성 세대 — 쓰기 완료 판정의 경합 방지
        self._polling_enabled: bool = False  # 폴링 게이트 — start_polling() 전에는 idle
        self._need_write: bool = True
        self._write_cmds: list[bytes] = []
        self._read_cmd: bytes = b""
        self._expected_count: int = 0
        self._sample_factory: SampleFactory | None = None

        # 수집 큐 — queue_mutex 로 보호. (샘플 객체, 원시 문자열 목록) 쌍으로 적재
        self.queue_mutex = QMutex()
        self.data_queue = deque(maxlen=200)

        self._pre_loop_ms: int = 0
        self._loop_log_count: int = 0

    # ------------------------------------------------------------ 외부 제어
    def set_slots(self, write_cmds: list[bytes], read_cmd: bytes,
                  expected_count: int, sample_factory: SampleFactory | None) -> None:
        with QMutexLocker(self._config_mutex):
            self._config_gen += 1
            self._need_write = True
            self._write_cmds = list(write_cmds)
            self._read_cmd = read_cmd
            self._expected_count = expected_count
            self._sample_factory = sample_factory

    def start_polling(self) -> None:
        """폴링 게이트 활성화 — 다음 루프에서 슬롯 쓰기부터 다시 수행한 뒤 폴링한다."""
        with QMutexLocker(self._config_mutex):
            self._config_gen += 1
            self._need_write = True
            self._polling_enabled = True

    def stop_polling(self) -> None:
        """폴링 게이트 비활성화 — 스레드는 유지한 채 idle 루프만 돈다.

        진행 중이던 트랜잭션 1건은 마저 끝난다 (중간에 끊을 수 없음)."""
        with QMutexLocker(self._config_mutex):
            self._polling_enabled = False

    def stop(self) -> None:
        self._is_running = False

    # ------------------------------------------------------------ 메인 루프
    def run(self):
        self._is_running = True

        while self._is_running:
            with QMutexLocker(self._config_mutex):
                polling_enabled = self._polling_enabled
                gen = self._config_gen
                need_write = self._need_write
                write_cmds = list(self._write_cmds)
                read_cmd = self._read_cmd
                expected = self._expected_count
                factory = self._sample_factory

            # 폴링 게이트 비활성 — 아무 동작도 하지 않는다.
            # (재개 여부/시점 판단은 윈도우가 start_polling() 으로 지시)
            if not polling_enabled:
                self.msleep(self.IDLE_DELAY_MS)
                continue

            # 미연결 — 폴링 불가 상태이므로 대기만 한다
            if not self.svc_port.connect_info:
                self.msleep(self.IDLE_DELAY_MS)
                continue

            if not read_cmd:
                self.sig_log.emit(True, "TX : Not Set", "", "[Compound Read Command] is not set")
                self.msleep(self.IDLE_DELAY_MS)
                continue

            if need_write:
                if not self._write_slots(write_cmds):
                    self.msleep(self.WRITE_RETRY_DELAY_MS)
                    continue
                with QMutexLocker(self._config_mutex):
                    # 쓰기 도중 configure()/start_polling() 이 왔다면 완료 처리하지 않는다
                    if gen == self._config_gen:
                        self._need_write = False

            self._poll_once(read_cmd, expected, factory)

    def _write_slots(self, write_cmds: list[bytes]) -> bool:
        for cmd in write_cmds:
            if not self._is_running:
                return False

            response, err_type = self.svc_port.request(cmd)

            if err_type != SvcPortErrType.NONE:
                self.sig_log.emit(True, cmd.decode('utf-8'), response or "", f"Write Compound Fail : {err_type}")
                return False

            if not response.startswith("p:0001"):
                self.sig_log.emit(True, cmd.decode('utf-8'), response, "Write Compound Fail")
                return False

            self.sig_log.emit(False, cmd.decode('utf-8'), response, "Write Compound Success")

        return True

    def _poll_once(self, read_cmd: bytes, expected: int,
                   factory: SampleFactory | None) -> None:
        start_time = time.perf_counter()

        response, err_type = self.svc_port.request(read_cmd)

        elapsed_ms = (time.perf_counter() - start_time) * 1000
        now_ms = int(time.time() * 1000)
        loop_ms = now_ms - self._pre_loop_ms
        if self._pre_loop_ms and (loop_ms > self.LOOP_WARN_MS or elapsed_ms > self.LOOP_WARN_MS):
            self.sig_log.emit(False, "", "", f"slow loop: loop={loop_ms}ms, request={elapsed_ms:.0f}ms")
        self._pre_loop_ms = now_ms

        # 통신 오류 — 시리얼 왕복 없이 즉시 실패할 수 있는 경로이므로 인위적 지연
        if err_type != SvcPortErrType.NONE or not response.startswith("p:0029"):
            self.sig_log.emit(True, read_cmd.decode('utf-8'), response or "", f"Read Compound Fail : {err_type}")
            self.msleep(self.ERROR_DELAY_MS)
            return

        # 여기서부터는 시리얼 왕복이 이미 끝났으므로 실패해도 지연 없이 계속 폴링
        try:
            payload = response[16:]  # "p:0029"(6) + id(8) + index(2) = 16
            values = payload.split(';')

            if len(values) < expected:
                self.sig_log.emit(True, read_cmd.decode('utf-8'), response, "Response is short")
                return

            if factory is not None:
                sample = factory(now_ms, values)  # 형 변환은 워커 스레드 부담
            else:
                sample = CompoundSample(now_ms, tuple(values))

            with QMutexLocker(self.queue_mutex):
                self.data_queue.append((sample, values))

            self._loop_log_count += 1
            if self._loop_log_count % 100 == 0:
                self.sig_log.emit(False, read_cmd.decode('utf-8'), response, "Read Compound Success")

        except Exception as e:
            self.sig_log.emit(True, read_cmd.decode('utf-8'), response, f"Parse Error: {e}")


class CompoundRunWorker(QObject):
    """Compound 폴링 워커의 외부 인터페이스 (UI 스레드에서 사용).

    사용 예 (main_win 등 사용측이 도메인 지식을 소유한다):
        worker = CompoundRunWorker(self, log_source="MainWin")
        worker.configure(pairs, sample_factory=make_compound_data)
        worker.start()                      # 스레드 기동 (폴링은 아직 비활성)
        ...
        worker.start_polling()              # param refresh 완료 시그널 수신 시
        worker.stop_polling()               # 연결 끊김 시
        data_list = worker.pop_all_data()   # 주기 타이머에서 배치로 회수

    log_source: 로그 출처 이름. 담당 윈도우 이름을 넘기면 해당 윈도우의
    LogView(sources 필터)에서 이 워커의 로그가 함께 보인다."""

    def __init__(self, parent=None, log_source: str = "CompoundRunWorker"):
        super().__init__(parent)

        self._log = AppLogManager().get_logger(log_source)
        self._pairs: list[tuple[Parameter, Parameter | None]] = []
        self._thread = CompoundPollThread(self)
        self._thread.sig_log.connect(self._handle_log)

        app = QCoreApplication.instance()
        if app is not None:
            app.aboutToQuit.connect(self._destroyed)

        self.destroyed.connect(self._destroyed)

    # ------------------------------------------------------------ 구성
    def configure(self, pairs: list[tuple[Parameter, Parameter | None]],
                  sample_factory: SampleFactory | None = None) -> None:
        """슬롯 구성 주입. 실행 중 호출해도 되며, 다음 루프에서 재기록된다.

        pairs: (compound 슬롯 param, 연동할 ref param) 목록.
               ref 가 None 이면 해당 슬롯을 해제(터미네이터)한다.
        sample_factory: 워커 스레드에서 (timestamp_ms, values) 로 호출되어
               큐에 쌓을 샘플을 만든다. None 이면 CompoundSample(원시 문자열)."""
        if self._thread is None:
            return

        write_cmds: list[bytes] = []
        for compound, ref in pairs:
            idx_str = f"{compound.index:02X}"
            ref_id = ref.id if ref is not None else "00000000"
            # 값 필드의 int(ref_id, 16) 은 의도된 변환이다:
            # ref param 의 hex id 를 10진수 문자열로 바꿔 서비스 01 값으로 전송한다.
            cmd_str = f"p:01{compound.id}{idx_str}{int(ref_id, 16)}"
            write_cmds.append(cmd_str.encode('utf-8'))

        read_cmd = b""
        if pairs:
            read_cmd = f"p:29{pairs[0][0].id}00".encode('utf-8')

        expected_count = sum(1 for _, ref in pairs if ref is not None)

        self._pairs = list(pairs)
        self._thread.set_slots(write_cmds, read_cmd, expected_count, sample_factory)

    # ------------------------------------------------------------ 제어
    def start(self) -> None:
        if self._thread is not None and not self._thread.isRunning():
            self._thread.start()

    def stop(self) -> None:
        if self._thread is not None and self._thread.isRunning():
            self._thread.stop()
            self._thread.wait()

    def start_polling(self) -> None:
        """슬롯 쓰기부터 다시 수행한 뒤 폴링 시작.

        호출 시점 판단은 윈도우 몫 — 보통 ParameterRunWorker.sig_finish_refresh
        수신 시점 (param 초기 읽기가 끝난 뒤 버스를 넘겨받는 순서 보장)."""
        if self._thread is not None:
            self._thread.start_polling()

    def stop_polling(self) -> None:
        """폴링 중단 (스레드는 유지). 연결 끊김 시 윈도우가 호출한다."""
        if self._thread is not None:
            self._thread.stop_polling()

    # ------------------------------------------------------------ 데이터 회수
    def pop_all_data(self) -> list:
        """큐의 샘플을 전부 회수해 반환한다 (UI 스레드에서 호출).

        마지막 샘플의 원시 문자열 값으로 ref param 들을 set_force_value 갱신한다
        — param 변경 시그널이 UI 스레드에서 발화되도록 여기서 수행."""
        if self._thread is None:
            return []

        items = []
        with QMutexLocker(self._thread.queue_mutex):
            while self._thread.data_queue:
                items.append(self._thread.data_queue.popleft())

        if not items:
            return []

        _, last_values = items[-1]
        for i, (_, ref) in enumerate(self._pairs):
            if ref is not None and i < len(last_values):
                ref.set_force_value(last_values[i])

        return [sample for sample, _ in items]

    # ------------------------------------------------------------ 내부
    def _handle_log(self, is_err: bool, tx: str, rx: str, msg: str):
        if is_err:
            self._log.error(f"Tx: {tx} Rx: {rx} {msg}")
        else:
            self._log.info(f"Tx: {tx} Rx: {rx} {msg}")

    def _destroyed(self):
        app = QCoreApplication.instance()
        if app is not None:
            try:
                app.aboutToQuit.disconnect(self._destroyed)
            except (TypeError, RuntimeError):
                pass

        self.stop()
        self._thread = None
