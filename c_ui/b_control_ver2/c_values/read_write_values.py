from typing import Type

from PySide6.QtCore import QSignalBlocker

from b_core.a_define.float_util import is_float_equal
from b_core.b_datatype.param_enum import DescriptionEnum

from c_ui.a_converter.pressure_converter_manager import PresConverterManager
from c_ui.a_converter.position_converter_manager import PosiConverterManager

from c_ui.b_control_ver2.b_base.inputs import BaseComboBox, BaseDoubleSpinBox
from c_ui.b_control_ver2.c_values.base_value import ValueWidget

class ReadWriteEnumValueWidget(ValueWidget):
    def __init__(self, enum_class : Type[DescriptionEnum], label_text="", label_width=150, is_vertical_mode = False, parent=None):
        value_widget = BaseComboBox()
        self.enum_class = enum_class

        # 항목은 enum 정의 순서대로 — 표시 텍스트는 description, 데이터는 enum 값
        for member in enum_class:
            value_widget.addItem(member.description, member.value)

        super().__init__(label_text = label_text, label_width = label_width, is_show_dirty = True, value_widget = value_widget, is_vertical_mode = is_vertical_mode, parent=parent)

        # 초기 상태를 clean 으로 확정한다 — c_values 는 param 바인딩 레이어가 아니므로
        # 단독 사용 시에도 dirty 마커 없이 시작해야 한다
        self.set_value(None, is_commit=True)

    def reg_value_widget_event(self):
        self.value_widget.sig_edited_by_user.connect(self.on_edited_by_user)
        self.value_widget.sig_assigned_by_code.connect(self.on_assigned_by_code)

    def normalize_value(self, value):
        # enum 에 없는 값은 표시할 수 없으므로 None(선택 없음)으로 정규화한다.
        # (원본 값을 그대로 두면 ori_value != 화면값이 되어 영구 dirty 가 된다)
        if value is not None and self.value_widget.findData(value) < 0:
            return None
        return value

    def is_dirty(self):
        # enum 값은 정확 비교 (float 정책 불필요).
        # 정규화 + set_value/commit 짝 보장 덕에 ori_value 비교로 충분하다
        # (스핀박스의 ori_edit_value 는 소수점 자릿수라는 고유 사유 — enum 은 불필요)
        return self.ori_value != self.get_value()

    def get_value(self):
        # 선택 항목의 데이터(enum 값). 선택 없음(-1)이면 None
        return self.value_widget.currentData()

    def apply_value(self, value):
        # 입력기는 값이 없더라도 값 할당이 되면 사용자 입력을 받을 수 있는 상태가 되어야 한다.
        self.setEnabled(True)

        # None 은 -1(빈 표시) — enum 에 없는 값은 normalize_value 가 이미 None 으로 바꿨다
        index = self.value_widget.findData(value)
        self.value_widget.setCurrentIndex(index)

    def set_not_support(self, is_not_support):
        # 비활성화 상태가 자동을 풀리는 경우는 set_value()호출하여 값을 지정할 때이다.
        if is_not_support:
            self.set_value(None)
            self.setEnabled(False)

class ReadWritePosiValueSpinBoxWidget(ValueWidget):
    def __init__(self, label_text="", label_width=150, is_vertical_mode = False, parent=None):
        value_widget = BaseDoubleSpinBox()
        self.converter = PosiConverterManager()

        # 단순 ori_value는 완전한 오리지널 값으로 되돌리기 위해 필요하고
        # 추가로 ori_edit_value는 is_dirty를 체크하기 위해 commit된 시점의 입력창에 값을 따로 저장해야된다.
        # 왜냐하면 소숫점 아래자릿수 설정에 따라서 ori_value로 비교하면 값이 변했다고 판단할 수 있기 때문이다.
        self.ori_edit_value = None

        super().__init__(label_text = label_text, label_width = label_width, is_show_dirty = True, value_widget = value_widget, is_vertical_mode = is_vertical_mode, parent=parent)

        # 초기 상태를 clean 으로 확정한다 — c_values 는 param 바인딩 레이어가 아니므로
        # 단독 사용 시에도 dirty 마커 없이 시작해야 한다
        self.set_value(None, is_commit=True)

        self.converter.sig_posi_range_changed.connect(self.handle_posi_range_changed)
        self.handle_posi_range_changed()

    def handle_posi_range_changed(self):
        # 자릿수를 지정하고 is_dirty를 하면 제대로 비교가 되지 않기 때문에.. is_dirty를 먼저 하고 결과에 따라서 다음 동작을 하도록 한다.
        if self.is_dirty():
            # 사용자가 수정중에 있으면 그대로 놔둬야 된다. 자릿수만 맞춘다.
            self.value_widget.setDecimals(self.converter.posi_decimal_places)
        else:
            self.value_widget.setDecimals(self.converter.posi_decimal_places)
            self.set_value(self.ori_value, is_commit=True)

    def reg_value_widget_event(self):
        self.value_widget.sig_edited_by_user.connect(self.on_edited_by_user)
        self.value_widget.sig_edited_by_enter.connect(self.on_edit_by_enter)
        self.value_widget.sig_editing_by_user.connect(self.on_editing_by_user)  # 실시간 dirty 표시
        self.value_widget.sig_assigned_by_code.connect(self.on_assigned_by_code)

    def _commit(self):
        self.ori_edit_value = self.get_value()
        super()._commit()

    def is_dirty(self):
        # 비교 기준은 앱 전역 유효숫자 6자리 정책 (b_core.a_define.float_util 참고)
        return not is_float_equal(self.ori_edit_value, self.get_value())

    def get_value(self):
        return self.converter.convert_dp_to_posi(self.value_widget.value())

    def apply_value(self, value):
        dp_value = self.converter.convert_posi_to_dp(value)

        # 입력기는 값이 없더라도 set_value()이 호출되면 사용자 입력을 받을 수 있는 상태가 되어야 한다.
        self.setEnabled(True)

        if dp_value is not None:
            self.value_widget.setValue(dp_value)
        else:
            self.value_widget.setValue(0)

    def set_not_support(self, is_not_support):
        # 비활성화 상태가 자동을 풀리는 경우는 set_value()호출하여 값을 지정할 때이다.
        if is_not_support:
            self.set_value(0)
            self.setEnabled(False)

class ReadWritePresValueSpinBoxWidget(ValueWidget):
    def __init__(self, label_text="", label_width=150, is_vertical_mode = False, parent=None):
        value_widget = BaseDoubleSpinBox()
        self.converter = PresConverterManager()

        # 단순 ori_value는 완전한 오리지널 값으로 되돌리기 위해 필요하고
        # 추가로 ori_edit_value는 is_dirty를 체크하기 위해 commit된 시점의 입력창에 값을 따로 저장해야된다.
        # 왜나하면 소숫점 아래자릿수 설정에 따라서 ori_value로 비교하면 값이 변했다고 판단할 수 있기 때문이다.
        self.ori_edit_value = None

        super().__init__(label_text = label_text, label_width = label_width, is_show_dirty = True, value_widget = value_widget, is_vertical_mode = is_vertical_mode, parent=parent)
        
        # 초기 상태를 clean 으로 확정한다 — c_values 는 param 바인딩 레이어가 아니므로
        # 단독 사용 시에도 dirty 마커 없이 시작해야 한다
        self.set_value(None, is_commit=True)

        self.converter.sig_pres_range_changed.connect(self.handle_pres_range_changed)
        self.handle_pres_range_changed()

    def handle_pres_range_changed(self):
        
        # 자릿수를 지정하고 is_dirty를 하면 제대로 비교가 되지 않기 때문에.. is_dirty를 먼저 하고 결과에 따라서 다음 동작을 하도록 한다.
        if self.is_dirty():     
            # 사용자가 수정중에 있으면 그대로 놔둬야 된다. 자릿수만 맞춘다.
            self.value_widget.setDecimals(self.converter.pres_decimal_places) 
        else:
            self.value_widget.setDecimals(self.converter.pres_decimal_places)
            self.set_value(self.ori_value, is_commit=True)
              
    def reg_value_widget_event(self):
        self.value_widget.sig_edited_by_user.connect(self.on_edited_by_user)
        self.value_widget.sig_edited_by_enter.connect(self.on_edit_by_enter)
        self.value_widget.sig_editing_by_user.connect(self.on_editing_by_user)  # 실시간 dirty 표시
        self.value_widget.sig_assigned_by_code.connect(self.on_assigned_by_code)

    def _commit(self):
        self.ori_edit_value = self.get_value()
        super()._commit()

    def is_dirty(self):
        # 비교 기준은 앱 전역 유효숫자 6자리 정책 (b_core.a_define.float_util 참고)
        return not is_float_equal(self.ori_edit_value, self.get_value())

    def get_value(self):
        return self.converter.convert_dp_pres_to_iface_pres(self.value_widget.value())

    def apply_value(self, value):
        dp_value = self.converter.convert_iface_pres_to_dp_pres(value)

        # 입력기는 값이 없더라도 set_value()이 호출되면 사용자 입력을 받을 수 있는 상태가 되어야 한다.
        self.setEnabled(True) 

        if dp_value is not None:
            self.value_widget.setValue(dp_value)
        else:
            self.value_widget.setValue(0)

    def set_not_support(self, is_not_support):
        # 비활성화 상태가 자동을 풀리는 경우는 set_value()호출하여 값을 지정할 때이다.
        if is_not_support:
            self.set_value(0)
            self.setEnabled(False)     
