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

ASSET_IMG = f"{ASSET_BASE}/images"
ASSET_FU_GUIDE_1_IMG_FILE = f"{ASSET_IMG}/fu_guide_1.png"
ASSET_FU_GUIDE_2_IMG_FILE = f"{ASSET_IMG}/fu_guide_2.png"
ASSET_FU_GUIDE_3_IMG_FILE = f"{ASSET_IMG}/fu_guide_3.png"
ASSET_FU_GUIDE_4_IMG_FILE = f"{ASSET_IMG}/fu_guide_4.png"
ASSET_FU_GUIDE_5_IMG_FILE = f"{ASSET_IMG}/fu_guide_5.png"
ASSET_RS232_IMG_FILE = f"{ASSET_IMG}/rs232_port.png"
ASSET_USB_IMG_FILE = f"{ASSET_IMG}/usb_port.png"



# 배포파일에 폴더 형태로 추가되는 리소스파일 경로
if getattr(sys, 'frozen', False):
    # exe 파일로 실행될 때: exe 가 있는 디렉토리 (exe 옆에 2_resource 배포)
    EXE_BASE = os.path.dirname(sys.executable)
else:
    # 파이썬 스크립트로 실행될 때: 이 파일(b_core/a_define/) 기준 2단계 상위 = 프로젝트 루트.
    # sys.argv[0] 기반은 실행 방식(IDE 러너, 다른 CWD, python -m 등)에 따라 틀어지므로
    # 파일 자신의 위치를 기준으로 계산한다.
    EXE_BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

# 로그 폴더 
LOG_PATH = os.path.join(EXE_BASE, "3_log")

# 로컬 리소스 베이스 폴더
RSRC_BASE = os.path.join(EXE_BASE, "2_resource")

RSRC_CONFIG_PATH = os.path.join(RSRC_BASE, "config")
RSRC_CONNECTIONS_JSON_FILE = os.path.join(RSRC_CONFIG_PATH, "connections.json")
RSRC_LOCAL_SETTING_JSON_FILE = os.path.join(RSRC_CONFIG_PATH, "local_setting.json")
RSRC_FTP_SETTING_FILE = os.path.join(RSRC_CONFIG_PATH, "ftp_connection.json")



RSRC_TEMP_PATH = os.path.join(RSRC_BASE, "temp")
RSRC_APP_CPU1_NEW_FILE    = os.path.join(RSRC_TEMP_PATH, "fcpuan.dlla")
RSRC_APP_CPU2_NEW_FILE    = os.path.join(RSRC_TEMP_PATH, "fcpubn.dlla")
RSRC_APP_CPU1_FILE        = os.path.join(RSRC_TEMP_PATH, "fcpua.dlla")
RSRC_APP_CPU2_FILE        = os.path.join(RSRC_TEMP_PATH, "fcpub.dlla")
RSRC_KERNEL_CPU1_FILE     = os.path.join(RSRC_TEMP_PATH, "fknlcp1.dlla")
RSRC_KERNEL_CPU2_FILE     = os.path.join(RSRC_TEMP_PATH, "fknlcp2.dlla")

RSRC_PARAM_SCHEMA_PATH = os.path.join(RSRC_BASE, "param_schema")
RSRC_PARAM_SCHEMA_JSON_FILE = os.path.join(RSRC_PARAM_SCHEMA_PATH, "param.json")

RSRC_TEMPLATE_PATH = os.path.join(RSRC_BASE, "template")
RSRC_TEMPLATE_EDS_FILE = os.path.join(RSRC_TEMPLATE_PATH, "eds_sample_v2.txt")
RSRC_TEMPLATE_ETHERCAT_XML_FILE = os.path.join(RSRC_TEMPLATE_PATH, "ethercat_sample.XML")