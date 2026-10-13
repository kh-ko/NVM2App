"""COM 포트 스캔 워커 — PortScanThread(스캔 스레드) + ComportScanRunWorker(QObject 래퍼).

창은 래퍼의 시그널에만 바운드 메서드로 1:1 연결한다 (다른 래퍼 Firmware/AppUpdate/Compound 와 같은 모양):
    sig_ports_found(list)            스캔 시작 직후 포트 이름 목록
    sig_port_checked(str, bool, str) 포트마다 (port_name, success, read_data)
    sig_scan_stopped()               stop() 이 False 를 돌려준 뒤 스캔이 실제로 끝났을 때 1회 (그 전에 start() 가 오면
                                     중지 알림은 취소되고 새 스캔이 시작된다 — 끝난 뒤 할 일은 하나, 마지막 요청 우선)
    sig_wait_started(title, message) 이전 스캔 종료를 기다리기 시작할 때 — 대기 표시는 창이 담당
                                     (c_window_ver2/x_message/wait_message_box.py)
    sig_wait_finished()              스레드를 치울 때마다(첫 start 포함) — 창은 표시 중일 때만 닫는다 (None 가드)
스레드 시그널은 래퍼 시그널로 전달(signal-to-signal)된다. 래퍼는 창의 자식(메인 스레드)이라 창 슬롯은 메인 스레드에서
실행된다 — 이전의 '스레드 시그널 → 창 슬롯 직접 연결' 과 배달 순서·스레드가 같다 (2026-10-13 실측).
"""

import serial.tools.list_ports

from PySide6.QtCore import QThread, Signal, QObject, QCoreApplication

from b_core.c_manager.app_log_manager import AppLogManager
from b_core.d_dal.serial_setting import SerialSetting, probe_once
from b_core.d_dal.service_port import ServicePort

SCAN_PACKET = "i:83"  # 장비 식별(SN 읽기) 요청 — 응답 유무·내용만 표시한다

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

            # 예외가 없으면 응답 유무와 무관하게 통신 가능으로 본다
            self.port_checked.emit(port_name, True, response.decode("utf-8", errors="ignore").strip())

class ComportScanRunWorker(QObject):
    sig_ports_found = Signal(list)
    sig_port_checked = Signal(str, bool, str)  # port_name, success, read_data
    sig_scan_stopped = Signal()
    # 이전 스캔 종료를 기다리는 동안 윈도우가 대기 표시를 띄우고/내리게 한다
    sig_wait_started = Signal(str, str)  # title, message
    sig_wait_finished = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._thread = None
        self._next_setting = None
        self._on_finished = None  # 스캔 스레드가 끝나면 할 일(_start_thread / _stopped_thread) — 중지 요청 때 기록 (N035)
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

    def _stop_thread(self, title, message, on_finished):
        """실행 중인 스캔에 중지를 요청하고, 끝나면 on_finished 를 수행하도록 기록한다.

        finished 는 스레드를 만들 때 이미 연결돼 있다 — 호출측의 isRunning() 검사와 이 호출 사이에
        스레드가 먼저 끝나 finished 가 큐에 들어가 있어도 _handle_thread_finished 가 기록된 on_finished 를
        수행하므로 놓치지 않는다 (N035: 놓치면 대기 박스가 영구히 남아 앱이 고착됐다).
        결과 시그널의 전달 연결은 여기서 끊는다 — 끊은 뒤 옛 스캔이 내는 결과가 대기 표시 중인 목록을 더 갱신하지 않게.
        끊기 전에 큐에 들어간 결과는 그대로 도달하고, 옛 결과는 같은 큐에서 finished 보다 먼저 처리되므로 새 스캔의
        목록을 덮어쓰는 일은 없다 (blockSignals 로 바꾸면 finished 까지 막혀 N035 가 재발한다)."""
        self._on_finished = on_finished
        self.sig_wait_started.emit(title, message)

        try:
            self._thread.ports_found.disconnect()
            self._thread.port_checked.disconnect()
        except Exception:
            pass

        self._thread.stop()

    def _start_thread(self):
        self._clean_thread()
        self._thread = PortScanThread(ServicePort().get_port_name(), self._next_setting, parent=self)
        self._thread.ports_found.connect(self.sig_ports_found)      # 스레드 → 래퍼 시그널 전달
        self._thread.port_checked.connect(self.sig_port_checked)
        self._thread.finished.connect(self._handle_thread_finished)  # 시작 전에 — 종료를 놓치지 않는다 (N035)
        self._thread.start()

    def _handle_thread_finished(self):
        if self.sender() is not self._thread:
            return  # _clean_thread 로 교체된 옛 스레드의 늦은 finished
        on_finished, self._on_finished = self._on_finished, None
        if on_finished is not None:
            on_finished()

    def stop(self) -> bool:
        """True = 스캔 중이 아니라 즉시 끝남. False = 중지를 요청했고, 끝나면 sig_scan_stopped 를 1회 낸다
        (끝나기 전에 start() 가 오면 중지 알림은 취소되고 새 스캔이 시작된다 — 마지막 요청 우선)."""
        if self._thread is not None and self._thread.isRunning():
            self._stop_thread("Closing", "Please wait for the previous scan to complete...", self._stopped_thread)
            return False
        
        return True

    def _stopped_thread(self):
        self._clean_thread()
        self.sig_scan_stopped.emit()

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
    