"""상태바 컨트롤 모음.

- BaseStatusBar: 하단 상태바. [라벨 N칸(좌측) + 프로그레스바(우측)] 합성과
  연결 상태 배경 전환만 담당한다.
- BaseProgressBar: 직각 모서리 프로그레스바 (기존 MainFootStatusBar 안의
  인라인 스타일 QProgressBar 를 분리한 것).

기존 main_foot_statusbar.py / param_setting_statusbar.py 에서 달라진 점:
- ServicePort / ParamManager 연동(set_connection_info, handle_sn_changed,
  set_scan_rate)은 레이어 규칙 위반이라 제거 — 각 라벨 칸에 무엇을 표시할지는
  윈도우가 set_label_text(index, text) 로 결정한다.
  (라벨 폭 고정 등 세부 조정은 labels[index] 직접 접근으로)
- QStatusBar[is_connected="..."] 매직 프로퍼티 + unpolish/polish 패턴 대신
  ColorStyled 의 set_colors(bg=...) 로 상태 배경을 교체한다.
- set_status_state() -> set_connected() 로 개명.
"""

from c_ui.b_control_ver2.b_base.buttons import BaseButton
from PySide6.QtWidgets import QProgressBar, QSizePolicy, QStatusBar

from c_ui.b_control_ver2.b_base.labels import BaseLabel, LabelRole
from c_ui.b_control_ver2.a_theme.color_styled import ColorStyled, WidgetColors
from c_ui.b_control_ver2.a_theme.tokens import tokens


class BaseProgressBar(QProgressBar, ColorStyled):
    """직각 모서리 프로그레스바. 퍼센트 텍스트는 중앙 정렬."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_colors(WidgetColors(bg=tokens().progress_bg))

    def _build_qss(self, c: WidgetColors) -> str:
        t = tokens()
        return f"""
            BaseProgressBar {{
                border: none;
                border-radius: 0px;
                background-color: {c.bg};
                text-align: center;
                margin: 0px;
                padding: 0px;
            }}
            BaseProgressBar::chunk {{
                background-color: {t.progress_chunk};
                border-radius: 0px;
            }}
        """


class BaseStatusBar(QStatusBar, ColorStyled):
    """하단 상태바. 초기 상태는 미연결(경고 배경)이다.

    - labels[0..N-1]: 좌측 라벨 칸 — 표시 내용은 윈도우가 결정
    - progress_bar: 우측 프로그레스바 — set_progress() 로 제어 (1~99 만 표시)
    """

    def __init__(self, label_count: int = 3, enable_log_btn = True, parent=None):
        super().__init__(parent)
        self.setFixedHeight(20)
        self.setContentsMargins(0, 0, 0, 0)

        # 좌측 라벨 칸 — addWidget: 왼쪽부터 차례대로 배치
        self.labels: list[BaseLabel] = []
        for _ in range(label_count):
            label = BaseLabel(role=LabelRole.DESCRIPTION)
            label.setWordWrap(False)
            self.addWidget(label)
            self.labels.append(label)

        # 우측 프로그레스바 — addPermanentWidget: 오른쪽 끝에 배치
        self.progress_bar = BaseProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setMaximumWidth(150)   # 늘어날 수 있는 최대 폭
        self.progress_bar.setMinimumWidth(10)    # 창이 좁아졌을 때 보장할 최소 폭
        self.progress_bar.setFixedHeight(15)
        self.progress_bar.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.progress_bar.hide()                 # 진행 중일 때만 표시
        self.addPermanentWidget(self.progress_bar)

        if enable_log_btn:
            self.btn_log = BaseButton("Log View", border=False)
            self.btn_log.setFixedWidth(50)
            self.addPermanentWidget(self.btn_log)
        else:
            self.btn_log = None

        self._init_colors(WidgetColors(bg=tokens().status_bad_bg))

    # ------------------------------------------------------------ 표시 제어
    def set_label_text(self, index: int, text: str) -> None:
        """index 번째 라벨 칸의 텍스트 교체."""
        if 0 <= index < len(self.labels):
            self.labels[index].setText(text)

    def set_connected(self, connected: bool) -> None:
        """연결 상태에 따라 배경색 전환."""
        t = tokens()
        self.set_colors(bg=t.status_ok_bg if connected else t.status_bad_bg)

    def set_progress(self, value: int) -> None:
        """진행률 표시. 0 이하/100 이상이면 프로그레스바를 숨긴다."""
        self.progress_bar.setVisible(0 < value < 100)
        self.progress_bar.setValue(value)

    # ------------------------------------------------------------ 스타일
    def _build_qss(self, c: WidgetColors) -> str:
        return f"""
            BaseStatusBar {{
                background-color: {c.bg};
                border: none;
                padding-left: 10px;
                padding-right: 10px;
            }}
            BaseStatusBar::item {{
                border: none;
                padding: 0px;
                margin: 0px;
            }}
        """
