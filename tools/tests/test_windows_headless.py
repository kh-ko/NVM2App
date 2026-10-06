"""창 생성 헤드리스 테스트 — 장비 없이 MainWin 이 여는 창을 전부 만들었다 닫고, 파괴 뒤 좀비 연결이 없는지 확인한다.

    python tools/tests/test_windows_headless.py

QT_QPA_PLATFORM=offscreen 으로 QApplication 을 띄우고, CASES 의 창을 MainWin 과 같은 인자로 만들었다 닫는다
(closeEvent 가 워커 cleanup 을 수행). 통신은 없으므로 refresh 는 NOT_CONNECTED 경로다.

검사 항목
  1. 생성·닫기: 예외 없음, paths 를 받는 창은 폴더 카드가 1개 이상(경로 오타 방지). 워커 등록 목록의 같은 param 중복은
     note 로만 보고한다 (새 워커는 spec 기준으로 한 번만 읽는다)
  2. 좀비 연결(F111): 창을 WA_DeleteOnClose 로 파괴한 뒤 싱글턴 시그널(ServicePort·LocalSetting·컨버터·연결 설정·로그·
     스키마의 모든 param)을 쏴서 파괴된 창의 슬롯이 남아 있지 않은지 — 람다/클로저 연결은 여기서 드러난다
  3. MainWin 임포트

CASES 는 MainWin 의 show_window 호출 인자를 글자 그대로 옮긴 것이다 (N133) — MainWin 을 고치면 여기도 고친다.
제외: ConnectionConnectWin(열자마자 COM 포트를 실제로 스캔), HelpNvmUpdateWin(start() 에서 FTP 릴리스 노트를 조회 —
test_service_win_headless 가 조회를 스텁해 다룬다).
"""

from __future__ import annotations

import os
import sys
import traceback

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

TOOLS = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, TOOLS)
import _harness  # noqa: E402

ROOT = _harness.ROOT
_harness.isolate_runtime()  # 실제 2_resource/config · 3_log 를 건드리지 않는다 — 매니저 import 전에
sys.path.insert(0, ROOT)

app = _harness.make_app()
_harness.silence_message_boxes()  # 창이 띄우는 안내/경고 모달이 헤드리스 이벤트 루프를 삼키지 않게

import resources_rc  # noqa: E402,F401
from b_core.b_datatype.general_enum import ParamAccType  # noqa: E402
from b_core.c_manager.app_log_manager import AppLogManager  # noqa: E402
from b_core.c_manager.connection_setting_manager import ConnectionSettingManager  # noqa: E402
from b_core.c_manager.parameter_manager import ParamManager  # noqa: E402
from b_core.c_manager.local_setting_manager import LocalSettingManager  # noqa: E402
from b_core.d_dal.service_port import ServicePort  # noqa: E402
from c_ui.a_converter.position_converter_manager import PosiConverterManager  # noqa: E402
from c_ui.a_converter.pressure_converter_manager import PresConverterManager  # noqa: E402
from c_ui.b_control_ver2.d_param.param_win import (ParamIfaceDentWin, ParamIfaceEtherCatWin,  # noqa: E402
                                                    ParamPresCtrlWin, ParamWin)
from c_ui.c_window_ver2.c_analysis.sensor_analysis_win import SensorAnalysisWin  # noqa: E402
from c_ui.c_window_ver2.d_backup_restore.backup_win import BackupWin  # noqa: E402
from c_ui.c_window_ver2.d_backup_restore.restore_win import RestoreWin  # noqa: E402
from c_ui.c_window_ver2.f_cluster.cluster_monitor_win import ClusterMonitorWin  # noqa: E402
from c_ui.c_window_ver2.g_factory.factory_firmware_update_win import FactoryFirmwareUpdateWin  # noqa: E402
from c_ui.c_window_ver2.h_help.help_about_win import HelpAboutWin  # noqa: E402
from c_ui.c_window_ver2.log_view_win import LogViewWin  # noqa: E402
from c_ui.c_window_ver2.x_localsetting.local_posi_setting_win import LocalPosiSettingWin  # noqa: E402
from c_ui.c_window_ver2.x_localsetting.local_pres_setting_win import LocalPresSettingWin  # noqa: E402
from c_ui.c_window_ver2.d_backup_restore import backup_win as backup_win_mod  # noqa: E402
from c_ui.c_window_ver2.x_message.firmware_update_message_box import NoBackupChoice  # noqa: E402

# FU 모드 백업 창은 닫을 때 '백업 없이 계속/머무름/취소' 를 묻는다 — 기본 답(닫음=STAY)은 창을 남기므로 '취소' 로 답한다
backup_win_mod.ask_close_without_backup = lambda parent: NoBackupChoice.CANCEL


def _pw(win_name, paths, filter_param_paths=(), is_editblock_win=False, label_width=210, **extra):
    """MainWin 의 ParamWin 호출 인자 (parent/win_id/is_modal 은 WinManager 몫이라 제외)."""
    return dict(win_name=win_name, paths=list(paths), filter_param_paths=list(filter_param_paths),
                is_editblock_win=is_editblock_win, label_width=label_width, **extra)


CASES = [
    # --- System
    ("System.Warning/Error", ParamWin, _pw(None, ["System.Warning/Error"])),
    ("System.Identification", ParamWin, _pw(None, ["System.Identification"], is_editblock_win=True)),
    ("System.Statistics", ParamWin, _pw(None, ["System.Statistics"])),
    ("System.Services", ParamWin, _pw(None, ["System.Services"], ["System.Services.Test Mode Used"])),
    # --- Valve / Sensor
    ("Valve.Basic", ParamWin, _pw(None, ["Valve.Basic"])),
    ("Valve.Cycle Counter", ParamWin, _pw(None, ["Valve.Cycle Counter"])),
    ("Valve.Option", ParamWin, _pw(None, ["Valve.Option"])),
    ("Sensor.Zero", ParamWin, _pw("Sensor.Zero", ["Sensor.Basic", "Sensor.Zero Adjust"])),
    ("Sensor.Settings", ParamWin,
     _pw("Sensor.Settings", ["Sensor.Sensor 1.Basic", "Sensor.Sensor 2.Basic",
                             "Sensor.Sensor 1.Range", "Sensor.Sensor 2.Range",
                             "Sensor.Sensor 1.Zero Adjust", "Sensor.Sensor 2.Zero Adjust",
                             "Sensor.Sensor 1.Filter", "Sensor.Sensor 2.Filter",
                             "Sensor.Sensor 1.Analog Sensor Input", "Sensor.Sensor 2.Analog Sensor Input",
                             "Sensor.Sensor 1.Digital Sensor Input", "Sensor.Sensor 2.Digital Sensor Input",
                             "Sensor.Crossover", "Sensor.General Setting.Logarithmic Pressure"], folder_max_width=350)),
    # --- Control
    ("Position Control", ParamWin, _pw("Position Control", ["Position Control"])),
    ("Pressure Control General Settings", ParamWin,
     _pw("Pressure Control General Settings", ["Pressure Control.Basic", "Pressure Control.General Settings"])),
    ("Pressure Control Controller Settings", ParamPresCtrlWin,
     _pw("Pressure Control Controller Settings",
         ["Pressure Control.Controller 1", "Pressure Control.Controller 2",
          "Pressure Control.Controller 3", "Pressure Control.Controller 4"], folder_max_width=350)),
    ("Adaptive Learn.Basic", ParamWin, _pw("Adaptive Learn.Basic", ["Adaptive Learn.Basic"])),
    *[(f"Adaptive Learn.Learn Bank {i}", ParamWin, _pw(f"Adaptive Learn.Learn Bank {i}", [f"Adaptive Learn.Learn Bank {i}"]))
      for i in (1, 2, 3, 4)],
    *[(f"Adaptive Learn List {i}", ParamWin, _pw(f"Adaptive Learn List {i}", [f"Adaptive Learn List {i}"], folder_max_width=350))
      for i in (1, 2, 3, 4)],
    ("Power Fail Option", ParamWin, _pw("Power Fail Option", ["Power Fail Option"])),
    ("Power Connector IO", ParamWin, _pw("Power Connector IO", ["Power Connector IO"])),
    # --- Interface
    ("Interface DeviceNet", ParamIfaceDentWin, _pw("Interface DeviceNet", ["Interface DeviceNet"])),
    ("Interface EtherCAT", ParamIfaceEtherCatWin,
     _pw("Interface EtherCAT", ["Interface EtherCAT.Basic", "Interface.Scaling", "Interface EtherCAT.Scaling",
                                "Interface EtherCAT.Range", "Interface EtherCAT.Connection Loss Reaction"])),
    # --- Cluster / Compound / Legacy (Cluster.Settings 의 filter 는 항상 2개: [Number of Valves | Cluster Address](User
    #     Interface 가 CLUSTER_SLAVE 인지) + [Baud Rate V2 | V1](펌웨어 < 6.2.3 인지) — 대표 조합 둘)
    ("Cluster.Settings (slave, fw>=6.2.3)", ParamWin,
     _pw("Cluster.Settings", ["Cluster.Settings"], ["Cluster.Settings.Number of Valves", "Cluster.Settings.Baud Rate V1"])),
    ("Cluster.Settings (master, fw<6.2.3)", ParamWin,
     _pw("Cluster.Settings", ["Cluster.Settings"], ["Cluster.Settings.Cluster Address", "Cluster.Settings.Baud Rate V2"])),
    *[(f"Compound Commands {i}", ParamWin,
       _pw(f"Compound Commands.User Interface.Compound Commands {i}", [f"Compound Commands.User Interface.Compound Commands {i}"]))
      for i in (1, 2, 3, 4)],
    ("Legacy Parameters", ParamWin, _pw("Legacy Parameters", ["Legacy Parameters"], label_width=310)),
    ("ADC Calibration", ParamWin, _pw("ADC Calibration", ["ADC Calibration"])),
    # --- 그 밖의 창 (ServiceWin 직계: Backup/Restore/Sensor Analysis/About · ParamWin 파생: Firmware Update/Cluster Monitor · 독립 창)
    ("BackupWin", BackupWin, dict(win_name="Backup", is_fu_backup=False)),
    ("BackupWin (FU)", BackupWin, dict(win_name="Firmware Backup", is_fu_backup=True)),
    ("RestoreWin", RestoreWin, dict(win_name="Restore")),
    ("SensorAnalysisWin", SensorAnalysisWin, dict(win_name="Sensor Analysis")),
    ("FactoryFirmwareUpdateWin", FactoryFirmwareUpdateWin, dict(win_name="Firmware Update", backup_file_path=None)),
    ("HelpAboutWin", HelpAboutWin, dict(win_name="About")),
    ("ClusterMonitorWin", ClusterMonitorWin, dict(win_name="Cluster Monitor")),
    ("LocalPosiSettingWin", LocalPosiSettingWin, {}),
    ("LocalPresSettingWin", LocalPresSettingWin, {}),
    ("LogViewWin", LogViewWin, dict(sources={"MainWin"})),
]


def singleton_signals():
    """파괴된 창이 연결했을 법한 싱글턴 시그널 전부 — 인자 없는 것은 그대로, 인자 있는 것은 (signal, args), 로그는 호출로.
    param 은 워커 등록 목록이 아니라 스키마 전체를 쏜다 — 창이 등록 없이 연결만 하는 param(SN 라벨, Cluster Monitor 의
    전 장치 status 등)도 잡기 위해."""
    signals = [(ServicePort().connect_info_changed, ("",))]
    local_setting = LocalSettingManager()
    signals += [getattr(local_setting, name) for name in dir(type(local_setting)) if name.startswith("sig_")]
    pres, posi = PresConverterManager(), PosiConverterManager()
    signals += [pres.sig_display_unit_changed, pres.sig_decimals_changed, pres.sig_full_scale_changed, posi.sig_posi_range_changed]
    signals += [ConnectionSettingManager().sig_list_changed, (ConnectionSettingManager().sig_selection_changed, (0,))]
    signals.append(lambda: AppLogManager().get_logger("zombie-probe", is_global=True).info("probe"))  # sig_logged (LogViewWin)
    for param in ParamManager().get_param_list():
        signals += [param.sig_value_changed, param.sig_is_not_support_changed, param.sig_is_err_changed]
    return signals


def main() -> int:
    rep = _harness.Report()
    dup_notes = []
    probe_signals = singleton_signals()
    for name, cls, kwargs in CASES:
        try:
            win = cls(parent=None, **kwargs)
            if hasattr(win, "start"):
                win.start()   # WinManager.show_window 가 하는 2단계 초기화
            app.processEvents()
            if kwargs.get("paths"):
                rep.check(len(win.folder_widgets) > 0, f"{name}: 폴더 카드 0개 — paths 가 스키마 폴더와 맞지 않는다")
            registered: list = []
            worker = getattr(win, "param_worker", None)
            if worker is not None:
                regs = (worker.init_param_list
                        + [p for p in worker.write_param_list if p.acc != ParamAccType.WO]
                        + worker.read_param_list)
                dup = len(regs) - len(set(regs))
                if dup:
                    dup_notes.append(f"{name}: 워커 등록 목록에 같은 param {dup}건 (새 워커는 spec 기준으로 한 번만 읽는다)")
                registered = list(dict.fromkeys(regs))

            _harness.destroy_window(win, app)                                   # 닫기 → closeEvent(cleanup) → 파괴
            problems = _harness.emit_signals_capture(probe_signals, app, process_events_each=False)
            rep.check(not problems, f"{name}: 파괴 뒤 좀비 연결\n" + "\n".join(problems))
            print(f"  ok   {name} (param {len(registered)})")
        except Exception:
            rep.check(False, f"{name}: 예외\n{traceback.format_exc()}")
    for note in dup_notes:
        rep.note(note)

    try:
        import c_ui.c_window_ver2.a_main.main_win  # noqa: F401
        rep.check(True, "MainWin import")
    except Exception:
        rep.check(False, f"MainWin import\n{traceback.format_exc()}")

    return rep.summary()


if __name__ == "__main__":
    sys.exit(main())
