from PySide6.QtWidgets import QWidget, QMessageBox

from PySide6.QtWidgets import QMainWindow, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QDoubleSpinBox
from PySide6.QtCore import Qt

from b_core.c_manager.local_setting_manager import LocalSettingManager

from c_ui.b_components.a_custom.custom_double_spin_box import CustomDoubleSpinBox
from c_ui.b_components.a_custom.custom_label import CustomLabel
from c_ui.b_components.a_custom.custom_panel import CustomPanel
from c_ui.b_components.a_custom.custom_toolbar import CustomToolBar

class MainPosiEditWin(QMainWindow):
    def __init__(self, parent=None):

        super().__init__(parent)
        self.setWindowTitle("Position Panel Editor")
        self.resize(350, 450)

        self.init_ui()

    def init_ui(self):
        self.toolbar = CustomToolBar(self)
        self.addToolBar(Qt.TopToolBarArea, self.toolbar)
        self.toolbar.add_action("Save", self.on_clicked_save)

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(10, 10, 10, 10)
        self.main_layout.setSpacing(10)

        self.detail_panel = CustomPanel("Position Panel Settings")
        self.main_layout.addWidget(self.detail_panel)

        manager = LocalSettingManager()
        self.spinboxes = []
        current_values = [
            manager.posi_setpoint01, manager.posi_setpoint02, 
            manager.posi_setpoint03, manager.posi_setpoint04, 
            manager.posi_setpoint05, manager.posi_setpoint06
        ]

        for i, val in enumerate(current_values, start=1):
            row_widget = CustomDoubleSpinBox(f"Setpoint {i:02d}")
            row_widget.setValue(val * 100)
            row_widget.setDecimals(2)
            
            # ★ 핵심: CustomPanel의 자체 메서드를 사용하여 위젯 추가
            self.detail_panel.add_widget(row_widget)
            self.spinboxes.append(row_widget)

        # ★ 핵심: 위로 밀착시키기 위한 add_stretch() 호출
        self.detail_panel.add_stretch()

    def on_clicked_save(self):
        manager = LocalSettingManager()
        
        # LocalSettingManager에 값 업데이트 (자동 저장 및 시그널 발생)
        manager.posi_setpoint01 = self.spinboxes[0].value() / 100
        manager.posi_setpoint02 = self.spinboxes[1].value() / 100
        manager.posi_setpoint03 = self.spinboxes[2].value() / 100
        manager.posi_setpoint04 = self.spinboxes[3].value() / 100
        manager.posi_setpoint05 = self.spinboxes[4].value() / 100
        manager.posi_setpoint06 = self.spinboxes[5].value() / 100

        for spinbox in self.spinboxes:
            spinbox.commit()  

        QMessageBox.information(self, "Success", "Position Panel Settings have been successfully saved.")
