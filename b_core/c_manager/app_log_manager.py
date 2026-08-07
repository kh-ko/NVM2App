"""앱 로그 시스템.

기존 c_manager/log_manager.py(LogManager) 와는 별개의 새 시스템이다.

- 모든 로그를 하루 1파일(logs/app_YYYY-MM-DD.log)로 저장한다. 보존 30일
  (시작 시 기한 지난 파일 자동 삭제). 배포 후 문제 발생 시
  "로그 폴더를 보내주세요" 워크플로우를 지원한다.
- 레벨 없음. 대신 카테고리(INFO / TX / RX / ERROR)로 분류하며
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
        self._ring: deque[LogEntry] = deque(maxlen=self.RING_SIZE)
        self._file = None
        self._file_date = None

        self._cleanup_old_files()

    # ------------------------------------------------------------ 기록
    def get_logger(self, source: str, is_global: bool = False) -> ScopedLogger:
        """is_global=True: 전역 클래스용 — 모든 LogView 에 표시된다."""
        return ScopedLogger(self, source, is_global)

    def log(self, category: LogCategory, source: str, message: str, is_global: bool = False) -> None:
        entry = LogEntry(datetime.now(), category, str(source), str(message), is_global)

        with self._lock:
            self._write_file(entry)
            self._ring.append(entry)
            print(entry.to_line())

        self.sig_logged.emit(entry)

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
            # 파일 기록 실패가 앱 동작을 막으면 안 된다.
            # (자기 자신을 다시 log 하면 재귀가 되므로 원본 stderr 로만 알림)
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
    """stderr 를 원본으로 전달하면서 줄 단위로 ERROR 로그에 수집하는 래퍼."""

    def __init__(self, original, manager: AppLogManager):
        self._original = original
        self._manager = manager
        self._buffer = ""

    def write(self, text: str) -> int:
        if self._original is not None:
            try:
                self._original.write(text)
            except Exception:
                pass

        self._buffer += text
        while "\n" in self._buffer:
            line, self._buffer = self._buffer.split("\n", 1)
            if line.strip():
                # 미처리 예외는 어느 윈도우에서든 보여야 하므로 전역 로그
                self._manager.log(LogCategory.ERROR, "stderr", line, is_global=True)
        return len(text)

    def flush(self) -> None:
        if self._original is not None:
            try:
                self._original.flush()
            except Exception:
                pass
