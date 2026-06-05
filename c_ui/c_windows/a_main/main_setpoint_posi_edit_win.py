from PySide6.QtWidgets import QWidget, QMessageBox

from PySide6.QtWidgets import QMainWindow, QVBoxLayout
from PySide6.QtCore import Qt

from b_core.b_datatype.general_enum import DecimalPlacesEnum
from b_core.c_manager.local_setting_manager import LocalSettingManager

from c_ui.a_converter.position_converter_manager import PosiConverterManager

from c_ui.b_control_packet.base.base_toolbar import BaseToolBar
from c_ui.b_control_packet.layout.my_panel_widget import MyPanelWidget
from c_ui.b_control_packet.controls_with_label.l_enum_rw_widget import LEnumReadWriteWidget
from c_ui.b_control_packet.controls_with_label.l_float_rw_widget import LFloatReadWriteWidget

class MainSetpointPosiEditWin(QMainWindow):
    def __init__(self, parent=None):

        super().__init__(parent)
        self.setWindowTitle("Position Panel Editor")
        self.resize(350, 450)

        self.converter = PosiConverterManager()   

        self.init_ui()

    def init_ui(self):
        self.toolbar = BaseToolBar(self)
        self.addToolBar(Qt.TopToolBarArea, self.toolbar)
        self.toolbar.add_action("Save", self.on_clicked_save)

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(10, 10, 10, 10)
        self.main_layout.setSpacing(10)

        self.detail_panel = MyPanelWidget("Position Panel Settings")
        self.main_layout.addWidget(self.detail_panel)

        manager = LocalSettingManager()
        self.spinboxes = []
        current_values = [
            manager.posi_setpoint01, manager.posi_setpoint02, 
            manager.posi_setpoint03, manager.posi_setpoint04, 
            manager.posi_setpoint05, manager.posi_setpoint06
        ]

        for i in range(1, 7):
            row_widget = LFloatReadWriteWidget(label_text=f"Setpoint {i:02d}")                 
            self.detail_panel.add_widget(row_widget)
            self.spinboxes.append(row_widget)

        self.deciaml_places_combo = LEnumReadWriteWidget(enum_class=DecimalPlacesEnum, label_text="Decimal Places")
        self.deciaml_places_combo.set_value(self.converter.posi_decimal_places)
        self.deciaml_places_combo.commit()
        self.detail_panel.add_widget(self.deciaml_places_combo)
        # ★ 핵심: 위로 밀착시키기 위한 add_stretch() 호출
        self.detail_panel.add_stretch()

        self.deciaml_places_combo.sig_value_changed.connect(self.on_clicked_deciaml_places_changed)

        self.on_clicked_deciaml_places_changed()

    def on_clicked_save(self):
        manager = LocalSettingManager()
        
        if(self.spinboxes[0].is_dirty()):
            posi_value = self.spinboxes[0].get_value()
            manager.posi_setpoint01 = self.converter.convert_dp_posi_to_pfs(posi_value)
        if(self.spinboxes[1].is_dirty()):
            posi_value = self.spinboxes[1].get_value()
            manager.posi_setpoint02 = self.converter.convert_dp_posi_to_pfs(posi_value)
        if(self.spinboxes[2].is_dirty()):
            posi_value = self.spinboxes[2].get_value()
            manager.posi_setpoint03 = self.converter.convert_dp_posi_to_pfs(posi_value)
        if(self.spinboxes[3].is_dirty()):
            posi_value = self.spinboxes[3].get_value()
            manager.posi_setpoint04 = self.converter.convert_dp_posi_to_pfs(posi_value)
        if(self.spinboxes[4].is_dirty()):
            posi_value = self.spinboxes[4].get_value()
            manager.posi_setpoint05 = self.converter.convert_dp_posi_to_pfs(posi_value)
        if(self.spinboxes[5].is_dirty()):
            posi_value = self.spinboxes[5].get_value()
            manager.posi_setpoint06 = self.converter.convert_dp_posi_to_pfs(posi_value)

        if(self.deciaml_places_combo.is_dirty()):
            manager.posi_decimal_places = self.deciaml_places_combo.get_value()

        for spinbox in self.spinboxes:
            spinbox.commit()  

        self.deciaml_places_combo.commit()

        QMessageBox.information(self, "Success", "Position Panel Settings have been successfully saved.")

    def on_clicked_deciaml_places_changed(self):

        manager = LocalSettingManager()
        current_values = [
            manager.posi_setpoint01, manager.posi_setpoint02, 
            manager.posi_setpoint03, manager.posi_setpoint04, 
            manager.posi_setpoint05, manager.posi_setpoint06
        ]

        for i, val in enumerate(current_values, start=0):
            self.spinboxes[i].set_decimal_places(self.deciaml_places_combo.get_value())
            posi_val = self.converter.convert_pfs_to_dp_posi(val)   
            self.spinboxes[i].set_value(posi_val)
            self.spinboxes[i].commit()

        
        


