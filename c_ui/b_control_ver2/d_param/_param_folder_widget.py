from typing import Optional

from b_core.b_datatype.general_enum import ParamAccType
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QSizePolicy

from b_core.b_datatype.general_enum import ParamDisplayType
from b_core.c_manager.parameter_manager import ParamManager

from c_ui.b_control_packet.layout.my_card_widget import MyCardWidget
from c_ui.b_control_packet.param.param_text_ro_widget import ParamTextReadOnlyWidget
from c_ui.b_control_packet.param.param_enum_ro_widget import ParamEnumReadOnlyWidget
from c_ui.b_control_packet.param.param_enum_wo_widget import ParamEnumWriteOnlyWidget
from c_ui.b_control_packet.param.param_enum_rw_widget import ParamEnumReadWriteWidget
from c_ui.b_control_packet.param.param_hex_rw_widget import ParamHexReadWriteWidget
from c_ui.b_control_packet.param.param_btn_wo_widget import ParamBtnWriteOnlyWidget
from c_ui.b_control_packet.param.param_float_ro_widget import ParamFloatReadOnlyWidget
from c_ui.b_control_packet.param.param_num_ro_widget import ParamNumReadOnlyWidget
from c_ui.b_control_packet.param.param_bitmap_ro_widget import ParamBitmapReadOnlyWidget
from c_ui.b_control_packet.param.param_digi_ro_widget import ParamDigiReadOnlyWidget
from c_ui.b_control_packet.param.param_posi_ro_widget import ParamPosiReadOnlyWidget
from c_ui.b_control_packet.param.param_posi_rw_widget import ParamPosiReadWriteWidget
from c_ui.b_control_packet.param.param_pres_rw_widget import ParamPresReadWriteWidget
from c_ui.b_control_packet.param.param_pres_ro_widget import ParamPresReadOnlyWidget
from c_ui.b_control_packet.param.param_float_rw_widget import ParamFloatReadWriteWidget
from c_ui.b_control_packet.param.param_bitmap_rw_widget import ParamBitmapReadWriteWidget
from c_ui.b_control_packet.param.param_scale_rw_widget import ParamScaleReadWriteWidget
from c_ui.b_control_packet.param.param_scale_ro_widget import ParamScaleReadOnlyWidget
from c_ui.b_control_packet.param.param_ifacegain_rw_widget import ParamIfaceGainReadWriteWidget
from c_ui.b_control_packet.param.param_num_rw_widget import ParamNumReadWriteWidget
from c_ui.b_control_packet.param.param_hex_ro_widget import ParamHexReadOnlyWidget

class ParamFolderWidget(MyCardWidget):
    """타이틀, 구분선, 컨텐츠 영역을 가지는 카드 형태의 커스텀 위젯"""
    def __init__(self, folder_name, param_path:str=None, label_width = 150, parent=None):
        super().__init__(title=folder_name, parent=parent)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)

        self.label_width = label_width
        self.folder_name = folder_name
        if param_path:
            self.param_path = param_path
        else:
            self.param_path = folder_name

        self.param_manager = ParamManager()
        self.param_components = []

        if self.param_path:
            params = self.param_manager.get_params_in_folder(self.param_path)
            for param in params:
                self.add_param(param)


    def add_param(self, param) -> Optional[QWidget]:
        widget = None
        if param.display_type == ParamDisplayType.TEXT:
            if param.acc == ParamAccType.RO:
                widget = ParamTextReadOnlyWidget(param_full_path=f"{param.path}.{param.name}", label_width=self.label_width)
            else:
                pass
        elif param.display_type == ParamDisplayType.ENUM:
            if param.acc == ParamAccType.RO:
                widget = ParamEnumReadOnlyWidget(param_full_path=f"{param.path}.{param.name}", label_width=self.label_width)
            elif param.acc == ParamAccType.WO:
                widget = ParamEnumWriteOnlyWidget(param_full_path=f"{param.path}.{param.name}", label_width=self.label_width)
            else:
                widget = ParamEnumReadWriteWidget(param_full_path=f"{param.path}.{param.name}",label_width=self.label_width)
        elif param.display_type == ParamDisplayType.HEX:
            if param.acc == ParamAccType.RO:
                widget = ParamHexReadOnlyWidget(param_full_path=f"{param.path}.{param.name}",label_width=self.label_width)
            else:
                widget = ParamHexReadWriteWidget(param_full_path=f"{param.path}.{param.name}",label_width=self.label_width)
        elif param.display_type == ParamDisplayType.NUMBER:
            if param.acc == ParamAccType.RO:
                widget = ParamNumReadOnlyWidget(param_full_path=f"{param.path}.{param.name}",label_width=self.label_width)
            else:
                widget = ParamNumReadWriteWidget(param_full_path=f"{param.path}.{param.name}",label_width=self.label_width)
        elif param.display_type == ParamDisplayType.REAL:
            if param.acc == ParamAccType.RO:
                widget = ParamFloatReadOnlyWidget(param_full_path=f"{param.path}.{param.name}",label_width=self.label_width)
            else:
                widget = ParamFloatReadWriteWidget(param_full_path=f"{param.path}.{param.name}",label_width=self.label_width)
        elif param.display_type == ParamDisplayType.IFACE_GAIN:
            if param.acc == ParamAccType.RO:
                pass
            else:
                widget = ParamIfaceGainReadWriteWidget(f"{param.path}.{param.name}",label_width=self.label_width)
        elif param.display_type == ParamDisplayType.SCALE:
            if param.acc == ParamAccType.RO:
                widget = ParamScaleReadOnlyWidget(f"{param.path}.{param.name}",label_width=self.label_width)
            else:
                widget = ParamScaleReadWriteWidget(f"{param.path}.{param.name}",label_width=self.label_width)
        elif param.display_type == ParamDisplayType.BITMAP:
            if param.acc == ParamAccType.RO:
                widget = ParamBitmapReadOnlyWidget(f"{param.path}.{param.name}")
            else:
                widget = ParamBitmapReadWriteWidget(f"{param.path}.{param.name}")
        elif param.display_type == ParamDisplayType.ERR_NUM:
            if param.acc == ParamAccType.RO:
                widget = ParamDigiReadOnlyWidget(f"{param.path}.{param.name}",label_width=self.label_width)
        #    else:
        #        pass
        elif param.display_type == ParamDisplayType.BTN:
            widget = ParamBtnWriteOnlyWidget(f"{param.path}.{param.name}",label_width=self.label_width)
        elif param.display_type == ParamDisplayType.POSI:
            if param.acc == ParamAccType.RO:
                widget = ParamPosiReadOnlyWidget(f"{param.path}.{param.name}",label_width=self.label_width)
            else:
                widget = ParamPosiReadWriteWidget(f"{param.path}.{param.name}",label_width=self.label_width)
        elif param.display_type == ParamDisplayType.SENS_PRES or param.display_type == ParamDisplayType.SENS1_PRES or param.display_type == ParamDisplayType.SENS2_PRES or param.display_type == ParamDisplayType.PRESS_SLOPE:
            if param.acc == ParamAccType.RO:
                widget = ParamPresReadOnlyWidget(f"{param.path}.{param.name}",label_width=self.label_width)
            else:
                widget = ParamPresReadWriteWidget(f"{param.path}.{param.name}",label_width=self.label_width)

        if widget != None:
            self.param_components.append(widget)
            self.add_widget(widget)
        
        return widget