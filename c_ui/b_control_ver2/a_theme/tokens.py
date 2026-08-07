"""테마 토큰 정의.

기존 b_control_packet/base/my_style.py 의 평면 상수들을 의미 단위 토큰으로 재구성.
- 동일 값 상수는 하나의 토큰으로 통합 (예: ERR/DIRTY -> danger)
- 색상이 아닌 STYLE_LABEL_* int 상수는 base/labels.py 의 LabelRole 로 이동

사용 규칙:
- 위젯은 스타일 문자열을 만드는 시점에 tokens() 를 호출해서 읽는다.
- 토큰 값을 클래스 속성 등에 캐시하지 않는다. (테마 교체 시 stale 값 방지)
- set_theme() 는 앱 시작 시(위젯 생성 전) 한 번만 호출한다.
- 다크 모드 추가 시: DARK = ThemeTokens(...) 인스턴스를 정의하고 set_theme(DARK) 호출.
  (현재 main.py 의 qdarktheme.setup_theme("light") 와 병행 사용 중이므로,
   다크 적용 시 qdarktheme 설정도 함께 변경해야 한다)
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class ThemeTokens:
    # 기본 텍스트/테두리
    text: str = "#000000"                # 기본 글자색
    text_inverse: str = "#ffffff"        # 어두운 배경(툴바 등) 위 글자색
    border: str = "#dcdcdc"              # 기본 테두리
    border_hover: str = "#1a73e8"        # 호버 시 테두리
    border_focus: str = "#d4d4d4"        # 포커스 시 테두리
    pressed_bg: str = "#d4d4d4"          # 버튼 눌림 배경
    panel_bg: str = "#ffffff"            # 패널(카드) 배경
    progress_bg: str = "#e0e0e0"         # 프로그레스바 배경(빈 영역)
    progress_chunk: str = "#4a90e2"      # 프로그레스바 진행 막대

    # 상태
    danger: str = "#ff0000"              # 에러 + dirty 마커
    warning: str = "#ffa000"             # 경고
    success: str = "#3fb950"             # 체크 아이콘, 램프 ON 등

    # 선택 (콤보 팝업, 리스트)
    selection_text: str = "#1976d2"      # 선택 항목 글자색
    selection_bg: str = "#e3f2fd"        # 선택 항목 배경색
    popup_bg: str = "#ffffff"            # 콤보 팝업 배경

    # 연결 상태 배경
    status_ok_bg: str = "transparent"    # 연결됨
    status_bad_bg: str = "#ffebee"       # 연결 끊김

    # 에러 배지
    badge_error_bg: str = "#ffebee"
    badge_error_text: str = "#c62828"

    # 툴바
    toolbar_bg: str = "#24292e"
    toolbar_border: str = "#000000"
    toolbar_handle: str = "#8b949e"
    toolbar_hover: str = "#14ffffff"     # ARGB
    toolbar_disabled: str = "#7FFFFFFF"  # ARGB
    toolbar_separator: str = "#444d56"

    # 로그 뷰 카테고리 색 (밝은 배경 기준. 일반 INFO 로그는 기본 text 색 사용)
    log_tx: str = "#1976d2"              # 통신 TX 로그
    log_rx: str = "#2e7d32"              # 통신 RX 로그
    log_error: str = "#c62828"           # 오류 로그

    # 도메인 패널 (위치/압력 표시 박스)
    panel_posi_bg: str = "#f0f4f8"
    panel_posi_border: str = "#1565c0"
    panel_posi_text: str = "#0d47a1"
    panel_pres_bg: str = "#ffebee"
    panel_pres_border: str = "#d32f2f"
    panel_pres_text: str = "#c62828"
    


LIGHT = ThemeTokens()

_current: ThemeTokens = LIGHT


def tokens() -> ThemeTokens:
    """현재 테마 토큰 반환. 스타일 생성 시점마다 호출할 것."""
    return _current


def set_theme(theme: ThemeTokens) -> None:
    """테마 교체. 앱 시작 시(위젯 생성 전) 한 번만 호출."""
    global _current
    _current = theme
