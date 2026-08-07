"""대기 안내 메시지 박스.

== x_message 컨셉 ==
이 폴더의 메시지 박스는 전부 '표시 전용' 모듈 함수다.
- 일회성 경고: 표시만 하고 반환값 없음
- 질문: 사용자의 답만 반환
- 수명이 있는 박스(대기 등): 박스 참조를 반환 — 닫기는 호출측(윈도우)이 수행
다음 행동 결정(워커 호출 등)은 항상 윈도우 몫이다.

사용 예 (윈도우 — 워커의 sig_wait_started/finished 와 연결):
    def handle_wait_started(self, title, message):
        self._wait_box = show_wait_message_box(self, title, message)

    def handle_wait_finished(self):
        if self._wait_box is not None:
            self._wait_box.accept()
            self._wait_box = None
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QMessageBox


def show_wait_message_box(parent, title: str, message: str) -> QMessageBox:
    """버튼 없는 WindowModal 대기 박스를 띄우고 참조를 반환한다.

    백그라운드 작업이 끝날 때까지 사용자 입력을 막는 용도 —
    닫기는 호출측이 반환된 박스의 accept() 로 수행한다."""
    box = QMessageBox(parent)
    box.setWindowTitle(title)
    box.setText(message)
    box.setStandardButtons(QMessageBox.StandardButton.NoButton)
    box.setWindowModality(Qt.WindowModality.WindowModal)
    box.show()
    return box
