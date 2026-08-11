from PySide6.QtCore import Qt
from PySide6.QtWidgets import QMainWindow, QVBoxLayout, QWidget

from b_core.b_datatype.param_enum import ChartRangeModeEnum
from b_core.c_manager.local_setting_manager import LocalSettingManager
from c_ui.b_control_ver2.b_base.toolbars import BaseToolBar
from c_ui.b_control_ver2.b_base.containers import PanelWidget
from c_ui.b_control_ver2.c_values.read_write_values import ReadWriteEnumValueWidget, ReadWriteFloatValueWidget


class LocalChartSettingWin(QMainWindow):
    """차트 축 범위 로컬 설정(local_setting.json) 편집 윈도우.

    Position(왼쪽 Y축)/Pressure(오른쪽 Y축) 각각:
    - Range Mode: Auto(데이터 기반) / Full(위치 0~100, 압력 0~최대) / Custom
    - Custom Min/Max: Custom 모드에서만 활성화. 표시 자리수는
      posi/pres decimal places 로컬 설정을 따른다.

    적용 정책은 다른 localsetting 윈도우와 동일 — Apply 버튼으로 dirty 행만
    일괄 반영하고, 차트 패널은 매니저의 변경 시그널로 스스로 갱신된다.
    """

    FLOAT32_MAX = 3.4028235e+38

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Local Setting >> Chart Range")
        self.resize(380, 500)

        self.toolbar = BaseToolBar(self)
        self.addToolBar(Qt.TopToolBarArea, self.toolbar)
        self.toolbar.add_action("Apply", self.on_clicked_apply)

        self.local_setting = LocalSettingManager()
        self._widgets = {}

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        for title, prefix in (("Position Axis (Left)", "posi"), ("Pressure Axis (Right)", "pres")):
            panel = PanelWidget(title=title, is_big_title=True)
            main_layout.addWidget(panel)

            mode_widget = ReadWriteEnumValueWidget(enum_class=ChartRangeModeEnum, label_text="Range Mode")
            panel.add_widget(mode_widget)
            self._widgets[f"{prefix}_chart_range_mode"] = mode_widget

            for suffix, label in (("custom_min", "Custom Min"), ("custom_max", "Custom Max")):
                widget = ReadWriteFloatValueWidget(label_text=label)
                widget.set_range(-self.FLOAT32_MAX, self.FLOAT32_MAX)
                # Custom 모드에서만 편집 가능
                widget.reg_enable_condition(mode_widget, [ChartRangeModeEnum.CUSTOM.value])
                panel.add_widget(widget)
                self._widgets[f"{prefix}_chart_range_{suffix}"] = widget

        # [주의] 이 창은 WA_DeleteOnClose 로 파괴되고 매니저는 앱 수명 싱글턴이므로
        # 반드시 바운드 메서드로 연결한다 — 람다/partial 은 좀비 연결이 남는다
        ls = self.local_setting
        ls.sig_posi_decimal_places_changed.connect(self.handle_posi_group_changed)
        ls.sig_posi_chart_range_mode_changed.connect(self.handle_posi_group_changed)
        ls.sig_posi_chart_range_custom_min_changed.connect(self.handle_posi_group_changed)
        ls.sig_posi_chart_range_custom_max_changed.connect(self.handle_posi_group_changed)
        ls.sig_pres_decimal_places_changed.connect(self.handle_pres_group_changed)
        ls.sig_pres_chart_range_mode_changed.connect(self.handle_pres_group_changed)
        ls.sig_pres_chart_range_custom_min_changed.connect(self.handle_pres_group_changed)
        ls.sig_pres_chart_range_custom_max_changed.connect(self.handle_pres_group_changed)

        # 초기 동기화
        self.handle_posi_group_changed()
        self.handle_pres_group_changed()

    def _sync_group(self, prefix, decimal_places):
        mode_widget = self._widgets[f"{prefix}_chart_range_mode"]
        mode_widget.set_value(getattr(self.local_setting, f"{prefix}_chart_range_mode"))
        mode_widget.commit()

        for suffix in ("custom_min", "custom_max"):
            widget = self._widgets[f"{prefix}_chart_range_{suffix}"]
            widget.set_decimals(decimal_places)
            widget.set_value(getattr(self.local_setting, f"{prefix}_chart_range_{suffix}"))
            widget.commit()
            # set_value 가 setEnabled(True) 로 복구하므로 Custom 조건을 다시 평가한다
            widget.on_enable_condition_changed()

    def handle_posi_group_changed(self):
        self._sync_group("posi", self.local_setting.posi_decimal_places)

    def handle_pres_group_changed(self):
        self._sync_group("pres", self.local_setting.pres_decimal_places)

    def on_clicked_apply(self):
        # 편집된(dirty) 행만 반영 — 값/dirty 는 반영 전에 함께 스냅샷한다
        # (반영 도중 발화되는 변경 시그널이 위젯을 재동기화(commit)하기 때문)
        dirty_values = {name: widget.get_value() for name, widget in self._widgets.items() if widget.is_dirty()}

        for name, value in dirty_values.items():
            # 편집 중간 상태("-", 빈 칸)는 반영하지 않는다
            if value is None:
                continue

            # mode 는 enum 정수값, min/max 는 dp(표시 단위) float 그대로 저장한다
            setattr(self.local_setting, name, value)
