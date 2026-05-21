
from b_core.b_datatype.general_enum import ParamAccType
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QVBoxLayout, QWidget

from b_core.b_datatype.general_enum import ParamDisplayType
from b_core.c_manager.parameter_manager import ParamManager

from c_ui.b_components.a_custom_base.custom_description import CustomDescription
from c_ui.b_components.d_usercontrol.a_param_controls.param_text_label_widget import ParamTextLabelWidget
from c_ui.b_components.d_usercontrol.a_param_controls.param_enum_widget import ParamEnumWidget
from c_ui.b_components.d_usercontrol.a_param_controls.param_hex_input import ParamHexInputWidget
from c_ui.b_components.d_usercontrol.a_param_controls.param_float_label_widget import ParamFloatLabelWidget
from c_ui.b_components.d_usercontrol.a_param_controls.param_number_label_widget import ParamNumberLabelWidget
from c_ui.b_components.d_usercontrol.a_param_controls.param_digi_label_widget import ParamDigiLabelWidget
from c_ui.b_components.d_usercontrol.a_param_controls.param_bitmap_label_widget import ParamBitmapLabelWidget

class ParamFolderWidget(QWidget):
    """타이틀, 구분선, 컨텐츠 영역을 가지는 카드 형태의 커스텀 위젯"""
    def __init__(self, folder_name, parent=None):
        super().__init__(parent)

        self.folder_name = folder_name
        #self.param_manager = ParamManager()
        self.setObjectName("Folder")

        self.setAttribute(Qt.WA_StyledBackground, True)
        
        # QWidget#Panel 에만 스타일이 적용되도록 제한 (#Panel)
        self.setStyleSheet("""
            QWidget#Folder {
                background-color: white;
                border: 1px solid #dcdcdc;
            }
        """)
        
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(10, 10, 10, 10)
        self.main_layout.setSpacing(5)
        
        # 1. 상단 타이틀
        lbl_title = CustomDescription(folder_name)
        self.main_layout.addWidget(lbl_title)

        line = QFrame()
        line.setFixedHeight(1) # 선의 두께를 명시적으로 1px로 지정
        # 스타일시트로 배경색 지정 및 위아래 여백 설정
        line.setStyleSheet("background-color: #dcdcdc; border: none; margin-top: 5px; margin-bottom: 5px;")
        self.main_layout.addWidget(line)
        
        self.param_components = []
        #params = self.param_manager.get_params_in_folder(folder_name)

        #for param in params:
        #    self.add_param(param)

    def add_param(self, param):
        widget = None
        if param.display_type == ParamDisplayType.TEXT:
            if param.acc == ParamAccType.RO:
                widget = ParamTextLabelWidget(f"{param.path}.{param.name}")
            else:
                pass
        elif param.display_type == ParamDisplayType.ENUM:
            if param.acc == ParamAccType.RO:
                pass
            else:
                widget = ParamEnumWidget(f"{param.path}.{param.name}")
        elif param.display_type == ParamDisplayType.HEX:
            if param.acc == ParamAccType.RO:
                pass
            else:
                widget = ParamHexInputWidget(f"{param.path}.{param.name}")
        elif param.display_type == ParamDisplayType.NUMBER:
            if param.acc == ParamAccType.RO:
                widget = ParamNumberLabelWidget(f"{param.path}.{param.name}")
            else:
                pass
        elif param.display_type == ParamDisplayType.REAL:
            if param.acc == ParamAccType.RO:
                widget = ParamFloatLabelWidget(f"{param.path}.{param.name}")
            else:
                pass
        elif param.display_type == ParamDisplayType.BITMAP:
            if param.acc == ParamAccType.RO:
                widget = ParamBitmapLabelWidget(f"{param.path}.{param.name}")
            else:
                pass
        elif param.display_type == ParamDisplayType.DIGI_NUM:
            if param.acc == ParamAccType.RO:
                widget = ParamDigiLabelWidget(f"{param.path}.{param.name}")
            else:
                pass

        if widget != None:
            self.param_components.append(widget)
            self.main_layout.addWidget(widget)