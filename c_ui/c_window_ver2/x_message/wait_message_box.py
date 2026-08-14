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
from PySide6.QtWidgets import (QDialog, QHBoxLayout, QLabel, QMessageBox,
                               QProgressBar, QPushButton, QVBoxLayout)


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


class _BusyWaitDialog(QDialog):
    """무한 진행 표시 대기 다이얼로그 — Esc/X 로는 닫히지 않는다.

    닫기는 호출측의 accept() 또는 quit_button(있는 경우) 경유만 허용 —
    대기 중 우회 종료를 막기 위한 장치다."""

    def reject(self):
        pass


def show_busy_wait_message_box(parent, title: str, message: str,
                               quit_text: str | None = None) -> QDialog:
    """무한 진행(busy) 프로그래스바가 있는 WindowModal 대기 다이얼로그를 띄우고
    참조를 반환한다.

    - 프로그래스바 range (0,0) = 무한 진행 표시 — 작업이 계속 진행 중임을 보인다.
    - Esc/X 로는 닫히지 않는다. 닫기는 호출측이 accept() 로 수행한다.
    - quit_text 를 주면 버튼이 생기고 dialog.quit_button 으로 노출된다 —
      클릭 후 동작(앱 종료 등) 결정은 호출측이 connect 해서 정한다."""
    dialog = _BusyWaitDialog(parent)
    dialog.setWindowTitle(title)
    dialog.setWindowModality(Qt.WindowModality.WindowModal)
    # 타이틀바 닫기(X) 버튼 제거 — 종료 경로를 quit_button 하나로 좁힌다
    dialog.setWindowFlags(dialog.windowFlags() & ~Qt.WindowCloseButtonHint)

    root = QVBoxLayout(dialog)
    root.addWidget(QLabel(message))

    progress = QProgressBar()
    progress.setRange(0, 0)  # 무한 진행(busy) 표시
    root.addWidget(progress)

    dialog.quit_button = None
    if quit_text is not None:
        dialog.quit_button = QPushButton(quit_text)
        button_row = QHBoxLayout()
        button_row.addStretch()
        button_row.addWidget(dialog.quit_button)
        root.addLayout(button_row)

    dialog.show()
    return dialog
