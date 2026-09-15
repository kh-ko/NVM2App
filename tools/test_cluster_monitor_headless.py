"""Cluster Monitor 창 헤드리스 테스트 — 장비 없이 표 구성 · 장치 수 연동 · 값 표시를 확인한다.

    python tools/test_cluster_monitor_headless.py

검사 항목
  1. 생성: 열 17개(Device 0 Status 의 param 순서), 행 0개(장치 수 미수신), 워커 읽기 등록 = Number of Valves 1개
  2. 장치 수 변경: Number of Valves 값 → 행 수와 읽기 등록(1 + 17 × n)이 따라감. 상한 30, None 이면 0
  3. 값 표시: NV1 spec 에 샘플 응답(구 C++ 주석 i:9301)을 넣으면 해당 행이 채워진다 —
     posi 는 LocalSetting 자릿수, enum 은 설명, real 은 유효숫자 6자리. E: → "Not Support", 빈 응답 → 오류 색
  4. 닫기: closeEvent 로 워커 정리 후 파괴 (예외 없음)
"""

from __future__ import annotations

import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)

from PySide6.QtWidgets import QApplication  # noqa: E402

app = QApplication.instance() or QApplication(sys.argv)

import resources_rc  # noqa: E402,F401
from b_core.c_manager.parameter_manager import ParamManager  # noqa: E402
from b_core.g_protocol.spec_registry import SpecRegistry  # noqa: E402
from c_ui.a_converter.position_converter_manager import PosiConverterManager  # noqa: E402
from c_ui.b_control_ver2.a_theme.tokens import tokens  # noqa: E402
from c_ui.c_window_ver2.f_cluster.cluster_monitor_win import NUM_VALVES_PATH, ClusterMonitorWin  # noqa: E402

SAMPLE_DEV1 = "i:9301100000+3000010000011000000000000000100000"


class Report:
    def __init__(self):
        self.fail = 0
        self.checks = 0

    def check(self, ok: bool, msg: str):
        self.checks += 1
        if not ok:
            self.fail += 1
            print(f"  FAIL {msg}")


def main() -> int:
    rep = Report()
    pm = ParamManager()
    reg = SpecRegistry()
    num = pm.get_by_full_path(NUM_VALVES_PATH)
    num.value = None

    win = ClusterMonitorWin(parent=None, win_name="Cluster Monitor")
    app.processEvents()
    try:
        # ---------------------------------------------------------------- 1. 생성
        table = win.table
        rep.check(table.columnCount() == 17 and table.rowCount() == 0,
                  f"초기 표: 열 {table.columnCount()} / 행 {table.rowCount()}")
        rep.check(table.horizontalHeaderItem(0).text() == "Actual Position (%)"
                  and table.horizontalHeaderItem(16).text() == "Compressed Air Value(mbar)",
                  f"열 제목: {table.horizontalHeaderItem(0).text()!r} … {table.horizontalHeaderItem(16).text()!r}")
        rep.check(win.param_worker.read_param_list == [num], "읽기 등록: Number of Valves 만")

        # ---------------------------------------------------------------- 2. 장치 수
        num.value = 3
        rep.check(table.rowCount() == 3 and len(win.param_worker.read_param_list) == 1 + 17 * 3,
                  f"장치 3: 행 {table.rowCount()} / 읽기 등록 {len(win.param_worker.read_param_list)}")
        rep.check(table.verticalHeaderItem(2).text() == "Device 2", "행 제목 Device 2")
        rep.check(all(table.item(r, c).text() == "-" for r in range(3) for c in range(17)), "값 미수신 셀은 '-'")

        num.value = 99
        rep.check(table.rowCount() == 30 and len(win.param_worker.read_param_list) == 1 + 17 * 30,
                  f"장치 99 → 상한 30: 행 {table.rowCount()}")
        num.value = 3
        rep.check(table.rowCount() == 3 and len(win.param_worker.read_param_list) == 1 + 17 * 3, "장치 3 으로 복귀")

        # ---------------------------------------------------------------- 3. 값 표시
        dev1 = pm.get_by_full_path("Cluster.Device 1.Status.Actual Position")
        spec = reg.get_read_spec(dev1)
        spec.apply_response(SAMPLE_DEV1)
        app.processEvents()  # 0 ms 합침 타이머
        fmt = PosiConverterManager().format_dp
        got = [table.item(1, c).text() for c in range(17)]
        expected = [fmt(100.0), fmt(30.0), "100", "Unfreeze", "Local", "Homing", "On",
                    "Off", "Off", "Off", "Off", "Off", "Off", "Off", "Off", "Off", "100000"]
        rep.check(got == expected, f"i:9301 표시: {got}")
        rep.check(all(table.item(0, c).text() == "-" for c in range(17)), "다른 장치 행은 그대로")
        rep.check(table.item(1, 0).foreground().color().name() == tokens().text, "정상 값 글자색")

        spec.apply_response("E:001")
        app.processEvents()
        rep.check(all(table.item(1, c).text() == "Not Support" for c in range(17)), "E: → Not Support")

        spec.apply_response(SAMPLE_DEV1)
        spec.apply_response("")
        app.processEvents()
        rep.check(table.item(1, 0).text() == fmt(100.0)
                  and table.item(1, 0).foreground().color().name() == tokens().danger,
                  f"통신 오류: 마지막 값 유지 + 오류 색 ({table.item(1, 0).foreground().color().name()})")

        spec.apply_response(SAMPLE_DEV1)
        app.processEvents()
        rep.check(table.item(1, 0).foreground().color().name() == tokens().text, "정상 응답 후 글자색 복귀")

        num.value = None
        rep.check(table.rowCount() == 0 and win.param_worker.read_param_list == [num], "장치 수 None → 행 0")
    finally:
        win.close()
        app.processEvents()
        num.value = None
        for p in pm.get_params_in_folder("Cluster.Device 1.Status"):
            p.value = None
            p.is_err = False
            p.is_not_support = False

    print(f"\nchecks {rep.checks} / fail {rep.fail}")
    print("ALL PASS" if rep.fail == 0 else f"{rep.fail} FAIL")
    return 0 if rep.fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
