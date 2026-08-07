"""ParameterRunWorker 의 StartResult 표시 메시지 박스.

== x_message 컨셉 ==
이 폴더의 메시지 박스는 전부 '표시 전용' 모듈 함수다.
- 일회성 경고: 표시만 하고 반환값 없음
- 질문: 사용자의 답만 반환
- 수명이 있는 박스(대기 등): 박스 참조를 반환 — 닫기는 호출측(윈도우)이 수행
다음 행동 결정(워커 호출 등)은 항상 윈도우 몫이다.

사용 예 (윈도우 — write 의 Local 전환 재시도 정책은 윈도우가 결정):
    pairs = [(param, value)]
    result = self.param_worker.write(pairs)

    if result == StartResult.NEED_LOCAL_SWITCH:
        if not ask_local_switch(self):
            return
        result = self.param_worker.write(pairs, switch_to_local=True)

    show_param_write_warning(self, result)
"""

from PySide6.QtWidgets import QMessageBox

from b_core.e_worker_ver2.parameter_run_worker import StartResult


def show_param_write_warning(parent, result: StartResult) -> None:
    """write() 결과 중 경고 대상만 표시.

    OK/EMPTY(표시할 것 없음), NEED_LOCAL_SWITCH(질문은 ask_local_switch 로)는
    표시하지 않는다."""
    if result == StartResult.NOT_CONNECTED:
        QMessageBox.warning(parent, "Connection Error",
                            "Communication is not connected. Please check the connection status.")

    elif result == StartResult.BUSY:
        QMessageBox.warning(parent, "Warning",
                            "Another operation is in progress. Please try again in a moment.")

    elif result == StartResult.LOCAL_BLOCKED:
        QMessageBox.warning(parent, "Access Denied",
                            "Cannot modify local-only parameters while in Remote Lock mode.")


def show_param_refresh_warning(parent, result: StartResult) -> None:
    """refresh() 결과 중 NOT_CONNECTED 만 표시.

    BUSY 는 재부팅 대기 중 재연결 시그널 경유 호출의 정상 흐름이므로 표시하지 않고,
    EMPTY(등록 param 없음)도 표시할 것이 없다."""
    if result == StartResult.NOT_CONNECTED:
        QMessageBox.warning(parent, "Connection Error",
                            "Communication is not connected. Please check the connection status.")


def ask_local_switch(parent) -> bool:
    """Remote 상태에서 local 전용 param 쓰기 시 Local 전환 여부 질문 — 답만 반환."""
    reply = QMessageBox.question(
        parent, "Access Mode Change",
        "You are attempting to change a local-only parameter while in Remote mode.\n"
        "Would you like to switch to Local mode and continue?",
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        QMessageBox.StandardButton.No)

    return reply == QMessageBox.StandardButton.Yes
