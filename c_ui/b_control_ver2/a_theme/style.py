"""스타일 문자열 생성 헬퍼.

기존 코드에서 16곳에 복붙되어 있던 disabled 색상 계산 블록을 이 모듈로 통합.
(기존 코드는 alpha * 0.5 로 float alpha 를 만들어 QSS 파서에 취약했음 -> int 로 수정)
"""

from PySide6.QtGui import QColor

DISABLED_ALPHA_FACTOR = 0.5


def with_alpha(color: str, alpha: int) -> str:
    """색상 문자열 -> 'rgba(r, g, b, a)'. alpha 는 0~255 정수."""
    c = QColor(color)
    return f"rgba({c.red()}, {c.green()}, {c.blue()}, {alpha})"


def disabled(color: str) -> str:
    """disabled 상태용 반투명 색상 파생. 'transparent' 는 그대로 반환."""
    if color == "transparent":
        return color
    c = QColor(color)
    return with_alpha(color, int(c.alpha() * DISABLED_ALPHA_FACTOR))
