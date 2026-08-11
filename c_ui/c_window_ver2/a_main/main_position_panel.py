from PySide6.QtCore import Signal
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QVBoxLayout

from b_core.b_datatype.general_enum import PositionUnitEnum
from b_core.c_manager.local_setting_manager import LocalSettingManager

from c_ui.a_converter.position_converter_manager import PosiConverterManager
from c_ui.b_control_ver2.b_base.icons import GLYPH_EDIT
from c_ui.b_control_ver2.a_theme.tokens import tokens
from c_ui.b_control_ver2.b_base.buttons import BaseButton
from c_ui.b_control_ver2.b_base.containers import PanelWidget
from c_ui.b_control_ver2.c_values.read_write_values import ReadWriteEnumValueWidget
from c_ui.b_control_ver2.d_param.param_values import ParamReadOnlyPosiValueWidget, ParamReadWritePosiValueSpinBoxWidget


class MainPositionPanel(PanelWidget):
    sig_setpoint = Signal(str)

    def __init__(self, parent=None):
        super().__init__(title="Position", is_big_title=True, btn_icon = GLYPH_EDIT, btn_text = "Edit",parent = parent)
        self.local_setting_manager = LocalSettingManager()
        self.converter = PosiConverterManager()

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

        self.point_01_btn = BaseButton("100")
        self.right_layout.addWidget(self.point_01_btn)
        self.point_02_btn = BaseButton("90")
        self.right_layout.addWidget(self.point_02_btn)
        self.point_03_btn = BaseButton("80")
        self.right_layout.addWidget(self.point_03_btn)
        self.point_04_btn = BaseButton("70")
        self.right_layout.addWidget(self.point_04_btn)
        self.point_05_btn = BaseButton("60")
        self.right_layout.addWidget(self.point_05_btn)
        self.point_06_btn = BaseButton("50")
        self.right_layout.addWidget(self.point_06_btn)

        split_layout.addLayout(self.left_layout, 1)
        split_layout.addLayout(self.right_layout, 1)
        self.content_layout.addLayout(split_layout)

        self.point_01_btn.clicked.connect(self._on_point_01_clicked)
        self.point_02_btn.clicked.connect(self._on_point_02_clicked)
        self.point_03_btn.clicked.connect(self._on_point_03_clicked)
        self.point_04_btn.clicked.connect(self._on_point_04_clicked)
        self.point_05_btn.clicked.connect(self._on_point_05_clicked)
        self.point_06_btn.clicked.connect(self._on_point_06_clicked)

        self.converter.sig_posi_range_changed.connect(self._handle_posi_range_changed)
        self.local_setting_manager.sig_posi_setpoint01_changed.connect(self._handle_posi_setpoint01_changed)
        self.local_setting_manager.sig_posi_setpoint02_changed.connect(self._handle_posi_setpoint02_changed)
        self.local_setting_manager.sig_posi_setpoint03_changed.connect(self._handle_posi_setpoint03_changed)
        self.local_setting_manager.sig_posi_setpoint04_changed.connect(self._handle_posi_setpoint04_changed)
        self.local_setting_manager.sig_posi_setpoint05_changed.connect(self._handle_posi_setpoint05_changed)
        self.local_setting_manager.sig_posi_setpoint06_changed.connect(self._handle_posi_setpoint06_changed)

        self._handle_posi_range_changed()

    def set_actual_posi_param(self, param):
        self._actual_posi_param = param

        t = tokens()
        widget = ParamReadOnlyPosiValueWidget(param_full_path = f"{param.path}.{param.name}", force_label_text="Pos. Actual", is_vertical_mode = True)
        widget.value_widget.set_boxed(True)
        widget.value_widget.set_colors(text=t.panel_posi_text, bg=t.panel_posi_bg, border=t.panel_posi_border)
        self.left_layout.addWidget(widget)

    def set_target_posi_used_param(self, param):
        self._target_posi_used_param = param
        
        t = tokens()
        widget = ParamReadOnlyPosiValueWidget(param_full_path = f"{param.path}.{param.name}", force_label_text="Pos. Used Target", is_vertical_mode = True)
        widget.value_widget.set_boxed(True)
        widget.value_widget.set_colors(text=t.panel_posi_text, bg=t.panel_posi_bg, border=t.panel_posi_border)
        self.left_layout.addWidget(widget)

        widget = ReadWriteEnumValueWidget(enum_class = PositionUnitEnum, label_text="Unit", is_vertical_mode = True)

        widget.set_value(value = PositionUnitEnum.POSI_UNIT_PERCENT.value)
        widget.commit()
        widget.setEnabled(False)

        # 빈 공간(Stretch)을 넣어서 아래로 밀어내고 Unit 위젯을 추가
        self.left_layout.addStretch(1)
        self.left_layout.addWidget(widget)

    def set_target_posi_param(self, param):
        self._target_posi_param = param

        self.target_posi_widget = ParamReadWritePosiValueSpinBoxWidget(param_full_path = f"{param.path}.{param.name}", force_label_text="Pos. Target", is_vertical_mode = True)
        self.target_posi_widget.sig_edited_by_enter.connect(self._on_target_posi_edited_by_enter)
        self.right_layout.insertWidget(0, self.target_posi_widget)

    def _on_target_posi_edited_by_enter(self):
        value = self.target_posi_widget.get_value_str()
        if value is not None:
            self.sig_setpoint.emit(value)
        self.target_posi_widget.commit()

    def _on_point_01_clicked(self):
        value = self.converter.convert_dp_str_to_posi_str(self.point_01_btn.text())
        if value is not None:
            self.sig_setpoint.emit(value)

    def _on_point_02_clicked(self):
        value = self.converter.convert_dp_str_to_posi_str(self.point_02_btn.text())
        if value is not None:
            self.sig_setpoint.emit(value)

    def _on_point_03_clicked(self):
        value = self.converter.convert_dp_str_to_posi_str(self.point_03_btn.text())
        if value is not None:
            self.sig_setpoint.emit(value)

    def _on_point_04_clicked(self):
        value = self.converter.convert_dp_str_to_posi_str(self.point_04_btn.text())
        if value is not None:
            self.sig_setpoint.emit(value)

    def _on_point_05_clicked(self):
        value = self.converter.convert_dp_str_to_posi_str(self.point_05_btn.text())
        if value is not None:
            self.sig_setpoint.emit(value)

    def _on_point_06_clicked(self):
        value = self.converter.convert_dp_str_to_posi_str(self.point_06_btn.text())
        if value is not None:
            self.sig_setpoint.emit(value)

    def _handle_posi_range_changed(self):
        self._handle_posi_setpoint01_changed()
        self._handle_posi_setpoint02_changed()
        self._handle_posi_setpoint03_changed()
        self._handle_posi_setpoint04_changed()
        self._handle_posi_setpoint05_changed()
        self._handle_posi_setpoint06_changed()

    def _handle_posi_setpoint01_changed(self):
        value = self.converter.convert_pfs_to_dp_str(self.local_setting_manager.posi_setpoint01)
        self.point_01_btn.setText(value)

    def _handle_posi_setpoint02_changed(self):
        value = self.converter.convert_pfs_to_dp_str(self.local_setting_manager.posi_setpoint02)
        self.point_02_btn.setText(value)

    def _handle_posi_setpoint03_changed(self):
        value = self.converter.convert_pfs_to_dp_str(self.local_setting_manager.posi_setpoint03)
        self.point_03_btn.setText(value)

    def _handle_posi_setpoint04_changed(self):
        value = self.converter.convert_pfs_to_dp_str(self.local_setting_manager.posi_setpoint04)
        self.point_04_btn.setText(value)

    def _handle_posi_setpoint05_changed(self):
        value = self.converter.convert_pfs_to_dp_str(self.local_setting_manager.posi_setpoint05)
        self.point_05_btn.setText(value)

    def _handle_posi_setpoint06_changed(self):
        value = self.converter.convert_pfs_to_dp_str(self.local_setting_manager.posi_setpoint06)
        self.point_06_btn.setText(value)        
        

    



