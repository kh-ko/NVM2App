# 앱 메타데이터 정의 — About 창 / 타이틀바 / QApplication 메타데이터가 이 값을 쓴다.
# 회사 표기(APP_COMPANY / APP_HOMEPAGE / APP_CONTACT)는 확정되면 값만 바꿔 빌드한다.
APP_NAME = "NVM2 Application"
APP_VERSION = "0.0.1"  # 순수 버전만 저장 (표시용 "v" 접두는 APP_DISPLAY_TITLE 에서 붙임)
APP_BUILD_DATE = ""    # build.bat 이 빌드 시 "YYYY-MM-DD" 를 주입한다. 개발 실행(소스)이면 빈 문자열

APP_COMPANY = "Novasen Co., Ltd"
APP_HOMEPAGE = "https://www.novasen.net/"
APP_CONTACT = ""       # 문의처 (이메일/전화 등). 비어 있으면 About 창에 표시하지 않는다

# 저작권 표기: "Copyright © <최초 공개 연도> <권리자>. All rights reserved."
# 연도는 저작물이 처음 공개된 해다 (매년 갱신하지 않아도 된다. 갱신하려면 "2026-2027" 형식)
APP_COPYRIGHT_YEAR = "2026"
# 회사명이 "Ltd." 처럼 마침표로 끝나면 마침표를 겹치지 않게 한다
APP_COPYRIGHT = f"Copyright © {APP_COPYRIGHT_YEAR} {APP_COMPANY.rstrip('.')}. All rights reserved."

# Windows 작업표시줄 앱 식별자 (AppUserModelID)
# 버전을 포함하지 않는다 — 포함하면 버전 업마다 작업표시줄 그룹/고정 핀이 초기화됨
APP_USER_MODEL_ID = "novasen.nvm2app"

# 전체 타이틀 포맷 조합
# 반환 예: NVM2 Application - v0.0.1
APP_DISPLAY_TITLE = f"{APP_NAME} - v{APP_VERSION}"
