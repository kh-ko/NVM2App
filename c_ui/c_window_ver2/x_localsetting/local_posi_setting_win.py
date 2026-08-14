from PySide6.QtCore import Qt
from PySide6.QtWidgets import QMainWindow, QVBoxLayout, QWidget

from b_core.c_manager.local_setting_manager import LocalSettingManager
from c_ui.a_converter.position_converter_manager import PosiConverterManager
from c_ui.b_control_ver2.b_base.toolbars import BaseToolBar
from c_ui.b_control_ver2.b_base.containers import PanelWidget
from c_ui.b_control_ver2.c_values.read_write_values import ReadWriteFloatValueWidget


class LocalPosiSettingWin(QMainWindow):
    """position 관련 로컬 설정(local_setting.json) 편집 윈도우.

    - Decimal Places: position 표시 소수점 자리수 (0~6, 정수).
      변경이 적용되면 setpoint 입력기들의 표시 자리수도 함께 갱신된다.
    - Setpoint 01~06: setpoint 버튼 값 (0.0~100.0, dp 로 표시하고 pfs 로 저장).
      표시 자리수는 posi_decimal_places 를 따른다.

    적용 정책: 툴바의 Apply 버튼으로 편집된(dirty) 행만 일괄 반영한다
    (전체 반영은 미편집 값까지 표시 자릿수 왕복을 태워 정밀도를 잠식하므로).
    반영 전까지는 dirty 마커로 미적용 편집을 표시한다. 저장과 변경 시그널
    발화는 LocalSettingManager 의 _Setting 이 전담하므로, 각 패널(setpoint
    버튼 등)은 그 시그널로 스스로 갱신된다.

    매니저 값이 바뀌면(다른 창 포함) sig_*_changed 수신으로 위젯을 매니저
    값으로 재동기화한다 — 이때 아직 Apply 하지 않은 편집은 덮어써진다.
    """

    # (설정명, 라벨, 최소, 최대) — 표시 자리수는 행 정의가 아니라
    # posi_decimal_places 설정이 결정한다 (handle_* 계열에서 동적 적용)
    _ROWS = [
        ("posi_decimal_places", "Decimal Places", 0,   6),
        ("posi_setpoint01",     "Setpoint 01",    0.0, 100.0),
        ("posi_setpoint02",     "Setpoint 02",    0.0, 100.0),
        ("posi_setpoint03",     "Setpoint 03",    0.0, 100.0),
        ("posi_setpoint04",     "Setpoint 04",    0.0, 100.0),
        ("posi_setpoint05",     "Setpoint 05",    0.0, 100.0),
        ("posi_setpoint06",     "Setpoint 06",    0.0, 100.0),
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Local Setting >> Position Setpoint")
        self.resize(380, 420)

        self.toolbar = BaseToolBar(self)
        self.addToolBar(Qt.TopToolBarArea, self.toolbar)
        self.toolbar.add_action("Apply", self.on_clicked_apply)

        self.local_setting = LocalSettingManager()
        self.converter = PosiConverterManager()
        self._widgets = {}
        self._setpoint_names = [name for name, *_ in self._ROWS if name != "posi_decimal_places"]

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)

        panel = PanelWidget(title="Position Local Setting", is_big_title=True)
        main_layout.addWidget(panel)

        for name, label, min_value, max_value in self._ROWS:
            widget = ReadWriteFloatValueWidget(label_text=label)
            widget.set_range(min_value, max_value)
            panel.add_widget(widget)
            self._widgets[name] = widget

        self._widgets["posi_decimal_places"].set_decimals(0)

        # [주의] 이 창은 WA_DeleteOnClose 로 파괴되고 매니저는 앱 수명 싱글턴이므로
        # 반드시 바운드 메서드로 연결한다 — 람다/partial 은 창 파괴 시 자동 disconnect
        # 되지 않아 좀비 연결이 남는다 (파괴된 C++ 객체 접근 크래시)
        self.local_setting.sig_posi_decimal_places_changed.connect(self.handle_decimal_changed)
        self.local_setting.sig_posi_setpoint01_changed.connect(self.handle_setpoint01_changed)
        self.local_setting.sig_posi_setpoint02_changed.connect(self.handle_setpoint02_changed)
        self.local_setting.sig_posi_setpoint03_changed.connect(self.handle_setpoint03_changed)
        self.local_setting.sig_posi_setpoint04_changed.connect(self.handle_setpoint04_changed)
        self.local_setting.sig_posi_setpoint05_changed.connect(self.handle_setpoint05_changed)
        self.local_setting.sig_posi_setpoint06_changed.connect(self.handle_setpoint06_changed)

        # 초기 동기화 — setpoint 자리수/값까지 함께 잡힌다
        self.handle_decimal_changed()

    def handle_decimal_changed(self):
        widget = self._widgets["posi_decimal_places"]
        widget.set_value(self.local_setting.posi_decimal_places)
        widget.commit()

        # 자리수가 바뀌면 setpoint 표시 자리수도 함께 갱신한다
        for name in self._setpoint_names:
            self.handle_setpoint_changed(name)

    def handle_setpoint_changed(self, name):
        widget = self._widgets[name]
        widget.set_decimals(self.local_setting.posi_decimal_places)
        pfs_value = getattr(self.local_setting, name)
        dp_value = self.converter.convert_pfs_to_dp(pfs_value)
        widget.set_value(dp_value)
        widget.commit()

    # 시그널 연결용 얇은 위임 — 바운드 메서드 연결 규칙 때문에 명시적으로 둔다 (__init__ 주석 참고)
    def handle_setpoint01_changed(self):
        self.handle_setpoint_changed("posi_setpoint01")

    def handle_setpoint02_changed(self):
        self.handle_setpoint_changed("posi_setpoint02")

    def handle_setpoint03_changed(self):
        self.handle_setpoint_changed("posi_setpoint03")

    def handle_setpoint04_changed(self):
        self.handle_setpoint_changed("posi_setpoint04")

    def handle_setpoint05_changed(self):
        self.handle_setpoint_changed("posi_setpoint05")

    def handle_setpoint06_changed(self):
        self.handle_setpoint_changed("posi_setpoint06")

    def on_clicked_apply(self):
        # 편집된(dirty) 행만 반영한다 — 전체 반영은 미편집 setpoint 까지
        # [저장 pfs -> 표시 자릿수 반올림 -> 역변환] 왕복을 태워 정밀도를 잠식한다.
        # 값/dirty 는 반영 전에 함께 스냅샷 — 반영 도중 발화되는 sig_*_changed 가
        # 위젯을 재동기화(commit=clean)하므로 루프 안에서 is_dirty() 를 물으면
        # 뒤 순서의 편집이 누락된다.
        dirty_values = {name: widget.get_value() for name, widget in self._widgets.items() if widget.is_dirty()}

        for name, value in dirty_values.items():
            # 편집 중간 상태("-", 빈 칸)는 반영하지 않는다 (툴바 버튼은 포커스를
            # 뺏지 않아 확정 전 텍스트인 채로 Apply 가 눌릴 수 있다)
            if value is None:
                continue

            # dp -> pfs 변환은 setpoint 에만 해당한다 — 자리수 설정까지 변환하면
            # posi_decimal_places 가 0.01 같은 float 로 저장되어 포맷 문자열이 깨진다
            if name in self._setpoint_names:
                value = self.converter.convert_dp_to_pfs(value)
            else:
                value = int(value)

            setattr(self.local_setting, name, value)
