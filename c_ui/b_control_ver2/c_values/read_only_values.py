from typing import Type

from PySide6.QtCore import QSignalBlocker

from b_core.b_datatype.param_enum import DescriptionEnum

from c_ui.a_converter.position_converter_manager import PosiConverterManager
from c_ui.a_converter.pressure_converter_manager import PresConverterManager
from c_ui.a_converter.float_converter_manager import FloatConverterManager
from c_ui.b_control_ver2.b_base.labels import BaseLabel
from c_ui.b_control_ver2.c_values.base_value import ValueWidget

class ReadOnlyEnumValueWidget(ValueWidget):

    def __init__(self, enum_class : Type[DescriptionEnum], label_text="", label_width=150, is_vertical_mode = False, parent=None):
        value_widget = BaseLabel("")
        super().__init__(label_text = label_text, label_width = label_width, is_show_dirty = False, value_widget = value_widget, is_vertical_mode = is_vertical_mode, parent=parent)
        
        self.enum_class = enum_class
        self.set_value(None)

    def reg_value_widget_event(self):
        self.value_widget.sig_assigned_by_code.connect(self.on_assigned_by_code)

    def is_dirty(self):
        return False

    def get_value(self):
        return self.ori_value

    def apply_value(self, value):
        try:
            enum_member = self.enum_class(value)
            description = enum_member.description
            self.value_widget.setText(description)
            self.setEnabled(True)
        except Exception:
            self.value_widget.setText(f"Unknown ({value})")
            self.setEnabled(False)

    def set_not_support(self, is_not_support):
        if is_not_support:
            self.set_value(None)
            # 표시 전용 setText — 값 할당이 아니므로 알림 차단
            with QSignalBlocker(self.value_widget):
                self.value_widget.setText("Not Support")
            self.setEnabled(False)

class ReadOnlyScaleValueWidget(ValueWidget):
    def __init__(self, label_text="", label_width=150, is_vertical_mode = False, parent=None):
        value_widget = BaseLabel("")
        self.converter = FloatConverterManager()
        super().__init__(label_text = label_text, label_width = label_width, is_show_dirty = False, value_widget = value_widget, is_vertical_mode = is_vertical_mode, parent=parent)
        
        self.set_value(None) 

    def reg_value_widget_event(self):
        self.value_widget.sig_assigned_by_code.connect(self.on_assigned_by_code)

    def is_dirty(self):
        return False

    def get_value(self):
        try:
            float_value = float(self.value_widget.text())    
            return float_value / 100
        except Exception:
            return None

    def apply_value(self, value):
        if value is not None:
            value = value * 100

        str_value = self.converter.to_str(value)

        if str_value:
            self.value_widget.setText(str_value)
            self.setEnabled(True)
        else:
            self.value_widget.setText(f"Unknown ({value})")
            self.setEnabled(False)

    def set_not_support(self, is_not_support):
        if is_not_support:
            self.set_value(None)
            # 표시 전용 setText — 값 할당이 아니므로 알림 차단
            with QSignalBlocker(self.value_widget):
                self.value_widget.setText("Not Support")
            self.setEnabled(False)     

class ReadOnlyPosiValueWidget(ValueWidget):
    def __init__(self, label_text="", label_width=150, is_vertical_mode = False, parent=None):
        value_widget = BaseLabel("")
        self.converter = PosiConverterManager()
        super().__init__(label_text = label_text, label_width = label_width, is_show_dirty = False, value_widget = value_widget, is_vertical_mode = is_vertical_mode, parent=parent)
        
        self.set_value(None) 

        self.converter.sig_posi_range_changed.connect(self.handle_posi_range_changed)

    def handle_posi_range_changed(self):
        self.set_value(self.last_set_value)

    def reg_value_widget_event(self):
        self.value_widget.sig_assigned_by_code.connect(self.on_assigned_by_code)

    def is_dirty(self):
        return False

    def get_value(self):
        try:
            float_value = float(self.value_widget.text())    
            return self.converter.convert_dp_to_posi(float_value)
        except Exception:
            return None

    def apply_value(self, value):
        str_value = self.converter.convert_posi_to_dp_str(value)

        if str_value:
            self.value_widget.setText(str_value)
            self.setEnabled(True)
        else:
            self.value_widget.setText(f"Unknown ({value})")
            self.setEnabled(False)

    def set_not_support(self, is_not_support):
        if is_not_support:
            self.set_value(None)
            # 표시 전용 setText — 값 할당이 아니므로 알림 차단
            with QSignalBlocker(self.value_widget):
                self.value_widget.setText("Not Support")
            self.setEnabled(False)                    

class ReadOnlyPresValueWidget(ValueWidget):
    def __init__(self, label_text="", label_width=150, is_vertical_mode = False, parent=None):
        value_widget = BaseLabel("")
        self.converter = PresConverterManager()
        super().__init__(label_text = label_text, label_width = label_width, is_show_dirty = False, value_widget = value_widget, is_vertical_mode = is_vertical_mode, parent=parent)
        
        self.set_value(None) 

        self.converter.sig_pres_range_changed.connect(self.handle_pres_range_changed)

    def handle_pres_range_changed(self):
        self.set_value(self.last_set_value)

    def reg_value_widget_event(self):
        self.value_widget.sig_assigned_by_code.connect(self.on_assigned_by_code)

    def is_dirty(self):
        return False

    def get_value(self):
        try:
            float_value = float(self.value_widget.text())    
            return self.converter.convert_dp_pres_to_iface_pres(float_value)
        except Exception:
            return None

    def apply_value(self, value):
        # 반드시 _str 버전 — float 버전을 setText 에 넣으면 TypeError
        str_value = self.converter.convert_iface_pres_to_dp_pres_str(value)

        if str_value:
            self.value_widget.setText(str_value)
            self.setEnabled(True)
        else:
            self.value_widget.setText(f"Unknown ({value})")
            self.setEnabled(False)

    def set_not_support(self, is_not_support):
        if is_not_support:
            self.set_value(None)
            # 표시 전용 setText — 값 할당이 아니므로 알림 차단
            with QSignalBlocker(self.value_widget):
                self.value_widget.setText("Not Support")
            self.setEnabled(False)                 

class ReadOnlyPresMaxValueWidget(ValueWidget):
    def __init__(self, label_text="", label_width=150, is_vertical_mode = False, parent=None):
        value_widget = BaseLabel("")
        self.converter = PresConverterManager()
        super().__init__(label_text = label_text, label_width = label_width, is_show_dirty = False, value_widget = value_widget, is_vertical_mode = is_vertical_mode, parent=parent)
        
        self.set_value(self.converter.get_dp_max_iface(), is_commit=True) 

        self.converter.sig_pres_range_changed.connect(self.handle_pres_range_changed)

    def handle_pres_range_changed(self):
        self.set_value(self.converter.get_dp_max_iface(), is_commit=True)

    def reg_value_widget_event(self):
        self.value_widget.sig_assigned_by_code.connect(self.on_assigned_by_code)

    def is_dirty(self):
        return False

    def get_value(self):
        try:
            float_value = float(self.value_widget.text())    
            return self.converter.convert_dp_pres_to_iface_pres(float_value)
        except Exception:
            return None

    def apply_value(self, value):
        # 반드시 _str 버전 — float 버전을 setText 에 넣으면 TypeError
        str_value = self.converter.convert_iface_pres_to_dp_pres_str(value)

        if str_value:
            self.value_widget.setText(str_value)
            self.setEnabled(True)
        else:
            self.value_widget.setText(f"Unknown ({value})")
            self.setEnabled(False)

    def set_not_support(self, is_not_support):
        if is_not_support:
            self.set_value(None)
            # 표시 전용 setText — 값 할당이 아니므로 알림 차단
            with QSignalBlocker(self.value_widget):
                self.value_widget.setText("Not Support")
            self.setEnabled(False)                                     