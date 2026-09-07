from b_core.c_manager.app_log_manager import AppLogManager
from c_ui.b_control_ver2.d_param.param_win import ParamWin

class RestoreWin(ParamWin):

    # handle_changed_connection_info 오버라이드가 super().__init__() 중에도
    # 호출되므로 (미연결 상태로 창을 열 때) 클래스 기본값으로 존재해야 한다
    _is_backup_running = False

    def __init__(self, parent=None, win_name = None):
        super().__init__(parent=parent, win_name = win_name, paths = [], filter_param_paths = [], is_editblock_win=False, label_width=210, folder_max_width=None)
        self._log = AppLogManager().get_logger(self.win_name)

        self.toolbar.remove_action("Refresh")
        self.toolbar.add_action("Restore", self.on_clicked_restore)

    def on_clicked_restore(self):
        pass