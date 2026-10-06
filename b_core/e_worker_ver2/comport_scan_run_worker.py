"""COM 포트 스캔 워커.

ver2 변경: 워커가 직접 띄우던 대기 QMessageBox 를 제거 — 워커는
sig_wait_started(title, message) / sig_wait_finished 시그널만 내고,
표시는 윈도우가 담당한다. (c_window_ver2/x_message/wait_message_box.py 참고)
"""

import serial.tools.list_ports

from PySide6.QtCore import QThread, Signal, QObject, QCoreApplication, Qt

from b_core.c_manager.app_log_manager import AppLogManager
from b_core.d_dal.serial_setting import SerialSetting, probe_once
from b_core.d_dal.service_port import ServicePort

SCAN_PACKET = "i:83"  # 장비 식별 요청 (ver1 과 같은 SN 읽기 요청) — 응답 유무·내용만 표시한다

class PortScanThread(QThread):
    """PC 의 COM 포트를 나열하고, 포트마다 선택된 통신 설정으로 1왕복(probe_once) 해 본다.
    (UI 프리징 방지를 위한 백그라운드 스레드)"""
    ports_found = Signal(list)
    port_checked = Signal(str, bool, str)  # port_name, success, read_data

    def __init__(self, used_service_port_name, setting: SerialSetting, parent=None):
        super().__init__(parent)
        self.used_service_port_name = used_service_port_name if used_service_port_name is not None else ""
        self.setting = setting  # port_name 은 포트마다 바꿔 쓴다
        self._log = AppLogManager().get_logger("ComportScan", is_global=True)
        self._is_running = True

    def stop(self):
        self._is_running = False

    def run(self):
        # 1. PC에서 사용 가능한 COM Port 검색
        available_ports = serial.tools.list_ports.comports()
        port_names = [port.device for port in available_ports]
        self.ports_found.emit(port_names)

        for port_name in port_names:
            if not self._is_running:
                break

            if port_name == self.used_service_port_name:
                self.port_checked.emit(port_name, False, "Used by NVM2App")
                continue

            try:
                # 열기 > 식별 요청 + 설정 종료문자 전송 > 종료문자까지 읽기(100ms) > 닫기
                response = probe_once(self.setting._replace(port_name=port_name), SCAN_PACKET, timeout=0.1)
            except Exception as e:
                # 다른 프로그램이 사용 중, 권한 없음, 쓰기 타임아웃 등 — 원인은 로그로 (N034)
                self._log.warning(f"{port_name}: {type(e).__name__}: {e}")
                self.port_checked.emit(port_name, False, "")
                continue

            # 예외가 없으면 응답 유무와 무관하게 통신 가능으로 본다 (ver1 과 같은 기준)
            self.port_checked.emit(port_name, True, response.decode("utf-8", errors="ignore").strip())

class ComportScanRunWorker(QObject):
    # 이전 스캔 종료를 기다리는 동안 윈도우가 대기 표시를 띄우고/내리게 한다
    sig_wait_started = Signal(str, str)  # title, message
    sig_wait_finished = Signal()

    def __init__(self, port_found_slot, port_checked_slot, scan_stopped_slot, parent=None):
        super().__init__(parent)
        self._thread = None
        self._next_setting = None
        self.port_found_slot = port_found_slot
        self.port_checked_slot = port_checked_slot
        self.scan_stopped_slot = scan_stopped_slot
        self._is_cleaned = False

        app = QCoreApplication.instance()
        if app is not None:
            app.aboutToQuit.connect(self.cleanup)

        self.destroyed.connect(self.cleanup)

    def start(self, setting: SerialSetting):
        """setting 의 통신 설정으로 스캔 시작 (port_name 은 무시 — 포트마다 바꿔 쓴다).
        스캔 중이면 끝나기를 기다렸다가 시작한다."""
        self._next_setting = setting
        if self._thread is not None and self._thread.isRunning():
            self._stop_thread("Preparing to scan...", "Please wait for the previous scan to complete...", self._start_thread)
            return 

        self._start_thread()

    def _stop_thread(self, title, message, finished_slot):
        self.sig_wait_started.emit(title, message)

        try:
            self._thread.ports_found.disconnect()
            self._thread.port_checked.disconnect()
        except Exception:
            pass

        self._thread.finished.connect(finished_slot, type=Qt.UniqueConnection)
        self._thread.stop()

    def _start_thread(self):
        self._clean_thread()
        if hasattr(self, '_next_setting'):
            self._thread = PortScanThread(ServicePort().get_port_name(), self._next_setting, parent=self)
            self._thread.ports_found.connect(self.port_found_slot)
            self._thread.port_checked.connect(self.port_checked_slot)
            self._thread.start()          

    def stop(self) -> bool:
        if self._thread is not None and self._thread.isRunning():
            self._stop_thread("Closing", "Please wait for the previous scan to complete...", self._stopped_thread)
            return False
        
        return True

    def _stopped_thread(self):
        self._clean_thread()
        self.scan_stopped_slot()

    def _clean_thread(self):
        # 대기 표시 중이 아니어도 발화될 수 있다 — 윈도우 쪽에서 None 가드
        self.sig_wait_finished.emit()

        if self._thread:
            self._thread.blockSignals(True)
            self._thread.deleteLater()
            self._thread = None            

    def cleanup(self):
        """스레드 종료 + aboutToQuit 연결 해제. 멱등 — aboutToQuit / destroyed 양쪽에서 불린다
        (F095: 워커 공통 종료 API 이름, ParameterRunWorker 와 동일)."""
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
                self._thread.stop()
                self._thread.wait()
            self._thread = None
    