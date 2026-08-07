from c_ui.b_control_ver2.c_values.read_only_values import ReadOnlyPresMaxValueWidget
from c_ui.b_control_ver2.b_base.buttons import BaseButton
from c_ui.b_control_ver2.d_param.param_values import ParamReadWritePresValueSpinBoxWidget
from b_core.b_datatype.param_enum import SensUnitEnum
from c_ui.b_control_ver2.c_values.read_write_values import ReadWriteEnumValueWidget
from c_ui.b_control_ver2.c_values.read_only_values import ReadOnlyPresValueWidget
from c_ui.b_control_ver2.d_param.param_values import ParamReadOnlyPresValueWidget
from c_ui.b_control_ver2.a_theme.tokens import tokens
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QVBoxLayout
from PySide6.QtWidgets import QHBoxLayout
from PySide6.QtCore import Signal

from c_ui.b_control_ver2.b_base.containers import PanelWidget

class MainPressurePanel(PanelWidget):
    def __init__(self, parent=None): 
        super().__init__(title="Pressure", is_big_title=True, parent = parent)
        # 콘텐츠를 좌/우 2열로 분할 — 왼쪽: 표시(actual / used target), 오른쪽: 입력(target)
        # (레이아웃만 중첩하고 QWidget 은 만들지 않는다 — plain QWidget 은
        #  qdarktheme 전역 배경 규칙에 노출되므로)
        split_layout = QHBoxLayout()
        split_layout.setContentsMargins(0, 0, 0, 0)
        split_layout.setSpacing(10)

        # 열 높이가 다를 때 위쪽 정렬 유지 (stretch 방식은 나중에 addWidget 이
        # stretch 뒤에 붙는 문제가 있어 정렬로 처리 — ScrolledPanelWidget 과 동일 규칙)
        self.left_layout = QVBoxLayout()
        self.left_layout.setContentsMargins(0, 0, 0, 0)
        self.left_layout.setSpacing(5)
        #self.left_layout.setAlignment(Qt.AlignTop)

        self.right_layout = QVBoxLayout()
        self.right_layout.setContentsMargins(0, 0, 0, 0)
        self.right_layout.setSpacing(5)
        self.right_layout.setAlignment(Qt.AlignTop)

        split_layout.addLayout(self.left_layout, 1)
        split_layout.addLayout(self.right_layout, 1)
        self.content_layout.addLayout(split_layout)

    def set_actual_pres_param(self, param):
        self._actual_posi_param = param

        t = tokens()
        widget = ParamReadOnlyPresValueWidget(param_full_path = f"{param.path}.{param.name}", force_label_text="Pres. Actual", is_vertical_mode = True)
        widget.value_widget.set_boxed(True)
        widget.value_widget.set_colors(text=t.panel_pres_text, bg=t.panel_pres_bg, border=t.panel_pres_border)
        self.left_layout.addWidget(widget)

    def set_target_pres_used_param(self, param):
        self._target_posi_used_param = param
        
        t = tokens()
        widget = ParamReadOnlyPresValueWidget(param_full_path = f"{param.path}.{param.name}", force_label_text="Pres. Used Target", is_vertical_mode = True)
        widget.value_widget.set_boxed(True)
        widget.value_widget.set_colors(text=t.panel_pres_text, bg=t.panel_pres_bg, border=t.panel_pres_border)
        self.left_layout.addWidget(widget)

        widget = ReadOnlyPresMaxValueWidget(label_text="Max Pres. Max", label_width=150, is_vertical_mode = True)
        widget.value_widget.set_boxed(True)
        widget.value_widget.set_colors(text=t.panel_pres_text, bg=t.panel_pres_bg, border=t.panel_pres_border)
        self.left_layout.addWidget(widget)

        widget = ReadWriteEnumValueWidget(enum_class = SensUnitEnum, label_text="Unit", is_vertical_mode = True)

        widget.set_value(value = SensUnitEnum.TORR.value, is_commit = True)
        widget.setEnabled(False)

        # 빈 공간(Stretch)을 넣어서 아래로 밀어내고 Unit 위젯을 추가
        self.left_layout.addStretch(1)
        self.left_layout.addWidget(widget)

    def set_target_pres_param(self, param):
        self._target_pres_param = param

        widget = ParamReadWritePresValueSpinBoxWidget(param_full_path = f"{param.path}.{param.name}", force_label_text="Pres. Target", is_vertical_mode = True)
        self.right_layout.addWidget(widget)

        widget = BaseButton("100")
        self.right_layout.addWidget(widget)
        widget = BaseButton("90")
        self.right_layout.addWidget(widget)
        widget = BaseButton("80")
        self.right_layout.addWidget(widget)
        widget = BaseButton("70")
        self.right_layout.addWidget(widget)
        widget = BaseButton("60")
        self.right_layout.addWidget(widget)
        widget = BaseButton("50")
        self.right_layout.addWidget(widget)