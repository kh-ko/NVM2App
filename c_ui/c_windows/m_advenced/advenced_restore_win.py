from PySide6.QtWidgets import QApplication
from PySide6.QtWidgets import QFileDialog
from PySide6.QtWidgets import QProgressBar
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QListView
from PySide6.QtCore import QAbstractListModel, Qt

from b_core.b_datatype.general_enum import SvcPortErrType
from b_core.b_datatype.general_enum import LogType
from c_ui.b_control_packet.param_container.param_setting_win import ParamSettingWin
from c_ui.b_control_packet.controls.my_consolelist import MyConsoleList

class AdvencedRestoreWin(ParamSettingWin):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Advenced >> Restore")

        self.restore_contents = []

        self.log_list_widget = MyConsoleList(parent = self)
        self.content_layout.addWidget(self.log_list_widget)
        
        self.progress_bar = QProgressBar(self)
        self.progress_bar.setAlignment(Qt.AlignCenter) # 퍼센트 텍스트 가운데 정렬
        self.progress_bar.setValue(0)
        self.content_layout.addWidget(self.progress_bar)

        self.param_worker.sig_single_name_value_write_result.connect(self.handle_single_name_value_write_result)

        self.init_toolbar()
        self.toolbar.remove_action("Refresh")
        self.toolbar.add_action("Restore Run", self.on_clicked_restore)
        self.toolbar.add_action("Copy to Clipboard", self.on_clicked_copy_to_clipboard)
        self.init_end()
        self.content_widget.setEnabled(True)

    def on_clicked_restore(self):
        self.log_list_widget.add_log(LogType.INFO, "[Restore Start !!!]")
        self.load_backup_file()

        if len(self.restore_contents) < 1:
            self.log_list_widget.add_log(LogType.ERROR, "[Error]: No restore contents found.")
            return
            
        self.progress_bar.setRange(0, len(self.restore_contents))
        self.progress_bar.setValue(0)
        self.param_worker.single_name_value_write_request(self.restore_contents[0][0], self.restore_contents[0][1])

    def on_clicked_copy_to_clipboard(self):
        content = self.log_list_widget.get_all_text()
        QApplication.clipboard().setText(content)     

    def handle_single_name_value_write_result(self, req_msg:str, resp_msg: str, name: str, value: str, err_type:SvcPortErrType):
        if err_type != SvcPortErrType.NONE:
            self.log_list_widget.add_log(LogType.ERROR, f"[Port Error]: Parameter = {name}, packet = {req_msg}, err_type = {err_type}")
            self.param_worker.single_name_value_write_request(name, value)
        else:            
            if resp_msg.startswith("E:") or (resp_msg.startswith("p:") == True and resp_msg.startswith("p:0001") == False):
                self.log_list_widget.add_log(LogType.ERROR, f"[Packet Error]: Parameter = {name}, packet = {resp_msg}")
            else:
                self.log_list_widget.add_log(LogType.INFO, f"[Success]: Parameter = {name}")

            try:
                current_idx = self.restore_contents.index((name, value))
                next_idx = current_idx + 1

                self.progress_bar.setValue(next_idx)
                
                if next_idx < len(self.restore_contents):
                    self.param_worker.single_name_value_write_request(self.restore_contents[next_idx][0], self.restore_contents[next_idx][1])
                else:
                    self.log_list_widget.add_log(LogType.INFO, "[Restore Completed Successfully !!!]")
                    
            except ValueError:
                self.log_list_widget.add_log(LogType.ERROR, f"[Error]: Parameter {name} is not in restore list.")

    def load_backup_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Open Backup File", "", "Text Files (*.txt);;All Files (*)")
        
        if file_path:
            try:
                self.restore_contents.clear()
                
                with open(file_path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line: # 빈 줄은 건너뜁니다
                            continue
                        
                        if "," in line:
                            name, packet = line.split(",", 1)
                            self.restore_contents.append((name.strip(), packet.strip()))
                        else:
                            self.restore_contents.append(("", line.strip()))
                
                self.log_list_widget.add_log(LogType.INFO, f"[File Loaded]: Loaded {len(self.restore_contents)} parameters from {file_path}")
                
            except Exception as e:
                # 파일 로드 오류 시 에러 로그 표시
                self.log_list_widget.add_log(LogType.ERROR, f"[Error]: Failed to load file. {str(e)}")
        else:
            # 사용자가 다이알로그에서 '취소'를 눌렀을 때
            self.log_list_widget.add_log(LogType.ERROR, "[Load Cancelled]: File load cancelled by user.")

        

