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

from c_ui.b_components.a_custom.custom_list import CustomListWidget
from c_ui.b_components.a_custom.custom_splitter import CustomSplitter
from c_ui.b_components.a_custom.custom_combobox import CustomComboBox
from c_ui.b_components.a_custom.custom_toolbar import CustomToolBar
from c_ui.b_components.a_custom.custom_panel import CustomPanel
from c_ui.b_components.a_custom.custom_line_edit import CustomLineEdit

class ConnectionSettingWin(QMainWindow):
    """
    통신 설정(connections.json) 데이터를 관리(생성, 저장, 삭제)하는 윈도우 클래스입니다.
    마스터-디테일(Master-Detail) 구조로 구현되어 있으며, 좌우 스플리터(Splitter)로 영역을 분할합니다.

    [주요 구성 및 동작]
    1. 툴바 (TopToolBar): 
       - 새로운 통신 설정 추가(Create), 현재 설정 수정/저장(Save), 선택된 설정 삭제(Delete) 기능을 제공합니다.
    2. 좌측 리스트 (CustomListWidget):
       - 저장된 통신 설정 데이터의 이름("name") 목록을 표시합니다.
       - 항목 선택 시 우측 상세 패널에 해당 설정의 값이 로딩됩니다.
    3. 우측 상세 패널 (CustomPanel - Detail):
       - 선택된 통신 설정의 상세 정보를 확인하고 수정할 수 있는 입력 폼입니다.
       - Name : 통신 설정의 이름 (CustomLineEdit)
       - Network : 네트워크 방식(RS232, RS485, TCP/IP) - 예정 기능으로 비활성화 (CustomComboBox)
       - Address : 연결 주소 - 예정 기능으로 비활성화 (CustomLineEdit)
       - Baudrate : 통신 속도(9600~115200) 지정 (CustomComboBox)
       - Data Bits : 데이터 비트(5~8) 지정 (CustomComboBox)
       - Parity : 패리티 비트(No, Even, Odd, Space, Mark) 지정 (CustomComboBox)
       - Stop Bits : 정지 비트(One, Two, OneAndHalf) 지정 (CustomComboBox)
       - Termination : 종료 문자(CR+LF, LF, CR) 지정 (CustomComboBox)
    """
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
        self.toolbar = CustomToolBar(self)
        self.addToolBar(Qt.TopToolBarArea, self.toolbar)
        self.toolbar.add_action("Create", self.add_connection_info)
        self.toolbar.add_action("Save", self.save_connection_info)
        self.toolbar.add_action("Delete", self.delete_connection_info)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)

        self.splitter = CustomSplitter(Qt.Horizontal)
        main_layout.addWidget(self.splitter)

        self.list_widget = CustomListWidget()
        self.list_widget.currentRowChanged.connect(self.on_change_item)
        self.splitter.addWidget(self.list_widget)

        self.panel = CustomPanel("Detail")
        self.splitter.addWidget(self.panel)
        
        self.name_edit = CustomLineEdit("Name")
        self.panel.add_widget(self.name_edit)

        self.network_combo = CustomComboBox("Network")
        self.network_combo.addItem("RS232", 0)
        self.network_combo.addItem("RS485", 1)
        self.network_combo.addItem("TCP/IP", 2)
        self.network_combo.setEnabled(False)
        self.panel.add_widget(self.network_combo)

        self.address_edit = CustomLineEdit("Address")
        self.address_edit.setEnabled(False)
        self.panel.add_widget(self.address_edit)

        self.baudrate_combo = CustomComboBox("Baudrate")
        for br in [9600, 19200, 38400, 57600, 115200]:
            self.baudrate_combo.addItem(str(br), br)
        self.panel.add_widget(self.baudrate_combo)

        self.databits_combo = CustomComboBox("Data Bits")
        for db in [5, 6, 7, 8]:
            self.databits_combo.addItem(str(db), db)
        self.panel.add_widget(self.databits_combo)

        self.parity_combo = CustomComboBox("Parity")
        self.parity_combo.addItem("NoParity", 0)
        self.parity_combo.addItem("EvenParity", 2)
        self.parity_combo.addItem("OddParity", 3)
        self.parity_combo.addItem("SpaceParity", 4)
        self.parity_combo.addItem("MarkParity", 5)
        self.panel.add_widget(self.parity_combo)

        self.stopbits_combo = CustomComboBox("Stop Bits")
        self.stopbits_combo.addItem("OneStop", 1)
        self.stopbits_combo.addItem("TwoStop", 2)
        self.stopbits_combo.addItem("OneAndHalfStop", 3)
        self.panel.add_widget(self.stopbits_combo)

        self.termination_combo = CustomComboBox("Termination")
        self.termination_combo.addItem("CR+LF", 0)
        self.termination_combo.addItem("LF", 1)
        self.termination_combo.addItem("CR", 2)
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
        base_name = self.name_edit.text().strip()
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
            "network": self.network_combo.currentData(),
            "address": self.address_edit.text(),
            "baudrate": self.baudrate_combo.currentData(),
            "dataBits": self.databits_combo.currentData(),
            "parity": self.parity_combo.currentData(),
            "stopBits": self.stopbits_combo.currentData(),
            "termination": self.termination_combo.currentData(),
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

        new_name = self.name_edit.text().strip()
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
        data["network"] = self.network_combo.currentData()
        data["address"] = self.address_edit.text()
        data["baudrate"] = self.baudrate_combo.currentData()
        data["dataBits"] = self.databits_combo.currentData()
        data["parity"] = self.parity_combo.currentData()
        data["stopBits"] = self.stopbits_combo.currentData()
        data["termination"] = self.termination_combo.currentData()

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
        self.name_edit.setText(str(data.get("name", "")))
        self.address_edit.setText(str(data.get("address", "0")))

        # 2. 콤보박스 업데이트 (데이터 값에 해당하는 index를 찾아 설정)
        self.network_combo.setCurrentIndex(
            self.network_combo.findData(data.get("network", 0))
        )
        self.baudrate_combo.setCurrentIndex(
            self.baudrate_combo.findData(data.get("baudrate", 9600))
        )
        self.databits_combo.setCurrentIndex(
            self.databits_combo.findData(data.get("dataBits", 8))
        )
        self.parity_combo.setCurrentIndex(
            self.parity_combo.findData(data.get("parity", 0))
        )
        self.stopbits_combo.setCurrentIndex(
            self.stopbits_combo.findData(data.get("stopBits", 1))
        )
        self.termination_combo.setCurrentIndex(
            self.termination_combo.findData(data.get("termination", 0))
        )