from b_core.d_dal.service_port import ServicePort
from PySide6.QtWidgets import QStatusBar, QLabel, QProgressBar, QSizePolicy

from c_ui.b_components.a_custom.custom_description import CustomDescription

class UserStatusBar(QStatusBar):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setFixedHeight(20)
        self.setContentsMargins(0, 0, 0, 0)
        
        # 1. 라벨 3개 생성
        self.lbl_connection_info = CustomDescription("Disconnected")
        self.lbl_serial_number = CustomDescription("S/N: -")
        self.lbl_scan_rate = CustomDescription("scan-rate: -")
        # scan-rate 라벨의 폭을 고정합니다. (텍스트 길이에 맞춰 120~130 정도가 적당합니다)
        self.lbl_scan_rate.setFixedWidth(120) 

        # 2. 프로그레스바 생성 및 기본 설정
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        
        # 가로 크기를 유동적으로 만들기 위한 설정
        self.progress_bar.setMaximumWidth(150)  # 늘어날 수 있는 최대 폭 지정
        self.progress_bar.setMinimumWidth(10)   # 창이 좁아졌을 때 보장할 최소 폭 지정
        self.progress_bar.setMaximumHeight(15)
        self.progress_bar.setMinimumHeight(15)
        # QSizePolicy를 사용하여 레이아웃 내에서 유연하게 줄어들고 늘어날 수 있도록 설정
        self.progress_bar.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        self.progress_bar.hide() # 평소에는 숨겨두고 필요할 때만 보여주는 것이 일반적입니다.

        self.set_progress(50)
        # 3. StatusBar에 위젯 추가
        # addWidget: 왼쪽부터 차례대로 배치됩니다.
        self.addWidget(self.lbl_connection_info)
        self.addWidget(self.lbl_serial_number)
        self.addWidget(self.lbl_scan_rate)

        # addPermanentWidget: 오른쪽 끝에 배치됩니다. (프로그레스바 등에 적합)
        self.addPermanentWidget(self.progress_bar)

        ServicePort().connect_info_changed.connect(self.set_connection_info)

        self.__design()

    def __design(self):
        self.setStyleSheet("""
            QStatusBar { 
                border: none; 
                /* 스타일시트 내부 패딩도 좌우 여백 확보 */
                padding-left: 10px; 
                padding-right: 10px; 
            }
            QStatusBar::item { 
                border: none; 
                padding: 0px; 
                margin: 0px; 
            }
        """)

        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: none;           /* 테두리 제거 */
                border-radius: 0px;     /* 둥근 모서리 제거 (직각) */
                background-color: #E0E0E0; /* 배경색 지정 (빈 영역) */
                text-align: center;     /* 퍼센트 텍스트 중앙 정렬 */
                margin: 0px;
                padding: 0px;
            }
            QProgressBar::chunk {
                background-color: #4A90E2; /* 진행 막대 색상 (이미지와 비슷한 파란색) */
                border-radius: 0px;
            }
        """)

    def set_connection_info(self, message: str):
        if not message:
            self.lbl_connection_info.setText("Disconnected")
        else:
            self.lbl_connection_info.setText(f"{message}")

    def set_serial_number(self, message: str):
        self.lbl_serial_number.setText(f"S/N: {message}")

    def set_scan_rate(self, ms: int):
        self.lbl_scan_rate.setText(f"scan-rate: {ms}ms")

    def set_progress(self, value: int):
        if value > 0 and value < 100:
            self.progress_bar.show()
        else:
            self.progress_bar.hide()
        self.progress_bar.setValue(value)