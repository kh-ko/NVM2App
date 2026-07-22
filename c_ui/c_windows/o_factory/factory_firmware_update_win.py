from PySide6.QtGui import QColor
from PySide6.QtWidgets import QListView
from PySide6.QtCore import QAbstractListModel
from b_core.e_worker.firmware_write_worker import FirmwarePhase
from PySide6.QtCore import Signal
from PySide6.QtWidgets import QProgressBar
from b_core.c_manager.parameter_manager import ParamManager
import ftplib
import os
import io
import serial
import serial.tools.list_ports

from PySide6.QtWidgets import QVBoxLayout, QHBoxLayout, QLabel, QMessageBox, QDialog, QFrame
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPixmap

from b_core.a_define.file_folder_path import ASSET_RS232_IMG_FILE, ASSET_USB_IMG_FILE, ASSET_FU_GUIDE_1_IMG_FILE, ASSET_FU_GUIDE_2_IMG_FILE, ASSET_FU_GUIDE_3_IMG_FILE, ASSET_FU_GUIDE_4_IMG_FILE, ASSET_FU_GUIDE_5_IMG_FILE, RSRC_TEMP_PATH, RSRC_KERNEL_CPU1_FILE, RSRC_KERNEL_CPU2_FILE, RSRC_APP_CPU1_FILE, RSRC_APP_CPU2_FILE, RSRC_APP_CPU1_NEW_FILE, RSRC_APP_CPU2_NEW_FILE
from b_core.b_datatype.general_enum import LogType
from b_core.d_dal.service_port import ServicePort
from b_core.e_worker.firmware_write_worker import FirmwareWriterWorker

from c_ui.b_control_packet.base.base_combobox import BaseComboBox
from c_ui.b_control_packet.controls.my_value_label_check import MyValueLabelCheck
from c_ui.b_control_packet.base.base_button import BaseButton
from c_ui.b_control_packet.controls.my_label import MyLabel
from c_ui.b_control_packet.controls.my_consolelist import MyConsoleList
from c_ui.b_control_packet.param_container.param_setting_win import ParamSettingWin


AUTOBAUD_CHAR   = 0x41        # 'A' : 부트ROM 오토보 감지용 문자
SCI8_KEY        = (0xAA, 0x08)  # SCI 8bit 부트 스트림 키값(0x08AA, LSB 우선)
ECHO_TIMEOUT_S  = 2.0         # 바이트 에코 대기 타임아웃
AUTOBAUD_RETRY  = 10          # 오토보 재시도 횟수
        
class SelectNetworkFirmwareDialog(QDialog):
    FTP_HOST = "121.175.173.236"
    FTP_PORT = 10021
    FTP_USER = "novasen"
    FTP_PASS = "nova1002"
    FTP_PATH = "/HDD1/FIRMWARE/VALVE/BASIC"
    VERSION_FILE = "version.txt"

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Select Network Firmware Version")
        self.setFixedSize(520, 350)
        self.selected_version = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        self.lbl_guide_text = MyLabel("Select firmware version from network repository", self)
        self.lbl_guide_text.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.lbl_guide_text.setWordWrap(True)
        layout.addWidget(self.lbl_guide_text)

        self.version_combo = BaseComboBox(self)
        layout.addWidget(self.version_combo)
        layout.addStretch()

        btn_layout = QHBoxLayout()
        btn_ok = BaseButton("OK", self)
        btn_ok.setFixedWidth(100)
        btn_ok.clicked.connect(self.on_select)

        btn_cancel = BaseButton("Cancel", self)
        btn_cancel.setFixedWidth(100)
        btn_cancel.clicked.connect(self.reject)

        btn_layout.addStretch()
        btn_layout.addWidget(btn_ok)
        btn_layout.setSpacing(10)
        btn_layout.addWidget(btn_cancel)
        btn_layout.addStretch()

        layout.addLayout(btn_layout)

        QTimer.singleShot(0, self.load_versions)


    def load_versions(self):
        try:
            ftp = ftplib.FTP()
            ftp.connect(self.FTP_HOST, self.FTP_PORT, timeout=10)
            ftp.login(self.FTP_USER, self.FTP_PASS)
            ftp.cwd(self.FTP_PATH)

            buffer = io.BytesIO()
            ftp.retrbinary(f"RETR {self.VERSION_FILE}", buffer.write)
            ftp.quit()

            buffer.seek(0)
            lines = buffer.getvalue().decode('utf-8', errors='ignore').splitlines()

            versions = [line.strip() for line in lines if line.strip()]

            if not versions:
                QMessageBox.warning(self, "Warning", "No firmware version list found on the server.")
                self.accept()
                return

            for ver in versions:
                self.version_combo.addItem(ver, ver)

        except Exception as e:
            QMessageBox.critical(self, "FTP Error", f"Failed to fetch firmware versions from FTP:\n{str(e)}")
            self.accept()

    def on_select(self):
        self.selected_version = self.version_combo.currentData(role=Qt.UserRole)
        if not self.selected_version:
            self.selected_version = self.version_combo.currentText()
        self.accept()

class SelectPortDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Select COM Port")
        self.setFixedSize(520, 350)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        self.lbl_guide_text = MyLabel("Select the COM port connected to the valve", self)
        self.lbl_guide_text.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.lbl_guide_text.setWordWrap(True)
        layout.addWidget(self.lbl_guide_text)

        used_svc_port = ServicePort().get_port_name()
        self.port_combo = BaseComboBox(self)

        if used_svc_port:
            self.port_combo.addItem(f"Connected Port : {used_svc_port}", used_svc_port)

        available_ports = serial.tools.list_ports.comports()
        port_names = [port.device for port in available_ports]

        for port_name in port_names :
            if port_name != used_svc_port:
                self.port_combo.addItem(port_name, port_name)

        layout.addWidget(self.port_combo)
        layout.addStretch()

        # 3. 하단 OK 버튼
        btn_layout = QHBoxLayout()
        self.select_port = None

        btn_ok = BaseButton("OK", self)
        btn_ok.setFixedWidth(100)
        btn_ok.clicked.connect(self.on_select)
        btn_ok.clicked.connect(self.accept)

        btn_layout.addStretch()
        btn_layout.addWidget(btn_ok)
        btn_layout.addStretch()

        layout.addLayout(btn_layout)

    def on_select(self):
        self.select_port = self.port_combo.currentData(role = Qt.UserRole)
        self.accept()

class GuideDialog(QDialog):
    def __init__(self, guide_str, guide_img_path, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Firmware Update Guide")
        self.setFixedSize(520, 350)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # 1. 상단 안내 메시지
        self.lbl_guide_text = MyLabel(guide_str, self)
        self.lbl_guide_text.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.lbl_guide_text.setWordWrap(True)
        layout.addWidget(self.lbl_guide_text)

        # 2. 안내 이미지
        self.lbl_img = QLabel(self)
        pix_guide = QPixmap(guide_img_path)
        if not pix_guide.isNull():
            self.lbl_img.setPixmap(pix_guide.scaled(480, 200, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        self.lbl_img.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.lbl_img, 1)

        # 3. 하단 OK 버튼
        btn_layout = QHBoxLayout()
        btn_ok = BaseButton("OK", self)
        btn_ok.setFixedWidth(100)
        btn_ok.clicked.connect(self.accept)

        btn_layout.addStretch()
        btn_layout.addWidget(btn_ok)
        btn_layout.addStretch()

        layout.addLayout(btn_layout)

class SelectServicePortTypeDialog(QDialog):
    """
    서비스 포트 (RS232 / USB) 선택을 위한 커스텀 다이얼로그
    (상단에 이미지를 크게 표시하고 아래에 선택 버튼 배치)
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Select Service Port Type")
        self.setFixedSize(520, 300)
        self.selected_port = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(25, 20, 25, 20)
        layout.setSpacing(15)

        lbl_title = MyLabel("Please select the service port type.")
        lbl_title.setAlignment(Qt.AlignCenter)
        layout.addWidget(lbl_title)

        content_layout = QHBoxLayout()
        content_layout.setSpacing(25)

        # ---------------- RS232 카드 ----------------
        rs232_card = QFrame(self)
        rs232_card.setFrameShape(QFrame.StyledPanel)
        rs232_layout = QVBoxLayout(rs232_card)
        rs232_layout.setContentsMargins(15, 15, 15, 15)
        rs232_layout.setSpacing(15)

        lbl_rs232_img = QLabel(self)
        pix_rs232 = QPixmap(ASSET_RS232_IMG_FILE)
        lbl_rs232_img.setPixmap(pix_rs232.scaled(160, 150, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        lbl_rs232_img.setAlignment(Qt.AlignCenter)

        btn_rs232 = BaseButton("RS232", self)
        btn_rs232.setFixedHeight(40)
        btn_rs232.clicked.connect(lambda: self.on_select("RS232"))

        rs232_layout.addWidget(lbl_rs232_img)
        rs232_layout.addWidget(btn_rs232)

        # ---------------- USB 카드 ----------------
        usb_card = QFrame(self)
        usb_card.setFrameShape(QFrame.StyledPanel)
        usb_layout = QVBoxLayout(usb_card)
        usb_layout.setContentsMargins(15, 15, 15, 15)
        usb_layout.setSpacing(15)

        lbl_usb_img = QLabel(self)
        pix_usb = QPixmap(ASSET_USB_IMG_FILE)
        lbl_usb_img.setPixmap(pix_usb.scaled(160, 150, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        lbl_usb_img.setAlignment(Qt.AlignCenter)

        btn_usb = BaseButton("USB", self)
        btn_usb.setFixedHeight(40)
        btn_usb.clicked.connect(lambda: self.on_select("USB"))

        usb_layout.addWidget(lbl_usb_img)
        usb_layout.addWidget(btn_usb)

        content_layout.addWidget(rs232_card)
        content_layout.addWidget(usb_card)

        layout.addLayout(content_layout)
        layout.addStretch()

    def on_select(self, port_type: str):
        self.selected_port = port_type
        self.accept()

class FactoryFirmwareUpdateWin(ParamSettingWin):
    sig_finished_firmware_update = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Factory >> Firmware Update")
        self.resize(750, 650)

        self.is_network_update = False
        self.is_rs232_svc_port = False
        self.service_port_name = None
        self.network_firmware_verion = None
        self.is_updating = False

        self.lbl_update_method = MyValueLabelCheck("Update Method : None")
        self.content_layout.addWidget(self.lbl_update_method)
        self.lbl_service_port_type = MyValueLabelCheck("Service Port Type : None")
        self.content_layout.addWidget( self.lbl_service_port_type)
        self.lbl_service_port_name = MyValueLabelCheck("Service Port Name : None")
        self.content_layout.addWidget( self.lbl_service_port_name)
        self.lbl_ready_firmware = MyValueLabelCheck("Ready Firmware")
        self.content_layout.addWidget( self.lbl_ready_firmware)

        self.layout_kernel_cpu1 = QHBoxLayout()
        self.lbl_kernel_cpu1 = MyValueLabelCheck("Write CPU1 Kernel")
        self.layout_kernel_cpu1.addWidget(self.lbl_kernel_cpu1,1)
        self.progress_kernel_cpu1 = QProgressBar()
        self.progress_kernel_cpu1.setRange(0, 100)  
        self.layout_kernel_cpu1.addWidget(self.progress_kernel_cpu1,1)
        self.content_layout.addLayout( self.layout_kernel_cpu1)
        
        self.lbl_erase_cpu1 = MyValueLabelCheck("Erase CPU1")
        self.content_layout.addWidget(self.lbl_erase_cpu1)

        self.layout_app_cpu1 = QHBoxLayout()
        self.lbl_app_cpu1 = MyValueLabelCheck("Write CPU1 Firmware Binary")
        self.layout_app_cpu1.addWidget(self.lbl_app_cpu1,1)
        self.progress_app_cpu1 = QProgressBar()
        self.progress_app_cpu1.setRange(0, 100)  
        self.layout_app_cpu1.addWidget(self.progress_app_cpu1,1)
        self.content_layout.addLayout( self.layout_app_cpu1)

        self.layout_verify_cpu1 = QHBoxLayout()
        self.lbl_verify_cpu1 = MyValueLabelCheck("Verify CPU1")
        self.layout_verify_cpu1.addWidget(self.lbl_verify_cpu1,1)
        self.progress_verify_cpu1 = QProgressBar()
        self.progress_verify_cpu1.setRange(0, 100)  
        self.layout_verify_cpu1.addWidget(self.progress_verify_cpu1,1)
        self.content_layout.addLayout( self.layout_verify_cpu1)

        self.lbl_reset_cpu1 = MyValueLabelCheck("Reset CPU1")
        self.content_layout.addWidget(self.lbl_reset_cpu1)

        self.layout_kernel_cpu2 = QHBoxLayout()
        self.lbl_kernel_cpu2 = MyValueLabelCheck("Write CPU2 Kernel")
        self.layout_kernel_cpu2.addWidget(self.lbl_kernel_cpu2,1)
        self.progress_kernel_cpu2 = QProgressBar()
        self.progress_kernel_cpu2.setRange(0, 100)  
        self.layout_kernel_cpu2.addWidget(self.progress_kernel_cpu2,1)
        self.content_layout.addLayout( self.layout_kernel_cpu2)

        self.lbl_erase_cpu2 = MyValueLabelCheck("Erase CPU2")
        self.content_layout.addWidget(self.lbl_erase_cpu2)

        self.layout_app_cpu2 = QHBoxLayout()
        self.lbl_app_cpu2 = MyValueLabelCheck("Write CPU2 Firmware Binary")
        self.layout_app_cpu2.addWidget(self.lbl_app_cpu2,1)
        self.progress_app_cpu2 = QProgressBar()
        self.progress_app_cpu2.setRange(0, 100)  
        self.layout_app_cpu2.addWidget(self.progress_app_cpu2,1)
        self.content_layout.addLayout( self.layout_app_cpu2)

        self.layout_verify_cpu2 = QHBoxLayout()
        self.lbl_verify_cpu2 = MyValueLabelCheck("Verify CPU2")
        self.layout_verify_cpu2.addWidget(self.lbl_verify_cpu2,1)
        self.progress_verify_cpu2 = QProgressBar()
        self.progress_verify_cpu2.setRange(0, 100)  
        self.layout_verify_cpu2.addWidget(self.progress_verify_cpu2,1)
        self.content_layout.addLayout( self.layout_verify_cpu2)

        self.lbl_reset_cpu2 = MyValueLabelCheck("Reset CPU2")
        self.content_layout.addWidget( self.lbl_reset_cpu2)

        self.content_layout.addStretch()

        self.log_list_widget = MyConsoleList(max_rows=10000, parent=self)
        self.content_layout.addWidget(self.log_list_widget, 1)

        self.init_toolbar()
        self.toolbar.remove_action("Refresh")
        self.toolbar.add_action("Update", self.on_clicked_update)
        self.init_end()

        self.content_widget.setEnabled(True)

        self.used_port_name   = ServicePort().port_name
        self.used_baudrate    = ServicePort().baudrate
        self.used_data_bits   = ServicePort().data_bits
        self.used_parity      = ServicePort().parity
        self.used_stop_bits   = ServicePort().stop_bits
        self.used_termination = ServicePort().termination

        self.log_list_widget.add_log(LogType.INFO, "[Firmware Update Windows]")

    def on_clicked_update(self):
        self.toolbar.set_action_enabled("Update", False)

        if self.start_selection_flow() == False:
            return

        ftp_host = "121.175.173.236"
        ftp_port = 10021
        ftp_user = "novasen"
        ftp_pwd = "nova1002"

        os.makedirs(RSRC_TEMP_PATH, exist_ok=True)

        if self.is_rs232_svc_port:
            local_cpu1_path = RSRC_APP_CPU1_FILE
            local_cpu2_path = RSRC_APP_CPU2_FILE
        else:
            local_cpu1_path = RSRC_APP_CPU1_NEW_FILE
            local_cpu2_path = RSRC_APP_CPU2_NEW_FILE

        if self.is_network_update:
            if not self.network_firmware_verion:
                msg = "Firmware version is not selected."
                QMessageBox.warning(self, "Warning", msg)
                self.set_error(msg)
                return

            if self.is_rs232_svc_port:
                ftp_cpu1_file = f"/HDD1/FIRMWARE/VALVE/BASIC/{self.network_firmware_verion}/VALVE_CPU1_{self.network_firmware_verion}_FLASH.txt"
                ftp_cpu2_file = f"/HDD1/FIRMWARE/VALVE/BASIC/{self.network_firmware_verion}/VALVE_CPU2_{self.network_firmware_verion}_FLASH.txt"
            else:
                ftp_cpu1_file = f"/HDD1/FIRMWARE/VALVE/BASIC/{self.network_firmware_verion}/VALVE_CPU1_{self.network_firmware_verion}_FLASH_NEW.txt"
                ftp_cpu2_file = f"/HDD1/FIRMWARE/VALVE/BASIC/{self.network_firmware_verion}/VALVE_CPU2_{self.network_firmware_verion}_FLASH_NEW.txt"

            try:
                ftp = ftplib.FTP()
                ftp.connect(ftp_host, ftp_port, timeout=10)
                ftp.login(ftp_user, ftp_pwd)

                with open(local_cpu1_path, "wb") as f:
                    ftp.retrbinary(f"RETR {ftp_cpu1_file}", f.write)

                with open(local_cpu2_path, "wb") as f:
                    ftp.retrbinary(f"RETR {ftp_cpu2_file}", f.write)

                ftp.quit()

                self.lbl_ready_firmware.set_value(True)
            except Exception as e:
                msg = f"Failed to download firmware files from FTP:\n{str(e)}"
                QMessageBox.critical(self, "FTP Error", msg)
                self.set_error(msg)
                return
        else:
            self.lbl_ready_firmware.set_value(True)

        self.start_firmware_writer(RSRC_KERNEL_CPU1_FILE, RSRC_KERNEL_CPU2_FILE, local_cpu1_path, local_cpu2_path)

    def start_selection_flow(self)->bool:
        # 업데이트 방식 선택
        update_method = self.select_update_method()

        if update_method is None:
            self.close()
            return False

        self.is_network_update = update_method == "Network"

        if self.is_network_update:
            self.network_firmware_verion = self.select_network_firmware_bin()
            if self.network_firmware_verion:
                self.lbl_update_method.set_text(f"Update Method : Network({self.network_firmware_verion})")
            else:
                self.close()
                return False
        else:
            self.lbl_update_method.set_text(f"Update Method : Embeded Files")

        self.lbl_update_method.set_value(True)

        # 서비스 포트 커넥터 타입 선택
        service_port_type = self.select_service_port_typ()
        self.lbl_service_port_type.set_text(f"Service Port Type : {service_port_type}")
        if service_port_type is None:
            self.close()
            return False

        self.lbl_service_port_type.set_value(True)
        self.is_rs232_svc_port = service_port_type == "RS232"

        self.service_port_name = self.select_port()
        self.lbl_service_port_name.set_text(f"Service Port Name : {self.service_port_name}")
        self.lbl_service_port_name.set_value(True)

        ServicePort().close()

        if service_port_type == "RS232":
            self.guide_rs232_port_setting()

        return True

    def select_update_method(self) -> str | None:
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("Select Firmware Update Method")
        msg_box.setText("Please select the firmware update method.")

        btn_network = msg_box.addButton("From Network", QMessageBox.AcceptRole)
        btn_embedded = msg_box.addButton("From Files", QMessageBox.AcceptRole)

        msg_box.exec()

        clicked = msg_box.clickedButton()
        if clicked == btn_network:
            return "Network"
        elif clicked == btn_embedded:
            return "File"
        return None     

    def select_service_port_typ(self) -> str | None:
        dialog = SelectServicePortTypeDialog(self)
        if dialog.exec() == QDialog.Accepted:
            return dialog.selected_port
        return None

    def guide_rs232_port_setting(self):
        guide_dlg = GuideDialog("1(1/3). Connect the update adapter to the valve's service port", ASSET_FU_GUIDE_1_IMG_FILE,self)
        guide_dlg.exec()
        guide_dlg = GuideDialog("2(2/3). Set the boot mode switch to 'up'", ASSET_FU_GUIDE_2_IMG_FILE,self)
        guide_dlg.exec()
        guide_dlg = GuideDialog("3(3/3). Click the reset button<br>(if the value version is older then 'R006', turn the power and on.)", ASSET_FU_GUIDE_3_IMG_FILE,self)
        guide_dlg.exec()

    def select_port(self) -> str | None:
        select_port_dlg = SelectPortDialog(self)

        select_port_dlg.exec()
        return select_port_dlg.select_port

    def select_network_firmware_bin(self) -> str | None:
        dlg = SelectNetworkFirmwareDialog(self)
        if dlg.exec() == QDialog.Accepted:
            return dlg.selected_version
        return None

    def start_firmware_writer(self, kernel_cpu1, kernel_cpu2, flash_cpu1, flash_cpu2):
        # ---------- 파일 유효성 검사 ----------
        files = {
            "CPU1 Kernel"  : kernel_cpu1,
            "CPU2 Kernel"  : kernel_cpu2,
            "CPU1 Firmware": flash_cpu1,
            "CPU2 Firmware": flash_cpu2,
        }
        missing = [name for name, path in files.items()
                   if not path or not os.path.isfile(path)]
        if missing:
            msg = "Firmware file(s) not found:\n - " + "\n - ".join(missing)
            QMessageBox.warning(self, "Warning", msg)
            self.set_error(msg)
            return

        if not self.service_port_name:
            msg = "Service port is not selected."
            QMessageBox.warning(self, "Warning", msg)
            self.set_error(msg)
            return

        # ---------- 진행률 다이얼로그 + 워커 스레드 ----------
        # 워커 내부 시퀀스(C++ ValveFirmwareUpgradeWorker 와 동일):
        #   CPU1: 커널 → 소거 → DFU → 검증 → 리셋(CPU2부트)
        #   CPU2: 커널 → 소거 → DFU → 검증 → 리셋
        self._fw_worker = FirmwareWriterWorker(
            self.is_rs232_svc_port,
            self.service_port_name,
            kernel_cpu1, kernel_cpu2, flash_cpu1, flash_cpu2)

        self._fw_worker.sig_phase.connect(self.set_phase)
        self._fw_worker.sig_progress.connect(self.set_progress)
        self._fw_worker.sig_log.connect(self.set_log)
        #self._fw_worker.sig_error.connect(self.set_error)
        self._fw_worker.sig_finished.connect(self.handle_firmware_writer_finished)

        self._fw_worker.start()

    def handle_firmware_writer_finished(self, ok: bool, msg: str):
        self._fw_worker.wait(3000)      # 스레드 정리

        if ok:
            if self.is_rs232_svc_port:
                guide_dlg = GuideDialog("1(1/2). Set the boot mode switch back to 'down'", ASSET_FU_GUIDE_4_IMG_FILE,self)
                guide_dlg.exec()
                guide_dlg = GuideDialog("2(2/2).  Click the reset button<br>(if the value version is older then 'R006', turn the power and on.)", ASSET_FU_GUIDE_5_IMG_FILE,self)
                guide_dlg.exec()

            self.start_wait_for_reboot()
        else:
            QMessageBox.critical(self, "Firmware Update Failed", msg)
            self.set_error(f"Firmware Update Failed : {msg}")

        self.is_updating = False

    def start_wait_for_reboot(self):
        if self.used_port_name == None or self.used_port_name == "":
            self.sig_finished_firmware_update.emit()
            self.close()
            return

        ServicePort().open(self.used_port_name, self.used_baudrate, self.used_data_bits, self.used_parity, self.used_stop_bits, self.used_termination)
        self.param_worker.reboot()
        self.param_worker.sig_reboot_check_result.connect(self.finish_reboot)

    def finish_reboot(self):
        self.param_worker.sig_reboot_check_result.disconnect(self.finish_reboot)

        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("Restore Factory Parameters")
        msg_box.setText("Restore factory parameters?")

        btn_restore = msg_box.addButton("Restore", QMessageBox.AcceptRole)
        btn_skip = msg_box.addButton("Skip", QMessageBox.AcceptRole)

        msg_box.exec()
        if msg_box.clickedButton() == btn_restore:
            self.log_list_widget.add_log(LogType.INFO, "Restore")
            self.param_worker.sig_reboot_check_result.connect(self.finish_restore_factory_params)
            restore_factory_param = self.param_worker.add_write_param("System.Services.Restore Factory Parameters")
            restore_factory_param.write_str_value = restore_factory_param.btn_str_value
            self.param_worker.write()
        elif msg_box.clickedButton() == btn_skip:
            self.log_list_widget.add_log(LogType.INFO, "Skip")
            self.close()

    def finish_restore_factory_params(self):
        self.close()        

    def set_phase(self, phase:FirmwarePhase):
        self.log_list_widget.add_log(LogType.INFO, f"[Phase] {phase.value}")

        if phase == FirmwarePhase.CPU1_KERNEL_DN:
            self.progress_kernel_cpu1.setRange(0, 0)
            self.lbl_kernel_cpu1.set_value(True)
        elif phase == FirmwarePhase.CPU1_ERASE:
            self.lbl_erase_cpu1.set_value(True)
        elif phase == FirmwarePhase.CPU1_APP_DN:
            self.progress_app_cpu1.setRange(0, 0)
            self.lbl_app_cpu1.set_value(True)
        elif phase == FirmwarePhase.CPU1_VERIFY:
            self.progress_verify_cpu1.setRange(0, 0)
            self.lbl_verify_cpu1.set_value(True)
        elif phase == FirmwarePhase.CPU1_RESET:
            self.lbl_reset_cpu1.set_value(True)
        elif phase == FirmwarePhase.CPU2_KERNEL_DN:
            self.progress_kernel_cpu2.setRange(0, 0)
            self.lbl_kernel_cpu2.set_value(True)
        elif phase == FirmwarePhase.CPU2_ERASE:
            self.lbl_erase_cpu2.set_value(True)
        elif phase == FirmwarePhase.CPU2_APP_DN:
            self.progress_app_cpu2.setRange(0, 0)
            self.lbl_app_cpu2.set_value(True)
        elif phase == FirmwarePhase.CPU2_VERIFY:
            self.progress_verify_cpu2.setRange(0, 0)
            self.lbl_verify_cpu2.set_value(True)
        elif phase == FirmwarePhase.CPU2_RESET:
            self.lbl_reset_cpu2.set_value(True)

    def set_progress(self, phase:FirmwarePhase, sent: int, total: int):
        value = int(sent * 100 / total) if total else 0

        if phase == FirmwarePhase.CPU1_KERNEL_DN:
            self.progress_kernel_cpu1.setRange(0, 100)
            self.progress_kernel_cpu1.setValue(value)
        elif phase == FirmwarePhase.CPU1_APP_DN:
            self.progress_app_cpu1.setRange(0, 100)
            self.progress_app_cpu1.setValue(value)
        elif phase == FirmwarePhase.CPU1_VERIFY:
            self.progress_verify_cpu1.setRange(0, 100)
            self.progress_verify_cpu1.setValue(value)
        elif phase == FirmwarePhase.CPU2_KERNEL_DN:
            self.progress_kernel_cpu2.setRange(0, 100)
            self.progress_kernel_cpu2.setValue(value)
        elif phase == FirmwarePhase.CPU2_APP_DN:
            self.progress_app_cpu2.setRange(0, 100)
            self.progress_app_cpu2.setValue(value)
        elif phase == FirmwarePhase.CPU2_VERIFY:
            self.progress_verify_cpu2.setRange(0, 100)
            self.progress_verify_cpu2.setValue(value)

        self.log_list_widget.add_log(LogType.INFO, f"[Progress] {value}%")

    def set_log(self, msg: str):
        self.log_list_widget.add_log(LogType.INFO, msg)
        pass

    def set_error(self, msg: str):
        self.log_list_widget.add_log(LogType.ERROR, msg)
        self.progress_kernel_cpu1.setRange(0, 100)
        self.progress_app_cpu1.setRange(0, 100)
        self.progress_verify_cpu1.setRange(0, 100)
        self.progress_kernel_cpu2.setRange(0, 100)
        self.progress_app_cpu2.setRange(0, 100)
        self.progress_verify_cpu2.setRange(0, 100)