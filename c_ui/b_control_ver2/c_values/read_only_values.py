from typing import Type

from PySide6.QtCore import QSignalBlocker

from b_core.b_datatype.param_enum import DescriptionEnum

from c_ui.a_converter.position_converter_manager import PosiConverterManager
from c_ui.a_converter.pressure_converter_manager import PresConverterManager
from c_ui.a_converter.float_converter_manager import FloatConverterManager
from c_ui.b_control_ver2.b_base.labels import BaseLabel
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

class ReadOnlyScaleValueWidget(ValueWidget):
    def __init__(self, label_text="", scale=100.0, label_width=150, is_vertical_mode = False, parent=None):
        value_widget = BaseLabel("")
        self.scale = scale
        self.converter = FloatConverterManager()
        super().__init__(label_text = label_text, label_width = label_width, is_show_dirty = False, value_widget = value_widget, is_vertical_mode = is_vertical_mode, parent=parent)
        
        self.set_value(None) 

    def set_value(self, value):
        if value is not None:
            value = value * self.scale

        str_value = self.converter.to_str(value)

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

class ReadOnlyFloatValueWidget(ValueWidget):
    def __init__(self, label_text="", label_width=150, is_vertical_mode = False, parent=None):
        value_widget = BaseLabel("")
        self.converter = FloatConverterManager()
        self.decimals = -1
        super().__init__(label_text = label_text, label_width = label_width, is_show_dirty = False, value_widget = value_widget, is_vertical_mode = is_vertical_mode, parent=parent)
        
        self.set_value(None) 

    def set_decimals(self, decimals):
        self.decimals = decimals

    def set_value(self, value):
        if self.decimals < 0:
            str_value = self.converter.to_str(value)
        else:
            str_value = self.converter.to_str_with_decimal_places(value, self.decimals)

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

