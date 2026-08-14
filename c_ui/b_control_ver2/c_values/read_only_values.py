from typing import List, Tuple, Type

from PySide6.QtCore import QSignalBlocker

from b_core.b_datatype.param_enum import DescriptionEnum

from b_core.f_helper.float_util import to_sig_str, to_str_with_decimal_places

from c_ui.a_converter.position_converter_manager import PosiConverterManager
from c_ui.a_converter.pressure_converter_manager import PresConverterManager
from c_ui.b_control_ver2.b_base.labels import BaseLabel, CheckLabel
from c_ui.b_control_ver2.b_base.containers import BaseValueBox
from c_ui.b_control_ver2.c_values.base_value import ValueWidget

class ReadOnlyTextValueWidget(ValueWidget):

    def __init__(self, label_text="", label_width=150, is_vertical_mode = False, parent=None):
        value_widget = BaseLabel("")
        super().__init__(label_text = label_text, label_width = label_width, is_show_dirty = False, value_widget = value_widget, is_vertical_mode = is_vertical_mode, parent=parent)
        
        self.set_value(None)

    def set_value(self, value):
        if value != None:
            self.value_widget.setText(value)
            self.setEnabled(True)
        else:
            self.value_widget.setText("Unknown (None)")
            self.setEnabled(False)

    def get_value(self):
        value = self.value_widget.text()
        if value == "Unknown (None)":
            return None
        else:
            return value

    def set_not_support(self, is_not_support):
        if is_not_support:
            self.set_value(None)
            # 표시 전용 setText — 값 할당이 아니므로 알림 차단
            with QSignalBlocker(self.value_widget):
                self.value_widget.setText("Not Support")
            self.setEnabled(False)

    def reg_value_widget_event(self):
        self.value_widget.sig_assigned_by_code.connect(self.on_assigned_by_code)

    def is_dirty(self):
        return False   

class ReadOnlyEnumValueWidget(ValueWidget):

    def __init__(self, enum_class : Type[DescriptionEnum], label_text="", label_width=150, is_vertical_mode = False, parent=None):
        value_widget = BaseLabel("")
        super().__init__(label_text = label_text, label_width = label_width, is_show_dirty = False, value_widget = value_widget, is_vertical_mode = is_vertical_mode, parent=parent)
        
        self.enum_class = enum_class
        self.set_value(None)

    def set_value(self, value):
        try:
            enum_member = self.enum_class(value)
            description = enum_member.description
            self.value_widget.setText(description)
            self.setEnabled(True)
        except Exception:
            self.value_widget.setText(f"Unknown ({value})")
            self.setEnabled(False)

    def get_value(self):
        current_desc = self.value_widget.text()
        enum_member = self.enum_class.from_desc(current_desc)
        return enum_member.value if enum_member else None

    def set_not_support(self, is_not_support):
        if is_not_support:
            self.set_value(None)
            # 표시 전용 setText — 값 할당이 아니므로 알림 차단
            with QSignalBlocker(self.value_widget):
                self.value_widget.setText("Not Support")
            self.setEnabled(False)

    def reg_value_widget_event(self):
        self.value_widget.sig_assigned_by_code.connect(self.on_assigned_by_code)

    def is_dirty(self):
        return False        

class ReadOnlyBitmapValueWidget(ValueWidget):
    """BaseValueBox + CheckLabel 조합의 비트맵 표시 (읽기 전용).

    비트 조합(값 <-> 비트별 체크 상태) 로직은 이 레이어가 소유한다 — 박스/행은
    b_base 의 범용 부품(BaseValueBox, CheckLabel)이고 값 계약을 모른다.
    enum_class 는 (비트 오프셋, 설명) 쌍의 DescriptionEnum — 정의 순서대로 행 등록.
    등록되지 않은 비트는 set_value 로 들어와도 보존되지 않는다 (표시값 계약).

    '값 없음'은 라인에딧 계열과 동일한 placeholder 컨셉: set_value(None) 이면
    비트 행이 숨고 "Unknown"/"Not Support" 문구만 보이며 get_value() 는 None.
    행이 세로로 쌓이므로 라벨은 항상 세로 모드(라벨 위/값 아래)로 배치한다."""

    def __init__(self, enum_class : Type[DescriptionEnum], label_text="", label_width=150, is_vertical_mode = False, parent=None):
        value_widget = BaseValueBox(box=True)
        value_widget.setPlaceholderText("Unknown")

        self._bit_checks = {}  # bit_offset -> CheckLabel
        for member in enum_class:
            check_label = CheckLabel(member.description)
            self._bit_checks[member.value] = check_label
            value_widget.add_value_widget(check_label)

        self._value = None  # 표시 중인 값 (등록 비트만 조합, None = 값 없음)

        super().__init__(label_text = label_text, label_width = label_width, is_show_dirty = False, value_widget = value_widget, is_vertical_mode = True, parent=parent)

        self.enum_class = enum_class
        self.set_value(None)

    def set_value(self, value):
        self.value_widget.setPlaceholderText("Unknown")

        if value is None:
            # 값이 없는데 체크 상태가 보이면 오해를 부른다 — 전부 uncheck + placeholder
            self._value = None
            for check_label in self._bit_checks.values():
                check_label.set_checked(False)
            self.value_widget.set_placeholder_visible(True)
        else:
            value = int(value)
            composed = 0
            for bit_offset, check_label in self._bit_checks.items():
                is_set = bool((value >> bit_offset) & 1)
                check_label.set_checked(is_set)
                if is_set:
                    composed |= 1 << bit_offset
            self._value = composed
            self.value_widget.set_placeholder_visible(False)

        self.setEnabled(value is not None)

    def get_value(self):
        # 값 없음 상태는 None, 아니면 등록된 비트 조합 int
        return self._value

    def set_not_support(self, is_not_support):
        if is_not_support:
            self.set_value(None)
            # set_value 가 placeholder 를 "Unknown" 으로 되돌리므로 반드시 그 뒤에 덮어쓴다
            self.value_widget.setPlaceholderText("Not Support")
            self.setEnabled(False)

    def reg_value_widget_event(self):
        # 코드 할당 알림은 CheckLabel.set_checked() 가 발신한다 — 표준 릴레이 경로.
        # (set_value() 1회가 비트 수만큼 set_checked 를 호출하므로 릴레이도 그만큼 발생)
        for check_label in self._bit_checks.values():
            check_label.sig_assigned_by_code.connect(self.on_assigned_by_code)

    def is_dirty(self):
        return False

class ReadOnlyMultipleEnumValueWidget(ValueWidget):
    """BaseValueBox + ReadOnlyEnumValueWidget 조합 — 10진 자릿수별 enum 표시 (읽기 전용).

    enum_items 는 [(이름, DescriptionEnum), ...] — 첫 항목이 최상위 자릿수다.
    예) 3개 등록 시 값 123 -> 첫째 행 1, 둘째 행 2, 셋째 행 3 을 각 enum 으로 해석.

    [프로토콜 규칙] n개 등록 시 유효 입력은 두 가지뿐이다:
    - 0: '미설정' — "Not Set" 문구만 표시, get_value() 는 0 (Unknown 과 구분)
    - 정확히 n자리 정수(선행 자릿수 >= 1): 자릿수별 enum 해석
    그 외(None/음수/자릿수 부족·초과/자릿값 enum 불일치)는 전부 Unknown —
    ReadOnlyBitmapValueWidget 의 '값 없음'과 동일하게 placeholder 문구만
    표시하고 get_value() 는 None 을 반환한다.
    행이 세로로 쌓이므로 라벨은 항상 세로 모드(라벨 위/값 아래)로 배치한다."""

    def __init__(self, enum_items : List[Tuple[str, Type[DescriptionEnum]]], label_text="", label_width=150, is_vertical_mode = False, parent=None):
        value_widget = BaseValueBox(box=True)
        value_widget.setPlaceholderText("Unknown")

        self._digit_widgets = []  # 등록 순서 = 자릿수 순서 (첫 항목이 최상위 자리)
        for name, enum_class in enum_items:
            digit_widget = ReadOnlyEnumValueWidget(enum_class=enum_class, label_text=name, label_width=label_width)
            self._digit_widgets.append(digit_widget)
            value_widget.add_value_widget(digit_widget)

        self._value = None  # 표시 중인 값 (None = 값 없음/해석 불가)

        super().__init__(label_text = label_text, label_width = label_width, is_show_dirty = False, value_widget = value_widget, is_vertical_mode = True, parent=parent)

        self.set_value(None)

    def set_value(self, value):
        self.value_widget.setPlaceholderText("Unknown")

        # [프로토콜 특례] 0 = '미설정' — 자릿수 해석 없이 Not Set 문구만 표시한다.
        # 알 수 없는 상태(Unknown)가 아니라 유효한 '없음' 값이므로 비활성화하지 않는다
        if self._is_not_set(value):
            self._value = 0
            for digit_widget in self._digit_widgets:
                digit_widget.set_value(None)
            self.value_widget.set_placeholder_visible(True)
            self.value_widget.setPlaceholderText("Not Set")
            self.setEnabled(True)
            return

        digits = self._split_digits(value)

        if digits is None:
            # 일부 자릿수만 표시되면 값을 오독하므로 전체를 Unknown 으로 —
            # placeholder 만 보이는 비트맵 위젯의 '값 없음' 효과와 동일
            self._value = None
            for digit_widget in self._digit_widgets:
                digit_widget.set_value(None)
            self.value_widget.set_placeholder_visible(True)
        else:
            self._value = int(value)
            for digit_widget, digit in zip(self._digit_widgets, digits):
                digit_widget.set_value(digit)
            self.value_widget.set_placeholder_visible(False)

        self.setEnabled(digits is not None)

    @staticmethod
    def _is_not_set(value) -> bool:
        try:
            return value is not None and int(value) == 0
        except (TypeError, ValueError):
            return False

    def _split_digits(self, value):
        """값 -> 자릿수 리스트. 유효하지 않으면 None.

        프로토콜 규칙상 0(Not Set — 호출 전에 분리됨)이 아니면 '정확히 n자리'
        정수만 유효하다 — 자릿수 부족(선행 0)/초과/음수는 전부 해석 불가."""
        if value is None:
            return None

        try:
            value = int(value)
        except (TypeError, ValueError):
            return None

        count = len(self._digit_widgets)
        if value < 10 ** (count - 1) or value >= 10 ** count:
            return None

        digits = []
        for index, digit_widget in enumerate(self._digit_widgets):
            digit = (value // (10 ** (count - 1 - index))) % 10

            # 자릿값이 해당 enum 에 없으면 전체를 해석 불가로 취급한다
            try:
                digit_widget.enum_class(digit)
            except ValueError:
                return None

            digits.append(digit)

        return digits

    def get_value(self):
        # 값 없음/해석 불가 상태는 None, 아니면 표시 중인 원본 int
        return self._value

    def set_not_support(self, is_not_support):
        if is_not_support:
            self.set_value(None)
            # set_value 가 placeholder 를 "Unknown" 으로 되돌리므로 반드시 그 뒤에 덮어쓴다
            self.value_widget.setPlaceholderText("Not Support")
            self.setEnabled(False)

    def reg_value_widget_event(self):
        # 코드 할당 알림은 각 자릿수 위젯(ReadOnlyEnumValueWidget)이 발신한다 —
        # 표준 릴레이 경로. (set_value() 1회가 자릿수만큼 릴레이를 발생시킨다)
        for digit_widget in self._digit_widgets:
            digit_widget.sig_assigned_by_code.connect(self.on_assigned_by_code)

    def is_dirty(self):
        return False

class ReadOnlyScaleValueWidget(ValueWidget):
    def __init__(self, label_text="", scale=100.0, label_width=150, is_vertical_mode = False, parent=None):
        value_widget = BaseLabel("")
        self.scale = scale
        super().__init__(label_text = label_text, label_width = label_width, is_show_dirty = False, value_widget = value_widget, is_vertical_mode = is_vertical_mode, parent=parent)

        self.set_value(None)

    def set_value(self, value):
        if value is not None:
            value = value * self.scale

        str_value = to_sig_str(value)

        if str_value:
            self.value_widget.setText(str_value)
            self.setEnabled(True)
        else:
            self.value_widget.setText(f"Unknown ({value})")
            self.setEnabled(False)

    def get_value(self):
        try:
            float_value = float(self.value_widget.text())
            return float_value / self.scale
        except Exception:
            return None

    def set_not_support(self, is_not_support):
        if is_not_support:
            self.set_value(None)
            # 표시 전용 setText — 값 할당이 아니므로 알림 차단
            with QSignalBlocker(self.value_widget):
                self.value_widget.setText("Not Support")
            self.setEnabled(False)             

    def reg_value_widget_event(self):
        self.value_widget.sig_assigned_by_code.connect(self.on_assigned_by_code)

    def is_dirty(self):
        return False

class ReadOnlyIntValueWidget(ValueWidget):
    def __init__(self, label_text="", label_width=150, is_vertical_mode = False, parent=None):
        value_widget = BaseLabel("")
        super().__init__(label_text = label_text, label_width = label_width, is_show_dirty = False, value_widget = value_widget, is_vertical_mode = is_vertical_mode, parent=parent)

        self.set_value(None)

    def set_value(self, value):
        if value is not None:
            self.value_widget.setText(str(value))
            self.setEnabled(True)
        else:
            self.value_widget.setText("Unknown (None)")
            self.setEnabled(False)

    def get_value(self):
        try:
            return int(self.value_widget.text())
        except Exception:
            return None

    def set_not_support(self, is_not_support):
        if is_not_support:
            self.set_value(None)
            # 표시 전용 setText — 값 할당이 아니므로 알림 차단
            with QSignalBlocker(self.value_widget):
                self.value_widget.setText("Not Support")
            self.setEnabled(False)

    def reg_value_widget_event(self):
        self.value_widget.sig_assigned_by_code.connect(self.on_assigned_by_code)

    def is_dirty(self):
        return False

class ReadOnlyFloatValueWidget(ValueWidget):
    def __init__(self, label_text="", label_width=150, is_vertical_mode = False, parent=None):
        value_widget = BaseLabel("")
        self.decimals = -1
        super().__init__(label_text = label_text, label_width = label_width, is_show_dirty = False, value_widget = value_widget, is_vertical_mode = is_vertical_mode, parent=parent)

        self.set_value(None)

    def set_decimals(self, decimals):
        self.decimals = decimals

    def set_value(self, value):
        if self.decimals < 0:
            str_value = to_sig_str(value)
        else:
            str_value = to_str_with_decimal_places(value, self.decimals)

        if str_value:
            self.value_widget.setText(str_value)
            self.setEnabled(True)
        else:
            self.value_widget.setText(f"Unknown ({value})")
            self.setEnabled(False)

    def get_value(self):
        try:
            float_value = float(self.value_widget.text())    
            return float_value
        except Exception:
            return None

    def set_not_support(self, is_not_support):
        if is_not_support:
            self.set_value(None)
            # 표시 전용 setText — 값 할당이 아니므로 알림 차단
            with QSignalBlocker(self.value_widget):
                self.value_widget.setText("Not Support")
            self.setEnabled(False)             

    def reg_value_widget_event(self):
        self.value_widget.sig_assigned_by_code.connect(self.on_assigned_by_code)

    def is_dirty(self):
        return False                  

