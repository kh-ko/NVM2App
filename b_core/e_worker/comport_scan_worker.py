from PySide6.QtCore import QThread, Signal, QIODevice, QElapsedTimer
from PySide6.QtSerialPort import QSerialPort, QSerialPortInfo

class PortScanThread(QThread):
    """
    UI 프리징을 방지하기 위해 백그라운드에서 사용 가능한 COM Port를 검색하고,
    각 Port에 순차적으로 연결하여 데이터를 읽어오는 Thread 클래스입니다.
    """
    ports_found = Signal(list)
    port_checked = Signal(str, bool, str)  # port_name, success, read_data

    def __init__(self, used_service_port_name, connection_setting):
        super().__init__()
        term_map_bytes = {0: b"\r\n", 1: b"\n", 2: b"\r"}

        self.used_service_port_name = used_service_port_name if used_service_port_name is not None else ""
        self.setting = connection_setting
        self._termination_chars = term_map_bytes.get(self.setting.get("termination", 0), b"\r\n")
        self._timer = QElapsedTimer()
        self._is_running = True

    def stop(self):
        self._is_running = False

    def run(self):
        # 1. PC에서 사용 가능한 COM Port 검색
        available_ports = QSerialPortInfo.availablePorts()
        port_names = [port.portName() for port in available_ports]
        self.ports_found.emit(port_names)

        # 2. 각 포트 순차 점검
        for port_name in port_names:
            if not self._is_running:
                break

            if port_name == self.used_service_port_name:
                self.port_checked.emit(port_name, False, "Used by NVM2App")
                continue

            serial = QSerialPort()
            serial.setPortName(port_name)

            # JSON 설정 값 맵핑
            serial.setBaudRate(self.setting.get("baudrate", 38400))
            serial.setDataBits(QSerialPort.DataBits(self.setting.get("dataBits", 7)))
            serial.setParity(QSerialPort.Parity(self.setting.get("parity", 2)))
            
            stop_bits = self.setting.get("stopBits", 1)
            if stop_bits == 1:
                serial.setStopBits(QSerialPort.OneStop)
            elif stop_bits == 2:
                serial.setStopBits(QSerialPort.TwoStop)
            elif stop_bits == 3:
                serial.setStopBits(QSerialPort.OneAndHalfStop)

            # Open > Send > Read > Close
            if serial.open(QIODevice.ReadWrite):
                serial.write(b"i:83\r\n")
                response_data = ""
                
                # 데이터 전송 및 수신 대기 (timeout 설정으로 무한 대기 방지)
                if serial.waitForBytesWritten(100):
                    buffer = bytearray()
                    self._timer.start() # 타이머 측정 시작
                    
                    while self._is_running:
                        elapsed = self._timer.elapsed()
                        remaining_ms = 100 - elapsed
                        
                        if remaining_ms <= 0:
                            break
                            
                        if serial.waitForReadyRead(remaining_ms):
                            buffer.extend(serial.readAll().data())
                            
                            if self._termination_chars in buffer:
                                break
                        else:
                            break
                    
                    response_data = buffer.decode('utf-8', errors='ignore').strip()
                
                serial.close()
                self.port_checked.emit(port_name, True, response_data)
            else:
                self.port_checked.emit(port_name, False, "")