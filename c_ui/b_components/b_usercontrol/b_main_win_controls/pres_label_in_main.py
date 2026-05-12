from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QVBoxLayout

from b_core.b_datatype import param_enum as p_enum
from b_core.b_datatype.parameter import Parameter
from b_core.c_manager.parameter_manager import ParamManager

from c_ui.a_converter.pressure_converter_manager import PresConverterManager
from c_ui.b_components.a_custom.custom_label import CustomLabel

class PresLabelInMain(QWidget):
    def __init__(self, title_text, param_full_path : str, parent=None):
        super().__init__(parent)

        self._decimal_places = 2

        # 위젯 자체의 레이아웃 설정
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0) # 다른 레이아웃에 들어갈 때를 위해 여백 제거
        self.main_layout.setSpacing(0)
        
        # 타이틀 라벨 생성
        self.lbl_title = CustomLabel(title_text)
        
        # 값 라벨 생성
        self.lbl_value = CustomLabel("-")
        self.lbl_value.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.lbl_value.setStyleSheet("""
            QLabel {
                background-color: #ffebee;
                border: 1px solid #dcdcdc;
                border-radius: 4px;
                padding: 4px;
                color: #c62828;
            }
        """)

        # 레이아웃에 위젯 추가
        self.main_layout.addWidget(self.lbl_title)
        self.main_layout.addWidget(self.lbl_value)

        self.value_param = ParamManager().get_by_full_path(param_full_path)    
        self.converter = PresConverterManager()    

        self.value_param.sig_value_changed.connect(self.handle_value_changed)
        self.value_param.sig_is_not_support_changed.connect(self.handle_is_not_support_changed)
        self.converter.sig_pres_range_changed.connect(self.handle_value_changed)

        self.handle_value_changed()

    def set_decimals(self, decimal_places: int):
        self._decimal_places = decimal_places

        if not self.value_param.str_value:
            return

        display_value = self.converter.convert_iface_pres_to_dp_pres(self.value_param.value)
        self.lbl_value.setText(f"{display_value:.{self._decimal_places}f}")

    def handle_value_changed(self):
        if not self.value_param.str_value:
            return

        display_value = self.converter.convert_iface_pres_to_dp_pres(self.value_param.value)
        self.lbl_value.setText(f"{display_value:.{self._decimal_places}f}")
        
    def handle_is_not_support_changed(self, is_not_support : bool):
        if is_not_support:
            self.lbl_value.setText("Not Support")