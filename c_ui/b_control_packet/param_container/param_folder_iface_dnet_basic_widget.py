from b_core.c_manager.parameter_manager import ParamManager
from c_ui.b_control_packet.param_container.param_folder_widget import ParamFolderWidget

class ParamFolderIfaceDnetBasicWidget(ParamFolderWidget):
    def __init__(self, parent=None):
        super().__init__(folder_name="Basic", param_path=None, label_width = 210, parent=parent)

        param = ParamManager().get_by_full_path("DeviceNet User Interface.DeviceNet Object.MAC ID Switch"        ); self.add_param(param)
        param = ParamManager().get_by_full_path("DeviceNet User Interface.DeviceNet Object.MAC ID"               ); self.add_param(param)
        param = ParamManager().get_by_full_path("DeviceNet User Interface.DeviceNet Object.Baud Rate"            ); self.add_param(param)
        param = ParamManager().get_by_full_path("DeviceNet User Interface.Identity Object.Instance.Vendor ID"    ); self.add_param(param)
        param = ParamManager().get_by_full_path("DeviceNet User Interface.Identity Object.Instance.Device Type"  ); self.add_param(param)
        param = ParamManager().get_by_full_path("DeviceNet User Interface.Identity Object.Instance.Product Code" ); self.add_param(param)
        param = ParamManager().get_by_full_path("DeviceNet User Interface.Identity Object.Instance.Product Name" ); self.add_param(param)
        param = ParamManager().get_by_full_path("DeviceNet User Interface.Identity Object.Instance.Revision"     ); self.add_param(param)
        param = ParamManager().get_by_full_path("DeviceNet User Interface.Identity Object.Instance.Serial Number"); self.add_param(param)
        param = ParamManager().get_by_full_path("DeviceNet User Interface.Connection Object.Profile.Profile"     ); self.add_param(param)
        param = ParamManager().get_by_full_path("DeviceNet User Interface.Connection Object.Profile.Data type"   ); self.add_param(param)
        param = ParamManager().get_by_full_path("DeviceNet User Interface.Identity Object.Services.Reset"        ); self.add_param(param)