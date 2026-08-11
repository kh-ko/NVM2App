"""차트 기록기 — Record 중 수신 샘플을 CSV 로 저장한다.

- 임시 폴더(%TEMP%/NVM2App/chart_record/record_<시작시각>)에 기록하고,
  파일은 파일 시작 시각 기준 1시간마다 롤링한다 (chart_YYYYMMDD_HHMMSS.csv).
- 값은 차트에 그려지는 표시(dp) 단위 그대로이며, 압력은 행마다 표시 단위
  컬럼(pres_unit)을 함께 기록한다 — 기록 중 단위가 바뀌어도 행 단위로
  자기 기술적(self-describing)이라 혼선이 없다.
- 매 append(200ms 배치)마다 flush — 비정상 종료 시에도 직전 배치까지 보존된다.
- 저장 위치 확정(다이얼로그/이동)은 사용측(차트 패널) 몫이다. stop() 은
  파일만 닫고 임시 폴더 경로를 돌려준다.
"""

import csv
import os
import tempfile
import time

_FILE_ROTATE_SEC = 3600  # 1시간 단위 파일 롤링

_HEADER = ["timestamp_ms", "time",
           "posi_actual", "posi_target", "pres_actual", "pres_target", "pres_unit"]


class ChartRecorder:

    def __init__(self):
        self.start_time = time.time()  # 경과 시간 표시용 (패널이 읽는다)

        base_dir = os.path.join(tempfile.gettempdir(), "NVM2App", "chart_record")
        os.makedirs(base_dir, exist_ok=True)

        # 같은 초에 두 번 시작해도 폴더가 섞이지 않게 충돌 가드
        stamp = time.strftime("%Y%m%d_%H%M%S")
        self.record_dir = os.path.join(base_dir, f"record_{stamp}")
        seq = 1
        while os.path.exists(self.record_dir):
            self.record_dir = os.path.join(base_dir, f"record_{stamp}_{seq}")
            seq += 1
        os.makedirs(self.record_dir)

        self._file = None
        self._writer = None
        self._file_start = 0.0
        self._open_new_file()

    def _open_new_file(self):
        if self._file is not None:
            self._file.close()

        self._file_start = time.time()

        # 같은 초에 롤링되는 극단 상황에서 이전 파일을 덮어쓰지 않게 충돌 가드
        base = time.strftime("chart_%Y%m%d_%H%M%S", time.localtime(self._file_start))
        path = os.path.join(self.record_dir, base + ".csv")
        seq = 1
        while os.path.exists(path):
            path = os.path.join(self.record_dir, f"{base}_{seq}.csv")
            seq += 1

        self._file = open(path, "w", newline="", encoding="utf-8")
        self._writer = csv.writer(self._file)
        self._writer.writerow(_HEADER)

    def append(self, rows):
        """rows: (timestamp_ms, posi_act, posi_tgt, pres_act, pres_tgt, pres_unit) 목록."""
        if self._file is None:
            return

        if time.time() - self._file_start >= _FILE_ROTATE_SEC:
            self._open_new_file()

        for timestamp_ms, posi_act, posi_tgt, pres_act, pres_tgt, pres_unit in rows:
            time_str = (time.strftime("%H:%M:%S", time.localtime(timestamp_ms / 1000))
                        + f".{int(timestamp_ms % 1000):03d}")
            self._writer.writerow([timestamp_ms, time_str,
                                   self._fmt(posi_act), self._fmt(posi_tgt),
                                   self._fmt(pres_act), self._fmt(pres_tgt), pres_unit])

        self._file.flush()

    @staticmethod
    def _fmt(value):
        # 변환 불가 샘플(NaN — 컨버터 미준비 등)은 빈 칸으로 기록한다
        return "" if value != value else value

    def stop(self) -> str:
        """기록을 종료하고 임시 폴더 경로를 반환한다 (폴더 이동은 사용측 몫)."""
        if self._file is not None:
            self._file.close()
            self._file = None

        return self.record_dir
