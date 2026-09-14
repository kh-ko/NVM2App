"""기동 단계 오류 안내 메시지 박스 (창이 생기기 전에 쓰인다).

== x_message 컨셉 ==
이 폴더의 메시지 박스는 전부 '표시 전용' 모듈 함수다.
- 일회성 경고: 표시만 하고 반환값 없음
- 질문: 사용자의 답만 반환
- 수명이 있는 박스(대기 등): 박스 참조를 반환 — 닫기는 호출측(윈도우)이 수행
다음 행동 결정(종료 등)은 항상 호출측(main.py) 몫이다.
"""

from PySide6.QtWidgets import QMessageBox

_PREVIEW_COUNT = 10  # 본문에 보여줄 오류 줄 수 — 나머지는 'Show Details...' 로


def show_schema_load_error(parent, files: list, errors: list) -> None:
    """param 스키마(params.json / nv2_spec.json) 누락·손상·불일치로 기동할 수 없음을 알린다.

    본문에는 파일 경로와 앞쪽 오류 몇 줄만 두고, 전체 오류 목록은 상세 영역에 넣는다.
    로그 파일에도 같은 문구가 남아 있다."""
    file_lines = "\n".join(f"  - {f}" for f in files)
    preview = "\n".join(f"  - {e}" for e in errors[:_PREVIEW_COUNT])
    more = f"\n  ... and {len(errors) - _PREVIEW_COUNT} more (see Details / the log file)" \
        if len(errors) > _PREVIEW_COUNT else ""

    box = QMessageBox(parent)
    box.setIcon(QMessageBox.Icon.Critical)
    box.setWindowTitle("Parameter Schema Error")
    box.setText("The parameter schema files could not be loaded, so the application cannot start.")
    box.setInformativeText(
        f"Files:\n{file_lines}\n\n"
        f"Errors ({len(errors)}):\n{preview}{more}\n\n"
        "Please restore the schema files from the release package and start the application again.")
    box.setDetailedText("\n".join(errors))
    box.setStandardButtons(QMessageBox.StandardButton.Ok)
    box.exec()
