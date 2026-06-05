
from PySide6.QtWidgets import QVBoxLayout
from PySide6.QtWidgets import QHeaderView

from b_core.c_manager.parameter_manager import ParamManager

from c_ui.b_control_packet.base.base_groupbox import BaseGroupBox
from c_ui.b_control_packet.base.base_table import BaseTableWidget
from c_ui.b_control_packet.param_container.param_folder_widget import ParamFolderWidget
from c_ui.b_control_packet.param.param_checkdummy_rw_widget import ParamCheckDummyReadWriteWidget
from c_ui.b_control_packet.param.param_pres_rw_widget import ParamPresReadWriteWidget

class ParamFolderPresCtrlRampWidget(ParamFolderWidget):
    def __init__(self, parent=None):
        super().__init__(folder_name="Profile Ramp", param_path=None, label_width = 210, parent=parent)

        self.param_manager = ParamManager()

        param = ParamManager().get_by_full_path("Pressure Control.General Settings.Profile Ramp.Enable")       
        self.add_param(param)             
        param = ParamManager().get_by_full_path("Pressure Control.General Settings.Profile Ramp.Threshold Mode")   
        self.add_param(param)         
        param = ParamManager().get_by_full_path("Pressure Control.General Settings.Profile Ramp.Ramp Type")                 
        self.add_param(param)
        param = ParamManager().get_by_full_path("Pressure Control.General Settings.Profile Ramp.Actual Slope")              
        self.add_param(param)
        param = ParamManager().get_by_full_path("Pressure Control.General Settings.Profile Ramp.Controller Selector Bitmap")
        self.add_param(param)
        param = ParamManager().get_by_full_path("Pressure Control.General Settings.Profile Ramp.Segment Selector Bitmap")   
        self.selection_seg_dummy_component = ParamCheckDummyReadWriteWidget(param_full_path=f"{param.path}.{param.name}", parent=self)
        self.param_components.append(self.selection_seg_dummy_component)

        self.seg_group = BaseGroupBox("Segments", enable_border = False)
        self.seg_layout = QVBoxLayout(self.seg_group)
        self.seg_layout.setContentsMargins(0, 5, 0, 0)
        
        self.seg_table = BaseTableWidget()
        self.seg_table.setColumnCount(3)
        self.seg_table.setHorizontalHeaderLabels(["Select", "Slope", "Threshold"])
        
        # 테스트를 위해 3개의 행(Row)을 생성
        self.seg_table.setRowCount(10)

        for index in range(0,10):
            check_widget = self.selection_seg_dummy_component.item_list[index][0]
            self.seg_table.setCellWidget(index, 0, check_widget)
            param = ParamManager().get_by_full_path(f"Pressure Control.General Settings.Profile Ramp.Segment Slope [{index+1}]") 
            slope_widget = ParamPresReadWriteWidget(param_full_path=f"{param.path}.{param.name}", label_width=0)
            self.seg_table.setCellWidget(index, 1, slope_widget)
            self.param_components.append(slope_widget)

            param = ParamManager().get_by_full_path(f"Pressure Control.General Settings.Profile Ramp.Segment Threshold [{index+1}]") 
            thres_widget = ParamPresReadWriteWidget(param_full_path=f"{param.path}.{param.name}", label_width=0)
            self.seg_table.setCellWidget(index, 2, thres_widget)
            self.param_components.append(thres_widget)

        header = self.seg_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        self.seg_table.resizeRowsToContents()
        self.seg_table.setShowGrid(False)
        self.seg_table.setFixedHeight(300)

        self.seg_layout.addWidget(self.seg_table) 
        self.add_widget(self.seg_group)