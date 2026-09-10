import os, sys

# ftd2xx.dll 검색 경로 — 개발: 프로젝트 루트 / 배포(PyInstaller --onedir): exe 옆 _internal\
# (sys._MEIPASS 가 그 폴더를 가리킨다. build.bat 의 --add-binary 가 DLL 을 거기에 둔다)
_dll_dir = sys._MEIPASS if getattr(sys, "frozen", False) \
           else os.path.dirname(os.path.abspath(__file__))
os.add_dll_directory(_dll_dir)