from PySide6.QtWidgets import QWidget, QMessageBox

from PySide6.QtWidgets import QMainWindow, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QDoubleSpinBox
from PySide6.QtCore import Qt

from b_core.c_manager.local_setting_manager import LocalSettingManager

from c_ui.a_converter.pressure_converter_manager import PresConverterManager

from c_ui.b_components.a_custom.custom_combobox import CustomComboBox
from c_ui.b_components.a_custom.custom_double_spin_box import CustomDoubleSpinBox
from c_ui.b_components.a_custom.custom_label import CustomLabel
from c_ui.b_components.a_custom.custom_panel import CustomPanel
from c_ui.b_components.a_custom.custom_toolbar import CustomToolBar

class MainPresEditWin(QMainWindow):
    def __init__(self, parent=None):

        super().__init__(parent)
        self.setWindowTitle("Pressure Panel Editor")
        self.resize(350, 450)

        self.converter = PresConverterManager()   
        self.decimal_places = LocalSettingManager().decimal_places

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

        self.detail_panel = CustomPanel("Pressure Panel Settings")
        self.main_layout.addWidget(self.detail_panel)

        manager = LocalSettingManager()
        self.spinboxes = []
        current_values = [
            manager.pres_setpoint01, manager.pres_setpoint02, 
            manager.pres_setpoint03, manager.pres_setpoint04, 
            manager.pres_setpoint05, manager.pres_setpoint06
        ]

        for i, val in enumerate(current_values, start=1):
            row_widget = CustomDoubleSpinBox(f"Setpoint {i:02d}")
            pres_value = self.converter.convert_sfs_to_dp_pres(val)
            row_widget.setValue(pres_value)
            row_widget.setDecimals(self.decimal_places)
            
            # ★ 핵심: CustomPanel의 자체 메서드를 사용하여 위젯 추가
            self.detail_panel.add_widget(row_widget)
            self.spinboxes.append(row_widget)

        self.deciaml_places_combo = CustomComboBox("Decimal Places")
        self.deciaml_places_combo.addItem("0", 0)
        self.deciaml_places_combo.addItem("1", 1)
        self.deciaml_places_combo.addItem("2", 2)
        self.deciaml_places_combo.addItem("3", 3)
        self.deciaml_places_combo.addItem("4", 4)
        self.deciaml_places_combo.addItem("5", 5)
        self.deciaml_places_combo.addItem("6", 6)
        self.deciaml_places_combo.setCurrentIndex(self.deciaml_places_combo.findData(self.decimal_places))
        self.deciaml_places_combo.combo_box.currentIndexChanged.connect(self.on_changed_decimal_places)
        self.deciaml_places_combo.commit()
        self.deciaml_places_combo.setEnabled(True)
        self.detail_panel.add_widget(self.deciaml_places_combo)
        # ★ 핵심: 위로 밀착시키기 위한 add_stretch() 호출
        self.detail_panel.add_stretch()

    def on_changed_decimal_places(self):
        for spinbox in self.spinboxes:
            spinbox.setDecimals(self.deciaml_places_combo.currentData())

    def on_clicked_save(self):
        manager = LocalSettingManager()
        
        manager.pres_setpoint01 = self.converter.convert_dp_pres_to_sfs(self.spinboxes[0].value())
        manager.pres_setpoint02 = self.converter.convert_dp_pres_to_sfs(self.spinboxes[1].value())
        manager.pres_setpoint03 = self.converter.convert_dp_pres_to_sfs(self.spinboxes[2].value())
        manager.pres_setpoint04 = self.converter.convert_dp_pres_to_sfs(self.spinboxes[3].value())
        manager.pres_setpoint05 = self.converter.convert_dp_pres_to_sfs(self.spinboxes[4].value())
        manager.pres_setpoint06 = self.converter.convert_dp_pres_to_sfs(self.spinboxes[5].value())
        manager.decimal_places = self.deciaml_places_combo.currentData()

        for spinbox in self.spinboxes:
            spinbox.commit()  

        self.deciaml_places_combo.commit()

        QMessageBox.information(self, "Success", "Pressure Panel Settings have been successfully saved.")


