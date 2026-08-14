from typing import Type
from PySide6.QtWidgets import QHBoxLayout

from b_core.b_datatype.param_enum import DescriptionEnum
from c_ui.b_control_ver2.b_base.buttons import BaseButton
from c_ui.b_control_ver2.b_base.inputs import BaseComboBox
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