
from PySide6.QtCore import Signal
from PySide6.QtWidgets import QHeaderView, QAbstractItemView
from PySide6.QtCore import QObject
import re

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QScrollArea
from PySide6.QtWidgets import QSizePolicy
from PySide6.QtWidgets import QHBoxLayout
from PySide6.QtWidgets import QVBoxLayout, QWidget

from b_core.b_datatype.general_enum import ParamDisplayType
from b_core.c_manager.local_setting_manager import LocalSettingManager
from b_core.c_manager.parameter_manager import ParamManager

from c_ui.a_converter.float_converter_manager import FloatConverterManager
from c_ui.b_control_packet.base import my_style
from c_ui.b_control_packet.base.base_label import BaseLabel
from c_ui.b_control_packet.base.base_table import BaseTableWidget
from c_ui.b_control_packet.base.base_labelcolorbox import BaseLabelColorBox
from c_ui.b_control_packet.param_container.param_folder_widget import ParamFolderWidget

class ParamClusterMonitorItem(QObject):
    def __init__(self, table, addr, sub_params, parent=None):
        super().__init__(parent)

        self.enabled = False
        self.table = table
        self.addr = addr
        self.converter = FloatConverterManager()
        self.local_setting = LocalSettingManager()
        self.err_warn_param_list = []

        self.comp_addr = BaseLabel("-")
        self.comp_addr.setIndent(8) 
        self.table.setCellWidget(self.addr, 0, self.comp_addr)

        self.comp_act_posi = BaseLabel("-")
        self.comp_act_posi.setIndent(8) 
        self.table.setCellWidget(self.addr, 1, self.comp_act_posi)

        self.comp_pos_offset = BaseLabel("-")
        self.comp_pos_offset.setIndent(8) 
        self.table.setCellWidget(self.addr, 2, self.comp_pos_offset)

        self.comp_pos_ctrl_speed = BaseLabel("-")
        self.comp_pos_ctrl_speed.setIndent(8) 
        self.table.setCellWidget(self.addr, 3, self.comp_pos_ctrl_speed)

        self.comp_freeze = BaseLabel("-")
        self.comp_freeze.setIndent(8) 
        self.table.setCellWidget(self.addr, 4, self.comp_freeze)

        self.comp_access_mode = BaseLabel("-")
        self.comp_access_mode.setIndent(8) 
        self.table.setCellWidget(self.addr, 5, self.comp_access_mode)

        self.comp_control_mode = BaseLabel("-")
        self.comp_control_mode.setIndent(8) 
        self.table.setCellWidget(self.addr, 6, self.comp_control_mode)

        self.comp_compressed_air_value = BaseLabel("-")
        self.comp_compressed_air_value.setIndent(8) 
        self.table.setCellWidget(self.addr, 7, self.comp_compressed_air_value)

        self.comp_err_warn = BaseLabelColorBox("Err/Warn")
        self.comp_err_warn.setIndent(8) 
        self.comp_err_warn.set_color(label_color=my_style.STYLE_ERR_BADGE_LABEL_COLOR, bg_color=my_style.STYLE_ERR_BADGE_BG_COLOR)
        self.table.setCellWidget(self.addr, 8, self.comp_err_warn)


        for offset, data_len, param in sub_params:
            if param.name == "Actual Position":
                param.sig_value_changed.connect(self.handle_actual_position_changed)
                self.act_posi_param = param
            elif param.name == "Position Offset Used":
                param.sig_value_changed.connect(self.handle_position_offset_changed)
                self.pos_offset_param = param
            elif param.name == "Position Control Speed Used (%)":
                param.sig_value_changed.connect(self.handle_position_control_speed_changed)
                self.pos_ctrl_speed_param = param
            elif param.name == "Freeze":
                param.sig_value_changed.connect(self.handle_freeze_changed)
                self.freeze_param = param
            elif param.name == "Access Mode Used":
                param.sig_value_changed.connect(self.handle_access_mode_changed)
                self.access_mode_param = param
            elif param.name == "Control Mode Used":
                param.sig_value_changed.connect(self.handle_control_mode_changed)
                self.control_mode_param = param
            elif param.name == "Compressed Air Value(mbar)":
                param.sig_value_changed.connect(self.handle_compressed_air_value_changed)
                self.compressed_air_value_param = param
            elif param.name == "Service Request":
                param.sig_value_changed.connect(self.handle_changed_err_warn)
                self.err_warn_param_list.append(param)
            elif param.name == "Parameter Error":
                param.sig_value_changed.connect(self.handle_changed_err_warn)
                self.err_warn_param_list.append(param)
            elif param.name == "PFO Not Fully Charged":
                param.sig_value_changed.connect(self.handle_changed_err_warn)
                self.err_warn_param_list.append(param)
            elif param.name == "Compressed Air Failure":
                param.sig_value_changed.connect(self.handle_changed_err_warn)
                self.err_warn_param_list.append(param)
            elif param.name == "Sensor Factor Warning":
                param.sig_value_changed.connect(self.handle_changed_err_warn)
                self.err_warn_param_list.append(param)
            elif param.name == "Offline Mode":
                param.sig_value_changed.connect(self.handle_changed_err_warn)
                self.err_warn_param_list.append(param)
            elif param.name == "ROM Error":
                param.sig_value_changed.connect(self.handle_changed_err_warn)
                self.err_warn_param_list.append(param)
            elif param.name == "No Interface Found":
                param.sig_value_changed.connect(self.handle_changed_err_warn)
                self.err_warn_param_list.append(param)
            elif param.name == "No ADC Signal":
                param.sig_value_changed.connect(self.handle_changed_err_warn)
                self.err_warn_param_list.append(param)
            elif param.name == "No ADC Siganl On Logic":
                param.sig_value_changed.connect(self.handle_changed_err_warn)
                self.err_warn_param_list.append(param)

    def set_enabled(self, value):
        self.enabled = value
        if value:
            self.comp_addr.set_text(f"{self.addr}")
            self.handle_actual_position_changed()
            self.handle_position_offset_changed()
            self.handle_position_control_speed_changed()
            self.handle_freeze_changed()
            self.handle_access_mode_changed()
            self.handle_control_mode_changed()
            self.handle_compressed_air_value_changed()
            self.handle_changed_err_warn()
        else:
            self.comp_addr.set_text("-")
            self.comp_act_posi.set_text("-")
            self.comp_pos_offset.set_text("-")
            self.comp_pos_ctrl_speed.set_text("-")
            self.comp_freeze.set_text("-")
            self.comp_access_mode.set_text("-")
            self.comp_control_mode.set_text("-")
            self.comp_compressed_air_value.set_text("-")
            self.comp_err_warn.set_color(label_color="transparent", bg_color="transparent")

    def handle_actual_position_changed(self):
        if self.act_posi_param.value is None:
            self.comp_act_posi.set_text("-")
        else:
            value = self.act_posi_param.value / 1000
            value_str = self.converter.to_str_with_decimal_places(value, self.local_setting.posi_decimal_places)
            self.comp_act_posi.set_text(value_str)

    def handle_position_offset_changed(self):
        if self.pos_offset_param.value is None:
            self.comp_pos_offset.set_text("-")
        else:
            value = self.pos_offset_param.value / 1000
            value_str = self.converter.to_str_with_decimal_places(value, self.local_setting.posi_decimal_places)
            self.comp_pos_offset.set_text(value_str)

    def handle_position_control_speed_changed(self):
        if self.pos_ctrl_speed_param.value is None:
            self.comp_pos_ctrl_speed.set_text("-")
        else:
            value = self.pos_ctrl_speed_param.value / 10
            value_str = self.converter.to_str_with_decimal_places(value, 1)
            self.comp_pos_ctrl_speed.set_text(f"{value_str} %")

    def handle_freeze_changed(self):
        if self.freeze_param.value is None:
            self.comp_freeze.set_text("-")
        else:
            value_str = self.freeze_param.ref_list.get_desc(self.freeze_param.value)
            self.comp_freeze.set_text(value_str)    

    def handle_access_mode_changed(self):
        value_str = self.access_mode_param.ref_list.get_desc(self.access_mode_param.value)
        self.comp_access_mode.set_text(value_str)   

    def handle_control_mode_changed(self):
        value_str = self.control_mode_param.ref_list.get_desc(self.control_mode_param.value)
        
        self.comp_control_mode.set_text(value_str) 

    def handle_compressed_air_value_changed(self):
        if self.compressed_air_value_param.value is None:
            self.comp_compressed_air_value.set_text("-")
        else:
            value_str = self.converter.to_str(self.compressed_air_value_param.value)
            self.comp_compressed_air_value.set_text(f"{value_str} mbar")

    def handle_changed_err_warn(self):
        for param in self.err_warn_param_list:
            if param.value is not None and param.value == 1:
                self.comp_err_warn.set_color(label_color=my_style.STYLE_ERR_BADGE_LABEL_COLOR, bg_color=my_style.STYLE_ERR_BADGE_BG_COLOR)
                return
        self.comp_err_warn.set_color(label_color="transparent", bg_color="transparent")

class ParamFolderClusterMonitorWidget(ParamFolderWidget):
    sig_selected_addr = Signal(int)

    def __init__(self, parent=None):
        super().__init__(folder_name="Cluster Monitor", param_path=None, label_width = 210, parent=parent)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)

        self.status_item_list = []
        self.status_table = BaseTableWidget()
        self.status_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.status_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.status_table.setColumnCount(9)
        self.status_table.setHorizontalHeaderLabels(["Addr", "Act Posi", "Posi Offset", "Posi Speed", "Freeze", "Acc Mode", "Ctrl Mode", "Air[mbar]", "Err/Warn"])
        self.status_table.setRowCount(30)

        for num in range(0, 30):
            status_param = ParamManager().get_by_full_path(f"Cluster.Device {num}.Status")
            status_item = ParamClusterMonitorItem(self.status_table, num, status_param.sub_items, self)
            self.status_item_list.append(status_item)

        header = self.status_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        for col in range(1, 9):
            header.setSectionResizeMode(col, QHeaderView.Stretch)
        self.status_table.resizeRowsToContents()
        self.status_table.setShowGrid(False)

        self.add_widget(self.status_table)

        # 부모 클래스(MyCardWidget) 생성 시 하단에 자동으로 추가되는 stretch(스페이서)를 제거합니다.
        layout = self.main_layout
        if layout.count() > 0:
            last_item = layout.itemAt(layout.count() - 1)
            if last_item.spacerItem():
                layout.removeItem(last_item)

        # 콘텐츠 영역 위젯과 테이블 위젯의 세로 크기 정책을 Expanding으로 변경하여 부모 영역을 가득 채우도록 합니다.
        self.content_widget.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        self.status_table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self.status_table.selectionModel().selectionChanged.connect(self.on_selection_changed)

    def on_selection_changed(self, selected, deselected):
        indexes = self.status_table.selectionModel().selectedRows()
        if indexes:
            selected_row = indexes[0].row()
            self.sig_selected_addr.emit(selected_row)
        else:
            self.sig_selected_addr.emit(-1)

    def set_cluster_num(self, num):
        for item in self.status_item_list:
            item.set_enabled(False)

        if num is None:
            self.on_selection_changed(None, None)
            return

        for num in range(0, num):
            self.status_item_list[num].set_enabled(True)

        self.on_selection_changed(None, None)

        