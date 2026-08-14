"""미구현 기능 안내 메시지 박스.

== x_message 컨셉 ==
이 폴더의 메시지 박스는 전부 '표시 전용' 모듈 함수다.
- 일회성 경고: 표시만 하고 반환값 없음
- 질문: 사용자의 답만 반환
- 수명이 있는 박스(대기 등): 박스 참조를 반환 — 닫기는 호출측(윈도우)이 수행
다음 행동 결정(워커 호출 등)은 항상 윈도우 몫이다.
"""

from PySide6.QtWidgets import QMessageBox


def show_not_ready(parent) -> None:
    """아직 구현되지 않은 기능 선택 시 준비 중 안내만 표시."""
    QMessageBox.information(parent, "Notice",
                            "This service is under preparation.")
