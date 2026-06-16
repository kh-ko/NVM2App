import json
from PySide6.QtCore import Qt
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import QWidget, QMainWindow, QFileDialog, QMessageBox, QScrollArea, QVBoxLayout


from b_core.b_datatype.general_enum import ParamAccType
from b_core.b_datatype.parameter import Parameter
from b_core.c_manager.parameter_manager import ParamManager
from b_core.e_worker.parameter_worker import ParameterWorker

from c_ui.b_control_packet.base.base_toolbar import BaseToolBar
from c_ui.b_control_packet.param_container.param_folder_widget import ParamFolderWidget
from c_ui.b_control_packet.param_container.param_setting_statusbar import ParamSettingStatusBar
from c_ui.b_control_packet.param.param_enum_wo_widget import ParamEnumWriteOnlyWidget
from c_ui.b_control_packet.param.param_btn_wo_widget import ParamBtnWriteOnlyWidget

class ParamSettingWin(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.resize(750, 450)

        self.toolbar = BaseToolBar(self)
        self.addToolBar(Qt.TopToolBarArea, self.toolbar)
        self.toolbar.add_action("Refresh", self.on_clicked_refresh)

        self.scroll_area = QScrollArea(self)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(10, 10, 10, 10)
        self.content_layout.setSpacing(10)

        self.scroll_area.setWidget(self.content_widget)

        self.setCentralWidget(self.scroll_area)

        self.statusbar = ParamSettingStatusBar(self)
        self.setStatusBar(self.statusbar)

        self.param_worker = ParameterWorker(self)  
        self.param_manager = ParamManager()
        self.parameter_folder_widgets = []
    
    def add_param_folder(self, folder_path : str, param_path=None, label_width= 150):
        folder_widget = ParamFolderWidget(folder_name=folder_path, param_path=param_path,label_width = label_width)
        self.content_layout.addWidget(folder_widget)
        self.parameter_folder_widgets.append(folder_widget)

    def add_param_folder_widget(self, folder_widget):
        self.content_layout.addWidget(folder_widget)
        self.parameter_folder_widgets.append(folder_widget)        
        
    def init_toolbar(self):
        is_contain_rw_param = False
        is_contain_wo_param = False

        for widget in self.parameter_folder_widgets:
            for param_component in widget.param_components:
                if param_component.param.acc == ParamAccType.RW:
                    is_contain_rw_param = True
                elif param_component.param.acc == ParamAccType.WO:# and not isinstance(param_component, ParamBtnInputWidget):
                    is_contain_wo_param = True

        if is_contain_rw_param:
            self.toolbar.add_action("Save File", self.on_clicked_save_file)
            self.toolbar.add_action("Load File", self.on_clicked_load_file)

        if is_contain_wo_param or is_contain_rw_param:
            self.toolbar.add_action("Apply", self.on_clicked_apply)

    def init_end(self):
        self.param_worker.win_name = self.windowTitle()

        for widget in self.parameter_folder_widgets:
            for param_component in widget.param_components:
                if param_component.param.acc == ParamAccType.RO:
                    self.param_worker.add_read_param_ptr(param_component.param)
                    self.param_worker.add_monitor_param_ptr(param_component.param)
                else:
                    self.param_worker.add_write_param_ptr(param_component.param)

                if param_component.param.enable_conditions is not None:
                    for enable_condition in param_component.param.enable_conditions:
                        ref_component = self._find_component_by_param_id(enable_condition.ref_id)
                        param_component.reg_enable_condition(ref_component, enable_condition.values)

                if isinstance(param_component, ParamBtnWriteOnlyWidget):
                    param_component.sig_value_changed.connect(self.on_btn_widget_clicked)

                if isinstance(param_component, ParamEnumWriteOnlyWidget):
                    param_component.sig_value_changed.connect(self.on_enum_widget_clicked)

        self.param_worker.sig_progress_changed.connect(self.handle_progress_changed)
        self.content_widget.setEnabled(False)
        self.param_worker.refresh()

    def on_clicked_refresh(self):
        for widget in self.parameter_folder_widgets:
                for param_component in widget.param_components:
                    if param_component.param.acc != ParamAccType.RO:
                        param_component.restore()

        self.param_worker.refresh()
    
    def on_clicked_save_file(self):
        data_to_save = []

        for widget in self.parameter_folder_widgets:
            for param_component in widget.param_components:
                if param_component.param.acc == ParamAccType.RW and param_component.param.is_nor_backup:
                    param_data = {
                        "path": param_component.param.path,
                        "name": param_component.param.name,
                        "id": param_component.param.id,
                        "index": str(param_component.param.index),
                        "value": param_component.get_backup_value()
                    }
                    data_to_save.append(param_data)

        if not data_to_save:
            QMessageBox.information(self, "Information", "There are no items to save.")
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Parameter File",     # 다이얼로그 제목
            "",                 # 기본 경로
            "JSON Files (*.json);;All Files (*)" # 파일 필터
        )

        if not file_path:
            return

        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data_to_save, f, indent=4, ensure_ascii=False)

            QMessageBox.information(self, "Success", "File saved successfully.")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"An error occurred while saving the file:\n{e}")



    def on_clicked_load_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Load Parameter File", "", "JSON Files (*.json);;All Files (*)")

        if not file_path:
            return

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                loaded_data = json.load(f)
        except Exception as e:
            QMessageBox.critical(self,"Error", f"An error occurred while reading the file:\n{e}")
            return

        if not isinstance(loaded_data, list):
            QMessageBox.warning(self, "Warning", "Invalid file format. The selected file is not a valid parameter file.")
            return

        for item in loaded_data:
            if not isinstance(item, dict) or not all(k in item for k in ("id", "index", "value")):
                continue

            target_id = item.get("id")
            target_index = item.get("index")
            target_value = item.get("value")

            found = False

            for widget in self.parameter_folder_widgets:
                for param_component in widget.param_components:
                    if (param_component.param.acc == ParamAccType.RW and param_component.param.id == target_id and str(param_component.param.index) == target_index):
                        param_component.set_backup_value(target_value)
                        found = True
                        break

                if found:
                    break # 바깥쪽 루프도 중단하고 다음 item으로 넘어감
        
        QMessageBox.information(self, "Success", "Parameter data loaded successfully.")

    def on_clicked_apply(self):
        for widget in self.parameter_folder_widgets:
            for param_component in widget.param_components:
                if param_component.param.acc != ParamAccType.RO and param_component.is_dirty():
                    param_component.param.write_str_value = param_component.get_param_write_value()
        
        self.param_worker.write()

    def on_btn_widget_clicked(self, param : Parameter):
        param.write_str_value = param.btn_str_value
        self.param_worker.write()

    def on_enum_widget_clicked(self, param : Parameter, write_value:str):
        param.write_str_value = write_value
        self.param_worker.write()

    def closeEvent(self, event: QCloseEvent):
        self.param_worker.cleanup()
        event.accept()

    def handle_progress_changed(self, progress: int):
        self.statusbar.set_progress(progress)

        if progress > 0:
            self.content_widget.setEnabled(False)
        else:
            self.content_widget.setEnabled(True)

    def _find_component_by_param_id(self, id):
        for widget in self.parameter_folder_widgets:
            for param_component in widget.param_components:
                if param_component.param.id == id:
                    return param_component
        return None
