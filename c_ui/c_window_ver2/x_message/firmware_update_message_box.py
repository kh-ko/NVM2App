"""펌웨어 업데이트 창의 선택/안내 다이얼로그.

== x_message 컨셉 ==
이 폴더의 메시지 박스는 전부 '표시 전용' 모듈 함수다.
- 일회성 경고/안내: 표시만 하고 반환값 없음
- 질문: 사용자의 답만 반환
- 수명이 있는 박스(대기 등): 박스 참조를 반환 — 닫기는 호출측(윈도우)이 수행
다음 행동 결정(워커 호출 등)은 항상 윈도우 몫이다.

ver1 의 SelectNetworkFirmwareDialog / SelectPortDialog / GuideDialog /
SelectServicePortTypeDialog 클래스와 QMessageBox 조합을 이 모듈의 함수로
정리했다. ver1 과 달리 다이얼로그 안에서 FTP/시리얼 포트를 조회하지 않는다 —
목록은 윈도우가 (워커로) 구해서 인자로 넘긴다.
"""

from enum import Enum, auto

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (QDialog, QFrame, QHBoxLayout, QLabel, QMessageBox,
                               QVBoxLayout)

from b_core.a_define import file_folder_path as path_def
from b_core.e_worker_ver2.firmware_run_worker import AdapterType, FirmwareSource

from c_ui.b_control_ver2.b_base.buttons import BaseButton
from c_ui.b_control_ver2.b_base.inputs import BaseComboBox
from c_ui.b_control_ver2.b_base.labels import BaseLabel

_DIALOG_SIZE = (520, 350)
_BUTTON_WIDTH = 100


class _SelectDialog(QDialog):
    """[안내 문구 / 콤보박스 / OK·Cancel] 선택 다이얼로그 공통 골격.

    ver1 SelectPortDialog 는 X 로 닫아도 Accepted 처럼 다뤄져 선택 없이
    진행되는 문제가 있었다 — 여기서는 OK 만 accept 하고 나머지는 전부 reject."""

    def __init__(self, title: str, guide: str, items: list[tuple[str, object]],
                 current_index: int = 0, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setFixedSize(*_DIALOG_SIZE)

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(15)

        lbl_guide = BaseLabel(guide)
        lbl_guide.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        root.addWidget(lbl_guide)

        self.combo = BaseComboBox(self)
        for text, data in items:
            self.combo.addItem(text, data)
        if 0 <= current_index < self.combo.count():
            self.combo.setCurrentIndex(current_index)
        root.addWidget(self.combo)
        root.addStretch()

        btn_ok = BaseButton("OK", parent=self)
        btn_ok.setFixedWidth(_BUTTON_WIDTH)
        btn_ok.clicked.connect(self.accept)

        btn_cancel = BaseButton("Cancel", parent=self)
        btn_cancel.setFixedWidth(_BUTTON_WIDTH)
        btn_cancel.clicked.connect(self.reject)

        button_row = QHBoxLayout()
        button_row.setSpacing(10)
        button_row.addStretch()
        button_row.addWidget(btn_ok)
        button_row.addWidget(btn_cancel)
        button_row.addStretch()
        root.addLayout(button_row)

    def selected_data(self):
        return self.combo.currentData(Qt.UserRole)


def ask_update_method(parent) -> FirmwareSource | None:
    """펌웨어 출처 질문 — 답만 반환 (닫으면 None)."""
    box = QMessageBox(parent)
    box.setWindowTitle("Select Firmware Update Method")
    box.setText("Please select the firmware update method.\n\n"
                "- From Network : select a version from the FTP repository\n"
                "- From Local Files : use the firmware files in 2_resource/temp (last downloaded)")

    btn_network = box.addButton("From Network", QMessageBox.ButtonRole.AcceptRole)
    btn_local = box.addButton("From Local Files", QMessageBox.ButtonRole.AcceptRole)
    box.addButton(QMessageBox.StandardButton.Cancel)
    box.exec()

    clicked = box.clickedButton()
    if clicked == btn_network:
        return FirmwareSource.NETWORK
    if clicked == btn_local:
        return FirmwareSource.LOCAL_FILES
    return None


def ask_network_version(parent, versions: list[str]) -> str | None:
    """FTP 저장소 버전 선택 — 답만 반환 (취소 시 None). 목록은 호출측이 넘긴다."""
    dialog = _SelectDialog("Select Network Firmware Version",
                           "Select the firmware version from the network repository.",
                           [(version, version) for version in versions],
                           parent=parent)
    if dialog.exec() != QDialog.DialogCode.Accepted:
        return None
    return dialog.selected_data()


def ask_adapter_type(parent) -> AdapterType | None:
    """업데이트 어댑터(RS232 / USB) 선택 — 이미지 카드 2장, 답만 반환."""
    dialog = QDialog(parent)
    dialog.setWindowTitle("Select Service Port Type")
    dialog.setFixedSize(520, 300)
    selected = {"value": None}

    root = QVBoxLayout(dialog)
    root.setContentsMargins(25, 20, 25, 20)
    root.setSpacing(15)

    lbl_title = BaseLabel("Please select the update adapter connected to the valve's service port.")
    lbl_title.setAlignment(Qt.AlignCenter)
    root.addWidget(lbl_title)

    cards = QHBoxLayout()
    cards.setSpacing(25)

    def select_rs232():
        selected["value"] = AdapterType.RS232
        dialog.accept()

    def select_usb():
        selected["value"] = AdapterType.USB
        dialog.accept()

    # 다이얼로그 수명 안에서만 쓰이는 지역 클로저 — 싱글턴 시그널이 아니므로
    # 좀비 연결 규칙(바운드 메서드 강제) 대상이 아니다
    for image_path, text, slot in ((path_def.ASSET_RS232_IMG_FILE, "RS232", select_rs232),
                                   (path_def.ASSET_USB_IMG_FILE, "USB", select_usb)):
        card = QFrame(dialog)
        card.setFrameShape(QFrame.Shape.StyledPanel)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(15, 15, 15, 15)
        card_layout.setSpacing(15)

        lbl_image = QLabel(card)
        pixmap = QPixmap(image_path)
        if not pixmap.isNull():
            lbl_image.setPixmap(pixmap.scaled(160, 150, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        lbl_image.setAlignment(Qt.AlignCenter)
        card_layout.addWidget(lbl_image)

        button = BaseButton(text, parent=card)
        button.setFixedHeight(40)
        button.clicked.connect(slot)
        card_layout.addWidget(button)

        cards.addWidget(card)

    root.addLayout(cards)
    root.addStretch()

    if dialog.exec() != QDialog.DialogCode.Accepted:
        return None
    return selected["value"]


def ask_com_port(parent, port_names: list[str], connected_port_name: str | None) -> str | None:
    """어댑터가 연결된 COM 포트 선택 — 답만 반환 (취소 시 None).

    connected_port_name(현재 ServicePort 가 쓰는 포트)이 목록에 있으면 표시에
    'connected' 를 붙이고 기본 선택한다 — 보통 서비스 포트 그대로 업데이트한다."""
    items = []
    current_index = 0
    for index, name in enumerate(port_names):
        if name == connected_port_name:
            items.append((f"{name}  (connected service port)", name))
            current_index = index
        else:
            items.append((name, name))

    if not items:
        QMessageBox.warning(parent, "Warning", "No COM port was found on this PC.")
        return None

    dialog = _SelectDialog("Select COM Port",
                           "Select the COM port connected to the valve (update adapter).",
                           items, current_index=current_index, parent=parent)
    if dialog.exec() != QDialog.DialogCode.Accepted:
        return None
    return dialog.selected_data()


def show_guide(parent, guide_text: str, image_path: str) -> None:
    """수동 조작 안내 (문구 + 이미지 + OK). 표시만 한다."""
    dialog = QDialog(parent)
    dialog.setWindowTitle("Firmware Update Guide")
    dialog.setFixedSize(*_DIALOG_SIZE)

    root = QVBoxLayout(dialog)
    root.setContentsMargins(20, 20, 20, 20)
    root.setSpacing(15)

    lbl_guide = BaseLabel(guide_text)
    lbl_guide.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
    root.addWidget(lbl_guide)

    lbl_image = QLabel(dialog)
    pixmap = QPixmap(image_path)
    if not pixmap.isNull():
        lbl_image.setPixmap(pixmap.scaled(480, 200, Qt.KeepAspectRatio, Qt.SmoothTransformation))
    lbl_image.setAlignment(Qt.AlignCenter)
    root.addWidget(lbl_image, 1)

    btn_ok = BaseButton("OK", parent=dialog)
    btn_ok.setFixedWidth(_BUTTON_WIDTH)
    btn_ok.clicked.connect(dialog.accept)

    button_row = QHBoxLayout()
    button_row.addStretch()
    button_row.addWidget(btn_ok)
    button_row.addStretch()
    root.addLayout(button_row)

    dialog.exec()


def show_rs232_boot_mode_guide(parent) -> None:
    """RS232 어댑터: 쓰기 시작 전 부트모드 진입 안내 3장 (ver1 guide_rs232_port_setting)."""
    show_guide(parent, "1(1/3). Connect the update adapter to the valve's service port",
               path_def.ASSET_FU_GUIDE_1_IMG_FILE)
    show_guide(parent, "2(2/3). Set the boot mode switch to 'up'",
               path_def.ASSET_FU_GUIDE_2_IMG_FILE)
    show_guide(parent, "3(3/3). Click the reset button<br>"
                       "(if the valve version is older than 'R006', turn the power off and on.)",
               path_def.ASSET_FU_GUIDE_3_IMG_FILE)


def show_rs232_reboot_guide(parent) -> None:
    """RS232 어댑터: 쓰기 완료 후 정상 부팅 복귀 안내 2장."""
    show_guide(parent, "1(1/2). Set the boot mode switch back to 'down'",
               path_def.ASSET_FU_GUIDE_4_IMG_FILE)
    show_guide(parent, "2(2/2). Click the reset button<br>"
                       "(if the valve version is older than 'R006', turn the power off and on.)",
               path_def.ASSET_FU_GUIDE_5_IMG_FILE)


def ask_restore_factory_params(parent, has_backup_file: bool) -> bool:
    """업데이트 후 공장 파라미터 복원 여부 — 답만 반환.

    Restore 를 고르면 공장 초기화(재부팅) 뒤에 백업 복원 창이 이어서 열린다는
    것을 함께 안내한다 (백업 파일 유무에 따라 문구가 다르다)."""
    if has_backup_file:
        follow_up = ("Afterwards (Restore or Skip), the Restore window will open with the backup file "
                     "saved before the update.")
    else:
        follow_up = "After that, the Restore window will open (no backup file was saved before the update)."

    box = QMessageBox(parent)
    box.setWindowTitle("Restore Factory Parameters")
    box.setText("Firmware update is completed and the device has reconnected.\n\n"
                "Restore factory parameters now?\n"
                "(The device will reboot once more.)\n\n"
                f"{follow_up}")
    btn_restore = box.addButton("Restore", QMessageBox.ButtonRole.AcceptRole)
    box.addButton("Skip", QMessageBox.ButtonRole.RejectRole)
    box.exec()
    return box.clickedButton() == btn_restore


def ask_backup_before_update(parent) -> bool:
    """펌웨어 업데이트 전 파라미터 백업 여부 — 답만 반환 (연결 상태에서만 묻는다)."""
    reply = QMessageBox.question(
        parent, "Backup Before Firmware Update",
        "Back up the device parameters before the firmware update?\n\n"
        "The Backup window will open. When the backup file is saved (or the window is closed),\n"
        "the Firmware Update window opens automatically.",
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        QMessageBox.StandardButton.Yes)
    return reply == QMessageBox.StandardButton.Yes


class NoBackupChoice(Enum):
    """백업 파일을 저장하지 않고 백업 창을 닫을 때의 선택."""
    CONTINUE = auto()  # 백업 없이 펌웨어 업데이트로 진행
    STAY     = auto()  # 백업 창을 닫지 않는다
    CANCEL   = auto()  # 창을 닫고 업데이트도 하지 않는다


def ask_close_without_backup(parent) -> NoBackupChoice:
    """백업 파일 없이 백업 창을 닫으려 할 때 — 선택만 반환 (닫으면 STAY)."""
    box = QMessageBox(parent)
    box.setWindowTitle("No Backup File")
    box.setText("No backup file has been saved.\n\n"
                "Continue to the firmware update without a backup?")
    btn_continue = box.addButton("Continue without backup", QMessageBox.ButtonRole.AcceptRole)
    btn_stay = box.addButton("Stay", QMessageBox.ButtonRole.RejectRole)
    btn_cancel = box.addButton("Cancel update", QMessageBox.ButtonRole.DestructiveRole)
    box.setDefaultButton(btn_stay)
    box.exec()

    clicked = box.clickedButton()
    if clicked == btn_continue:
        return NoBackupChoice.CONTINUE
    if clicked == btn_cancel:
        return NoBackupChoice.CANCEL
    return NoBackupChoice.STAY


def ask_abort_update(parent) -> bool:
    """진행 중인 펌웨어 쓰기 중단 여부 — 답만 반환."""
    reply = QMessageBox.question(
        parent, "Abort Firmware Update",
        "Firmware update is in progress.\n"
        "Aborting may leave the valve without a valid firmware until the update is run again.\n\n"
        "Abort now?",
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        QMessageBox.StandardButton.No)
    return reply == QMessageBox.StandardButton.Yes
