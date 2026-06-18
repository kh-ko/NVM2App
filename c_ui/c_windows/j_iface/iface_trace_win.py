import os
import shutil
from datetime import datetime
from PySide6.QtCore import QAbstractListModel, QTimer, Qt
from PySide6.QtWidgets import QFileDialog, QApplication, QListView
from PySide6.QtGui import QCloseEvent

from b_core.b_datatype.param_enum import StopStartEnum
from b_core.c_manager.parameter_manager import ParamManager
from b_core.d_dal.service_port import ServicePort

from c_ui.b_control_packet.param_container.param_setting_win import ParamSettingWin
from c_ui.b_control_packet.controls.my_lamptoolbutton import MyLampToolButton

class TraceModel(QAbstractListModel):
    def __init__(self, max_rows=1000, parent=None):
        super().__init__(parent)
        self._logs = []
        self._max_rows = max_rows

    def rowCount(self, parent=None):
        return len(self._logs)

    def data(self, index, role=Qt.DisplayRole):
        if index.isValid() and role == Qt.DisplayRole:
            return self._logs[index.row()]
        return None

    def add_log(self, log_str):
        if len(self._logs) >= self._max_rows:
            chunk_size = self._max_rows // 10  
            self.beginRemoveRows(self.index(0).parent(), 0, chunk_size - 1)
            del self._logs[:chunk_size]
            self.endRemoveRows()

        self.beginInsertRows(self.index(0).parent(), self.rowCount(), self.rowCount())
        self._logs.append(log_str)
        self.endInsertRows()

    def clear(self):
        self.beginResetModel()
        self._logs = []
        self.endResetModel()

    def get_all_text(self):
        return "\n".join(self._logs)
        
class IfaceTraceWin(ParamSettingWin):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Interface >> Trace")

        self.service_port = ServicePort()
        self.is_record_file = False
        self.temp_record_path = None
        self.temp_record_file = None
        self.mode = "STOP"
        self.is_pause = False

        self.trace_model = TraceModel(max_rows=1000)
        self.log_list_widget = QListView(self)
        self.log_list_widget.setModel(self.trace_model)
        self.log_list_widget.setWordWrap(True)
        self.content_layout.addWidget(self.log_list_widget)

        self.init_toolbar()        
        self.toolbar.remove_action("Refresh")
        self.start_btn = MyLampToolButton(self)
        self.start_btn.setText("Start")
        self.start_btn.set_accent(False)
        self.start_btn.clicked.connect(self.on_clicked_start)
        self.toolbar.addWidget(self.start_btn)
        self.pause_btn = MyLampToolButton(self)
        self.pause_btn.setText("Pause")
        self.pause_btn.set_accent(False)
        self.pause_btn.clicked.connect(self.on_clicked_pause)
        self.toolbar.addWidget(self.pause_btn)
        self.toolbar.add_action("Stop", self.on_clicked_stop)
        self.toolbar.add_action("Clear", self.on_clicked_clear)
        self.record_to_file_btn = MyLampToolButton(self)
        self.record_to_file_btn.setText("Rec to File")
        self.record_to_file_btn.set_accent(False)
        self.record_to_file_btn.clicked.connect(self.on_clicked_record_to_file)
        self.toolbar.addWidget(self.record_to_file_btn)
        self.toolbar.add_action("Copy to Clipboard", self.on_clicked_copy_to_clipboard)
        
        self.init_end()
        self.trace_param = ParamManager().get_by_full_path("User interface.Trace")
        self.trace_param.sig_value_changed.connect(self.handle_trace_param_changed)
        self.param_worker.add_write_param_ptr(self.trace_param)
        self.handle_trace_param_changed()

        self.temp_dir = "temp_logs"  # 임시 파일을 저장할 디렉토리
        if not os.path.exists(self.temp_dir):
            os.makedirs(self.temp_dir)

        self.trace_timer = QTimer(self)
        self.trace_timer.setInterval(200)  # 100ms = 0.1초
        self.trace_timer.timeout.connect(self.handle_trace_data)
        self.trace_timer.start()

    def on_clicked_record_to_file(self):
        self.is_record_file = not self.is_record_file
        if self.is_record_file:
            self.record_to_file_btn.set_accent(True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
            filename = f"trace_{timestamp}.log"
            self.temp_record_path = os.path.join(self.temp_dir, filename)
            self.temp_record_file = open(self.temp_record_path, "w", encoding="utf-8")
        else:
            self.record_to_file_btn.set_accent(False)
            if self.temp_record_file:
                self.temp_record_file.close()
                self.temp_record_file = None

                file_path, _ = QFileDialog.getSaveFileName(self, "Save Trace Log", "", "Log Files (*.log)")

                if file_path:
                    shutil.move(self.temp_record_path, file_path)
                else:
                    if os.path.exists(self.temp_record_path):
                        os.remove(self.temp_record_path)

    def on_clicked_copy_to_clipboard(self):
        content = self.trace_model.get_all_text()
        QApplication.clipboard().setText(content)

    def on_clicked_clear(self):
        self.trace_model.clear()

    def on_clicked_start(self):
        if self.mode == "TRACING":
            self.start_btn.set_accent(True)
            self.pause_btn.set_accent(False)
            self.is_pause = False
            return

        self.trace_param.write_str_value = "1"
        self.param_worker.write()

    def on_clicked_stop(self):
        self.trace_param.write_str_value = "0"
        self.param_worker.write()

    def on_clicked_pause(self):
        if self.mode != "TRACING":
            return

        self.start_btn.set_accent(False)
        self.pause_btn.set_accent(True)
        self.is_pause = True

    def handle_trace_param_changed(self):
        if self.trace_param.value == StopStartEnum.STOP.value: 
            self.start_btn.set_accent(False)
            self.pause_btn.set_accent(False)
            self.service_port.set_trace_mode(False)
            self.mode = "STOP"
            self.is_pause = False
        elif self.trace_param.value == StopStartEnum.START.value:  
            self.start_btn.set_accent(True)
            self.pause_btn.set_accent(False)
            self.service_port.set_trace_mode(True)
            self.mode = "TRACING"

    def handle_trace_data(self):        
        if self.mode != "TRACING" or self.is_pause:
            return

        traces = self.service_port.get_trace_buffer()

        if traces:
            for t in traces:
                self.trace_model.add_log(t)

                if self.is_record_file and self.temp_record_file:
                    self.temp_record_file.write(t + "\n")
                    
            self.log_list_widget.scrollToBottom()
            if self.is_record_file and self.temp_record_file:
                self.temp_record_file.flush()

    def closeEvent(self, event: QCloseEvent):
        super().closeEvent(event)
        #self.on_clicked_stop()
        if self.is_record_file and self.temp_record_file:
            self.temp_record_file.close()
            if hasattr(self, 'temp_record_path') and os.path.exists(self.temp_record_path):
                os.remove(self.temp_record_path)

        if self.trace_timer.isActive():
            self.trace_timer.stop()

        event.accept()
