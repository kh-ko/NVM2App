"""앱 업데이트 워커 (ver1 HelpNvmUpdateWin 의 VersionLoadWorker / FileDownloadWorker 대응).

FirmwareRunWorker 와 같은 외부 인터페이스 [AppUpdateRunWorker(QObject) + 작업별
QThread] — start_* / abort / cleanup, aboutToQuit·destroyed 정리. 윈도우는
래퍼의 시그널에만 연결한다.

ver1 에서 달라진 점:
- 다운로드 뒤 압축 해제도 스레드에서 한다 (ver1 은 UI 스레드에서 extractall).
  결과는 교체 원본 폴더(exe 가 있는 폴더) 경로 — 설치 스크립트 기동은 윈도우가
  app_update_helper.launch_installer() 로 한다 (앱 종료 결정은 UI 몫).
- 취소는 "CANCELED" 문자열 비교 대신 (ok=False, ABORT_MESSAGE) 로 통일.
- 로그는 sig_log 로 넘기고 래퍼가 AppLogManager 에 기록한다
  (log_source 에 담당 윈도우 이름을 넘기면 그 창의 LogView 에 보인다).
"""

from PySide6.QtCore import QCoreApplication, QObject, QThread, Signal

from b_core.c_manager.app_log_manager import AppLogManager
from b_core.f_helper import app_update_helper

ABORT_MESSAGE = "Aborted by user."


class _AppUpdateThreadBase(QThread):
    sig_log = Signal(bool, str)  # is_err, message

    def __init__(self, parent=None):
        super().__init__(parent)
        self._abort = False

    def abort(self):
        self._abort = True

    @property
    def is_aborted(self) -> bool:
        return self._abort

    def _check_abort(self):
        if self._abort:
            raise RuntimeError(ABORT_MESSAGE)


class ReleaseNotesThread(_AppUpdateThreadBase):
    """FTP version_info.txt 조회 + 파싱 1회."""

    sig_release_notes_finished = Signal(bool, list, str)  # ok, notes(list[ReleaseNote]), message

    def run(self):
        try:
            setting = app_update_helper.load_setting()
            self.sig_log.emit(False, f"[FTP] fetching release notes from {setting.host}:{setting.port}{setting.path}")
            notes = app_update_helper.fetch_release_notes(setting)
            self.sig_log.emit(False, f"[FTP] {len(notes)} release(s): {', '.join(n.version for n in notes)}")
            self.sig_release_notes_finished.emit(True, notes, "")
        except Exception as e:
            self.sig_log.emit(True, f"[FTP] release notes failed: {e}")
            self.sig_release_notes_finished.emit(False, [], f"Failed to fetch the release notes from FTP:\n{e}")


class PackagePrepareThread(_AppUpdateThreadBase):
    """배포 zip 다운로드 -> 압축 해제 1회. 결과는 교체 원본 폴더 경로."""

    sig_prepare_progress = Signal(int, int)       # done, total (total=0 이면 미상)
    sig_prepare_finished = Signal(bool, str, str)  # ok, package_root, message

    def __init__(self, version: str, parent=None):
        super().__init__(parent)
        self._version = version

    def run(self):
        version = self._version
        try:
            setting = app_update_helper.load_setting()
            remote = app_update_helper.remote_package_path(setting, version)
            self.sig_log.emit(False, f"[FTP] {setting.host}:{setting.port} <- {remote}")

            def on_progress(done: int, total: int):
                self._check_abort()  # 콜백에서 던진 예외는 retrbinary 를 뚫고 올라온다
                self.sig_prepare_progress.emit(done, total)

            self.sig_prepare_progress.emit(0, 0)
            zip_path = app_update_helper.download_package(setting, version, on_progress)
            self.sig_log.emit(False, f"[FTP] downloaded -> {zip_path}")

            self._check_abort()
            package_root = app_update_helper.extract_package(zip_path, version)
            self.sig_log.emit(False, f"[Extract] package root -> {package_root}")

            self.sig_prepare_finished.emit(True, package_root, "")

        except Exception as e:
            if self.is_aborted:
                self.sig_log.emit(True, f"[Aborted] {version}")
                self.sig_prepare_finished.emit(False, "", ABORT_MESSAGE)
            else:
                self.sig_log.emit(True, f"[Failed] {version} : {e}")
                self.sig_prepare_finished.emit(False, "", f"Failed to prepare the update package '{version}':\n{e}")


class AppUpdateRunWorker(QObject):
    """앱 업데이트 워커의 외부 인터페이스. 한 번에 하나의 작업(릴리스 노트 조회
    또는 패키지 준비)만 수행하며, 진행 중이면 start_* 가 False 를 반환한다.

    사용 예 (윈도우):
        worker = AppUpdateRunWorker(self, log_source=self.win_name)
        worker.sig_release_notes_finished.connect(self.handle_release_notes_finished)
        worker.sig_prepare_progress.connect(self.handle_prepare_progress)
        worker.sig_prepare_finished.connect(self.handle_prepare_finished)
        worker.start_release_notes()
        worker.start_prepare("20260616-v0.0.2")
        worker.abort()      # 실행 중 작업 중단 요청 -> sig_prepare_finished(False, "", ABORT_MESSAGE)
        worker.cleanup()    # 창 closeEvent 에서 — 중단 + 스레드 종료 대기
    """

    sig_release_notes_finished = Signal(bool, list, str)  # ok, notes, message
    sig_prepare_progress = Signal(int, int)               # done, total
    sig_prepare_finished = Signal(bool, str, str)          # ok, package_root, message

    def __init__(self, parent=None, log_source: str = "AppUpdateRunWorker"):
        super().__init__(parent)
        self._log = AppLogManager().get_logger(log_source)
        self._thread: _AppUpdateThreadBase | None = None
        self._is_cleaned = False

        app = QCoreApplication.instance()
        if app is not None:
            app.aboutToQuit.connect(self.cleanup)
        self.destroyed.connect(self.cleanup)

    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.isRunning()

    # ------------------------------------------------------------ 작업 시작
    def start_release_notes(self) -> bool:
        if self.is_running:
            return False

        thread = ReleaseNotesThread(self)
        thread.sig_release_notes_finished.connect(self.sig_release_notes_finished)
        self._replace_thread(thread)
        thread.start()
        return True

    def start_prepare(self, version: str) -> bool:
        if self.is_running:
            return False

        thread = PackagePrepareThread(version, self)
        thread.sig_prepare_progress.connect(self.sig_prepare_progress)
        thread.sig_prepare_finished.connect(self.sig_prepare_finished)
        self._replace_thread(thread)
        self._log.info(f"[Start] prepare update package: {version}")
        thread.start()
        return True

    def abort(self):
        """실행 중 작업 중단 요청. 다운로드 중이면 다음 수신 블록에서,
        접속 대기 중이면 접속 타임아웃 안에 (False, "", ABORT_MESSAGE) 로 끝난다."""
        if self.is_running:
            self._log.warning("[Abort] requested")
            self._thread.abort()

    # ------------------------------------------------------------ 내부
    def _replace_thread(self, thread: _AppUpdateThreadBase):
        old = self._thread
        if old is not None:
            old.blockSignals(True)
            old.deleteLater()

        thread.sig_log.connect(self._handle_log)
        self._thread = thread

    def _handle_log(self, is_err: bool, msg: str):
        if is_err:
            self._log.error(msg)
        else:
            self._log.info(msg)

    # ------------------------------------------------------------ 종료
    def cleanup(self):
        """중단 요청 후 스레드 종료를 기다린다 (최대 접속 타임아웃 안팎 블로킹).
        창 closeEvent 에서 반드시 호출한다 — 실행 중 QThread 가 파괴되면 앱 전체가
        abort 된다 (ParameterRunWorker 와 같은 이유)."""
        if self._is_cleaned:
            return
        self._is_cleaned = True

        app = QCoreApplication.instance()
        if app is not None:
            try:
                app.aboutToQuit.disconnect(self.cleanup)
            except (TypeError, RuntimeError):
                pass

        if self._thread is not None:
            self._thread.blockSignals(True)
            if self._thread.isRunning():
                self._thread.abort()
                self._thread.wait()
            self._thread = None
