from typing import Type

from b_core.b_datatype.param_enum import DescriptionEnum

from c_ui.b_control_ver2.b_base.inputs import BaseComboBox, BaseDoubleSpinBox, BaseFloatLineEdit
from c_ui.b_control_ver2.c_values.base_value import ValueWidget

class ReadWriteEnumValueWidget(ValueWidget):
    def __init__(self, enum_class : Type[DescriptionEnum], label_text="", label_width=150, is_vertical_mode = False, parent=None):
        value_widget = BaseComboBox()
        self.enum_class = enum_class

        # 항목은 enum 정의 순서대로 — 표시 텍스트는 description, 데이터는 enum 값
        for member in enum_class:
            value_widget.addItem(member.description, member.value)

        value_widget.setPlaceholderText("Unknown")

        super().__init__(label_text = label_text, label_width = label_width, is_show_dirty = True, value_widget = value_widget, is_vertical_mode = is_vertical_mode, parent=parent)

        # 초기 상태를 clean 으로 확정한다 — c_values 는 param 바인딩 레이어가 아니므로
        # 단독 사용 시에도 dirty 마커 없이 시작해야 한다
        self.set_value(None)

    def set_value(self, value):
        self.value_widget.setPlaceholderText("Unknown")
        self.setEnabled(True)
        index = self.value_widget.findData(value)
        self.value_widget.setCurrentIndex(index)

    def get_value(self):
        return self.value_widget.currentData()

    def set_not_support(self, is_not_support):
        if is_not_support:
            self.set_value(None)
            self.commit()
            # set_value 가 placeholder 를 "Unknown" 으로 되돌리므로 반드시 그 뒤에 덮어쓴다
            self.value_widget.setPlaceholderText("Not Support")
            self.setEnabled(False)

    def reg_value_widget_event(self):
        self.value_widget.sig_assigned_by_code.connect(self.on_assigned_by_code)
        self.value_widget.sig_edited_by_user.connect(self.on_edited_by_user)

class ReadWriteFloatValueSpinBoxWidget(ValueWidget):
    def __init__(self, label_text="", label_width=150, is_vertical_mode = False, parent=None):
        value_widget = BaseDoubleSpinBox()

        super().__init__(label_text = label_text, label_width = label_width, is_show_dirty = True, value_widget = value_widget, is_vertical_mode = is_vertical_mode, parent=parent)

        # 초기 상태를 clean 으로 확정한다 — c_values 는 param 바인딩 레이어가 아니므로
        # 단독 사용 시에도 dirty 마커 없이 시작해야 한다
        self.set_value(None)
        self.commit()

    def set_range(self, min_value, max_value):
        self.value_widget.setRange(min_value, max_value)
        
    def set_decimals(self, decimals):
        self.value_widget.setDecimals(decimals)

    def set_value(self, value):
        self.setEnabled(True)
        # 스핀박스는 '값 없음'을 표현할 수 없으므로 None 은 0 으로 표시한다 (setValue(None) 은 TypeError)
        if value is None:
            value = 0
        self.value_widget.setValue(value)

    def get_value(self):
        return self.value_widget.value()

    def set_not_support(self, is_not_support):
        # 비활성화 상태가 자동을 풀리는 경우는 set_value()호출하여 값을 지정할 때이다.
        if is_not_support:
            self.set_value(0)
            self.commit()
            self.setEnabled(False)
            
    def reg_value_widget_event(self):
        self.value_widget.sig_edited_by_user.connect(self.on_edited_by_user)
        self.value_widget.sig_edited_by_enter.connect(self.on_edit_by_enter)
        self.value_widget.sig_editing_by_user.connect(self.on_editing_by_user)  # 실시간 dirty 표시
        self.value_widget.sig_assigned_by_code.connect(self.on_assigned_by_code)

class ReadWriteFloatValueWidget(ValueWidget):
    """BaseFloatLineEdit 기반 실수 입력 — 스핀박스 버전과 같은 공개 API/루틴.

    범위/자릿수/클램프/입력 검증(validator+fixup)은 전부 BaseFloatLineEdit 이
    관장하므로, 이 클래스는 스핀박스 버전과 동일한 얇은 구조가 된다.

    스핀박스 버전과의 차이 — '값 없음' 상태를 지원한다:
    set_value(None) 은 빈 표시 + placeholder("Unknown"/"Not Support") 로
    나타나고 get_value() 는 None 을 반환한다 (enum 콤보의 -1 과 동일 의미론).
    스핀박스는 빈 표시가 구조적으로 불가능해 None 을 0 으로 표시한다."""

    def __init__(self, label_text="", label_width=150, is_vertical_mode = False, parent=None):
        value_widget = BaseFloatLineEdit()
        value_widget.setPlaceholderText("Unknown")

        super().__init__(label_text = label_text, label_width = label_width, is_show_dirty = True, value_widget = value_widget, is_vertical_mode = is_vertical_mode, parent=parent)

        # 초기 상태를 clean 으로 확정한다 — c_values 는 param 바인딩 레이어가 아니므로
        # 단독 사용 시에도 dirty 마커 없이 시작해야 한다
        self.set_value(None)
        self.commit()

    def set_range(self, min_value, max_value):
        self.value_widget.setRange(min_value, max_value)

    def set_decimals(self, decimals):
        self.value_widget.setDecimals(decimals)

    def set_value(self, value):
        self.value_widget.setPlaceholderText("Unknown")
        self.setEnabled(True)
        # None 은 빈 표시(placeholder 노출) — enum 콤보의 -1 과 동일 의미론 (BaseFloatLineEdit 계약)
        self.value_widget.setValue(value)

    def get_value(self):
        # 값 없음/편집 중간 상태("", "-" 등)는 None (is_dirty 는 None 안전)
        return self.value_widget.value()

    def set_not_support(self, is_not_support):
        # 비활성화 상태가 자동을 풀리는 경우는 set_value()호출하여 값을 지정할 때이다.
        if is_not_support:
            self.set_value(None)
            self.commit()
            # set_value 가 placeholder 를 "Unknown" 으로 되돌리므로 반드시 그 뒤에 덮어쓴다
            self.value_widget.setPlaceholderText("Not Support")
            self.setEnabled(False)

    def reg_value_widget_event(self):
        self.value_widget.sig_edited_by_user.connect(self.on_edited_by_user)
        self.value_widget.sig_edited_by_enter.connect(self.on_edit_by_enter)
        self.value_widget.sig_editing_by_user.connect(self.on_editing_by_user)  # 실시간 dirty 표시
        self.value_widget.sig_assigned_by_code.connect(self.on_assigned_by_code)






