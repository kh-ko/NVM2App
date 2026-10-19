"""차트 기록 세션 헤드리스 테스트 — 기록 중 쓰기 실패(F066), 시작 실패(N099), 기록 중 앱 종료(F067)의 패널 동작과
ChartCSVFileHelper 의 실패 경로, Range 패널 편집의 설정 반영(N101)을 장비·실제 4_chart_record 없이 확인한다.

    python tools/tests/test_chart_record_headless.py

검사 항목
  1. ChartCSVFileHelper (작업 폴더 CHART_RECORD_PATH 는 isolate_runtime 이 격리): 실제 세션 1회 — 헤더 + 행, NaN 은 빈 칸, stop 뒤 두 번째
     stop 은 무해; 첫 파일 열기 실패 → OSError 전파 + 세션 폴더가 남지 않음 (N099)
  2. MainChartPanel (오프스크린, 기록기는 모듈 속성 교체, QMessageBox 는 호출을 기록하는 스텁):
     - 시작 실패 → 기록 안 됨, 버튼 Record, 타이머 정지, [Record] ERROR 로그 1건, 경고 대화상자 1회 (N099)
     - append OSError → 세션 종료(stop 1회), 버튼 복귀, 타이머 정지, 버퍼 갱신 + _redraw 호출(차트는 계속), ERROR 로그,
       경고 대화상자 1회 (F066); stop 도 실패하면 ERROR 2건 + 폴더 경로는 record_dir
     - 기록 중 stop_recording_for_exit → stop 1회, WARN 로그에 폴더 경로, 대화상자 0회, 재호출 무해 (F067);
       stop 실패면 ERROR 1건 + WARN 1건, 예외 없음
     - Range 패널: 자릿수 3 에서 Custom Min/Max 12.345/87.654 → 자릿수 1 → Mode 만 사용자 편집 → Min/Max 설정은 그대로 (N101)
  대화상자 정책(F066 경고 1회 / F067 없음)은 사용자 결정이라 호출 횟수를 센다. 패널 로그는 MainWin 과 같은 source 로 남는다.
"""

from __future__ import annotations

import os
import sys
import time
from typing import NamedTuple

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

TOOLS = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, TOOLS)
import _harness  # noqa: E402

ROOT = _harness.ROOT
BASE = _harness.isolate_runtime()  # 실제 2_resource/config · 3_log 를 건드리지 않는다 — 매니저 import 전에
sys.path.insert(0, ROOT)

app = _harness.make_app()
_harness.silence_message_boxes()

import resources_rc  # noqa: E402,F401
from PySide6.QtWidgets import QMessageBox  # noqa: E402
from b_core.a_define import file_folder_path as path_def  # noqa: E402
from b_core.b_datatype import param_enum as p_enum  # noqa: E402
from b_core.c_manager.app_log_manager import AppLogManager, LogCategory  # noqa: E402
from b_core.f_helper.chart_csv_file_helper import ChartCSVFileHelper  # noqa: E402
from c_ui.c_window_ver2.a_main import main_chart_panel as panel_mod  # noqa: E402
from c_ui.c_window_ver2.a_main.main_chart_panel import MainChartPanel  # noqa: E402

LOG_SOURCE = "MainWin"

# 대화상자 호출 기록 — silence 뒤에 덧씌운다 (test_service_win_headless 와 같은 형태), 반환은 Ok
dialogs: list[tuple[str, str]] = []
QMessageBox.warning = staticmethod(lambda parent, title, text: dialogs.append(("warning", text)) or QMessageBox.StandardButton.Ok)
QMessageBox.information = staticmethod(lambda parent, title, text: dialogs.append(("information", text)) or QMessageBox.StandardButton.Ok)


class _Sample(NamedTuple):      # MainWin.CompoundData 와 같은 필드 — 패널은 이 다섯 필드만 읽는다
    timestamp: int
    act_posi: float
    target_posi: float
    act_pres: float
    target_pres: float


class _FakeRecorder:
    """ChartCSVFileHelper 대역 — fail_at 번째 append 에서 OSError, fail_stop 이면 stop 도 OSError(호출 수는 센다)."""

    def __init__(self, fail_at: int | None = None, fail_stop: bool = False):
        self.start_time = time.time()
        self.record_dir = r"X:\fake\record_20261012_120000"
        self.appended = 0
        self.stop_calls = 0
        self._fail_at = fail_at
        self._fail_stop = fail_stop

    def append(self, rows):
        if self._fail_at is not None and self.appended + 1 >= self._fail_at:
            raise OSError(28, "No space left on device")
        self.appended += 1

    def stop(self):
        self.stop_calls += 1
        if self._fail_stop:
            raise OSError(5, "Input/output error")
        return self.record_dir


def record_logs(category: LogCategory) -> list[str]:
    return [e.message for e in AppLogManager().snapshot(sources={LOG_SOURCE})
            if e.category is category and e.message.startswith("[Record]")]


def main() -> int:
    rep = _harness.Report()

    # ---------------------------------------------------------------- 1. ChartCSVFileHelper
    rec = ChartCSVFileHelper()
    base_dir = os.path.dirname(rec.record_dir)
    rep.check(base_dir == path_def.CHART_RECORD_PATH and base_dir.startswith(BASE), f"기록 폴더 = 격리된 CHART_RECORD_PATH: {rec.record_dir}")
    rec.append([(1700000000000, 1.5, 2.0, 3.25, 4.0, "Torr"), (1700000000200, float("nan"), 2.0, 3.25, 4.0, "Torr")])
    record_dir = rec.stop()
    rep.check(rec.stop() == record_dir, "stop 두 번째 호출은 무해 (같은 경로)")
    csv_files = [f for f in os.listdir(record_dir) if f.endswith(".csv")]
    rep.check(len(csv_files) == 1, f"CSV 1개: {csv_files}")
    with open(os.path.join(record_dir, csv_files[0]), newline="", encoding="utf-8") as f:
        lines = f.read().splitlines()
    rep.check(lines[0].split(",") == ChartCSVFileHelper.CSV_HEADER and len(lines) == 3 and lines[2].split(",")[2] == "",
              f"헤더 + 행 2개, NaN 은 빈 칸: {lines}")

    before = set(os.listdir(base_dir))
    saved_open = ChartCSVFileHelper._open_new_file

    def failing_open(self):
        raise OSError(13, "Permission denied")

    ChartCSVFileHelper._open_new_file = failing_open
    try:
        try:
            ChartCSVFileHelper()
            rep.check(False, "첫 파일 열기 실패 → OSError")
        except OSError:
            rep.check(set(os.listdir(base_dir)) == before, "첫 파일 열기 실패 → OSError 전파 + 세션 폴더 없음 (N099)")
    finally:
        ChartCSVFileHelper._open_new_file = saved_open

    # ---------------------------------------------------------------- 2. MainChartPanel
    panel = MainChartPanel(log_source=LOG_SOURCE)
    saved_helper = panel_mod.ChartCSVFileHelper
    redraws = [0]
    real_redraw = panel._redraw

    def counting_redraw():
        redraws[0] += 1
        real_redraw()

    panel._redraw = counting_redraw
    try:
        # 2-a 시작 실패 (N099)
        def failing_start():
            raise OSError(28, "No space left on device")

        panel_mod.ChartCSVFileHelper = failing_start
        errors_before = len(record_logs(LogCategory.ERROR))
        dialogs.clear()
        panel.on_clicked_record()
        rep.check(panel._recorder is None and panel.record_btn.text() == "Record" and not panel._record_timer.isActive(),
                  "시작 실패: 기록 없음·버튼 Record·타이머 정지 (N099)")
        rep.check(len(record_logs(LogCategory.ERROR)) == errors_before + 1
                  and "cannot start recording" in record_logs(LogCategory.ERROR)[-1], "시작 실패: [Record] ERROR 로그 1건")
        rep.check(dialogs == [("warning", dialogs[0][1])] if dialogs else False, f"시작 실패: 경고 대화상자 1회: {dialogs}")

        # 2-b 쓰기 실패 (F066) — 첫 배치는 성공, 두 번째 배치에서 OSError
        fake = _FakeRecorder(fail_at=2)
        panel_mod.ChartCSVFileHelper = lambda: fake
        dialogs.clear()
        panel.on_clicked_record()
        rep.check(panel._recorder is fake and panel._record_timer.isActive() and panel.record_btn.text().startswith("Stop"),
                  "기록 시작: 기록기 생성·타이머 동작·버튼 Stop")
        panel.update_chart([_Sample(1000, 1.0, 2.0, 3.0, 4.0), _Sample(1200, 1.0, 2.0, 3.0, 4.0)])
        rep.check(fake.appended == 1 and panel._size == 2 and redraws[0] == 1, "첫 배치: append 1회, 버퍼 2샘플, _redraw 1회")
        errors_before = len(record_logs(LogCategory.ERROR))
        panel.update_chart([_Sample(1400, 1.0, 2.0, 3.0, 4.0)])
        rep.check(panel._recorder is None and fake.stop_calls == 1 and not panel._record_timer.isActive()
                  and panel.record_btn.text() == "Record", "쓰기 실패: 세션 종료(stop 1회)·타이머 정지·버튼 Record (F066)")
        rep.check(panel._size == 3 and redraws[0] == 2, "쓰기 실패: 버퍼 갱신 + _redraw 호출 — 차트는 계속 (F066)")
        err = record_logs(LogCategory.ERROR)
        rep.check(len(err) == errors_before + 1 and "write failed" in err[-1] and fake.record_dir in err[-1],
                  f"쓰기 실패: [Record] ERROR 로그에 사유와 폴더: {err[-1] if err else None}")
        rep.check(len(dialogs) == 1 and dialogs[0][0] == "warning" and fake.record_dir in dialogs[0][1],
                  f"쓰기 실패: 경고 대화상자 1회에 폴더 경로: {dialogs}")
        panel.update_chart([_Sample(1600, 1.0, 2.0, 3.0, 4.0)])
        rep.check(fake.appended == 1 and panel._size == 4 and redraws[0] == 3, "종료 뒤 배치는 기록기에 가지 않고 차트만 갱신")

        # 2-b' 쓰기 실패 + 닫기도 실패 — 폴더 경로는 record_dir, ERROR 2건, 예외 없음
        fake_b = _FakeRecorder(fail_at=1, fail_stop=True)
        panel_mod.ChartCSVFileHelper = lambda: fake_b
        dialogs.clear()
        panel.on_clicked_record()
        errors_before = len(record_logs(LogCategory.ERROR))
        panel.update_chart([_Sample(1800, 1.0, 2.0, 3.0, 4.0)])
        err = record_logs(LogCategory.ERROR)
        rep.check(panel._recorder is None and fake_b.stop_calls == 1 and len(err) == errors_before + 2
                  and "closing the record file failed" in err[-2] and fake_b.record_dir in err[-1]
                  and len(dialogs) == 1 and fake_b.record_dir in dialogs[0][1],
                  f"쓰기+닫기 실패: ERROR 2건(닫기, 쓰기), 경로는 record_dir, 대화상자 1회: {err[-2:]}")

        # 2-c 기록 중 앱 종료 (F067)
        fake2 = _FakeRecorder()
        panel_mod.ChartCSVFileHelper = lambda: fake2
        panel.on_clicked_record()
        panel.update_chart([_Sample(2000, 1.0, 2.0, 3.0, 4.0)])
        warns_before = len(record_logs(LogCategory.WARN))
        dialogs.clear()
        panel.stop_recording_for_exit()
        warns = record_logs(LogCategory.WARN)
        rep.check(fake2.stop_calls == 1 and panel._recorder is None and not panel._record_timer.isActive(),
                  "종료 처리: stop 1회·기록기 해제·타이머 정지 (F067)")
        rep.check(len(warns) == warns_before + 1 and fake2.record_dir in warns[-1] and not dialogs,
                  f"종료 처리: WARN 로그에 폴더 경로, 대화상자 없음: {warns[-1] if warns else None}")
        panel.stop_recording_for_exit()
        rep.check(fake2.stop_calls == 1 and len(record_logs(LogCategory.WARN)) == warns_before + 1 and not dialogs,
                  "기록 중이 아니면 종료 처리는 아무것도 하지 않음")

        # 2-c' 종료 처리 중 닫기 실패 — ERROR 1건 + WARN 1건, 예외 없음
        fake3 = _FakeRecorder(fail_stop=True)
        panel_mod.ChartCSVFileHelper = lambda: fake3
        panel.on_clicked_record()
        errors_before, warns_before = len(record_logs(LogCategory.ERROR)), len(record_logs(LogCategory.WARN))
        panel.stop_recording_for_exit()
        rep.check(fake3.stop_calls == 1 and panel._recorder is None
                  and len(record_logs(LogCategory.ERROR)) == errors_before + 1 and len(record_logs(LogCategory.WARN)) == warns_before + 1
                  and fake3.record_dir in record_logs(LogCategory.WARN)[-1] and not dialogs,
                  "종료 처리 + 닫기 실패: ERROR 1건 + WARN 1건(경로는 record_dir), 대화상자 없음")

        # 2-d Range 패널 — Mode 만 편집하면 건드리지 않은 Custom Min/Max 가 표시(반올림)값으로 되쓰이지 않는다 (N101)
        ls = panel.local_setting
        mode_w = panel._range_widgets["posi_chart_range_mode"]
        ls.posi_decimal_places = 3
        ls.posi_chart_range_mode = p_enum.ChartRangeModeEnum.CUSTOM.value
        ls.posi_chart_range_custom_min = 12.345
        ls.posi_chart_range_custom_max = 87.654
        ls.posi_decimal_places = 1   # Min/Max 표시는 12.3/87.7 로 반올림, 설정값은 그대로
        full_index = mode_w.value_widget.findData(p_enum.ChartRangeModeEnum.FULL.value)
        mode_w.value_widget.setCurrentIndex(full_index)
        mode_w.value_widget.activated.emit(full_index)   # 사용자 선택 전용 시그널 → Mode 위젯의 sig_edited_by_user 만
        rep.check(ls.posi_chart_range_mode == p_enum.ChartRangeModeEnum.FULL.value
                  and (ls.posi_chart_range_custom_min, ls.posi_chart_range_custom_max) == (12.345, 87.654),
                  f"Mode 만 편집: mode 반영, Custom Min/Max 는 표시값으로 덮어쓰지 않음 (N101): "
                  f"{ls.posi_chart_range_custom_min}/{ls.posi_chart_range_custom_max}")
    finally:
        panel_mod.ChartCSVFileHelper = saved_helper
        _harness.destroy_window(panel, app)   # 루프 밖에서는 deleteLater+processEvents 만으로는 파괴되지 않는다

    _harness.assert_isolated()
    return rep.summary()


if __name__ == "__main__":
    sys.exit(main())
