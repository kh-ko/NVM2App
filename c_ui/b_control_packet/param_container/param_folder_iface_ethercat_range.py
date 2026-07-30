from c_ui.b_control_packet.param_container.param_folder_iface_ethercat_all_datatype_widget import ParamFolderIfaceEtherCATAllDataTypeWidget
from b_core.b_datatype.param_enum import EtherCATDataTypeEnum
from c_ui.b_control_packet.controls_with_label.l_enum_rw_widget import LEnumReadWriteWidget
from c_ui.b_control_packet.param.param_enum_ro_widget import ParamEnumReadOnlyWidget
from c_ui.b_control_packet.param.param_enum_rw_widget import ParamEnumReadWriteWidget
from PySide6.QtWidgets import QHeaderView
from c_ui.b_control_packet.base.base_label import BaseLabel
from c_ui.b_control_packet.param.param_enum_wo_widget import ParamEnumWriteOnlyWidget
from c_ui.b_control_packet.param.param_float_rw_widget import ParamFloatReadWriteWidget
from c_ui.b_control_packet.base.base_table import BaseTableWidget
from PySide6.QtWidgets import QVBoxLayout
from c_ui.b_control_packet.base.base_groupbox import BaseGroupBox
from b_core.c_manager.parameter_manager import ParamManager
from c_ui.b_control_packet.param_container.param_folder_widget import ParamFolderWidget

class ParamFolderIfaceEtherCATRangeWidget(ParamFolderWidget):
    def __init__(self, parent=None):
        super().__init__(folder_name="Interface EtherCAT.Range", param_path=None, label_width = 210, parent=parent)

        self.folder_all_datatype_widget : ParamFolderIfaceEtherCATAllDataTypeWidget = None
        self.datatype_components = []

        self.range_group = BaseGroupBox("Range", enable_border = False)
        self.range_layout = QVBoxLayout(self.range_group)
        self.range_layout.setContentsMargins(0, 5, 0, 0)
        
        self.range_table = BaseTableWidget()
        self.range_table.setColumnCount(4)
        self.range_table.setHorizontalHeaderLabels(["Name", "Data Type", "Lower", "Upper"])
        
        self.range_table.setRowCount(12)

        header = self.range_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        header.setSectionResizeMode(3, QHeaderView.Stretch)
        self.range_table.setShowGrid(False)
        self.range_table.setFixedHeight(610)

        self.range_layout.addWidget(self.range_table) 
        self.add_widget(self.range_group)

        self.add_range_row(  0, "Data Type", "Interface EtherCAT.Range.Pressure.Data type"                                  , "Pressure"                      )
        self.add_range_row(  0, "Lower"    , "Interface EtherCAT.Range.Pressure.Lower Limit Data Value"                     )
        self.add_range_row(  0, "Upper"    , "Interface EtherCAT.Range.Pressure.Upper Limit Data Value"                     )
        self.add_range_row(  1, "Data Type", "Interface EtherCAT.Range.Pressure sensor 1.Data type"                         , "Pressure sensor 1"             )
        self.add_range_row(  1, "Lower"    , "Interface EtherCAT.Range.Pressure sensor 1.Lower Limit Data Value"            )
        self.add_range_row(  1, "Upper"    , "Interface EtherCAT.Range.Pressure sensor 1.Upper Limit Data Value"            )
        self.add_range_row(  2, "Data Type", "Interface EtherCAT.Range.Pressure sensor 2.Data type"                         , "Pressure sensor 2"             )
        self.add_range_row(  2, "Lower"    , "Interface EtherCAT.Range.Pressure sensor 2.Lower Limit Data Value"            )
        self.add_range_row(  2, "Upper"    , "Interface EtherCAT.Range.Pressure sensor 2.Upper Limit Data Value"            )
        self.add_range_row(  3, "Data Type", "Interface EtherCAT.Range.Position.Data type"                                  , "Position"                      )
        self.add_range_row(  3, "Lower"    , "Interface EtherCAT.Range.Position.Lower Limit Data Value"                     )
        self.add_range_row(  3, "Upper"    , "Interface EtherCAT.Range.Position.Upper Limit Data Value"                     )
        self.add_range_row(  4, "Data Type", "Interface EtherCAT.Range.Target position.Data type"                           , "Target position"               )
        self.add_range_row(  4, "Lower"    , "Interface EtherCAT.Range.Target position.Lower Limit Data Value"              )
        self.add_range_row(  4, "Upper"    , "Interface EtherCAT.Range.Target position.Upper Limit Data Value"              )
        self.add_range_row(  5, "Data Type", "Interface EtherCAT.Range.Cluster valve position.Data type"                    , "Cluster valve position"        ) 
        self.add_range_row(  5, "Lower"    , "Interface EtherCAT.Range.Cluster valve position.Lower Limit Data Value"       )
        self.add_range_row(  5, "Upper"    , "Interface EtherCAT.Range.Cluster valve position.Upper Limit Data Value"       )
        self.add_range_row(  6, "Data Type", "Interface EtherCAT.Range.Pressure setpoint.Data type"                         , "Pressure setpoint"             )
        self.add_range_row(  6, "Lower"    , "Interface EtherCAT.Range.Pressure setpoint.Lower Limit Data Value"            )
        self.add_range_row(  6, "Upper"    , "Interface EtherCAT.Range.Pressure setpoint.Upper Limit Data Value"            )
        self.add_range_row(  7, "Data Type", "Interface EtherCAT.Range.Position setpoint.Data type"                         , "Position setpoint"             )
        self.add_range_row(  7, "Lower"    , "Interface EtherCAT.Range.Position setpoint.Lower Limit Data Value"            )
        self.add_range_row(  7, "Upper"    , "Interface EtherCAT.Range.Position setpoint.Upper Limit Data Value"            )
        self.add_range_row(  8, "Data Type", "Interface EtherCAT.Range.Pressure alignment setpoint.Data type"               , "Pressure alignment setpoint"   )
        self.add_range_row(  8, "Lower"    , "Interface EtherCAT.Range.Pressure alignment setpoint.Lower Limit Data Value"  )
        self.add_range_row(  8, "Upper"    , "Interface EtherCAT.Range.Pressure alignment setpoint.Upper Limit Data Value"  )
        self.add_range_row(  9, "Data Type", "Interface EtherCAT.Range.External digital sensor1.Data type"                  , "External digital sensor1"      )
        self.add_range_row(  9, "Lower"    , "Interface EtherCAT.Range.External digital sensor1.Lower Limit Data Value"     )
        self.add_range_row(  9, "Upper"    , "Interface EtherCAT.Range.External digital sensor1.Upper Limit Data Value"     )
        self.add_range_row( 10, "Data Type", "Interface EtherCAT.Range.External digital sensor2.Data type"                  , "External digital sensor2"      )
        self.add_range_row( 10, "Lower"    , "Interface EtherCAT.Range.External digital sensor2.Lower Limit Data Value"     )
        self.add_range_row( 10, "Upper"    , "Interface EtherCAT.Range.External digital sensor2.Upper Limit Data Value"     )
        self.add_range_row( 11, "Data Type", "Interface EtherCAT.Range.Cluster valve freeze position.Data type"             , "Cluster valve freeze position" )
        self.add_range_row( 11, "Lower"    , "Interface EtherCAT.Range.Cluster valve freeze position.Lower Limit Data Value")
        self.add_range_row( 11, "Upper"    , "Interface EtherCAT.Range.Cluster valve freeze position.Upper Limit Data Value")

        #self.seg_table.resizeRowsToContents()

        padding = 10
        for r in range(self.range_table.rowCount()):
            self.range_table.setRowHeight(r, self.range_table.rowHeight(r) + padding)

    def set_folder_all_datatype(self, folder_widget : ParamFolderIfaceEtherCATAllDataTypeWidget):
        self.folder_all_datatype_widget = folder_widget

    def add_range_row(self, row_idx, type, param_path, name = ""):
        param = ParamManager().get_by_full_path(param_path)
        param_component = None

        if type == "Data Type":
            name_component = BaseLabel(name); name_component.setWordWrap(False); name_component.setIndent(8) 
            param_component = ParamEnumReadWriteWidget (param_full_path=param_path, label_width=0)
            param_component.sig_ui_changed.connect(lambda r=row_idx: self.on_changed_datatype(r))
            self.range_table.setCellWidget(row_idx, 0, name_component)
            self.range_table.setCellWidget(row_idx, 1, param_component)        
            self.datatype_components.append(param_component)   
        elif type == "Lower":
            param_component = ParamFloatReadWriteWidget (param_full_path=param_path, label_width=0)
            self.range_table.setCellWidget(row_idx, 2, param_component)
        elif type == "Upper":
            param_component = ParamFloatReadWriteWidget (param_full_path=param_path, label_width=0)
            self.range_table.setCellWidget(row_idx, 3, param_component)

        self.param_components.append(param_component)

    def on_changed_datatype(self, idx):
        value = self.datatype_components[idx].get_value()
        self.folder_all_datatype_widget.on_changed_all_datatype(value)


