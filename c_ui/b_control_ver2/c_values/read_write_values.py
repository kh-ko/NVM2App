from typing import Type

from PySide6.QtCore import QSignalBlocker, Qt

from b_core.b_datatype.param_enum import DescriptionEnum

from c_ui.b_control_ver2.b_base.containers import BaseValueBox
from c_ui.b_control_ver2.b_base.inputs import (BaseCheckBox, BaseComboBox, BaseDoubleSpinBox,
                                               BaseFloatLineEdit, BaseHexLineEdit)
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

class ReadWriteBitmapValueWidget(ValueWidget):
    """BaseValueBox + BaseCheckBox 조합의 비트맵 입력 (읽기/쓰기).

    ReadOnlyBitmapValueWidget 의 RW 대응 — 비트별 체크박스를 사용자가 직접
    토글해 값을 구성한다. enum_class 는 (비트 오프셋, 설명) 쌍의 DescriptionEnum.

    - set_value(None): placeholder 가 아니라 전 체크박스를 '중간 상태'로 둔다.
      사용자가 비트 하나라도 클릭해 확정하면 값을 설정한 것이므로, 남은 중간
      상태는 전부 Unchecked 로 풀린다 — 중간 상태가 끼어 있으면 get_value()
      를 만들 수 없기 때문. (코드가 다시 set_value(None) 하기 전까지 중간
      상태는 재등장하지 않는다)
    - get_value(): 중간 상태가 남아 있으면 None (값 미확정 — dirty 수집/쓰기
      경로에서 자연 제외), 아니면 등록 비트 조합 int.
    - Not Support: RO 와 동일하게 placeholder 문구("Not Support")로 표시한다.
    행이 세로로 쌓이므로 라벨은 항상 세로 모드(라벨 위/값 아래)로 배치한다."""

    def __init__(self, enum_class : Type[DescriptionEnum], label_text="", label_width=150, is_vertical_mode = False, parent=None):
        value_widget = BaseValueBox(box=True)

        self._bit_checks = {}  # bit_offset -> BaseCheckBox
        for member in enum_class:
            check_box = BaseCheckBox(member.description)
            self._bit_checks[member.value] = check_box
            value_widget.add_value_widget(check_box)

        super().__init__(label_text = label_text, label_width = label_width, is_show_dirty = True, value_widget = value_widget, is_vertical_mode = True, parent=parent)

        self.enum_class = enum_class

        # 초기 상태를 clean 으로 확정한다 — c_values 는 param 바인딩 레이어가 아니므로
        # 단독 사용 시에도 dirty 마커 없이 시작해야 한다
        self.set_value(None)
        self.commit()

    def set_value(self, value):
        self.value_widget.set_placeholder_visible(False)
        self.setEnabled(True)

        if value is None:
            # 값 없음 — 전 비트를 '중간 상태'로 (클릭하면 해당 비트만 Checked 로
            # 확정된다 — BaseCheckBox 가 사용자 클릭을 2상태로만 순환시킨다)
            for check_box in self._bit_checks.values():
                check_box.setCheckState(Qt.CheckState.PartiallyChecked)
            return

        value = int(value)
        for bit_offset, check_box in self._bit_checks.items():
            is_set = bool((value >> bit_offset) & 1)
            check_box.setCheckState(Qt.CheckState.Checked if is_set else Qt.CheckState.Unchecked)

    def get_value(self):
        # 중간 상태가 하나라도 있으면 값 미확정 -> None. 아니면 등록 비트 조합 int
        result = 0
        for bit_offset, check_box in self._bit_checks.items():
            state = check_box.checkState()
            if state == Qt.CheckState.PartiallyChecked:
                return None
            if state == Qt.CheckState.Checked:
                result |= 1 << bit_offset
        return result

    def set_not_support(self, is_not_support):
        if is_not_support:
            self.set_value(None)
            self.commit()
            # set_value 가 placeholder 를 걷으므로 반드시 그 뒤에 다시 씌운다
            self.value_widget.setPlaceholderText("Not Support")
            self.value_widget.set_placeholder_visible(True)
            self.setEnabled(False)

    def reg_value_widget_event(self):
        # 각 체크박스가 표준 시그널 소스 — 클릭 확정/코드 할당을 그대로 릴레이한다
        # (set_value() 1회가 비트 수만큼 setCheckState 를 호출하므로 릴레이도 그만큼 발생)
        for check_box in self._bit_checks.values():
            check_box.sig_edited_by_user.connect(self.on_bit_edited_by_user)
            check_box.sig_assigned_by_code.connect(self.on_assigned_by_code)

    def on_bit_edited_by_user(self, _check_box):
        # 사용자가 비트 하나를 확정하면 값을 설정한 것 — 남은 중간 상태를 전부
        # Unchecked 로 풀어 get_value() 가 성립하게 한다. 같은 사용자 제스처의
        # 일부이므로 코드 할당 알림은 차단하고 확정 통지 1회로 처리한다
        for check_box in self._bit_checks.values():
            if check_box.checkState() == Qt.CheckState.PartiallyChecked:
                with QSignalBlocker(check_box):
                    check_box.setCheckState(Qt.CheckState.Unchecked)

        self.on_edited_by_user()

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

class ReadWriteScaleValueWidget(ValueWidget):
    """BaseFloatLineEdit 기반 배율(scale) 입력 — float 라인에딧 버전과 같은 공개 API/루틴.

    ReadOnlyScaleValueWidget 의 RW 대응: 원시값에 scale 을 곱해 표시하고
    (예: scale=100.0 이면 0.5 -> "50"), get_value() 는 표시값을 다시 scale 로
    나눈 원시값을 반환한다. set_range 는 다른 RW 위젯들과 동일하게 표시값
    기준이다 — 스키마 min/max 가 표시 범위 기준(예: 0~100(%))이므로 그대로
    전달하면 된다.

    '값 없음' 상태 지원: set_value(None) 은 빈 표시 + placeholder("Unknown"/
    "Not Support") 로 나타나고 get_value() 는 None 을 반환한다."""

    def __init__(self, label_text="", scale=100.0, label_width=150, is_vertical_mode = False, parent=None):
        value_widget = BaseFloatLineEdit()
        value_widget.setPlaceholderText("Unknown")
        # 자릿수 미지정 — BaseFloatLineEdit 기본인 유효숫자 6자리 모드를 그대로 쓴다
        self.scale = scale

        super().__init__(label_text = label_text, label_width = label_width, is_show_dirty = True, value_widget = value_widget, is_vertical_mode = is_vertical_mode, parent=parent)

        # 초기 상태를 clean 으로 확정한다 — c_values 는 param 바인딩 레이어가 아니므로
        # 단독 사용 시에도 dirty 마커 없이 시작해야 한다
        self.set_value(None)
        self.commit()

    def set_range(self, min_value, max_value):
        # 표시값 기준 (다른 RW 위젯들과 동일 — 스키마 min/max 를 그대로 전달)
        self.value_widget.setRange(min_value, max_value)

    def set_decimals(self, decimals):
        self.value_widget.setDecimals(decimals)

    def set_value(self, value):
        self.value_widget.setPlaceholderText("Unknown")
        self.setEnabled(True)

        # None 은 빈 표시(placeholder 노출) — enum 콤보의 -1 과 동일 의미론 (BaseFloatLineEdit 계약)
        if value is not None:
            value = value * self.scale
        self.value_widget.setValue(value)

    def get_value(self):
        # 값 없음/편집 중간 상태("", "-" 등)는 None. 표시값을 원시값으로 되돌린다
        value = self.value_widget.value()
        if value is None:
            return None
        return value / self.scale

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

class ReadWriteIntValueWidget(ValueWidget):
    """BaseFloatLineEdit(소수 0자리) 기반 정수 입력 — float 라인에딧 버전과 같은 공개 API/루틴.

    전용 정수 라인에딧을 새로 만드는 대신 BaseFloatLineEdit 을 소수 0자리로
    고정해 재사용한다 (범위/클램프/validator+fixup/'값 없음' 의미론 전부 동일).
    get_value() 만 int 로 좁혀서 반환한다."""

    def __init__(self, label_text="", label_width=150, is_vertical_mode = False, parent=None):
        value_widget = BaseFloatLineEdit()
        value_widget.setDecimals(0)
        value_widget.setPlaceholderText("Unknown")

        super().__init__(label_text = label_text, label_width = label_width, is_show_dirty = True, value_widget = value_widget, is_vertical_mode = is_vertical_mode, parent=parent)

        # 초기 상태를 clean 으로 확정한다 — c_values 는 param 바인딩 레이어가 아니므로
        # 단독 사용 시에도 dirty 마커 없이 시작해야 한다
        self.set_value(None)
        self.commit()

    def set_range(self, min_value, max_value):
        self.value_widget.setRange(min_value, max_value)

    def set_value(self, value):
        self.value_widget.setPlaceholderText("Unknown")
        self.setEnabled(True)
        # None 은 빈 표시(placeholder 노출) — enum 콤보의 -1 과 동일 의미론 (BaseFloatLineEdit 계약)
        self.value_widget.setValue(value)

    def get_value(self):
        # 값 없음/편집 중간 상태("")는 None. 소수 0자리 표시라 int 변환은 손실 없음
        value = self.value_widget.value()
        return None if value is None else int(value)

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

class ReadWriteHexValueWidget(ValueWidget):
    """BaseHexLineEdit 기반 16진수(정수) 입력 — float 라인에딧 버전과 같은 공개 API/루틴.

    범위/자릿수/클램프/입력 검증(validator+fixup)은 전부 BaseHexLineEdit 이
    관장한다. set_decimals 대신 set_digits(0 패딩 표시 폭)를 쓰는 것만 다르다.

    '값 없음' 상태 지원: set_value(None) 은 빈 표시 + placeholder("Unknown"/
    "Not Support") 로 나타나고 get_value() 는 None 을 반환한다."""

    def __init__(self, label_text="", label_width=150, is_vertical_mode = False, parent=None):
        value_widget = BaseHexLineEdit()
        value_widget.setPlaceholderText("Unknown")

        super().__init__(label_text = label_text, label_width = label_width, is_show_dirty = True, value_widget = value_widget, is_vertical_mode = is_vertical_mode, parent=parent)

        # 초기 상태를 clean 으로 확정한다 — c_values 는 param 바인딩 레이어가 아니므로
        # 단독 사용 시에도 dirty 마커 없이 시작해야 한다
        self.set_value(None)
        self.commit()

    def set_range(self, min_value, max_value):
        self.value_widget.setRange(min_value, max_value)

    def set_digits(self, digits):
        self.value_widget.setDigits(digits)

    def set_value(self, value):
        self.value_widget.setPlaceholderText("Unknown")
        self.setEnabled(True)
        # None 은 빈 표시(placeholder 노출) — enum 콤보의 -1 과 동일 의미론 (BaseHexLineEdit 계약)
        self.value_widget.setValue(value)

    def get_value(self):
        # 값 없음/편집 중간 상태("")는 None (is_dirty 는 None 안전)
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


