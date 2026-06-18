from PySide6.QtWidgets import QToolBar, QToolButton, QMenu
from PySide6.QtGui import QAction
from PySide6.QtCore import Qt

from c_ui.b_control_packet.base import my_style

class BaseToolBar(QToolBar):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMovable(False)   
        self.setFloatable(False) 
        self.set_color()

        self._actions = {}

    def set_color(self):
        ext_icon_text = "\ue5cc"  

        # 2. 스타일시트 적용
        self.setStyleSheet(f"""
            QToolBar {{
                background-color: {my_style.STYLE_TOOLBAR_BG_COLOR};
                border: 1px solid {my_style.STYLE_TOOLBAR_BOLDER_COLOR};
                spacing: 4px; 
                padding: 2px;
                min-height: 30px;
            }}
            
            /* ---- 이동 손잡이(Handle) 색상 및 형태 직접 제어 ---- */
            
            /* 가로 툴바 핸들 (두 줄의 세로선으로 표현) */
            QToolBar::handle:horizontal {{
                image: none; /* 기본 점 무늬 제거 */
                width: 2px;
                margin: 4px 8px; /* 핸들 주변 여백 */
                border-left: 1px solid {my_style.STYLE_TOOLBAR_HANDLE_COLOR};
                border-right: 1px solid {my_style.STYLE_TOOLBAR_HANDLE_COLOR};
            }}
            
            /* 세로 툴바 핸들 (툴바가 좌/우에 도킹될 경우를 대비) */
            QToolBar::handle:vertical {{
                image: none;
                height: 2px;
                margin: 8px 4px;
                border-top: 1px solid {my_style.STYLE_TOOLBAR_HANDLE_COLOR};
                border-bottom: 1px solid {my_style.STYLE_TOOLBAR_HANDLE_COLOR};
            }}
            
            /* ---------------------------------------------------- */
            
            QToolButton[menuBtn="true"] {{
                background: transparent;
                border: none;
                border-radius: 4px;
                padding: 6px;
                color: white; 
            }}
            
            QToolButton[menuBtn="true"]:hover {{
                background-color: {my_style.STYLE_TOOLBAR_HOVER_COLOR}; 
            }}

            QToolButton[menuBtn="true"]:disabled {{
                color: {my_style.STYLE_TOOLBAR_DISABLE_COLOR};
            }}
            
            QToolButton[menuBtn="true"]::menu-indicator {{
                image: none; /* 드롭다운 기본 화살표 아이콘 제거 (원할 경우 생략 가능) */
            }}
            
            QToolButton {{
                color: white;              /* 글자 색상을 흰색으로 설정 */
                background: transparent;   /* 배경은 투명하게 */
                border: none;              /* 테두리 제거 */
                padding: 8px 12px;         /* 클릭 영역 및 툴바 높이 확보를 위한 패딩 */
                border-radius: 4px;        /* 둥근 모서리 */
            }}

            /* 마우스가 올라갔을 때(Hover)의 효과 */
            QToolButton:hover {{
                background-color: {my_style.STYLE_TOOLBAR_HOVER_COLOR}; 
            }}

            QToolButton:disabled {{
                color: {my_style.STYLE_TOOLBAR_DISABLE_COLOR};
                background: transparent; /* hover 효과 무시 */
            }}

            QToolButton#qt_toolbar_ext_button {{
                qproperty-toolButtonStyle: ToolButtonTextOnly;
                qproperty-text: "{ext_icon_text}";
                font-family: "Material Icons";
                font-size: 18px;
                background: transparent;
                border: none;
                color: white;
                padding: 0px; 
                margin: 0px;
            }}

            QToolBar::separator {{
                width: 1px;
                background-color: {my_style.STYLE_TOOLBAR_SEPARATOR_COLOR};
                margin: 6px 4px; 
            }}
            
            /* ---- 하위 메뉴 (QMenu) 스타일 ---- */
            QMenu {{
                background-color: {my_style.STYLE_TOOLBAR_BG_COLOR};
                color: white;
                border: 1px solid {my_style.STYLE_TOOLBAR_BOLDER_COLOR};
                padding: 4px 0px;
            }}
            
            QMenu::item {{
                padding: 6px 24px;
                background-color: transparent;
            }}
            
            QMenu::item:selected {{
                background-color: {my_style.STYLE_TOOLBAR_HOVER_COLOR}; /* 마우스 오버 시 색상 */
            }}

            QMenu::item:disabled {{
                color: {my_style.STYLE_TOOLBAR_DISABLE_COLOR};
            }}
            
            QMenu::separator {{
                height: 1px;
                background-color: {my_style.STYLE_TOOLBAR_SEPARATOR_COLOR};
                margin: 4px 0px;
            }}
        """)

    def add_action(self, name, slot):
        action = self.addAction(name)
        action.triggered.connect(slot)
        self._actions[name] = action

    def remove_action(self, name):
        if name in self._actions:
            self.removeAction(self._actions[name])
            del self._actions[name]

    def set_action_enabled(self, name, enabled):
        # 딕셔너리에 해당 이름의 액션이 존재하는지 확인
        if name in self._actions:
            self._actions[name].setEnabled(enabled)