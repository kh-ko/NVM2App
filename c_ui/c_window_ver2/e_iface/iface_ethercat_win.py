"""Interface EtherCAT 창 — ParamWin(폴더 카드) + Create XML + Advanced Range 모드 (2단계 8위 ③ 에서 param_win.py 에서 분리).

Range 폴더들의 Data type 은 프로토콜상 폴더마다 따로지만 UI 에서는 하나의 값으로 일괄 운용한다 (하나를 편집하면 나머지에
복사 → Apply 가 일괄로 쓴다). Advanced Range 모드는 Scaling 폴더 표시 ↔ Range 의 Data Value 표시를 맞바꾸며, 숨겨지는 쪽의
RW 편집은 원복한다. Load File 은 파일에 Scaling 항목이 있으면 Advanced, 없으면 Basic 으로 맞춘 뒤 적용한다
(before_apply_loaded_items).
"""

from PySide6.QtWidgets import QFileDialog, QMessageBox

from b_core.b_datatype.general_enum import ParamAccType
from b_core.b_datatype.param_enum import EtherCATDataTypeEnum
from b_core.c_manager.app_log_manager import AppLogManager
from b_core.f_helper import ethercat_xml_file_helper

from c_ui.c_window_ver2.param_win import ParamWin


class ParamIfaceEtherCatWin(ParamWin):
    def __init__(self, parent=None, win_name = None, paths : list[str] = None, filter_param_paths : list[str] = None, is_editblock_win=False, label_width=210, folder_max_width=None):

        super().__init__(parent=parent, win_name = win_name, paths = paths, filter_param_paths = filter_param_paths, is_editblock_win=is_editblock_win, label_width=label_width, folder_max_width=folder_max_width)
        self.toolbar.add_action("Create XML", self.on_clicked_create_xml)
        self.action_advanced_range = self.toolbar.add_action("Enable Advanced Range", self.on_clicked_toggle_advanced_range)

        # 초기 모드: Basic — Scaling 폴더 숨김, Range 전체 표시
        self._apply_advanced_range_mode(False)

    def additional_param_settings(self):
        # Range 폴더들의 Data type 위젯 수집 — 프로토콜상 param 은 폴더별로
        # 따로지만 UI 에서는 하나의 값으로 일괄 운용한다. 경로/이름은 바뀔 수
        # 있으므로 전용 enum(EtherCATDataTypeEnum) 사용 여부로 걸러낸다
        self.data_type_widgets = [pw
                                  for fw in self.folder_widgets
                                  for pw in fw.widgets
                                  if pw.param.ref_list is EtherCATDataTypeEnum]

        for pw in self.data_type_widgets:
            pw.sig_edited_by_user.connect(self.handle_edited_data_type)

        # Advanced Range 모드 전환 대상 — Scaling 폴더 전체(EtherCAT 전용 +
        # 공용 Interface.Scaling)와, Range 폴더의 Data type 을 제외한
        # 나머지(= Data Value 들)
        self.scaling_folder_widgets = [fw for fw in self.folder_widgets
                                       if fw.folder_path.startswith(("Interface EtherCAT.Scaling", "Interface.Scaling"))]
        self.range_data_value_widgets = [pw
                                         for fw in self.folder_widgets
                                         for pw in fw.widgets
                                         if pw.param.path.startswith("Interface EtherCAT.Range")
                                         and pw.param.ref_list is not EtherCATDataTypeEnum]

    def handle_edited_data_type(self, edited_widget):
        value = edited_widget.get_value()
        for pw in self.data_type_widgets:
            if pw is not edited_widget:
                pw.set_value(value)   # 코드 할당 -> dirty, Apply 가 일괄로 쓴다

    def _apply_advanced_range_mode(self, is_advanced: bool):
        """Advanced: Scaling 폴더 표시 + Range 의 Data Value 숨김 / Basic: 반대.

        숨겨지는 쪽의 RW 편집은 원복한다 — Apply 의 is_editable() 은 위젯 자신의 isHidden() 만 보므로
        폴더 단위로 숨긴 Scaling 위젯은 걸러지지 않는다(Save/Load 의 isVisible 과 기준이 다름).
        숨은 편집이 장비로 새어 나가면 안 된다"""
        self.is_advanced_range = is_advanced

        hidden_widgets = (self.range_data_value_widgets if is_advanced
                          else [pw for fw in self.scaling_folder_widgets for pw in fw.widgets])
        for pw in hidden_widgets:
            if pw.param.acc != ParamAccType.RO:
                pw.handle_param_value_changed()  # set_value(param.value) + commit — dirty 원복

        for fw in self.scaling_folder_widgets:
            fw.setVisible(is_advanced)
        for pw in self.range_data_value_widgets:
            pw.setVisible(not is_advanced)

        self.action_advanced_range.setText("Disable Advanced Range" if is_advanced else "Enable Advanced Range")

    def on_clicked_toggle_advanced_range(self):
        self._apply_advanced_range_mode(not self.is_advanced_range)

    def before_apply_loaded_items(self, loaded_items):
        # 파일에 Scaling 항목이 있으면 Advanced, 없으면 Basic 으로 맞춘 뒤 적용 —
        # 이후의 visible 필터가 반대편(숨겨진) 항목을 자동으로 걸러낸다
        scaling_keys = {(pw.param.path, pw.param.name)
                        for fw in self.scaling_folder_widgets
                        for pw in fw.widgets}
        has_scaling = any(isinstance(item, dict)
                          and (item.get("path"), item.get("name")) in scaling_keys
                          for item in loaded_items)
        self._apply_advanced_range_mode(has_scaling)

    def on_clicked_create_xml(self):
        file_path, _ = QFileDialog.getSaveFileName(self, "Save XML File", "", "XML Files (*.xml);;All Files (*)")
        if not file_path:
            return

        try:
            ethercat_xml_file_helper.create_xml_file(file_path)
        except Exception as e:
            AppLogManager().get_logger(self.win_name).error(f"XML 파일 생성 실패: {e}")
            QMessageBox.critical(self, "Error", f"Failed to create XML file.\nError details: {e}")
            return

        QMessageBox.information(self, "Success", "XML file has been created successfully.")       
