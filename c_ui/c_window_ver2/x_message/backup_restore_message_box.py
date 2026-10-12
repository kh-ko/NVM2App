"""백업/복원 창의 질문 — 표시 전용 (x_message 컨셉: 질문은 사용자의 답만 돌려준다, 다음 행동은 창 몫)."""

from PySide6.QtWidgets import QMessageBox


def ask_save_partial_backup(parent, missing_names: list[str]) -> bool:
    """백업 읽기에 누락이 있을 때, 누락 목록을 보이고 그것 없이 저장할지 묻는다 (F087 — 2026-10-12 결정 (a))."""
    shown = "\n- ".join(missing_names[:10])
    more = "" if len(missing_names) <= 10 else f"\n... and {len(missing_names) - 10} more"
    reply = QMessageBox.question(
        parent, "Incomplete Backup",
        f"{len(missing_names)} parameter(s) could not be read:\n- {shown}{more}\n\n"
        "Save the backup file without them?",
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        QMessageBox.StandardButton.No)

    return reply == QMessageBox.StandardButton.Yes
