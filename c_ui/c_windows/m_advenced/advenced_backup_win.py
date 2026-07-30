from b_core.b_datatype.param_enum import SysUserInterfaceEnum
from c_ui.b_control_packet.controls.my_consolelist import MyConsoleList
from PySide6.QtWidgets import QApplication
from PySide6.QtWidgets import QFileDialog
from PySide6.QtWidgets import QProgressBar
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QListView
from PySide6.QtCore import QAbstractListModel, Qt
from PySide6.QtWidgets import QVBoxLayout

from b_core.b_datatype.general_enum import SvcPortErrType
from b_core.b_datatype.general_enum import LogType
from b_core.b_datatype.parameter import Parameter
from b_core.c_manager.parameter_manager import ParamManager

from c_ui.b_control_packet.base.base_button import BaseButton
from c_ui.b_control_packet.param_container.param_setting_win import ParamSettingWin


class AdvencedBackupWin(ParamSettingWin):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Advenced Setup>> Backup")
        self.backup_params = []
        self.backup_contents = []
        self.is_firmware_update_backup = False

        self.log_list_widget = MyConsoleList(parent = self)
        self.content_layout.addWidget(self.log_list_widget)
        
        self.progress_bar = QProgressBar(self)
        self.progress_bar.setAlignment(Qt.AlignCenter) # 퍼센트 텍스트 가운데 정렬
        self.progress_bar.setValue(0)
        self.content_layout.addWidget(self.progress_bar)

        self.param_worker.sig_single_read_result.connect(self.handle_single_read_result)

        self.init_toolbar()
        self.toolbar.remove_action("Refresh")
        self.toolbar.add_action("Backup Run", self.on_clicked_backup)
        self.toolbar.add_action("Copy to Clipboard", self.on_clicked_copy_to_clipboard)
        self.init_end()
        self.content_widget.setEnabled(True)

    def set_firmware_update_backup(self, value : bool):
        self.is_firmware_update_backup = value

    def load_backup_list(self):
        param_manager = ParamManager()
        params = param_manager.get_param_list()

        user_iface_param = param_manager.get_by_full_path("System.Identification.Configuration.User Interface")

        for param in params:
            if param.is_fu_backup:
                if param.path.startswith("Interface"):
                    if param.path.startswith("Interface.Scaling"):
                        self.backup_params.append(param)
                    elif (user_iface_param.value == SysUserInterfaceEnum.DEVICENET.value or user_iface_param.value == SysUserInterfaceEnum.DEVICENET_LEGACY_MKS.value or user_iface_param.value == SysUserInterfaceEnum.DEVICENET_APSYSTEM.value or user_iface_param.value == SysUserInterfaceEnum.DEVICENET_NORCAL.value) and param.path.startswith("Interface DeviceNet"):
                        self.backup_params.append(param)
                    elif (user_iface_param.value == SysUserInterfaceEnum.RS232.value or user_iface_param.value == SysUserInterfaceEnum.RS232_ANALOG_OUTPUT.value or user_iface_param.value == SysUserInterfaceEnum.RS485_ANALOG_OUTPUT.value) and param.path.startswith("Interface RS232/RS485"):
                        self.backup_params.append(param)
                elif param.path.startswith("Legacy Parameters") and self.is_firmware_update_backup:
                    continue
                elif param.path.startswith("Legacy Parameters.Hardware.051 Position offset(0)"):
                    continue
                else:
                    self.backup_params.append(param)

    def on_clicked_backup(self):
        self.load_backup_list()
        self.log_list_widget.add_log(LogType.INFO,"[Backup Start !!!]")
        self.progress_bar.setRange(0, len(self.backup_params))
        self.progress_bar.setValue(0)
        self.param_worker.single_read_request(self.backup_params[0])

    def on_clicked_copy_to_clipboard(self):
        content = self.log_list_widget.get_all_text()
        QApplication.clipboard().setText(content)        

    def handle_single_read_result(self, req_msg:str, resp_msg: str, param: Parameter, err_type:SvcPortErrType):
        if err_type != SvcPortErrType.NONE:
            self.log_list_widget.add_log(LogType.ERROR, f"[Port Error]: Parameter = {param.path}.{param.name}, packet = {req_msg}, err_type = {err_type}")
            self.param_worker.single_read_request(param)
        else:
            resp_check_prefix = f"p:000B{param.id}{param.index:02X}"

            if resp_msg.startswith(resp_check_prefix) == False:
                self.log_list_widget.add_log(LogType.ERROR, f"[Packet Error]: Parameter = {param.path}.{param.name}, packet = {resp_msg}")
            else:
                self.log_list_widget.add_log(LogType.INFO, f"[Success]: Parameter = {param.path}.{param.name}")
                value = resp_msg[16:]
                content = f"{param.path}.{param.name}, p:01{param.id}{param.index:02X}{value}"
                self.backup_contents.append(content)

            try:
                current_idx = self.backup_params.index(param)
                next_idx = current_idx + 1

                self.progress_bar.setValue(next_idx)
                
                if next_idx < len(self.backup_params):
                    next_param = self.backup_params[next_idx]
                    self.param_worker.single_read_request(next_param)
                else:
                    self.log_list_widget.add_log(LogType.INFO, "[Backup Completed Successfully !!!]")
                    self.save_backup_to_file()
                    
            except ValueError:
                self.log_list_widget.add_log(LogType.ERROR, f"[Error]: Parameter {param.name} is not in backup list.")

    def save_backup_to_file(self):
        # 1. 파일 저장 다이알로그 띄우기
        # 반환값은 (선택된 파일의 절대 경로, 선택된 파일 확장자 필터) 튜플입니다.
        file_path, _ = QFileDialog.getSaveFileName(
            self, 
            "Save Backup File",      # 다이알로그 타이틀
            "",                      # 기본 경로 (비워두면 기본 작업 디렉토리)
            "Text Files (*.txt);;All Files (*)" # 파일 형식 필터
        )
        
        # 2. 사용자가 파일 이름을 입력하고 확인을 눌렀을 때만 실행
        if file_path:
            try:
                # self.backup_contents 리스트의 요소들을 줄바꿈(\n)으로 합칩니다.
                file_data = "\n".join(self.backup_contents)
                
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(file_data)
                
                self.log_list_widget.add_log(LogType.INFO, f"[File Saved]: Successfully saved to {file_path}")
            except Exception as e:
                # 파일 저장 중 예외 발생 시 에러 로그 표시
                self.log_list_widget.add_log(LogType.ERROR, f"[Error]: Failed to save file. {str(e)}")
        else:
            # 사용자가 다이알로그에서 '취소'를 눌렀을 때
            self.log_list_widget.add_log(LogType.ERROR, "[Save Cancelled]: File save cancelled by user.")

        

