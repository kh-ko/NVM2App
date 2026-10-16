"""연결(ServicePort)·장비 정보(미연결/첫 refresh 전) 관련 메시지 박스.

== x_message 컨셉 ==
이 폴더의 메시지 박스는 전부 '표시 전용' 모듈 함수다.
- 일회성 경고: 표시만 하고 반환값 없음
- 질문: 사용자의 답만 반환
- 수명이 있는 박스(대기 등): 박스 참조를 반환 — 닫기는 호출측(윈도우)이 수행
다음 행동 결정(워커 호출 등)은 항상 윈도우 몫이다.
"""

from PySide6.QtWidgets import QMessageBox


def ask_disconnect(parent) -> bool:
    """연결 해제 확인 질문 — 답만 반환. (실제 close 는 윈도우가 수행)"""
    reply = QMessageBox.question(
        parent, "Confirm Disconnect",
        "Are you sure you want to disconnect?",
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        QMessageBox.StandardButton.No)

    return reply == QMessageBox.StandardButton.Yes


def show_device_info_unavailable(parent, firmware_version: str | None = None) -> None:
    """장비 정보(User Interface / Firmware Version)가 없어 창을 열 수 없을 때 — 미연결 또는 첫 refresh 전 (F076).
    firmware_version 이 주어지면 '형식을 해석할 수 없다' 쪽 문구."""
    if firmware_version is None:
        text = ("Device information (user interface / firmware version) is not available yet.\n"
                "Connect the device and wait for the first refresh, then try again.")
    else:
        text = (f"The firmware version '{firmware_version}' is not in the expected format,\n"
                "so the window cannot choose its parameters.")
    QMessageBox.information(parent, "Device Information", text)
