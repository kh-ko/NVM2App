
from c_ui.b_control_packet.param_container.param_folder_sens_log_pres_widget import ParamFolderSensLogPresWidget
from c_ui.b_control_packet.param_container.param_folder_sens_crossover_widget import ParamFolderSensCrossoverWidget
from PySide6.QtWidgets import QVBoxLayout
from PySide6.QtWidgets import QHBoxLayout
from c_ui.b_control_packet.param_container.param_folder_widget import ParamFolderWidget
from c_ui.b_control_packet.param_container.param_setting_win import ParamSettingWin
from c_ui.b_control_packet.param_container.param_folder_sens_sens1_digital_input_widget import ParamFolderSensSens1DigitalInputWidget
from c_ui.b_control_packet.param_container.param_folder_sens_sens1_analog_input_widget import ParamFolderSensSens1AnalogInputWidget
from c_ui.b_control_packet.param_container.param_folder_sens_sens1_filter_widget import ParamFolderSensSens1FilterWidget
from c_ui.b_control_packet.param_container.param_folder_sens_sens1_zero_adj_widget import ParamFolderSensSens1ZeroAdjWidget
from c_ui.b_control_packet.param_container.param_folder_sens_sens1_range_widget import ParamFolderSensSens1RangeWidget
from c_ui.b_control_packet.param_container.param_folder_sens_sens1_basic_widget import ParamFolderSensSens1BasicWidget
from c_ui.b_control_packet.param_container.param_folder_sens_sens2_digital_input_widget import ParamFolderSensSens2DigitalInputWidget
from c_ui.b_control_packet.param_container.param_folder_sens_sens2_analog_input_widget import ParamFolderSensSens2AnalogInputWidget
from c_ui.b_control_packet.param_container.param_folder_sens_sens2_filter_widget import ParamFolderSensSens2FilterWidget
from c_ui.b_control_packet.param_container.param_folder_sens_sens2_zero_adj_widget import ParamFolderSensSens2ZeroAdjWidget
from c_ui.b_control_packet.param_container.param_folder_sens_sens2_range_widget import ParamFolderSensSens2RangeWidget
from c_ui.b_control_packet.param_container.param_folder_sens_sens2_basic_widget import ParamFolderSensSens2BasicWidget

class SensorSettingWin(ParamSettingWin):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.resize(800, 450)
        self.setWindowTitle("Sensor >> Setting")

        columns_layout = QHBoxLayout()
        columns_layout.setSpacing(5)

        self.sensor1_layout = QVBoxLayout()
        self.sensor2_layout = QVBoxLayout()

        columns_layout.addLayout(self.sensor1_layout)
        columns_layout.addLayout(self.sensor2_layout)

        self.content_layout.addLayout(columns_layout)
        
        self.add_sensor1_folder(ParamFolderSensSens1BasicWidget())
        self.add_sensor1_folder(ParamFolderSensSens1RangeWidget())
        self.add_sensor1_folder(ParamFolderSensSens1ZeroAdjWidget())
        self.add_sensor1_folder(ParamFolderSensSens1FilterWidget())
        self.add_sensor1_folder(ParamFolderSensSens1AnalogInputWidget())
        self.add_sensor1_folder(ParamFolderSensSens1DigitalInputWidget())
        self.sensor1_layout.addStretch()

        self.add_sensor2_folder(ParamFolderSensSens2BasicWidget())
        self.add_sensor2_folder(ParamFolderSensSens2RangeWidget())
        self.add_sensor2_folder(ParamFolderSensSens2ZeroAdjWidget())
        self.add_sensor2_folder(ParamFolderSensSens2FilterWidget())
        self.add_sensor2_folder(ParamFolderSensSens2AnalogInputWidget())
        self.add_sensor2_folder(ParamFolderSensSens2DigitalInputWidget())
        self.sensor2_layout.addStretch()

        self.add_param_folder_widget(ParamFolderSensCrossoverWidget())
        self.add_param_folder_widget(ParamFolderSensLogPresWidget())

        self.content_layout.addStretch()

        self.init_toolbar()
        self.init_end()

    def add_sensor1_folder(self, widget):
        self.sensor1_layout.addWidget(widget)
        self.parameter_folder_widgets.append(widget)

    def add_sensor2_folder(self, widget):
        self.sensor2_layout.addWidget(widget)
        self.parameter_folder_widgets.append(widget)        