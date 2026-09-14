import sys
import os
import ctypes
import dll_setup

# 1. 외부 라이브러리 및 자동 생성된 자원 임포트
import qdarktheme
import resources_rc  # qdarktheme와 함께 라이브러리성 그룹으로 묶음
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon, QFontDatabase, QFont

# 2. 프로젝트 내부 모듈 (정의된 경로 및 메인 윈도우)
from b_core.a_define import app_info
from b_core.a_define import file_folder_path as path_def
from b_core.c_manager.app_log_manager import AppLogManager
from b_core.c_manager.parameter_manager import ParamManager
from c_ui.c_window_ver2.a_main.main_win import MainWin
from c_ui.c_window_ver2.x_message.startup_message_box import show_schema_load_error


def setup_fonts(app):
    """
    애플리케이션 전역에서 사용할 외부 폰트들을 로드하고 초기 설정을 수행합니다.
    """
    log = AppLogManager().get_logger("App", is_global=True)

    # 1. 일반 텍스트용 D2Coding 폰트 설정
    font_id = QFontDatabase.addApplicationFont(path_def.ASSET_COMMON_FONT_FILE)
    if font_id != -1:
        font_families = QFontDatabase.applicationFontFamilies(font_id)
        if font_families:
            # 기본 폰트 패밀리 지정 (폰트 크기: 12px)
            custom_font = QFont(font_families[0])
            custom_font.setPixelSize(14)
            app.setFont(custom_font)
    else:
        log.error(f"기본 폰트 로드 실패: {path_def.ASSET_COMMON_FONT_FILE}")

    # 2. 아이콘 표시용 Material Icons 폰트 등록
    # UI 요소에서 아이콘 텍스트를 렌더링할 때 필요합니다.
    if QFontDatabase.addApplicationFont(path_def.ASSET_ICON_FONT_FILE) == -1:
        log.error(f"아이콘 폰트 로드 실패: {path_def.ASSET_ICON_FONT_FILE}")

def main():
    """
    애플리케이션 메인 엔트리 포인트
    """
    # [Step 1] Windows 작업 표시줄 전용 아이콘 설정
    # 애플리케이션 ID를 명시적으로 설정하여 파이썬 기본 아이콘과 분리합니다.
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_info.APP_USER_MODEL_ID)
    except Exception:
        pass

    # [Step 2] QApplication 인스턴스 생성 및 앱 메타데이터 설정
    app = QApplication(sys.argv)
    app.setApplicationName(app_info.APP_NAME)
    app.setApplicationVersion(app_info.APP_VERSION)
    app.setOrganizationName(app_info.APP_COMPANY)

    # stderr 후킹 후 시작 로그 — 로그 파일만 봐도 실행 버전을 알 수 있게 한다
    AppLogManager().install_stderr_hook()
    AppLogManager().get_logger("App", is_global=True).info(f"===== {app_info.APP_DISPLAY_TITLE} started =====")

    # [Step 3] 전역 테마 설정 (qDarkTheme)
    # 애플리케이션 전체에 일관된 밝은 테마(Light Mode)를 적용합니다.
    qdarktheme.setup_theme("light")

    # [Step 4] 앱 공통 리소스 및 환경 설정
    # - 앱 타이틀 바 및 작업 표시줄 아이콘 설정
    app.setWindowIcon(QIcon(path_def.ASSET_APP_ICON_FILE))
    
    # - 폰트 로드 및 적용
    setup_fonts(app)

    # [Step 5] 코어 초기화 — 창 생성 전에 param 스키마와 전송 규약(SpecRegistry)을 로드한다.
    # 스키마 파일(params.json / nv2_spec.json)이 없거나 깨졌거나 서로 맞지 않으면 창을 만들지
    # 않고 대화상자로 알린 뒤 종료한다 — 손상된 스키마로 잘못된 값을 표시/전송하거나
    # 창 생성 중 예외로 조용히 죽는 것을 막는다 (2026-09-14 사용자 결정).
    param_manager = ParamManager()
    if param_manager.load_errors:
        log = AppLogManager().get_logger("App", is_global=True)
        log.error(f"param 스키마 오류 {len(param_manager.load_errors)}건 — 기동 중단")
        show_schema_load_error(None,
                               [path_def.RSRC_PARAMS_JSON_FILE, path_def.RSRC_NV2_SPEC_JSON_FILE],
                               param_manager.load_errors)
        sys.exit(1)

    # [Step 6] 메인 윈도우 초기화 및 실행
    window = MainWin()
    window.show()
    
    # [Step 7] 앱 종료 이벤트 핸들링
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
