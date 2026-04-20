import serial
import serial.tools.list_ports

from PySide6.QtCore import QThread, Signal, QObject, QCoreApplication, Qt
from PySide6.QtWidgets import QMessageBox

from b_core.d_dal.service_port import ServicePort

class PortScanThread(QThread):
    """
    UI 프리징을 방지하기 위해 백그라운드에서 사용 가능한 COM Port를 검색하고,
    각 Port에 순차적으로 연결하여 데이터를 읽어오는 Thread 클래스입니다.
    """
    ports_found = Signal(list)
    port_checked = Signal(str, bool, str)  # port_name, success, read_data

    def __init__(self, used_service_port_name, connection_setting, parent=None):
        super().__init__(parent)
        term_map_bytes = {0: b"\r\n", 1: b"\n", 2: b"\r"}

        self.used_service_port_name = used_service_port_name if used_service_port_name is not None else ""
        self.setting = connection_setting
        self._termination_chars = term_map_bytes.get(self.setting.get("termination", 0), b"\r\n")
        self._is_running = True

    def stop(self):
        self._is_running = False

    def run(self):
        # 1. PC에서 사용 가능한 COM Port 검색
        available_ports = serial.tools.list_ports.comports()
        port_names = [port.device for port in available_ports]
        self.ports_found.emit(port_names)

        parity_map = {0: serial.PARITY_NONE, 2: serial.PARITY_EVEN, 3: serial.PARITY_ODD, 4: serial.PARITY_SPACE, 5: serial.PARITY_MARK}
        stop_map = {1: serial.STOPBITS_ONE, 2: serial.STOPBITS_TWO, 3: serial.STOPBITS_ONE_POINT_FIVE}

        baudrate = self.setting.get("baudrate", 38400)
        data_bits = self.setting.get("dataBits", 7)
        parity = parity_map.get(self.setting.get("parity", 2), serial.PARITY_EVEN)
        stop_bits = stop_map.get(self.setting.get("stopBits", 1), serial.STOPBITS_ONE)

        for port_name in port_names:
            if not self._is_running:
                break

            if port_name == self.used_service_port_name:
                self.port_checked.emit(port_name, False, "Used by NVM2App")
                continue

            try:
                # Open: pyserial은 생성과 동시에 포트가 열립니다. (with 문으로 자동 Close 처리)
                with serial.Serial(
                    port=port_name,
                    baudrate=baudrate,
                    bytesize=data_bits,
                    parity=parity,
                    stopbits=stop_bits,
                    timeout=0.1  # 읽기 타임아웃 100ms 설정
                ) as ser:

                    # Send
                    ser.write(b"i:83\r\n")
                    ser.flush()  # 전송 완료 대기 (waitForBytesWritten 대체)

                    # Read: 종료 문자열이 오거나 100ms 타임아웃이 발생할 때까지 대기
                    buffer = ser.read_until(self._termination_chars)
                    
                    # 수신된 데이터가 있으면 디코딩, 없으면 빈 문자열
                    response_data = buffer.decode('utf-8', errors='ignore').strip() if buffer else ""

                    # 응답 데이터가 있으면 성공, 없으면 실패로 간주할 수도 있습니다.
                    # 여기서는 기존 로직을 따라 예외가 나지 않으면 응답 데이터 유무와 상관없이 정상 통신으로 처리했습니다.
                    self.port_checked.emit(port_name, True, response_data)

            except serial.SerialException:
                # 포트가 이미 다른 프로그램에 의해 사용 중이거나, 권한이 없거나, 열 수 없는 경우
                self.port_checked.emit(port_name, False, "")
            except Exception:
                # 기타 알 수 없는 에러
                self.port_checked.emit(port_name, False, "")

class ComportScanRunWorker(QObject):
    def __init__(self, port_found_slot, port_checked_slot, scan_stopped_slot, parent=None):
        super().__init__(parent)
        self._thread = None
        self._next_setting = None
        self.port_found_slot = port_found_slot
        self.port_checked_slot = port_checked_slot
        self.scan_stopped_slot = scan_stopped_slot
        self.wait_msg_box = None

        app = QCoreApplication.instance()
        if app is not None:
            app.aboutToQuit.connect(self._destroyed)

        self.destroyed.connect(self._destroyed)

    def start(self, connection_setting):
        self._next_setting = connection_setting
        if self._thread is not None and self._thread.isRunning():
            self._stop_thread("Preparing to scan...", "Please wait for the previous scan to complete...", self._start_thread)
            return 

        self._start_thread()

    def _stop_thread(self, title, message, finished_slot):
        self.wait_msg_box = QMessageBox(self.parent())
        self.wait_msg_box.setWindowTitle(title)
        self.wait_msg_box.setText(message)
        self.wait_msg_box.setStandardButtons(QMessageBox.StandardButton.NoButton)
        self.wait_msg_box.setWindowModality(Qt.WindowModality.WindowModal)
        self.wait_msg_box.show()

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
        if hasattr(self, 'wait_msg_box') and self.wait_msg_box:
            self.wait_msg_box.accept()
            self.wait_msg_box = None
            
        if self._thread:
            self._thread.blockSignals(True)
            self._thread.deleteLater()
            self._thread = None            

    def _destroyed(self):
        app = QCoreApplication.instance()
        if app is not None:
            try:
                app.aboutToQuit.disconnect(self._destroyed)
            except (TypeError, RuntimeError):
                pass

        if self._thread is not None:
            self._thread.blockSignals(True)
            if self._thread.isRunning():
                self._thread.stop()
                self._thread.wait()
                
            self._thread = None           
    