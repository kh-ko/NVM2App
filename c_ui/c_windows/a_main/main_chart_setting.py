from PySide6.QtCore import Signal
from PySide6.QtWidgets import QCheckBox
from PySide6.QtWidgets import QHBoxLayout
from PySide6.QtWidgets import QDoubleSpinBox
from PySide6.QtWidgets import QComboBox
from PySide6.QtWidgets import QLabel
from PySide6.QtWidgets import QVBoxLayout
from PySide6.QtWidgets import QWidget

from c_ui.b_components.b_custom_layout.custom_card_widget import CustomCardWidget

class MainChartSettingPanel(QWidget):
    sig_changed_settings = Signal()

    def __init__(self, title, target_color, actual_color, parent=None):
        super().__init__(parent)

        self.is_init = False
        self.decimal_places = 2

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.legend_card = CustomCardWidget(f"{title} Legend")

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

        self.scale_card = CustomCardWidget(f"{title} Range")
        
        self.mode_combo = QComboBox()
        self.mode_combo.setMinimumWidth(10)
        self.mode_combo.addItems(["Auto", "Full", "Custom"])
        self.mode_combo.setStyleSheet("""
            /* 콤보박스 기본 디자인 */
            QComboBox {
                color: black;
                border: 1px solid #dcdcdc;
                border-radius: 4px;
                padding: 4px 8px;
                background-color: white;
                min-height: 24px;
            }
            
            /* 콤보박스에 마우스를 올렸을 때 */
            QComboBox:hover {
                border: 1px solid #1976d2;
            }

            QComboBox:disabled {
                /* rgba(R, G, B, Alpha) 형태로 작성하며, Alpha 값 127이 약 50% 투명도입니다. */
                color: rgba(0, 0, 0, 127);                 /* 검은색 글자 투명도 50% */
                border: 1px solid rgba(220, 220, 220, 127);/* #dcdcdc 테두리 투명도 50% */
                background-color: rgba(255, 255, 255, 127);/* 하얀색 배경 투명도 50% */
            }
            
            /* 콤보박스 우측 화살표 영역 */
            QComboBox::drop-down {
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 20px;
                border-left: 1px solid #dcdcdc;
            }

            /* ★ 콤보박스 드롭다운 팝업 리스트 스타일 (테두리 추가) ★ */
            QComboBox QAbstractItemView {
                border: 1px solid #a0a0a0; /* 팝업창 테두리 추가 */
                border-radius: 4px;
                background-color: white;
                outline: 0px; /* 클릭 시 생기는 점선 테두리 제거 */
                selection-background-color: #e3f2fd; /* 선택 항목 배경색 */
                selection-color: #1976d2;            /* 선택 항목 글자색 */
            }
        """)

        self.mode_combo.currentIndexChanged.connect(self._on_mode_changed)
        
        spinbox_style = """
            QDoubleSpinBox {
                border: 1px solid #dcdcdc; /* 테두리 두께, 스타일(실선), 색상 */
                border-radius: 4px;        /* 모서리를 살짝 둥글게 */
                padding: 2px;              /* 내부 텍스트와 테두리 사이의 여백 */
            }
            QDoubleSpinBox:disabled {
                color: #dcdcdc;            /* 비활성화일 때의 글자색 */
            }
        """

        self.spin_min = QDoubleSpinBox()
        self.spin_min.setMinimumWidth(10)
        self.spin_min.setRange(-999999.0, 999999.0)
        self.spin_min.setPrefix("Min: ")
        self.spin_min.setEnabled(False) 
        self.spin_min.setStyleSheet(spinbox_style)
        self.spin_min.editingFinished.connect(self._on_min_editing_finished)
        
        self.spin_max = QDoubleSpinBox()
        self.spin_max.setMinimumWidth(10)
        self.spin_max.setRange(-999999.0, 999999.0)
        self.spin_max.setPrefix("Max: ")
        self.spin_max.setEnabled(False)
        self.spin_max.setStyleSheet(spinbox_style)
        self.spin_max.editingFinished.connect(self._on_max_editing_finished)
        
        self.scale_card.add_widget(self.mode_combo)
        self.scale_card.add_widget(self.spin_min)
        self.scale_card.add_widget(self.spin_max)
        
        # 레이아웃에 카드들 배치
        layout.addWidget(self.legend_card, stretch=10)
        layout.addWidget(self.scale_card, stretch=26)
        #layout.addStretch()

    def _on_mode_changed(self, index):
        """콤보박스 모드가 Custom일 때만 Min/Max 스핀박스 활성화"""
        is_custom = (self.mode_combo.currentIndex() == 2) # 0:Auto, 1:Full, 2:Custom
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

    def _on_max_editing_finished(self):
        if self.is_init == True:
            self.sig_changed_settings.emit()

    def set_init_settings(self, b_en_actual, b_en_target, scale_mode_idx, scale_custom_min, scale_custom_max, decimal_places):
        self.decimal_places = decimal_places

        self.chk_actual.setChecked(b_en_actual)
        self.chk_target.setChecked(b_en_target)
        self.mode_combo.setCurrentIndex(scale_mode_idx)

        self.spin_min.setValue(scale_custom_min)
        self.spin_max.setValue(scale_custom_max)

        self.set_decimal_places(decimal_places)
        
        self.is_init = True

    def set_decimal_places(self, decimal_places):
        self.decimal_places = decimal_places
        self.spin_min.setDecimals(decimal_places)
        self.spin_max.setDecimals(decimal_places)
        
        