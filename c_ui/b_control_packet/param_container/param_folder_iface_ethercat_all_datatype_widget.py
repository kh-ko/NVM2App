from b_core.b_datatype.param_enum import EtherCATDataTypeEnum
from c_ui.b_control_packet.controls_with_label.l_enum_rw_widget import LEnumReadWriteWidget
from c_ui.b_control_packet.param.param_enum_rw_widget import ParamEnumReadWriteWidget
from b_core.c_manager.parameter_manager import ParamManager
from c_ui.b_control_packet.param_container.param_folder_widget import ParamFolderWidget

class ParamFolderIfaceEtherCATAllDataTypeWidget(ParamFolderWidget):
    def __init__(self, parent=None):
        super().__init__(folder_name="Interface EtherCAT.All Data Type", param_path=None, label_width = 210, parent=parent)

        self.datatype_components = []

        self.all_datatype_comp = LEnumReadWriteWidget(enum_class=EtherCATDataTypeEnum, label_text="All Data Type", label_width=300)
        self.all_datatype_comp.sig_ui_changed.connect(self.on_changed_all_datatype)
        self.add_widget(self.all_datatype_comp)
        
    def set_range_folder_widget(self, range_folder_widget):
        self.datatype_components = range_folder_widget.datatype_components

        for comp in self.datatype_components:
            comp.param.sig_value_changed.connect(self.handle_changed_datatype)

    def reload_datatype(self):
        self.handle_changed_datatype()

    def on_changed_all_datatype(self, value = None):
        if value is not None:
            self.all_datatype_comp.set_value(value)

        for comp in self.datatype_components:
            comp.blockSignals(True)
            comp.set_value(self.all_datatype_comp.get_value())
            comp.blockSignals(False)

    def handle_changed_datatype(self):
        is_unknown = False
        first_value = self.datatype_components[0].param.value

        for comp in self.datatype_components:
            if first_value != comp.param.value:
                is_unknown = True
                break
                
        if is_unknown:
            self.all_datatype_comp.set_value(None)
        else:
            self.all_datatype_comp.set_value(first_value)

        self.all_datatype_comp.commit()
        
        



