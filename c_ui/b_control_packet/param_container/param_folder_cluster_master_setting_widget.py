from c_ui.b_control_packet.param_container.param_folder_widget import ParamFolderWidget

class ParamFolderClusterMasterSettingWidget(ParamFolderWidget):
    def __init__(self, parent=None):
        super().__init__(folder_name="Master Setting", param_path="Cluster.Settings", label_width = 210, parent=parent)

        firmware_ver_param = self.param_manager.get_by_full_path("System.Identification.Firmware.Firmware Version")

        is_ver_1 = False

        if firmware_ver_param.value is None:
            is_ver_1 = True
        else:
            firmware_ver_int = int(firmware_ver_param.value.replace(".", ""), 16)
            if firmware_ver_int < 0x623:
                is_ver_1 = True
            else:
                is_ver_1 = False

        print(f"레이아웃 내 아이템 개수: {self.content_layout.count()}")

        for child in self.content_widget.children():
            if hasattr(child, "param"):
                if child.param.name == "Baud Rate V1" and is_ver_1 == False:
                    self.content_layout.removeWidget(child)
                    self.param_components.remove(child)
                    child.deleteLater()
                elif child.param.name == "Baud Rate V2" and is_ver_1:
                    self.content_layout.removeWidget(child)
                    self.param_components.remove(child)
                    child.deleteLater()
