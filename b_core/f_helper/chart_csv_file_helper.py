"""차트 CSV 파일 헬퍼 — 차트 기록 CSV 포맷의 소유자 (쓰기 + 읽기 + 헤더 정의).

[f_helper 폴더 규칙] UI(Qt) 무관 보조 기능을 담는다 — 순수 함수 모듈
(float_util 등)이든 세션 객체(이 클래스처럼 생성되고 수명이 끝나는)든 좋다.
단, 여러 곳이 공유하는 앱 수명 상태(싱글턴)가 되는 순간 c_manager 로 승격할 것.
(b_core 폴더 접두사는 가독성 정렬용이며 의존 규칙이 아니다 — 어느 층이든 참조 가능)

쓰기 (인스턴스 — 기록 세션):
- 생성 = 기록 시작. 임시 폴더(%TEMP%/NVM2App/chart_record/record_<시작시각>)에
  기록하고, 파일은 파일 시작 시각 기준 1시간마다 롤링한다 (chart_YYYYMMDD_HHMMSS.csv).
- 값은 차트에 그려지는 표시(dp) 단위 그대로이며, 압력은 행마다 표시 단위
  컬럼(pres_unit)을 함께 기록한다 — 기록 중 단위가 바뀌어도 행 단위로
  자기 기술적(self-describing)이라 혼선이 없다.
- 매 append(200ms 배치)마다 flush — 비정상 종료 시에도 직전 배치까지 보존된다.
- 저장 위치 확정(다이얼로그/이동)은 사용측(차트 패널) 몫이다. stop() 은
  파일만 닫고 임시 폴더 경로를 돌려준다.

읽기 (정적 — 기록 세션과 무관):
- read_csv_files() 가 파싱/다중 파일 병합/timestamp 정렬/단위 코드 변환을
  담당한다. 값은 기록 당시 표시 단위 그대로 반환하며, 단위 해석·변환
  (캐노니컬화 등)은 호출측(차트 분석 윈도우) 몫이다 — 압력 단위 환산표가
  c_ui(a_converter) 소속이라 b_core 에서는 변환하지 않는다.
"""

import csv
import os
import tempfile
import time

import numpy as np

from b_core.b_datatype import param_enum as p_enum

_FILE_ROTATE_SEC = 3600  # 1시간 단위 파일 롤링


class ChartCSVFileHelper:

    # 기록/판독이 공유하는 CSV 컬럼 정의 (이 포맷의 단일 출처)
    CSV_HEADER = ["timestamp_ms", "time",
                  "posi_actual", "posi_target", "pres_actual", "pres_target", "pres_unit"]

    # ------------------------------------------------------------ 쓰기 (기록 세션)
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
        self._writer.writerow(self.CSV_HEADER)

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

    # ------------------------------------------------------------ 읽기 (정적)
    @staticmethod
    def read_csv_files(paths):
        """기록된 CSV(들)를 읽어 timestamp 순으로 병합해 반환한다.

        반환: (timestamps_ms, posi_act, posi_tgt, pres_act, pres_tgt, unit_codes)
        - 전부 numpy 배열. 값은 기록 당시 표시 단위 그대로 (변환은 호출측 몫)
        - unit_codes: 행별 SensUnitEnum 값, 해석 불가 단위는 -1
        - 빈 값("")은 NaN
        헤더 불일치/데이터 없음이면 ValueError."""
        rows = []

        for path in paths:
            with open(path, newline="", encoding="utf-8") as f:
                reader = csv.reader(f)
                header = next(reader, None)
                if header != ChartCSVFileHelper.CSV_HEADER:
                    raise ValueError(f"unexpected csv header: {os.path.basename(path)}")

                for row in reader:
                    unit_member = p_enum.SensUnitEnum.from_desc(row[6])
                    unit = unit_member.value if unit_member else -1
                    values = [float(v) if v != "" else float("nan") for v in row[2:6]]
                    rows.append((int(row[0]), *values, unit))

        if not rows:
            raise ValueError("no data rows in selected csv")

        rows.sort(key=lambda r: r[0])
        data = np.array(rows, dtype=float)
        return (data[:, 0], data[:, 1], data[:, 2], data[:, 3], data[:, 4],
                data[:, 5].astype(int))
