from PySide6.QtCore import Signal
from b_core.b_datatype.general_enum import EtherCATRangeSettingOptEnum
from c_ui.b_control_packet.controls_with_label.l_enum_rw_widget import LEnumReadWriteWidget
from c_ui.b_control_packet.param_container.param_folder_widget import ParamFolderWidget

class ParamFolderIfaceEtherCATRangeSettingOptWidget(ParamFolderWidget):
    sig_changed_opt = Signal(int)
    def __init__(self, parent=None):
        super().__init__(folder_name="Interface EtherCAT.Range Setting Option", param_path=None, label_width = 210, parent=parent)

        self.opt = LEnumReadWriteWidget(enum_class=EtherCATRangeSettingOptEnum, label_text="Range Setting Option", label_width=300)
        self.opt.set_value(EtherCATRangeSettingOptEnum.BASIC.value)
        self.opt.commit()
        self.opt.sig_ui_changed.connect(self.on_changed_opt)
        self.add_widget(self.opt)

    def on_changed_opt(self):
        self.sig_changed_opt.emit(self.opt.get_value())
        self.opt.commit()