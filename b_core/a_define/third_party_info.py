"""서드파티 구성 요소 목록 — Help > About 창의 라이선스 공시용.

배포 exe 에 실제로 포함되는 것만 올린다 (2026-09-10 조사: pip freeze + import
스캔 + a_assets + ftd2xx.dll). 전문은 a_assets/licenses/*.txt (qrc 에 포함 —
exe 내부에 들어가 지워지지 않는다) 에 있고, files 순서대로 이어 붙여 표시한다.

버전은 여기 적지 않고 실행 시점에 조회한다 (help_about_win) — 패키지를 올리면
목록을 고칠 필요가 없다. dist_name 이 importlib.metadata 조회 키다.

패키지를 추가/제거하면 이 목록과 resources.qrc, a_assets/licenses 를 함께 맞춘다.
"""

from typing import NamedTuple


class ThirdParty(NamedTuple):
    name: str                       # 표시 이름
    license_name: str               # 라이선스 식별자 (SPDX 표기 위주)
    copyright: str                  # 권리자 표기 (전문 상단에 함께 표시)
    files: tuple[str, ...]          # a_assets/licenses 안의 파일명 — 순서대로 이어 붙인다
    dist_name: str | None = None    # importlib.metadata 버전 조회 키. None 이면 버전 미표시
                                    # ("PySide6" / "python" 은 창에서 특수 처리)


THIRD_PARTIES: tuple[ThirdParty, ...] = (
    ThirdParty("Qt / PySide6", "LGPL-3.0",
               "Copyright (C) The Qt Company Ltd. and other contributors",
               ("qt_notice.txt", "LGPL-3.0.txt", "GPL-3.0.txt"), "PySide6"),
    ThirdParty("pyqtgraph", "MIT",
               "Copyright (c) 2012 University of North Carolina at Chapel Hill, Luke Campagnola",
               ("pyqtgraph.txt",), "pyqtgraph"),
    ThirdParty("NumPy", "BSD-3-Clause",
               "Copyright (c) 2005-2025, NumPy Developers",
               ("numpy.txt",), "numpy"),
    ThirdParty("pySerial", "BSD-3-Clause",
               "Copyright (c) 2001-2020 Chris Liechti",
               ("pyserial.txt",), "pyserial"),
    ThirdParty("PyQtDarkTheme (fork)", "MIT",
               "Copyright (c) 2021-2022 Yunosuke Ohsugi",
               ("pyqtdarktheme.txt",), "PyQtDarkTheme-fork"),
    ThirdParty("darkdetect", "BSD-3-Clause",
               "Copyright (c) 2019, Alberto Sottile",
               ("darkdetect.txt",), "darkdetect"),
    ThirdParty("ftd2xx (Python binding)", "MIT",
               "Copyright (c) 2019 Satya Mishra",
               ("ftd2xx.txt",), "ftd2xx"),
    ThirdParty("FTDI D2XX Driver (ftd2xx.dll)", "FTDI Driver Licence Terms",
               "Copyright (C) Future Technology Devices International Limited",
               ("ftdi_d2xx_driver.txt",)),
    ThirdParty("D2Coding Font", "SIL OFL 1.1",
               "Copyright (c) 2015 NAVER Corporation (NHN), with Reserved Font Name D2Coding. "
               "Font designed by FONTRIX Inc.",
               ("d2coding.txt",)),
    ThirdParty("Material Icons Font", "Apache-2.0",
               "Copyright 2018 Google, Inc.",
               ("material_icons.txt",)),
    ThirdParty("Python", "PSF-2.0",
               "Copyright (c) 2001 Python Software Foundation",
               ("python.txt",), "python"),
)
