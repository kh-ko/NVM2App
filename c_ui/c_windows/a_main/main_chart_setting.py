from c_ui.b_control_packet.controls_with_label.l_float_rw_widget import LFloatReadWriteWidget
from PySide6.QtCore import Signal
from PySide6.QtWidgets import QCheckBox
from PySide6.QtWidgets import QHBoxLayout
from PySide6.QtWidgets import QLabel
from PySide6.QtWidgets import QVBoxLayout
from PySide6.QtWidgets import QWidget

from b_core.b_datatype.general_enum import MainChartRangeModeEnum

from c_ui.b_control_packet.layout.my_card_widget import MyCardWidget
from c_ui.b_control_packet.controls.my_value_input_enum import MyValueInputEnum

class MainChartSettingPanel(QWidget):
    sig_changed_settings = Signal()

    def __init__(self, title, target_color, actual_color, parent=None):
        super().__init__(parent)

        self.is_init = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.legend_card = MyCardWidget(f"{title} Legend")

        target_container = QWidget()
        target_layout = QHBoxLayout(target_container)
        target_layout.setContentsMargins(0, 0, 0, 0)
        self.chk_target = QCheckBox("Target")
        self.chk_target.setChecked(True)
        self.chk_target.clicked.connect(self._on_chk_target_toggled)
        self.icon_target = QLabel("\ue5d3") # Material Icons의 유니코드 예시 (직접 수정 필요)
        self.icon_target.setStyleSheet(f"font-family: 'Material Icons'; color: {target_color}; font-size: 18px;")
        target_layout.addWidget(self.chk_target)
        target_layout.addStretch() # 체크박스는 좌측에, 아이콘은 우측에 밀착시키기 위함
        target_layout.addWidget(self.icon_target)
        self.legend_card.add_widget(target_container)
        
        actual_container = QWidget()
        actual_layout = QHBoxLayout(actual_container)
        actual_layout.setContentsMargins(0, 0, 0, 0)
        self.chk_actual = QCheckBox("Actual")
        self.chk_actual.setChecked(True)
        self.chk_actual.clicked.connect(self._on_chk_actual_toggled)
        self.icon_actual = QLabel("\ue15b") # Material Icons의 유니코드 예시 (직접 수정 필요)
        self.icon_actual.setStyleSheet(f"font-family: 'Material Icons'; color: {actual_color}; font-size: 18px;")
        
        actual_layout.addWidget(self.chk_actual)
        actual_layout.addStretch()
        actual_layout.addWidget(self.icon_actual)
        
        # 카드에 컨테이너 위젯들 추가
        self.legend_card.add_widget(target_container)
        self.legend_card.add_widget(actual_container)

        self.scale_card = MyCardWidget(f"{title} Range")
        
        self.mode_combo = MyValueInputEnum(enum_class = MainChartRangeModeEnum)
        self.mode_combo.setMinimumWidth(10)
        
        self.mode_combo.currentIndexChanged.connect(self._on_mode_changed)

        self.spin_min = LFloatReadWriteWidget(label_text="Min", label_width=20)
        self.spin_min.setEnabled(False) 
        self.spin_min.sig_value_changed.connect(self._on_min_editing_finished)
        
        self.spin_max = LFloatReadWriteWidget(label_text="Max", label_width=20)
        self.spin_max.setEnabled(False) 
        self.spin_max.sig_value_changed.connect(self._on_max_editing_finished)
        
        self.scale_card.add_widget(self.mode_combo)
        self.scale_card.add_widget(self.spin_min)
        self.scale_card.add_widget(self.spin_max)
        
        # 레이아웃에 카드들 배치
        layout.addWidget(self.legend_card, stretch=10)
        layout.addWidget(self.scale_card, stretch=26)
        #layout.addStretch()

    def _on_mode_changed(self, index):
        """콤보박스 모드가 Custom일 때만 Min/Max 스핀박스 활성화"""
        is_custom = (self.mode_combo.get_value() == MainChartRangeModeEnum.CUSTOM.value)
        self.spin_min.setEnabled(is_custom)
        self.spin_max.setEnabled(is_custom)
        
        if self.is_init == True:
            self.sig_changed_settings.emit()

    def _on_chk_target_toggled(self):
        if self.is_init == True:
            self.sig_changed_settings.emit()

    def _on_chk_actual_toggled(self):
        if self.is_init == True:
            self.sig_changed_settings.emit()

    def _on_min_editing_finished(self):
        if self.is_init == True:
            self.sig_changed_settings.emit()
            self.spin_min.commit()

    def _on_max_editing_finished(self):
        if self.is_init == True:
            self.sig_changed_settings.emit()
            self.spin_max.commit()

    def set_init_settings(self, b_en_actual, b_en_target, scale_mode, scale_custom_min, scale_custom_max, decimal_places):
        self.chk_actual.setChecked(b_en_actual)
        self.chk_target.setChecked(b_en_target)
        self.mode_combo.set_value(scale_mode)

        self.spin_min.set_value(scale_custom_min)
        self.spin_min.commit()
        self.spin_max.set_value(scale_custom_max)
        self.spin_max.commit()

        self.set_decimal_places(decimal_places)
        
        self.is_init = True

    def set_decimal_places(self, decimal_places):
        self.spin_min.set_decimal_places(decimal_places)
        self.spin_max.set_decimal_places(decimal_places)
        
        