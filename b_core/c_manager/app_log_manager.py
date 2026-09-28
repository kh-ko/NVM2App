"""앱 로그 시스템.

기존 c_manager/log_manager.py(LogManager) 와는 별개의 새 시스템이다.

- 모든 로그를 하루 1파일(logs/app_YYYY-MM-DD.log)로 저장한다. 보존 30일
  (시작 시 기한 지난 파일 자동 삭제). 배포 후 문제 발생 시
  "로그 폴더를 보내주세요" 워크플로우를 지원한다.
- 레벨 없음. 대신 카테고리(INFO / WARN / TX / RX / ERROR)로 분류하며
  UI(LogViewWin)가 카테고리별 색상으로 표시한다.
- sig_logged 로 실시간 배포(윈도우별 LogView 구독),
  snapshot() 으로 뷰가 열릴 때 최근분(링버퍼)을 백필한다.
- 전역 로그: 앱 전체에서 쓰이는 클래스(ServicePort, ParamManager 등)는
  get_logger(source, is_global=True) 로 선언한다. is_global 로그는 LogView 의
  sources 필터와 무관하게 모든 윈도우의 LogView 에 표시된다.
  (윈도우 소속 워커는 기본값 False — 담당 윈도우의 LogView 에만 표시)
- install_stderr_hook() 을 앱 시작 시 호출하면 미처리 예외 traceback 등
  stderr 출력이 ERROR 로그(source="stderr")로 수집된다.
  (windowed 배포 빌드에서 stderr 가 허공으로 사라지는 문제 대응)
  sig_logged 슬롯이 낸 예외의 traceback 은 파일/링버퍼에만 기록하고 다시 발화하지
  않는다(is_logging() 재진입 판정 — 재귀 크래시 방지). 개행 없이 끝난 조각은 flush 때 기록.
- 로그 파일 기록 실패는 이번 실행에서 재시도하지 않고 ERROR 1건을 링버퍼에 남기며
  다음 log() 에서 1회 emit 한다(이미 열린 LogView 도 본다).

사용:
    self._log = AppLogManager().get_logger("CompoundRunWorker")
    self._log.tx("p:29...")
    self._log.rx("p:0029...")
    self._log.error("Read Compound Fail : TIMEOUT")
    self._log.info("Write Compound Success")
"""

import os
import sys
import threading
from collections import deque
from datetime import datetime, timedelta
from enum import Enum
from typing import NamedTuple

from PySide6.QtCore import QObject, Signal

from b_core.a_define import file_folder_path as path_def


class LogCategory(Enum):
    INFO = "INFO"
    WARN = "WARN"
    TX = "TX"
    RX = "RX"
    ERROR = "ERROR"


class LogEntry(NamedTuple):
    timestamp: datetime
    category: LogCategory
    source: str
    message: str
    is_global: bool = False  # True 면 모든 LogView 에 표시 (sources 필터 무시)

    def to_line(self) -> str:
        """파일/뷰 공용 한 줄 표기. (날짜는 파일명에 있으므로 시각만)"""
        time_str = self.timestamp.strftime("%H:%M:%S.%f")[:-3]
        return f"[{time_str}][{self.category.value:<5}][{self.source}] {self.message}"


class ScopedLogger:
    """source 를 고정한 편의 프록시. AppLogManager().get_logger() 로 얻는다."""

    __slots__ = ("_manager", "_source", "_is_global")

    def __init__(self, manager: "AppLogManager", source: str, is_global: bool = False):
        self._manager = manager
        self._source = source
        self._is_global = is_global

    def info(self, message: str) -> None:
        self._manager.log(LogCategory.INFO, self._source, message, self._is_global)

    def warning(self, message: str) -> None:
        self._manager.log(LogCategory.WARN, self._source, message, self._is_global)

    def tx(self, message: str) -> None:
        self._manager.log(LogCategory.TX, self._source, message, self._is_global)

    def rx(self, message: str) -> None:
        self._manager.log(LogCategory.RX, self._source, message, self._is_global)

    def error(self, message: str) -> None:
        self._manager.log(LogCategory.ERROR, self._source, message, self._is_global)


class AppLogManager(QObject):
    _instance = None
    _creation_lock = threading.Lock()

    sig_logged = Signal(object)  # LogEntry — 워커 스레드에서 emit 되어도 Qt 가 큐잉

    RETENTION_DAYS = 30   # 로그 파일 보존 기한
    RING_SIZE = 2000      # 실시간 뷰 백필용 최근 로그 개수
    FILE_PREFIX = "app_"

    def __new__(cls, *args, **kwargs):
        # 멀티스레드 환경에서 동시에 생성되는 것을 방지
        with cls._creation_lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        # 중복 초기화 방어
        if self._initialized:
            return

        super().__init__()

        self._initialized = True

        self._lock = threading.Lock()  # 파일/링버퍼 보호 (여러 스레드에서 log 호출됨)
        self._tls = threading.local()  # 스레드별 emit 재진입 깊이 (F007 — is_logging 참고)
        self._ring: deque[LogEntry] = deque(maxlen=self.RING_SIZE)
        self._file = None
        self._file_date = None
        self._file_failed = False      # 파일 기록 실패 → 이번 실행에서는 재시도하지 않는다 (F006)
        self._pending_notice = None    # 파일 실패 알림 — 다음 log() 가 락 밖에서 1회 emit (열린 LogView 용)

        self._cleanup_old_files()

    # ------------------------------------------------------------ 기록
    def get_logger(self, source: str, is_global: bool = False) -> ScopedLogger:
        """is_global=True: 전역 클래스용 — 모든 LogView 에 표시된다."""
        return ScopedLogger(self, source, is_global)

    def log(self, category: LogCategory, source: str, message: str, is_global: bool = False) -> None:
        entry = LogEntry(datetime.now(), category, str(source), str(message), is_global)
        self._record(entry)

        # 파일 기록 실패 알림(_write_file 이 링버퍼에만 넣어 둔 것)이 있으면 먼저 1회 emit —
        # 이미 열린 LogView 도 실시간으로 본다. 락 밖에서 emit 한다.
        with self._lock:
            notice, self._pending_notice = self._pending_notice, None
        if notice is not None:
            self._emit(notice)
        self._emit(entry)

    def _emit(self, entry: LogEntry) -> None:
        # 구독 슬롯이 예외를 내면 PySide6 가 traceback 을 sys.stderr(_StderrTee) 에 찍고,
        # 그 줄들이 다시 log() 로 들어와 같은 슬롯을 호출하는 재귀가 된다(F007, 스택 오버플로 실측).
        # emit 구간을 스레드별 깊이로 표시해 두면 _StderrTee 가 is_logging() 을 보고
        # 파일/링버퍼 기록만 하고 다시 emit 하지 않는다.
        # PySide6 6.10 기준 슬롯 예외는 emit 밖으로 전파되지 않는다(전파되는 버전이면
        # try 로 감싸 sys.__stderr__ 에 1줄 요약으로 전환).
        depth = getattr(self._tls, "depth", 0)
        self._tls.depth = depth + 1
        try:
            self.sig_logged.emit(entry)
        finally:
            self._tls.depth = depth

    def is_logging(self) -> bool:
        """이 스레드가 log() 의 emit 구간 안이면 True — stderr 후킹의 재진입 판정."""
        return getattr(self._tls, "depth", 0) > 0

    def _record(self, entry: LogEntry) -> None:
        """파일 + 링버퍼 + 콘솔 기록. emit 없음 (재진입 경로와 log() 가 공용)."""
        line = entry.to_line()
        with self._lock:
            self._write_file(entry)
            self._ring.append(entry)
        self._print_console(line)  # 락 밖 — stdout 이 후킹돼도 재진입 데드락 없음

    @staticmethod
    def _print_console(line: str) -> None:
        """콘솔 에코. 콘솔 인코딩(cp949 등)이 표현 못 하는 문자(—, 장비 응답의
        임의 바이트 등)는 '?' 로 바꿔 찍는다 — 로그 한 줄 때문에 호출측이
        UnicodeEncodeError 로 죽으면 안 된다. 콘솔이 없으면(--noconsole) 건너뛴다."""
        stream = sys.stdout
        if stream is None:
            return
        try:
            print(line, file=stream)
        except UnicodeEncodeError:
            encoding = getattr(stream, "encoding", None) or "utf-8"
            safe = line.encode(encoding, errors="replace").decode(encoding, errors="replace")
            print(safe, file=stream)
        except (OSError, ValueError):
            pass  # 닫힌 스트림 등 — 파일/링버퍼 기록은 이미 끝났다

    def snapshot(self, sources: set[str] | None = None) -> list[LogEntry]:
        """최근 로그(링버퍼) 복사본 반환 — 뷰 창이 열릴 때 백필용 (비파괴).

        sources 필터가 있어도 전역(is_global) 로그는 항상 포함된다."""
        with self._lock:
            entries = list(self._ring)

        if sources:
            entries = [e for e in entries if e.is_global or e.source in sources]
        return entries

    # ------------------------------------------------------------ stderr 후킹
    def install_stderr_hook(self) -> None:
        """stderr 출력을 ERROR 로그로 수집한다. 앱 시작 시 한 번 호출."""
        if not isinstance(sys.stderr, _StderrTee):
            sys.stderr = _StderrTee(sys.stderr, self)

    # ------------------------------------------------------------ 파일 IO
    def _write_file(self, entry: LogEntry) -> None:
        if self._file_failed:
            return  # 한 번 실패하면 이번 실행에서는 다시 시도하지 않는다 (알림은 아래에서 1회)

        try:
            date = entry.timestamp.date()

            # 자정이 지나면 다음 날짜 파일로 전환
            if self._file is None or date != self._file_date:
                if self._file is not None:
                    self._file.close()
                os.makedirs(path_def.LOG_PATH, exist_ok=True)
                file_path = os.path.join(path_def.LOG_PATH,
                                         f"{self.FILE_PREFIX}{date.isoformat()}.log")
                self._file = open(file_path, "a", encoding="utf-8")
                self._file_date = date

            # 크래시 직전 로그도 남도록 줄마다 flush
            self._file.write(entry.to_line() + "\n")
            self._file.flush()
        except Exception as e:
            # 파일 기록 실패가 앱 동작을 막으면 안 된다. --noconsole 배포에서도 보이도록
            # 링버퍼에 ERROR 항목을 직접 1회 남기고(LogView 백필로 표시; 자기 자신을 log() 하면 재귀),
            # 원본 stderr 에도 알린다. (호출자가 _lock 을 잡고 있으므로 링버퍼 접근은 안전)
            self._file_failed = True
            if self._file is not None:
                try:
                    self._file.close()
                except Exception:
                    pass
                self._file = None
            notice = LogEntry(datetime.now(), LogCategory.ERROR, "AppLogManager",
                              f"log file write failed: {e} (file logging disabled for this run)", True)
            self._ring.append(notice)
            self._pending_notice = notice  # 다음 log() 가 열린 LogView 에도 1회 emit
            if sys.__stderr__ is not None:
                sys.__stderr__.write(f"[AppLogManager] file write failed: {e}\n")

    def _cleanup_old_files(self) -> None:
        """보존 기한(RETENTION_DAYS)이 지난 로그 파일 삭제."""
        try:
            if not os.path.isdir(path_def.LOG_PATH):
                return

            limit_date = datetime.now().date() - timedelta(days=self.RETENTION_DAYS)

            for name in os.listdir(path_def.LOG_PATH):
                if not (name.startswith(self.FILE_PREFIX) and name.endswith(".log")):
                    continue
                try:
                    file_date = datetime.strptime(
                        name[len(self.FILE_PREFIX):-len(".log")], "%Y-%m-%d").date()
                except ValueError:
                    continue

                if file_date < limit_date:
                    try:
                        os.remove(os.path.join(path_def.LOG_PATH, name))
                    except OSError:
                        pass
        except Exception as e:
            if sys.__stderr__ is not None:
                sys.__stderr__.write(f"[AppLogManager] cleanup failed: {e}\n")


class _StderrTee:
    """stderr 를 원본으로 전달하면서 줄 단위로 ERROR 로그에 수집하는 래퍼.

    줄 조립 버퍼는 스레드별(threading.local)이다 — CPython 은 traceback 하나를 여러 번의
    write() 로 쪼개 쓰므로, 버퍼가 공용이면 그 사이에 끼어든 다른 스레드의 줄이 같은
    LogEntry 로 병합된다(실측). 스레드별이면 락 없이도 각 스레드의 줄이 따로 조립된다."""

    def __init__(self, original, manager: AppLogManager):
        self._original = original
        self._manager = manager
        self._tls = threading.local()

    def _take_lines(self, text: str) -> list[str]:
        """이 스레드의 버퍼에 text 를 붙이고 완성된 줄(공백 줄 제외)을 꺼낸다."""
        buf = getattr(self._tls, "buffer", "") + text
        lines = []
        while "\n" in buf:
            line, buf = buf.split("\n", 1)
            if line.strip():
                lines.append(line)
        self._tls.buffer = buf
        return lines

    def write(self, text: str) -> int:
        if self._original is not None:
            try:
                self._original.write(text)
            except Exception:
                pass

        for line in self._take_lines(text):
            # 미처리 예외는 어느 윈도우에서든 보여야 하므로 전역 로그
            if self._manager.is_logging():
                # log() → emit → 슬롯 예외 → traceback 이 여기로 온 경우:
                # 파일/링버퍼에는 남기되 다시 emit 하지 않는다 (F007 재귀 차단)
                self._manager._record(LogEntry(datetime.now(), LogCategory.ERROR, "stderr", line, True))
            else:
                self._manager.log(LogCategory.ERROR, "stderr", line, is_global=True)
        return len(text)

    def flush(self) -> None:
        # 자기 스레드의 남은 조각만 (종료 시 다른 스레드의 조각은 포기 — 어차피 종료 직전)
        rest = getattr(self._tls, "buffer", "")
        self._tls.buffer = ""
        if rest.strip():
            # 개행 없이 끝난 조각(종료 직전 출력 등)도 버리지 않는다 — emit 없이 기록만
            self._manager._record(LogEntry(datetime.now(), LogCategory.ERROR, "stderr", rest, True))

        if self._original is not None:
            try:
                self._original.flush()
            except Exception:
                pass
