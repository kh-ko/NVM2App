from b_core.c_manager.parameter_manager import ParamManager
from c_ui.b_control_packet.param_container.param_folder_widget import ParamFolderWidget

class ParamFolderPresCtrlControllerWidget(ParamFolderWidget):
    def __init__(self, controller_index: int, parent=None):
        super().__init__(folder_name=f"Controller {controller_index}", param_path=None, label_width = 150, parent=parent)

        param = ParamManager().get_by_full_path(f"Pressure Control.Controller {controller_index}.Control Algorithm.Algorithm mode"       ); self.add_param(param)
        param = ParamManager().get_by_full_path(f"Pressure Control.Controller {controller_index}.Adaptive Settings.Gain Factor"          ); self.add_param(param)
        param = ParamManager().get_by_full_path(f"Pressure Control.Controller {controller_index}.Adaptive Settings.Delta Factor"         ); self.add_param(param)
        param = ParamManager().get_by_full_path(f"Pressure Control.Controller {controller_index}.Adaptive Settings.Sensor Delay [sec]"   ); self.add_param(param)
        param = ParamManager().get_by_full_path(f"Pressure Control.Controller {controller_index}.Adaptive Settings.Learn Data Selection" ); self.add_param(param)
        param = ParamManager().get_by_full_path(f"Pressure Control.Controller {controller_index}.PI/Soft Pump Settings.Control Direction"); self.add_param(param)
        param = ParamManager().get_by_full_path(f"Pressure Control.Controller {controller_index}.PI/Soft Pump Settings.P-Gain"           ); self.add_param(param)
        param = ParamManager().get_by_full_path(f"Pressure Control.Controller {controller_index}.PI/Soft Pump Settings.I-Gain"           ); self.add_param(param)
        param = ParamManager().get_by_full_path(f"Pressure Control.Controller {controller_index}.PI/Soft Pump Settings.Pressure Scaler"  ); self.add_param(param)
        param = ParamManager().get_by_full_path(f"Pressure Control.Controller {controller_index}.Ramp.Enable"                            ); self.add_param(param)
        param = ParamManager().get_by_full_path(f"Pressure Control.Controller {controller_index}.Ramp.Time [sec]"                        ); self.add_param(param)
        param = ParamManager().get_by_full_path(f"Pressure Control.Controller {controller_index}.Ramp.Slope"                             ); self.add_param(param)
        param = ParamManager().get_by_full_path(f"Pressure Control.Controller {controller_index}.Ramp.Mode"                              ); self.add_param(param)
        param = ParamManager().get_by_full_path(f"Pressure Control.Controller {controller_index}.Ramp.Start Value"                       ); self.add_param(param)
        param = ParamManager().get_by_full_path(f"Pressure Control.Controller {controller_index}.Ramp.Type"                              ); self.add_param(param)
        