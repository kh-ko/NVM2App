import sys
import os
import ctypes

# 1. 외부 라이브러리 및 자동 생성된 자원 임포트
import qdarktheme
import resources_rc  # qdarktheme와 함께 라이브러리성 그룹으로 묶음
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon, QFontDatabase, QFont

# 2. 프로젝트 내부 모듈 (정의된 경로 및 메인 윈도우)
from b_core.a_define import file_folder_path as path_def
from c_ui.c_windows.a_main.main_win import MainWin


def setup_fonts(app):
    """
    애플리케이션 전역에서 사용할 외부 폰트들을 로드하고 초기 설정을 수행합니다.
    """
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
        print(f"[경고] 기본 폰트 로드 실패: {path_def.ASSET_COMMON_FONT_FILE}")

    # 2. 아이콘 표시용 Material Icons 폰트 등록
    # UI 요소에서 아이콘 텍스트를 렌더링할 때 필요합니다.
    if QFontDatabase.addApplicationFont(path_def.ASSET_ICON_FONT_FILE) == -1:
        print(f"[경고] 아이콘 폰트 로드 실패: {path_def.ASSET_ICON_FONT_FILE}")

def main():
    """
    애플리케이션 메인 엔트리 포인트
    """
    # [Step 1] Windows 작업 표시줄 전용 아이콘 설정
    # 애플리케이션 ID를 명시적으로 설정하여 파이썬 기본 아이콘과 분리합니다.
    try:
        myappid = 'company.nvm2app.1.0.0'
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
    except Exception:
        pass

    # [Step 2] QApplication 인스턴스 생성
    app = QApplication(sys.argv)

    # [Step 3] 전역 테마 설정 (qDarkTheme)
    # 애플리케이션 전체에 일관된 밝은 테마(Light Mode)를 적용합니다.
    qdarktheme.setup_theme("light")

    # [Step 4] 앱 공통 리소스 및 환경 설정
    # - 앱 타이틀 바 및 작업 표시줄 아이콘 설정
    app.setWindowIcon(QIcon(path_def.ASSET_APP_ICON_FILE))
    
    # - 폰트 로드 및 적용
    setup_fonts(app)

    # [Step 5] 메인 윈도우 초기화 및 실행
    window = MainWin()
    window.show()
    
    # [Step 6] 앱 종료 이벤트 핸들링
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
