from PySide6.QtWidgets import QDialog, QVBoxLayout, QPlainTextEdit, QPushButton, QHBoxLayout, QLabel
from PySide6.QtGui import QFont, QGuiApplication
from PySide6.QtCore import Qt

class UserErrorReportDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Communication Error Report")
        self.resize(600, 400)
        self.setWindowModality(Qt.WindowModal)

        layout = QVBoxLayout(self)

        # 상단 안내 레이블
        self.label = QLabel("The following errors occurred during communication:")
        layout.addWidget(self.label)

        # 에러 메시지 표시 영역 (스크롤 및 복사 가능)
        self.text_edit = QPlainTextEdit()
        self.text_edit.setReadOnly(True)
        # 고정폭 글꼴 설정 (로그 데이터 보기 편함)
        self.text_edit.setFont(QFont("Courier New", 10))
        layout.addWidget(self.text_edit)

        # 하단 버튼 레이아웃
        btn_layout = QHBoxLayout()
        
        # 클립보드 복사 버튼
        copy_btn = QPushButton("Copy to Clipboard")
        copy_btn.clicked.connect(self._copy_to_clipboard)
        
        # 닫기 버튼
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)

        btn_layout.addStretch()
        btn_layout.addWidget(copy_btn)
        btn_layout.addWidget(close_btn)
        
        layout.addLayout(btn_layout)

    def append_message(self, message: str):
        """메시지를 추가하고 스크롤을 최하단으로 이동"""
        self.text_edit.appendPlainText(message)
        self.text_edit.appendPlainText("-" * 50) # 구분선
        self.text_edit.ensureCursorVisible()

    def clear(self):
        self.text_edit.clear()

    def _copy_to_clipboard(self):
        clipboard = QGuiApplication.clipboard()
        clipboard.setText(self.text_edit.toPlainText())