import re

from PySide6.QtWidgets import QHeaderView
from PySide6.QtWidgets import QVBoxLayout
from b_core.c_manager.parameter_manager import ParamManager

from c_ui.b_control_packet.base.base_groupbox import BaseGroupBox
from c_ui.b_control_packet.base.base_label import BaseLabel
from c_ui.b_control_packet.base.base_table import BaseTableWidget
from c_ui.b_control_packet.param.param_checkdummy_rw_widget import ParamCheckDummyReadWriteWidget
from c_ui.b_control_packet.param_container.param_folder_widget import ParamFolderWidget

RE_BITMAP_LENGTH = re.compile(r"(.*?)\[Length:\s*(\d+)\]")

class ParamFolderIfaceDnetIoInWidget(ParamFolderWidget):
    def __init__(self, parent=None):
        super().__init__(folder_name="Connection Object.Input", param_path=None, label_width = 210, parent=parent)

        param = ParamManager().get_by_full_path("Interface DeviceNet.Connection Object.Input.Input IO Produced Assembly"   ); self.add_param(param)
        param = ParamManager().get_by_full_path("Interface DeviceNet.Connection Object.Input.Input length (Byte)"          ); self.add_param(param)
        param = ParamManager().get_by_full_path("Interface DeviceNet.Connection Object.Input.Input Name"                   ); self.add_param(param)
        param = ParamManager().get_by_full_path("Interface DeviceNet.Connection Object.Input.Input Selector 1"             ); self.add_param(param)
        param = ParamManager().get_by_full_path("Interface DeviceNet.Connection Object.Input.Input Selector 2"             ); self.add_param(param)
        param = ParamManager().get_by_full_path("Interface DeviceNet.Connection Object.Input.Input Selector 3"             ); self.add_param(param)
        param = ParamManager().get_by_full_path("Interface DeviceNet.Connection Object.Input.Input Selector 4"             ); self.add_param(param)
        param = ParamManager().get_by_full_path("Interface DeviceNet.Connection Object.Input.Input Selector 5"             ); self.add_param(param)
        param = ParamManager().get_by_full_path("Interface DeviceNet.Connection Object.Input.Input Selector 6"             ); self.add_param(param)
        param = ParamManager().get_by_full_path("Interface DeviceNet.Connection Object.Input.Input Selector 7"             ); self.add_param(param)
        param = ParamManager().get_by_full_path("Interface DeviceNet.Connection Object.Input.Input Selector 8"             ); self.add_param(param)
        param = ParamManager().get_by_full_path("Interface DeviceNet.Connection Object.Input.Input Selector 9"             ); self.add_param(param)
        param = ParamManager().get_by_full_path("Interface DeviceNet.Connection Object.Input.Input Selector 10"            ); self.add_param(param)
        param = ParamManager().get_by_full_path("Interface DeviceNet.Connection Object.Input.Input Selector 11"            ); self.add_param(param)
        param = ParamManager().get_by_full_path("Interface DeviceNet.Connection Object.Input.Input Selector 12"            ); self.add_param(param)
        param = ParamManager().get_by_full_path("Interface DeviceNet.Connection Object.Input.Input Selector 13"            ); self.add_param(param)
        param = ParamManager().get_by_full_path("Interface DeviceNet.Connection Object.Input.Input Selector 14"            ); self.add_param(param)
        param = ParamManager().get_by_full_path("Interface DeviceNet.Connection Object.Input.Input Selector 15"            ); self.add_param(param)
        param = ParamManager().get_by_full_path("Interface DeviceNet.Connection Object.Input.Input Selector 16"            ); self.add_param(param)
        param = ParamManager().get_by_full_path("Interface DeviceNet.Connection Object.Input.Input Selector 17"            ); self.add_param(param)
        param = ParamManager().get_by_full_path("Interface DeviceNet.Connection Object.Input.Input Selector 18"            ); self.add_param(param)
        param = ParamManager().get_by_full_path("Interface DeviceNet.Connection Object.Input.Input Selector 19"            ); self.add_param(param)
        param = ParamManager().get_by_full_path("Interface DeviceNet.Connection Object.Input.Input Selector 20"            ); self.add_param(param)

        self.selection_seg_dummy_component = ParamCheckDummyReadWriteWidget(param_full_path="Interface DeviceNet.Connection Object.Input.Input Selector Bitmap (old)", parent=self)
        self.param_components.append(self.selection_seg_dummy_component)

        self.seg_group = BaseGroupBox("Input Selector Bitmap (old)", enable_border = False)
        self.seg_layout = QVBoxLayout(self.seg_group)
        self.seg_layout.setContentsMargins(0, 5, 0, 0)
        
        self.seg_table = BaseTableWidget()
        self.seg_table.setColumnCount(2)
        self.seg_table.setHorizontalHeaderLabels(["Offset", "Item"])
        self.selector_list = []
        
        enum_class=self.selection_seg_dummy_component.param.ref_list
        # 테스트를 위해 3개의 행(Row)을 생성
        self.seg_table.setRowCount(len(enum_class))

        for index, enum_item in enumerate(enum_class):
            offset = BaseLabel("-")
            offset.setIndent(8) 
            self.seg_table.setCellWidget(index, 0, offset)
            check_widget = self.selection_seg_dummy_component.item_list[index][0]
            self.seg_table.setCellWidget(index, 1, check_widget)

            description = enum_item.description.strip()
            match = RE_BITMAP_LENGTH.search(description)
            length = 0
            if match:
                length = int(match.group(2))

            self.selector_list.append((offset,check_widget, length))
            check_widget.sig_value_changed.connect(self.on_check_widget_value_changed)

        header = self.seg_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        self.seg_table.resizeRowsToContents()
        self.seg_table.setShowGrid(False)
        self.seg_table.setFixedHeight(710)

        self.seg_layout.addWidget(self.seg_table) 
        self.add_widget(self.seg_group)

        self.on_check_widget_value_changed()

    def on_check_widget_value_changed(self):
        offset_value = 0

        for offset, check_widget, length in self.selector_list:
            if check_widget.get_value():
                offset.setText(f"{offset_value}")
                offset_value += length
            else:
                offset.setText("-")