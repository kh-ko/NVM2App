"""Help >> About 창 — 앱 정보와 서드파티 라이선스 공시.

구성:
  좌측 상단  [About]                  앱 이름 / 버전 / 빌드 날짜 / 회사 / 홈페이지 / 문의처 / 저작권
  좌측 하단  [Open Source Licenses]   서드파티 목록 (third_party_info.THIRD_PARTIES)
  우측       [License]                선택한 항목의 권리자 표기 + 라이선스 전문 (qrc 의 a_assets/licenses)

값의 출처:
- 앱 정보는 app_info 상수 — 회사 표기(APP_COMPANY/HOMEPAGE/CONTACT)는 값만 바꿔 빌드하면 반영된다.
  APP_BUILD_DATE 는 build.bat 이 주입하며 소스 실행이면 비어 있어 '(development build)' 로 표시한다.
  APP_CONTACT 가 비어 있으면 행을 만들지 않는다.
- 서드파티 버전은 실행 시점 조회 (Qt 는 qVersion, Python 은 platform, 그 외는
  importlib.metadata). 배포본에 dist-info 가 빠져 조회되지 않으면 버전 없이 표시한다.

ParamWin 을 상속하는 이유는 HelpNvmUpdateWin 과 같다 — 장비 param 은 없지만 상태바/창
규약을 다른 창들과 통일한다 (사용자 결정). paths=[], Refresh 제거, 본문 항상 활성,
monitor_tick=1000. 워커/네트워크는 없으므로 closeEvent 는 ParamWin 기본으로 충분하다.
"""

import platform
from importlib import metadata

from PySide6.QtCore import QFile, QIODevice, Qt
from PySide6.QtWidgets import QHBoxLayout, QListWidgetItem, QVBoxLayout, QWidget

from b_core.a_define import app_info
from b_core.a_define import file_folder_path as path_def
from b_core.a_define.third_party_info import THIRD_PARTIES, ThirdParty

from c_ui.b_control_ver2.b_base.containers import (BaseListWidget, BaseSplitter, PanelWidget,
                                                   ScrolledPanelWidget)
from c_ui.b_control_ver2.b_base.labels import BaseLabel, LabelRole
from c_ui.b_control_ver2.d_param.param_win import ParamWin

_KEY_WIDTH = 110
_DEV_BUILD_TEXT = "(development build)"


def _read_license_text(file_name: str) -> str:
    """qrc 의 라이선스 전문. 없으면 안내 문구 (빌드 시 qrc 누락을 화면에서 바로 드러낸다)."""
    file = QFile(f"{path_def.ASSET_LICENSE_PATH}/{file_name}")
    if not file.open(QIODevice.ReadOnly | QIODevice.Text):
        return f"(license file not found in resources: {file_name})"
    try:
        return bytes(file.readAll().data()).decode("utf-8", errors="replace")
    finally:
        file.close()


def _component_version(component: ThirdParty) -> str:
    """실행 시점의 구성 요소 버전 문자열. 조회 불가면 빈 문자열."""
    if component.dist_name is None:
        return ""
    if component.dist_name == "PySide6":
        import PySide6
        from PySide6.QtCore import qVersion
        return f"Qt {qVersion()} / PySide6 {PySide6.__version__}"
    if component.dist_name == "python":
        return platform.python_version()
    try:
        return metadata.version(component.dist_name)
    except metadata.PackageNotFoundError:
        return ""


class _InfoRow(QWidget):
    """[항목명(고정 폭) + 값] 한 행. 값은 마우스로 선택/복사할 수 있다."""

    def __init__(self, key: str, value: str, parent=None):
        super().__init__(parent)
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(10)

        self.lbl_key = BaseLabel(key, role=LabelRole.DESCRIPTION)
        self.lbl_key.setFixedWidth(_KEY_WIDTH)
        self.lbl_key.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        row.addWidget(self.lbl_key)

        self.lbl_value = BaseLabel(value)
        self.lbl_value.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        self.lbl_value.setTextInteractionFlags(Qt.TextSelectableByMouse)
        row.addWidget(self.lbl_value, 1)


class _LinkRow(_InfoRow):
    """값이 외부 링크인 행 — 클릭하면 기본 브라우저로 연다."""

    def __init__(self, key: str, url_text: str, parent=None):
        super().__init__(key, "", parent)
        href = url_text if "://" in url_text else f"https://{url_text}"
        self.lbl_value.setTextFormat(Qt.RichText)
        self.lbl_value.setTextInteractionFlags(Qt.TextBrowserInteraction)
        self.lbl_value.setOpenExternalLinks(True)
        self.lbl_value.setText(f'<a href="{href}">{url_text}</a>')


class HelpAboutWin(ParamWin):

    # 오버라이드 핸들러가 super().__init__() 중에도 호출될 수 있으므로 클래스 기본값
    content_widget = None

    def __init__(self, parent=None, win_name: str = "About"):
        super().__init__(parent=parent, win_name=win_name, paths=[], filter_param_paths=[],
                         is_editblock_win=False, label_width=210, folder_max_width=None,
                         monitor_tick=1000)
        self.setWindowTitle("Help >> About")
        self.resize(900, 550)

        self.toolbar.remove_action("Refresh")

        self._build_body()

        if self.license_list.count() > 0:
            self.license_list.setCurrentRow(0)

    # ------------------------------------------------------------ GUI 구성
    def _build_body(self):
        """ParamWin 의 폴더 카드 스크롤 영역은 쓰지 않으므로 중앙 위젯을 교체한다."""
        old_central = self.takeCentralWidget()
        old_central.deleteLater()

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        self.content_widget = central_widget
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)

        self.splitter = BaseSplitter(Qt.Horizontal)
        main_layout.addWidget(self.splitter)

        # ---- 좌측: 앱 정보 + 서드파티 목록
        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(10)

        left_layout.addWidget(self._build_about_panel())

        licenses_panel = PanelWidget(title="Open Source Licenses")
        self.license_list = BaseListWidget()
        for index, component in enumerate(THIRD_PARTIES):
            item = QListWidgetItem(f"{component.name}  ({component.license_name})")
            item.setData(Qt.UserRole, index)
            self.license_list.addItem(item)
        self.license_list.currentRowChanged.connect(self.on_changed_license_item)
        licenses_panel.add_widget(self.license_list)
        # PanelWidget 은 콘텐츠 아래에 stretch 를 두므로 목록이 남는 높이를 채우게 한다
        licenses_panel.main_layout.setStretchFactor(licenses_panel.content_widget, 1)
        left_layout.addWidget(licenses_panel, 1)

        self.splitter.addWidget(left)

        # ---- 우측: 선택한 항목의 라이선스 전문
        self.license_panel = ScrolledPanelWidget(title="License")
        self.lbl_license = BaseLabel("Select a component from the list.")
        self.lbl_license.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        self.lbl_license.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.license_panel.add_widget(self.lbl_license)
        self.splitter.addWidget(self.license_panel)

        self.splitter.setSizes([380, 520])
        self.content_widget.setEnabled(True)  # 모듈 주석 '본문은 항상 활성' 참고

    def _build_about_panel(self) -> PanelWidget:
        panel = PanelWidget(title="About", is_big_title=True)

        lbl_name = BaseLabel(app_info.APP_NAME, role=LabelRole.TITLE)
        panel.add_widget(lbl_name)

        panel.add_widget(_InfoRow("Version", f"v{app_info.APP_VERSION}"))
        panel.add_widget(_InfoRow("Build Date", app_info.APP_BUILD_DATE or _DEV_BUILD_TEXT))
        panel.add_widget(_InfoRow("Company", app_info.APP_COMPANY))
        panel.add_widget(_LinkRow("Homepage", app_info.APP_HOMEPAGE))
        if app_info.APP_CONTACT:
            panel.add_widget(_InfoRow("Contact", app_info.APP_CONTACT))
        panel.add_widget(_InfoRow("Copyright", app_info.APP_COPYRIGHT))
        return panel

    def handle_changed_working(self, working: bool):
        # 본문은 표시 전용 — param 워커 동작 여부와 무관하게 항상 활성 (모듈 주석 참고)
        if self.content_widget is not None:
            self.content_widget.setEnabled(True)

    # ------------------------------------------------------------ 라이선스 표시
    def on_changed_license_item(self, row: int):
        item = self.license_list.item(row) if row >= 0 else None
        if item is None:
            self.license_panel.lbl_title.setText("License")
            self.lbl_license.setText("Select a component from the list.")
            return

        component = THIRD_PARTIES[item.data(Qt.UserRole)]
        version = _component_version(component)

        header_lines = [component.name + (f"  {version}" if version else ""),
                        f"License   : {component.license_name}",
                        f"Copyright : {component.copyright}",
                        "=" * 72, ""]
        bodies = [_read_license_text(file_name) for file_name in component.files]
        separator = "\n\n" + "-" * 72 + "\n\n"

        self.license_panel.lbl_title.setText(f"License : {component.name}")
        self.lbl_license.setText("\n".join(header_lines) + separator.join(bodies))
