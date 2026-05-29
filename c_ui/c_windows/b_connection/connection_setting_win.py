import json
import os
from PySide6.QtWidgets import (
    QMainWindow, QVBoxLayout, QHBoxLayout, QListWidget, 
    QPushButton, QMessageBox, QWidget, QFormLayout, 
    QLineEdit, QCheckBox, QSplitter, QComboBox,
    QLabel, QFrame
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtSerialPort import QSerialPort 

from b_core.a_define import file_folder_path
from b_core.b_datatype.general_enum import ConnectionBaudRateEnum, ConnectionDataBitsEnum, ConnectionNetworkEnum, ConnectionParityEnum, ConnectionStopBitsEnum, ConnectionTerminationEnum

from c_ui.b_control_packet.base.base_toolbar import BaseToolBar
from c_ui.b_control_packet.layout.my_splitter import MySplitter
from c_ui.b_control_packet.layout.my_panel_widget import MyPanelWidget
from c_ui.b_control_packet.layout.my_list_widget import MyListWidget
from c_ui.b_control_packet.controls_with_label.l_enum_rw_widget import LEnumReadWriteWidget
from c_ui.b_control_packet.controls_with_label.l_text_rw_widget import LTextReadWriteWidget

class ConnectionSettingWin(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Connection >> Settings")
        self.resize(750, 450)
        
        self.json_path = file_folder_path.RSRC_CONNECTIONS_JSON_FILE
        self.connection_data = []
        self.current_index = -1

        self.init_ui()
        self._load_connection_infos()

    def init_ui(self):
        self.toolbar = BaseToolBar(self)
        self.addToolBar(Qt.TopToolBarArea, self.toolbar)
        self.toolbar.add_action("Create", self.add_connection_info)
        self.toolbar.add_action("Save", self.save_connection_info)
        self.toolbar.add_action("Delete", self.delete_connection_info)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)

        self.splitter = MySplitter(Qt.Horizontal)
        main_layout.addWidget(self.splitter)

        self.list_widget = MyListWidget()
        self.list_widget.currentRowChanged.connect(self.on_change_item)
        self.splitter.addWidget(self.list_widget)

        self.panel = MyPanelWidget("Detail")
        self.splitter.addWidget(self.panel)
        
        self.name_edit = LTextReadWriteWidget("Name")
        self.panel.add_widget(self.name_edit)

        self.network_combo = LEnumReadWriteWidget(enum_class=ConnectionNetworkEnum, label_text="Network")
        self.network_combo.setEnabled(False)
        self.panel.add_widget(self.network_combo)

        self.address_edit = LTextReadWriteWidget("Address")
        self.address_edit.setEnabled(False)
        self.panel.add_widget(self.address_edit)

        self.baudrate_combo = LEnumReadWriteWidget(enum_class=ConnectionBaudRateEnum, label_text="Baudrate")
        self.panel.add_widget(self.baudrate_combo)

        self.databits_combo = LEnumReadWriteWidget(enum_class=ConnectionDataBitsEnum, label_text="Data Bits")
        self.panel.add_widget(self.databits_combo)

        self.parity_combo = LEnumReadWriteWidget(enum_class=ConnectionParityEnum, label_text="Parity")
        self.panel.add_widget(self.parity_combo)

        self.stopbits_combo = LEnumReadWriteWidget(enum_class=ConnectionStopBitsEnum, label_text="Stop Bits")
        self.panel.add_widget(self.stopbits_combo)

        self.termination_combo = LEnumReadWriteWidget(enum_class=ConnectionTerminationEnum, label_text="Termination")
        self.panel.add_widget(self.termination_combo)

        self.panel.add_stretch()

        self.splitter.setSizes([200, 550])

    def _load_connection_infos(self):
        self.list_widget.clear()
        self.connection_data = []

        if os.path.exists(self.json_path):
            try:
                with open(self.json_path, 'r', encoding='utf-8') as f:
                    self.connection_data = json.load(f)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to load connections: {str(e)}")
                return
        else:
            self.connection_data = []

        for item in self.connection_data:
            name = item.get("name", "Unknown")
            self.list_widget.addItem(name)

        # 3. 데이터가 있다면 첫 번째 항목을 선택하도록 설정
        if self.list_widget.count() > 0:
            self.list_widget.setCurrentRow(0)

    def add_connection_info(self):
        base_name = self.name_edit.get_value().strip()
        if not base_name:
            base_name = "New_Connection"
            
        new_name = base_name
        existing_names = [item.get("name", "") for item in self.connection_data]
        
        counter = 1
        while new_name in existing_names:
            new_name = f"{base_name}_{counter}"
            counter += 1

        new_data = {
            "name": new_name,
            "network": self.network_combo.get_value(),
            "address": self.address_edit.get_value(),
            "baudrate": self.baudrate_combo.get_value(),
            "dataBits": self.databits_combo.get_value(),
            "parity": self.parity_combo.get_value(),
            "stopBits": self.stopbits_combo.get_value(),
            "termination": self.termination_combo.get_value(),
            "isSelect": False
        }

        self.connection_data.append(new_data)

        try:
            os.makedirs(os.path.dirname(self.json_path), exist_ok=True)
            
            with open(self.json_path, 'w', encoding='utf-8') as f:
                json.dump(self.connection_data, f, indent=4, ensure_ascii=False)
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save connection info:\n{str(e)}")
            self.connection_data.pop()
            return

        self.list_widget.addItem(new_name)
        self.list_widget.setCurrentRow(self.list_widget.count() - 1)

        QMessageBox.information(self, "Success", f"'{new_name}' has been successfully added.")
        
    def save_connection_info(self):
        if self.current_index < 0 or self.current_index >= len(self.connection_data):
            QMessageBox.warning(self, "Warning", "Please select an item to save.")
            return

        new_name = self.name_edit.get_value().strip()
        if not new_name:
            QMessageBox.warning(self, "Warning", "Please enter a name.")
            return

        for i, item in enumerate(self.connection_data):
            if i != self.current_index and item.get("name") == new_name:
                QMessageBox.warning(self, "Warning", f"The name '{new_name}' already exists.\nPlease choose a different name.")
                return

        data = self.connection_data[self.current_index]

        old_data = {
            "name": data.get("name", ""),
            "network": data.get("network", 0),
            "address": data.get("address", "192.168.1.1"),
            "baudrate": data.get("baudrate", 9600),
            "dataBits": data.get("dataBits", 8),
            "parity": data.get("parity", 0),
            "stopBits": data.get("stopBits", 1),
            "termination": data.get("termination", 0),
            "isSelect": data.get("isSelect", False)
        }

        data["name"] = new_name
        data["network"] = self.network_combo.get_value()
        data["address"] = self.address_edit.get_value()
        data["baudrate"] = self.baudrate_combo.get_value()
        data["dataBits"] = self.databits_combo.get_value()
        data["parity"] = self.parity_combo.get_value()
        data["stopBits"] = self.stopbits_combo.get_value()
        data["termination"] = self.termination_combo.get_value()

        try:
            os.makedirs(os.path.dirname(self.json_path), exist_ok=True)
            
            with open(self.json_path, 'w', encoding='utf-8') as f:
                json.dump(self.connection_data, f, indent=4, ensure_ascii=False)

                list_item = self.list_widget.item(self.current_index)
                if list_item:
                    list_item.setText(new_name)

                self.name_edit.commit()
                self.network_combo.commit()
                self.address_edit.commit()
                self.baudrate_combo.commit()
                self.databits_combo.commit()
                self.parity_combo.commit()
                self.stopbits_combo.commit()
                self.termination_combo.commit()
                QMessageBox.information(self, "Success", f"'{new_name}' has been successfully updated.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save connection info:\n{str(e)}")
            data.update(old_data)
            return

    def delete_connection_info(self):
        if self.current_index < 0 or self.current_index >= len(self.connection_data):
            QMessageBox.warning(self, "Warning", "Please select an item to delete.")
            return

        if len(self.connection_data) <= 1:
            QMessageBox.warning(self, "Warning", "Cannot delete the last remaining item.\nAt least one item must be kept.")
            return

        item_name = self.connection_data[self.current_index].get("name", "Unknown")
        reply = QMessageBox.question(self, "Confirm Delete", 
                                     f"Are you sure you want to delete '{item_name}'?",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        
        if reply == QMessageBox.No:
            return

        deleted_data = self.connection_data.pop(self.current_index)

        try:
            with open(self.json_path, 'w', encoding='utf-8') as f:
                json.dump(self.connection_data, f, indent=4, ensure_ascii=False)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to delete connection info:\n{str(e)}")
            self.connection_data.insert(self.current_index, deleted_data)
            return

        self.list_widget.takeItem(self.current_index)

        if self.list_widget.count() > 0:
            self.list_widget.setCurrentRow(0)
            
        QMessageBox.information(self, "Success", f"'{item_name}' has been successfully deleted.")

    def on_change_item(self, current_row):
        if current_row < 0 or current_row >= len(self.connection_data):
            self.current_index = -1
            return

        self.current_index = current_row
        data = self.connection_data[current_row]

        # 1. 텍스트 입력창 업데이트
        self.name_edit.set_value(str(data.get("name", "")))
        self.name_edit.commit()
        self.address_edit.set_value(str(data.get("address", "0")))
        self.address_edit.commit()

        # 2. 콤보박스 업데이트 (데이터 값에 해당하는 index를 찾아 설정)
        self.network_combo.set_value(data.get("network", 0))
        self.network_combo.commit()

        self.baudrate_combo.set_value(data.get("baudrate", 9600))
        self.baudrate_combo.commit()

        self.databits_combo.set_value(data.get("dataBits", 8))
        self.databits_combo.commit()

        self.parity_combo.set_value(data.get("parity", 0))
        self.parity_combo.commit()

        self.stopbits_combo.set_value(data.get("stopBits", 1))
        self.stopbits_combo.commit()

        self.termination_combo.set_value(data.get("termination", 0))
        self.termination_combo.commit()