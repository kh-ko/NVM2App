import sys
from PySide6.QtWidgets import QComboBox

class CustomComboBox(QComboBox):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.__color_design()

    def __color_design(self):
        # 전달해주신 스타일시트를 그대로 적용합니다.
        self.setStyleSheet("""
            /* 콤보박스 기본 디자인 */
            QComboBox {
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