# 앱 메타데이터 정의
APP_NAME = "NVM2 Application"
APP_VERSION = "0.0.1"  # 순수 버전만 저장 (표시용 "v" 접두는 APP_DISPLAY_TITLE 에서 붙임)
APP_AUTHOR = "novasen"
APP_COPYRIGHT = "Copyright © 2026 company Inc. All rights reserved."  # TODO: 회사 표기 확정 필요

# Windows 작업표시줄 앱 식별자 (AppUserModelID)
# 버전을 포함하지 않는다 — 포함하면 버전 업마다 작업표시줄 그룹/고정 핀이 초기화됨
APP_USER_MODEL_ID = "novasen.nvm2app"

# 전체 타이틀 포맷 조합
# 반환 예: NVM2 Application - v0.0.1
APP_DISPLAY_TITLE = f"{APP_NAME} - v{APP_VERSION}"
