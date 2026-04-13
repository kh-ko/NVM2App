import os
import sys

# Qt 리소스 시스템 베이스 경로 (qrc 파일에 설정된 prefix/폴더 구조에 맞춤)
# OS에 상관없이 무조건 슬래시(/)를 사용합니다.
ASSET_BASE = ":/a_assets"

# 하위 폴더 경로
ASSET_FONTS = f"{ASSET_BASE}/fonts"
ASSET_COMMON_FONT_FILE = f"{ASSET_FONTS}/D2Coding.ttf"
ASSET_ICON_FONT_FILE = f"{ASSET_FONTS}/MaterialIcons-Regular.ttf"

ASSET_ICON = f"{ASSET_BASE}/icons"
ASSET_APP_ICON_FILE = f"{ASSET_ICON}/nova_icon.ico"



# 배포파일에 폴더 형태로 추가되는 리소스파일 경로
if getattr(sys, 'frozen', False):
    # exe 파일로 실행될 때의 디렉토리
    EXE_BASE = os.path.dirname(sys.executable)
else:
    # 파이썬 스크립트로 실행될 때의 최상위 디렉토리
    # (주의: 현재 이 경로 관리 파일이 최상단 폴더에 있다고 가정합니다. 
    # 만약 a_global 같은 하위 폴더에 있다면 os.path.join(..., "..", "..") 등으로 루트를 맞춰주세요)
    EXE_BASE = os.path.abspath(os.path.dirname(sys.argv[0]))
    # ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")) # 하위 폴더일 경우 예시

# 로컬 베이스 폴더
RSRC_BASE = os.path.join(EXE_BASE, "2_resource")

RSRC_CONFIG_PATH = os.path.join(RSRC_BASE, "config")
RSRC_CONNECTIONS_JSON_FILE = os.path.join(RSRC_CONFIG_PATH, "connections.json")