from PySide6.QtWidgets import QFrame
from PySide6.QtWidgets import QTableWidget

from c_ui.b_control_packet.base import my_style

class BaseTableWidget(QTableWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.set_color()

    def set_color(self):
        self.verticalHeader().setVisible(False)
        self.setFrameShape(QFrame.NoFrame)
        self.setStyleSheet("""
            QTableWidget {
                /* 좌우 테두리는 0px로 채우고 투명하게 처리 */
                border-left: 0px solid transparent;
                border-right: 0px solid transparent;
                
                /* 상하 테두리는 필요할 경우 유지하거나 변경 (예: light 테마 기본 border 색상) */
                border-top: 1px solid #dcdcdc;
                border-bottom: 1px solid #dcdcdc;
            }
            
            /* 테이블 최상단 가로 헤더(컬럼명 영역) 자체의 테두리 제거 */
            QHeaderView {
                border: none;
                background-color: transparent;
            }
            
            /* 헤더 개별 섹션(Select, Slope, Threshold 칸)의 우측 경계선 제거 */
            QHeaderView::section {
                border-top: none;
                border-left: none;
                border-right: none;
                border-bottom: 1px solid #dcdcdc; /* 헤더 아래쪽 구분선만 유지 */
            }
        """)