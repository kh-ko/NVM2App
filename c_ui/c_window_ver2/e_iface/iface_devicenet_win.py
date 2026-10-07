"""Interface DeviceNet 창 — ParamWin(폴더 카드) + Create EDS (2단계 8위 ③ 에서 param_win.py 에서 분리).

EDS 생성(Param16)에 쓰이는 Cluster.Settings.Number of Valves 는 이 창의 폴더 밖이라 직접 읽기 등록한다.
"""

from PySide6.QtWidgets import QFileDialog, QMessageBox

from b_core.c_manager.app_log_manager import AppLogManager
from b_core.f_helper import eds_file_helper

from c_ui.c_window_ver2.param_win import ParamWin


class ParamIfaceDentWin(ParamWin):
    def __init__(self, parent=None, win_name = None, paths : list[str] = None, filter_param_paths : list[str] = None, is_editblock_win=False, label_width=210, folder_max_width=None):

        super().__init__(parent=parent, win_name = win_name, paths = paths, filter_param_paths = filter_param_paths, is_editblock_win=is_editblock_win, label_width=label_width, folder_max_width=folder_max_width)
        self.toolbar.add_action("Create EDS", self.on_clicked_create_eds)

    def additional_param_settings(self):
        # EDS 생성(Param16)에 쓰이는 클러스터 param — 이 창의 폴더 밖이므로 직접 읽기 등록
        self.param_worker.add_read_param_ptr(self.param_manager.get_by_full_path("Cluster.Settings.Number of Valves"))

    def on_clicked_create_eds(self):
        file_path, _ = QFileDialog.getSaveFileName(self, "Save EDS File", "", "EDS Files (*.eds);;All Files (*)")
        if not file_path:
            return

        try:
            eds_file_helper.create_eds_file(file_path)
        except Exception as e:
            AppLogManager().get_logger(self.win_name).error(f"EDS 파일 생성 실패: {e}")
            QMessageBox.critical(self, "Error", f"Failed to create EDS file.\nError details: {e}")
            return

        QMessageBox.information(self, "Success", "EDS file has been created successfully.")
