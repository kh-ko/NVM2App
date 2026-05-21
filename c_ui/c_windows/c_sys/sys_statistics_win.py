import json
from PySide6.QtCore import Qt
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import QWidget, QMainWindow, QFileDialog, QMessageBox, QScrollArea, QVBoxLayout

from b_core.b_datatype.general_enum import ParamAccType
from b_core.c_manager.parameter_manager import ParamManager
from b_core.e_worker.parameter_worker import ParameterWorker

from c_ui.b_components.a_custom_base.custom_toolbar import CustomToolBar
from c_ui.b_components.d_usercontrol.a_param_controls.param_folder_widget import ParamFolderWidget
from c_ui.c_windows.param_base_win import ParamBaseWin

class SysStatisticsWin(ParamBaseWin):
    """

    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("System >> Statistics")

        folder_widget = ParamFolderWidget(folder_name="System.Statistics")

        params = self.param_manager.get_params_in_folder(folder_widget.folder_name)

        for param in params:
            self.param_worker.add_read_param_ptr(param)
            folder_widget.add_param(param)

        self.parameter_folder_widgets.append(folder_widget)
        self.content_layout.addWidget(folder_widget)

        self.content_layout.addStretch()

        self.init_toolbar()
        self.init_end()
