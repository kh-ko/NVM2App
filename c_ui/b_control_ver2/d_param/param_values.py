from b_core.c_manager.parameter_manager import ParamManager
from c_ui.b_control_ver2.a_theme.tokens  import tokens
from c_ui.b_control_ver2.c_values.read_only_values import ReadOnlyEnumValueWidget, ReadOnlyScaleValueWidget, ReadOnlyPosiValueWidget, ReadOnlyPresValueWidget
from c_ui.b_control_ver2.c_values.read_write_values import ReadWritePresValueSpinBoxWidget, ReadWritePosiValueSpinBoxWidget

class ParamWidget:
    """param 바인딩 공통 동작 믹스인 — c_value 위젯과 다중상속으로 사용한다.

    사용 규칙 (서브클래스 __init__ 에서):
        1. label_text = self._resolve_param(param_full_path, force_label_text)
        2. super().__init__(...)   # 각자 베이스 위젯 인자 매핑 (enum_class 등)
        3. self._bind_param()      # 시그널 연결 + 초기 상태 동기화
    """

    def _resolve_param(self, param_full_path: str, force_label_text: str = None) -> str:
        self.param = ParamManager().get_by_full_path(param_full_path)
        if self.param is None:
            # ParamManager 가 오류 로그를 남긴 뒤 None 을 주므로, 여기서 명확히 실패시킨다
            raise ValueError(f"param not found: {param_full_path}")

        return force_label_text if force_label_text else self.param.name

    def _bind_param(self):
        self.param.sig_value_changed.connect(self.handle_param_value_changed)
        # refresh 동기화 확정 통지 — 값이 안 변해도 set_value+commit 으로 dirty 를 클리어한다
        self.param.sig_synced.connect(self.handle_param_value_changed)
        self.param.sig_is_err_changed.connect(self.handle_param_is_err_changed)
        self.param.sig_is_not_support_changed.connect(self.handle_param_is_not_support_changed)
        self.handle_param_value_changed()
        self.handle_param_is_err_changed()
        self.handle_param_is_not_support_changed()

    def handle_param_value_changed(self):
        # 할당과 확정은 항상 짝 — is_commit=True 로 dirty 기준까지 갱신한다
        self.set_value(self.param.value, is_commit=True)

    def handle_param_is_err_changed(self):
        if self.lbl_label is None:  # 라벨 없는 구성(label_text="")에서는 표시할 곳이 없다
            return

        if self.param.is_err:
            self.lbl_label.set_colors(text=tokens().danger)
        else:
            self.lbl_label.set_colors(text=tokens().text)

    def handle_param_is_not_support_changed(self):
        self.set_not_support(self.param.is_not_support)

class ParamReadOnlyEnumValueWidget(ParamWidget,ReadOnlyEnumValueWidget):
    def __init__(self, param_full_path : str, force_label_text:str=None, label_width : int = 150, is_vertical_mode = False, parent = None):
        label_text = self._resolve_param(param_full_path, force_label_text)
        super().__init__(enum_class=self.param.ref_list, label_text=label_text, label_width=label_width, is_vertical_mode=is_vertical_mode, parent=parent)
        self._bind_param()

class ParamReadOnlyScaleValueWidget(ParamWidget, ReadOnlyScaleValueWidget):
    def __init__(self, param_full_path : str, force_label_text:str=None, label_width : int = 150, is_vertical_mode = False, parent = None):
        label_text = self._resolve_param(param_full_path, force_label_text)
        super().__init__(label_text=f"{label_text} (%)", label_width=label_width, is_vertical_mode=is_vertical_mode, parent=parent)
        self._bind_param()          

class ParamReadOnlyPosiValueWidget(ParamWidget, ReadOnlyPosiValueWidget):
    def __init__(self, param_full_path : str, force_label_text:str=None, label_width : int = 150, is_vertical_mode = False, parent = None):
        label_text = self._resolve_param(param_full_path, force_label_text)
        super().__init__(label_text=label_text, label_width=label_width, is_vertical_mode=is_vertical_mode, parent=parent)
        self._bind_param() 

class ParamReadWritePosiValueSpinBoxWidget(ParamWidget, ReadWritePosiValueSpinBoxWidget):
    def __init__(self, param_full_path : str, force_label_text:str=None, label_width : int = 150, is_vertical_mode = False, parent = None):
        label_text = self._resolve_param(param_full_path, force_label_text)
        super().__init__(label_text=label_text, label_width=label_width, is_vertical_mode=is_vertical_mode, parent=parent)
        self._bind_param()  

class ParamReadOnlyPresValueWidget(ParamWidget, ReadOnlyPresValueWidget):
    def __init__(self, param_full_path : str, force_label_text:str=None, label_width : int = 150, is_vertical_mode = False, parent = None):
        label_text = self._resolve_param(param_full_path, force_label_text)
        super().__init__(label_text=label_text, label_width=label_width, is_vertical_mode=is_vertical_mode, parent=parent)
        self._bind_param()      

class ParamReadWritePresValueSpinBoxWidget(ParamWidget, ReadWritePresValueSpinBoxWidget):
    def __init__(self, param_full_path : str, force_label_text:str=None, label_width : int = 150, is_vertical_mode = False, parent = None):
        label_text = self._resolve_param(param_full_path, force_label_text)
        super().__init__(label_text=label_text, label_width=label_width, is_vertical_mode=is_vertical_mode, parent=parent)
        self._bind_param()               