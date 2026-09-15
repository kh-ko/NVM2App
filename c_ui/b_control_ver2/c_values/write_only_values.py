from typing import Type
from PySide6.QtWidgets import QHBoxLayout

from b_core.b_datatype.param_enum import DescriptionEnum
from c_ui.b_control_ver2.b_base.buttons import BaseButton
from c_ui.b_control_ver2.b_base.inputs import BaseComboBox, BaseFloatLineEdit
from c_ui.b_control_ver2.c_values.base_value import ValueWidget


class WriteOnlyButtonValueWidget(ValueWidget):
    def __init__(self, label_text="", btn_text = "Execute", label_width=150, is_vertical_mode = False, parent=None):
        self._btn_text = btn_text
        value_widget = BaseButton(self._btn_text)

        super().__init__(label_text = label_text, label_width = label_width, is_show_dirty = False, value_widget = value_widget, is_vertical_mode = is_vertical_mode, parent=parent)

    def set_value(self, value):
        pass

    def get_value(self):
        return None
        
    def set_not_support(self, is_not_support):
        if is_not_support:
            self.value_widget.setText("Not Support")
            self.setEnabled(False)
        else:
            self.value_widget.setText(self._btn_text)
            self.setEnabled(True)

    def reg_value_widget_event(self):
        self.value_widget.clicked.connect(self.on_edited_by_user)

    def is_dirty(self):
        return False   


class WriteOnlyEnumValueWidget(WriteOnlyButtonValueWidget):
    def __init__(self, enum_class : Type[DescriptionEnum], btn_text = "Execute", label_text="", label_width=150, is_vertical_mode = False, parent=None):
        super().__init__(btn_text = btn_text, label_text=label_text, label_width=label_width, is_vertical_mode=is_vertical_mode, parent=parent)
        self.combo_widget = BaseComboBox()
        self.enum_class = enum_class

        # 항목은 enum 정의 순서대로 — 표시 텍스트는 description, 데이터는 enum 값
        for member in enum_class:
            self.combo_widget.addItem(member.description, member.value)

        self.combo_widget.setCurrentIndex(0)

        # 버튼 바로 앞에 콤보를 넣는다. BaseComboBox 는 가로 폭 정책이 Ignored 라
        # stretch 없이 넣으면 폭이 0 으로 접힌다 — 가로 모드에서는 콤보가 stretch 를
        # 갖고 버튼은 원래 폭(sizeHint)으로 되돌린다
        index = self._root_layout.indexOf(self.value_widget)
        if isinstance(self._root_layout, QHBoxLayout):
            self._root_layout.insertWidget(index, self.combo_widget, 1)
            self._root_layout.setStretchFactor(self.value_widget, 0)
        else:
            self._root_layout.insertWidget(index, self.combo_widget)

    def set_value(self, value):
        pass

    def get_value(self):
        return self.combo_widget.currentData()

    def set_not_support(self, is_not_support):
        if is_not_support:
            self.value_widget.setText("Not Support")
            self.setEnabled(False)
        else:
            self.value_widget.setText(self._btn_text)
            self.setEnabled(True)

    def reg_value_widget_event(self):
        self.value_widget.clicked.connect(self.on_edited_by_user)

    def is_dirty(self):
        return False


class WriteOnlyFloatValueWidget(WriteOnlyButtonValueWidget):
    """실수 입력 + 실행 버튼 (쓰기 전용) — 읽기 값이 없는 명령형 값(예: 클러스터 장치의 Target Position).

    값은 get_value() 로 꺼낸다 (float, 편집 중간 상태면 None). 버튼 클릭과 라인에딧의 Enter 가
    같은 확정(sig_edited_by_user)이다. 범위/자릿수는 BaseFloatLineEdit 계약(set_range / set_decimals).
    dirty 개념이 없다 — 보낸 뒤에도 입력값은 남아 다시 보낼 수 있다."""

    def __init__(self, btn_text = "Send", label_text="", label_width=150, is_vertical_mode = False, parent=None):
        super().__init__(btn_text = btn_text, label_text=label_text, label_width=label_width, is_vertical_mode=is_vertical_mode, parent=parent)
        self.edit_widget = BaseFloatLineEdit()

        # 버튼 바로 앞에 입력기를 넣는다 — 가로 모드에서는 입력기가 stretch 를 갖고 버튼은 원래 폭
        index = self._root_layout.indexOf(self.value_widget)
        if isinstance(self._root_layout, QHBoxLayout):
            self._root_layout.insertWidget(index, self.edit_widget, 1)
            self._root_layout.setStretchFactor(self.value_widget, 0)
        else:
            self._root_layout.insertWidget(index, self.edit_widget)

        # Enter 도 실행 — editingFinished 계열(sig_edited_by_user)은 포커스 아웃에도 발화하므로 쓰지 않는다
        self.edit_widget.sig_edited_by_enter.connect(self.on_edited_by_user)

    def set_range(self, min_value, max_value):
        self.edit_widget.setRange(min_value, max_value)

    def set_decimals(self, decimals):
        self.edit_widget.setDecimals(decimals)

    def set_value(self, value):
        pass

    def get_value(self):
        return self.edit_widget.value()

    def is_dirty(self):
        return False