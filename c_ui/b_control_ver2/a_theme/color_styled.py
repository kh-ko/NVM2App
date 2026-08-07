"""테마 소비 계약: 위젯이 테마를 어떻게 입는가.

theme 패키지 구성:
- tokens.py       어떤 색이 존재하는가 (데이터)
- style.py        색 파생 헬퍼 (disabled 등 순수 함수)
- color_styled.py 위젯이 색을 적용/변경하는 공통 계약 (이 파일)

ColorStyled 는 Qt 를 import 하지 않는 순수 믹스인이다. QWidget 서브클래스와
다중상속되어 self.setStyleSheet 를 덕타이핑으로 사용한다.

기존 b_control_packet 의 set_color() 는 클래스마다 시그니처가 4가지였고
(인자 0~3개, BaseGroupBox 는 첫 인자가 border 색), disabled 색 계산이
16곳에 복붙되어 있었다. ver2 는 이 믹스인 하나로 통일한다.
"""

from dataclasses import dataclass, replace


@dataclass
class WidgetColors:
    text: str = ""              # 글자색
    border: str = ""            # 테두리색
    bg: str = "transparent"     # 배경색
    hover_border: str = ""      # 호버 시 테두리색
    focus_border: str = ""      # 포커스 시 테두리색


class ColorStyled:
    """QWidget 서브클래스와 다중상속으로 사용하는 색상 스타일 믹스인.

    규칙:
    - set_colors(): None 인자는 '현재 값 유지'. 호출할 때마다 전체 스타일시트 재생성.
    - disabled 색상은 theme.style.disabled() 로 항상 자동 파생한다. (직접 지정 불가)
    - set_border_enabled(False): 평시/disabled 테두리만 투명 처리.
      hover/focus 테두리까지 없애려면 set_colors(hover_border="transparent",
      focus_border="transparent") 를 병행할 것. (테두리 없는 버튼도 호버 피드백은
      유지하는 기존 동작과, 완전 무테두리 스핀박스 동작을 모두 표현하기 위함)
    - 서브클래스는 _build_qss() 를 구현한다. QSS 선택자는 반드시 구체 타입명을
      사용한다. ('*' 금지 — 자식 위젯까지 새어나감. 타입명 선택자는 파생 클래스에도
      매칭되므로 서브클래스에서 재정의할 필요 없음)
    """

    def _init_colors(self, colors: WidgetColors, border_enabled: bool = True) -> None:
        """__init__ 마지막에 호출. 초기 색상 상태 저장 + 첫 스타일 적용."""
        self._colors = colors
        self._border_enabled = border_enabled
        self._apply_style()

    def set_colors(self, *, text: str | None = None, border: str | None = None,
                   bg: str | None = None, hover_border: str | None = None,
                   focus_border: str | None = None) -> None:
        kwargs = {k: v for k, v in dict(text=text, border=border, bg=bg,
                                        hover_border=hover_border,
                                        focus_border=focus_border).items()
                  if v is not None}
        self._colors = replace(self._colors, **kwargs)
        self._apply_style()

    def set_border_enabled(self, enabled: bool) -> None:
        self._border_enabled = enabled
        self._apply_style()

    def _effective_border(self) -> str:
        return self._colors.border if self._border_enabled else "transparent"

    def _apply_style(self) -> None:
        self.setStyleSheet(self._build_qss(self._colors))  # type: ignore[attr-defined]

    def _build_qss(self, c: WidgetColors) -> str:
        raise NotImplementedError
