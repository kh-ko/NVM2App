from typing import List

from b_core.b_datatype.general_enum import ParamAccType
from b_core.b_datatype.general_enum import ParamDisplayType
from b_core.c_manager.parameter_manager import ParamManager
from c_ui.a_converter.pressure_converter_manager import PresConvertType
from c_ui.b_control_ver2.b_base.containers import PanelWidget
from c_ui.b_control_ver2.d_param.param_values import (ParamWriteOnlyButtonValueWidget, ParamReadWriteHexValueWidget, ParamReadWriteEnumValueWidget, 
                                                    ParamReadOnlyTextValueWidget, ParamReadOnlyNumValueWidget, ParamReadWriteNumValueWidget, 
                                                    ParamReadOnlyRealValueWidget, ParamReadWriteRealValueWidget, ParamReadOnlyBitmapValueWidget, 
                                                    ParamReadOnlyEnumValueWidget, ParamReadOnlyMultipleEnumValueWidget, ParamReadOnlyPosiValueWidget,
                                                    ParamReadWritePosiValueWidget, ParamReadOnlyPresValueWidget, ParamWriteOnlyEnumValueWidget,
                                                    ParamReadWritePresValueWidget, ParamReadOnlyScaleValueWidget, ParamReadWriteScaleValueWidget,
                                                    ParamReadWriteBitmapValueWidget, ParamReadOnlyPresSlopeValueWidget, ParamReadWritePresSlopeValueWidget)

class ParamFolderWidget(PanelWidget):
    def __init__(self, force_title : str = None, folder_path: str = None, filter_param_paths : List[str] = None, params : List = None, label_width = 210, parent=None):
        if force_title is not None:
            title = force_title
        else:
            title = folder_path
        super().__init__(title=title, parent=parent)

        self.widgets = []

        # params 를 직접 받으면 재스캔 없이 사용한다 — ParamWin 처럼 여러 폴더를
        # 만들 때 get_params_grouped() 결과를 나눠 받는 경로 (전체 param 1회 순회).
        # 단독 사용 시에는 기존처럼 폴더 경로로 직접 조회한다
        if params is not None:
            all_params = params
        else:
            all_params = ParamManager().get_params_in_folder(folder_path, filter_param_paths)

        for param in all_params:
            component = None

            if param.display_type == ParamDisplayType.TEXT:
                if param.acc == ParamAccType.RO:
                    component = ParamReadOnlyTextValueWidget(param_full_path=f"{param.path}.{param.name}", force_label_text=None, label_width=label_width, is_vertical_mode=False)
                elif param.acc == ParamAccType.RW:
                    pass
                elif param.acc == ParamAccType.WO:
                    pass
            elif param.display_type == ParamDisplayType.BTN:
                if param.acc == ParamAccType.WO:
                    component = ParamWriteOnlyButtonValueWidget(param_full_path=f"{param.path}.{param.name}", force_label_text=None, label_width=label_width, is_vertical_mode=False)
                else:
                    pass
            elif param.display_type == ParamDisplayType.ENUM:
                if param.acc == ParamAccType.RO:
                    component = ParamReadOnlyEnumValueWidget(param_full_path=f"{param.path}.{param.name}", force_label_text=None, label_width=label_width, is_vertical_mode=False)
                elif param.acc == ParamAccType.RW:
                    component = ParamReadWriteEnumValueWidget(param_full_path=f"{param.path}.{param.name}", force_label_text=None, label_width=label_width, is_vertical_mode=False)
                elif param.acc == ParamAccType.WO:
                    component = ParamWriteOnlyEnumValueWidget(param_full_path=f"{param.path}.{param.name}", force_label_text=None, label_width=label_width, is_vertical_mode=False)
            elif param.display_type == ParamDisplayType.ERR_NUM:
                if param.acc == ParamAccType.RO:
                    component = ParamReadOnlyMultipleEnumValueWidget(param_full_path=f"{param.path}.{param.name}", force_label_text=None, label_width=label_width, is_vertical_mode=False)
                else:
                    pass
            elif param.display_type == ParamDisplayType.HEX:
                if param.acc == ParamAccType.RO:
                    pass
                elif param.acc == ParamAccType.RW:
                    component = ParamReadWriteHexValueWidget(param_full_path=f"{param.path}.{param.name}", force_label_text=None, label_width=label_width, is_vertical_mode=False)
                elif param.acc == ParamAccType.WO:
                    pass
            elif param.display_type == ParamDisplayType.NUMBER:
                if param.acc == ParamAccType.RO:
                    component = ParamReadOnlyNumValueWidget(param_full_path=f"{param.path}.{param.name}", force_label_text=None, label_width=label_width, is_vertical_mode=False)
                elif param.acc == ParamAccType.RW:
                    component = ParamReadWriteNumValueWidget(param_full_path=f"{param.path}.{param.name}", force_label_text=None, label_width=label_width, is_vertical_mode=False)
                elif param.acc == ParamAccType.WO:
                    pass
            elif param.display_type == ParamDisplayType.REAL:
                if param.acc == ParamAccType.RO:
                    component = ParamReadOnlyRealValueWidget(param_full_path=f"{param.path}.{param.name}", force_label_text=None, label_width=label_width, is_vertical_mode=False)
                elif param.acc == ParamAccType.RW:
                    component = ParamReadWriteRealValueWidget(param_full_path=f"{param.path}.{param.name}", force_label_text=None, label_width=label_width, is_vertical_mode=False)
                elif param.acc == ParamAccType.WO:
                    pass
            elif param.display_type == ParamDisplayType.BITMAP:
                if param.acc == ParamAccType.RO:
                    component = ParamReadOnlyBitmapValueWidget(param_full_path=f"{param.path}.{param.name}", force_label_text=None, label_width=label_width, is_vertical_mode=False)
                elif param.acc == ParamAccType.RW:
                    component = ParamReadWriteBitmapValueWidget(param_full_path=f"{param.path}.{param.name}", force_label_text=None, label_width=label_width, is_vertical_mode=False)
                #elif param.acc == ParamAccType.WO:
                #    pass
            elif param.display_type == ParamDisplayType.POSI:
                if param.acc == ParamAccType.RO:
                    component = ParamReadOnlyPosiValueWidget(param_full_path=f"{param.path}.{param.name}", force_label_text=None, label_width=label_width, is_vertical_mode=False)
                elif param.acc == ParamAccType.RW:
                    component = ParamReadWritePosiValueWidget(param_full_path=f"{param.path}.{param.name}", force_label_text=None, label_width=label_width, is_vertical_mode=False)
                elif param.acc == ParamAccType.WO:
                    pass
            elif param.display_type == ParamDisplayType.SENS_PRES:
                if param.acc == ParamAccType.RO:
                    component = ParamReadOnlyPresValueWidget(param_full_path=f"{param.path}.{param.name}", force_label_text=None, label_width=label_width, is_vertical_mode=False, is_visible_unit = True, convert_type = PresConvertType.AUTO)
                elif param.acc == ParamAccType.RW:
                    component = ParamReadWritePresValueWidget(param_full_path=f"{param.path}.{param.name}", force_label_text=None, label_width=label_width, is_vertical_mode=False, is_visible_unit = True, convert_type = PresConvertType.AUTO)
                elif param.acc == ParamAccType.WO:
                    pass
            elif param.display_type == ParamDisplayType.SENS1_PRES:
                if param.acc == ParamAccType.RO:
                    component = ParamReadOnlyPresValueWidget(param_full_path=f"{param.path}.{param.name}", force_label_text=None, label_width=label_width, is_vertical_mode=False, is_visible_unit = True, convert_type = PresConvertType.SENSOR1)
                elif param.acc == ParamAccType.RW:
                    component = ParamReadWritePresValueWidget(param_full_path=f"{param.path}.{param.name}", force_label_text=None, label_width=label_width, is_vertical_mode=False, is_visible_unit = True, convert_type = PresConvertType.SENSOR1)
                elif param.acc == ParamAccType.WO:
                    pass
            elif param.display_type == ParamDisplayType.SENS2_PRES:
                if param.acc == ParamAccType.RO:
                    component = ParamReadOnlyPresValueWidget(param_full_path=f"{param.path}.{param.name}", force_label_text=None, label_width=label_width, is_vertical_mode=False, is_visible_unit = True, convert_type = PresConvertType.SENSOR2)
                elif param.acc == ParamAccType.RW:
                    component = ParamReadWritePresValueWidget(param_full_path=f"{param.path}.{param.name}", force_label_text=None, label_width=label_width, is_vertical_mode=False, is_visible_unit = True, convert_type = PresConvertType.SENSOR2)
                elif param.acc == ParamAccType.WO:
                    pass
            elif param.display_type == ParamDisplayType.SCALE:
                if param.acc == ParamAccType.RO:
                    component = ParamReadOnlyScaleValueWidget(param_full_path=f"{param.path}.{param.name}", force_label_text=None, label_width=label_width, is_vertical_mode=False)
                elif param.acc == ParamAccType.RW:
                    component = ParamReadWriteScaleValueWidget(param_full_path=f"{param.path}.{param.name}", force_label_text=None, label_width=label_width, is_vertical_mode=False)
                elif param.acc == ParamAccType.WO:
                    pass
            elif param.display_type == ParamDisplayType.PRESS_SLOPE:
                if param.acc == ParamAccType.RO:
                    component = ParamReadOnlyPresSlopeValueWidget(param_full_path=f"{param.path}.{param.name}", force_label_text=None, label_width=label_width, is_vertical_mode=False, is_visible_unit = True, convert_type = PresConvertType.AUTO)
                elif param.acc == ParamAccType.RW:
                    component = ParamReadWritePresSlopeValueWidget(param_full_path=f"{param.path}.{param.name}", force_label_text=None, label_width=label_width, is_vertical_mode=False, is_visible_unit = True, convert_type = PresConvertType.AUTO)
                elif param.acc == ParamAccType.WO:
                    pass

            
            if component is not None:
                self.add_widget(component)
                self.widgets.append(component)

    def get_param_count(self)->int:
        # param 목록은 widgets 에서 파생 가능 (widget.param) — 병렬 리스트를 두지 않는다
        return len(self.widgets)
