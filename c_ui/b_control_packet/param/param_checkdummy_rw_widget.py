from PySide6.QtCore import Signal
from c_ui.b_control_packet.controls_with_label.l_check_rw_widget import LCheckReadWriteWidget
from PySide6.QtCore import QObject
from b_core.c_manager.parameter_manager import ParamManager

class ParamCheckDummyReadWriteWidget(QObject):
    sig_value_changed = Signal()

    def __init__(self, param_full_path : str, parent = None):
        super().__init__(parent) 
        self.original_value = None

        self.param = ParamManager().get_by_full_path(param_full_path)

        self.item_list = []

        enum_class=self.param.ref_list

        for enum_item in enum_class:
            check_box = LCheckReadWriteWidget(enum_item.description)
            check_box.sig_value_changed.connect(self._on_input_changed)
            self.item_list.append((check_box, enum_item.value))

        self.param.sig_value_changed.connect(self.handle_value_changed)
        self.param.sig_is_err_changed.connect(self.handle_is_err_changed)
        self.param.sig_is_not_support_changed.connect(self.handle_is_not_support_changed)
        
        self.handle_value_changed()
        self.handle_is_err_changed()
        self.handle_is_not_support_changed() 

    def _on_input_changed(self):
        self.sig_value_changed.emit()        

    def handle_value_changed(self):
        self.set_value(self.param.value)
        self.commit()
            
    def handle_is_err_changed(self):
        self.set_error(self.param.is_err)

    def handle_is_not_support_changed(self):
        self.set_support(not self.param.is_not_support)

    def get_param_write_value(self) -> str:
        input_value = self.get_value()
        return f"{input_value}"

    def get_backup_value(self) -> str:
        input_value = self.get_value()
        return f"{input_value}"

    def set_backup_value(self, value):
        try:
            backup_value = int(value)
            self.set_value(backup_value)
        except ValueError:
            self.set_value(None)

    def add_widget(self, widget):
        pass

    def restore(self):
        for check_box, item_value in self.item_list:
            check_box.set_value(check_box.original_value)
        self.commit()

    def set_error(self, value : bool):
        for check_box, item_value in self.item_list:
            check_box.set_error(value)

    def set_support(self, support : bool):
        for check_box, item_value in self.item_list:
            check_box.value_widget.set_support(support)
        
    def commit(self):
        for check_box, item_value in self.item_list:
            check_box.commit()
    
    def set_value(self, value : int):
        if value is None:
            value = 0
            
        for check_box, item_value in self.item_list:
            is_set = (value & (1 << item_value)) != 0
            check_box.set_value(is_set)

    def get_value(self) -> int:
        value = 0
        for check_box, item_value in self.item_list:
            if check_box.get_value():
                value = value | (1 << item_value)

        return value

    def is_dirty(self) -> bool:
        for check_box, item_value in self.item_list:
            if check_box.is_dirty():
                return True
        return False
          
        


