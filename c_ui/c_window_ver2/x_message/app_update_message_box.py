"""앱 업데이트 창의 질문/안내 메시지 박스.

== x_message 컨셉 ==
이 폴더의 메시지 박스는 전부 '표시 전용' 모듈 함수다.
- 일회성 경고/안내: 표시만 하고 반환값 없음
- 질문: 사용자의 답만 반환
- 수명이 있는 박스(대기 등): 박스 참조를 반환 — 닫기는 호출측(윈도우)이 수행
다음 행동 결정(워커 호출 등)은 항상 윈도우 몫이다.
"""

from PySide6.QtWidgets import QMessageBox


def ask_install_version(parent, version: str, is_installed: bool) -> bool:
    """선택한 버전으로 업데이트할지 — 답만 반환. 이미 설치된 버전이면 재설치 문구."""
    if is_installed:
        text = (f"Version '{version}' is the currently installed version.\n\n"
                "Reinstall it anyway?\n"
                "The application will restart automatically when the update is completed.")
    else:
        text = (f"Update the application to version '{version}'?\n\n"
                "The application will restart automatically when the update is completed.")

    reply = QMessageBox.question(parent, "Application Update", text,
                                 QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                 QMessageBox.StandardButton.No)
    return reply == QMessageBox.StandardButton.Yes


def ask_abort_download(parent) -> bool:
    """진행 중인 배포 파일 다운로드 중단 여부 — 답만 반환."""
    reply = QMessageBox.question(parent, "Abort Update",
                                 "The update package is being downloaded.\n\nAbort now?",
                                 QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                 QMessageBox.StandardButton.No)
    return reply == QMessageBox.StandardButton.Yes


def show_source_run_notice(parent) -> None:
    """소스(python main.py) 실행 중에는 설치할 수 없음을 안내만 한다."""
    QMessageBox.information(parent, "Application Update",
                            "Application update is available only in the deployed executable (NVM2App.exe).\n"
                            "The application is currently running from source.")
