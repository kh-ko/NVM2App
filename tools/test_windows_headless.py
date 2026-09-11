"""창 생성 헤드리스 테스트 — 장비 없이 주요 창이 생성·정리되는지만 확인한다.

    python tools/test_windows_headless.py

QT_QPA_PLATFORM=offscreen 으로 QApplication 을 띄우고, ParamWin 계열 / BackupWin /
RestoreWin 을 만들었다가 닫는다 (closeEvent 가 워커 cleanup 을 수행). MainWin 은
임포트 경로만 통과시킨다. 통신은 없으므로 refresh 는 NOT_CONNECTED 경로다.
"""

from __future__ import annotations

import os
import sys
import traceback

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)

from PySide6.QtWidgets import QApplication  # noqa: E402

app = QApplication.instance() or QApplication(sys.argv)

import resources_rc  # noqa: E402,F401
from b_core.b_datatype.general_enum import ParamAccType  # noqa: E402
from c_ui.b_control_ver2.d_param.param_win import (ParamIfaceEtherCatWin, ParamPresCtrlWin,  # noqa: E402
                                                    ParamWin)
from c_ui.c_window_ver2.d_backup_restore.backup_win import BackupWin  # noqa: E402
from c_ui.c_window_ver2.d_backup_restore.restore_win import RestoreWin  # noqa: E402

CASES = [
    ("ParamWin System.Identification", ParamWin,
     dict(win_name=None, paths=["System.Identification"], filter_param_paths=[], is_editblock_win=True)),
    ("ParamWin Sensor.Settings", ParamWin,
     dict(win_name="Sensor.Settings", paths=["Sensor.Basic", "Sensor.Zero Adjust"], filter_param_paths=[])),
    ("ParamPresCtrlWin Controller 1-4", ParamPresCtrlWin,
     dict(win_name="Pressure Control Controller Settings",
          paths=["Pressure Control.Controller 1", "Pressure Control.Controller 2",
                 "Pressure Control.Controller 3", "Pressure Control.Controller 4"],
          filter_param_paths=[], folder_max_width=350)),
    ("ParamWin Adaptive Learn List 1", ParamWin,
     dict(win_name="Adaptive Learn List 1", paths=["Adaptive Learn List 1"], filter_param_paths=[],
          folder_max_width=350)),
    ("ParamIfaceEtherCatWin", ParamIfaceEtherCatWin,
     dict(win_name="Interface EtherCAT", paths=["Interface EtherCAT"], filter_param_paths=[])),
    ("BackupWin", BackupWin, dict(win_name="Backup")),
    ("RestoreWin", RestoreWin, dict(win_name="Restore")),
]


def main() -> int:
    fail = 0
    for name, cls, kwargs in CASES:
        try:
            win = cls(parent=None, **kwargs)
            app.processEvents()
            n_widgets = sum(len(fw.widgets) for fw in getattr(win, "folder_widgets", []))

            # 워커 목록에 같은 param 이 두 번 등록됐는지 — 새 워커는 spec 기준으로 한 번만
            # 읽으므로, 중복이 있으면 구 워커와 요청 수가 달라진다 (있으면 보고)
            worker = getattr(win, "param_worker", None)
            dup = 0
            if worker is not None:
                regs = (worker.init_param_list
                        + [p for p in worker.write_param_list if p.acc != ParamAccType.WO]
                        + worker.read_param_list)
                dup = len(regs) - len(set(regs))

            win.close()
            app.processEvents()
            print(f"  ok   {name} (param widgets {n_widgets}, 워커 중복 등록 {dup})")
        except Exception:
            fail += 1
            print(f"  FAIL {name}")
            traceback.print_exc()

    try:
        import c_ui.c_window_ver2.a_main.main_win  # noqa: F401
        print("  ok   MainWin import")
    except Exception:
        fail += 1
        print("  FAIL MainWin import")
        traceback.print_exc()

    print(f"\n{'ALL PASS' if fail == 0 else f'FAILED {fail}'}")
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
