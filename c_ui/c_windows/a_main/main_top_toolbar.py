from PySide6.QtWidgets import QToolBar, QToolButton, QMenu
from PySide6.QtGui import QAction
from PySide6.QtCore import Qt

from c_ui.b_components.a_custom.custom_lamp_tool_button import CustomLampToolButton

class MainTopToolBar(QToolBar):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMovable(True)   
        self.setFloatable(True) 
        
        self.local_btn = CustomLampToolButton(self)
        self.local_btn.setText("Local")
        self.local_btn.set_accent(False)
        self.addWidget(self.local_btn)

        self.remote_btn = CustomLampToolButton(self)
        self.remote_btn.setText("Remote")
        self.remote_btn.set_accent(False)
        self.addWidget(self.remote_btn)

        self.addSeparator()
        # 1. Connection 툴버튼 생성
        self.conn_btn = QToolButton(self)
        self.conn_btn.setText("Connection")
        self.conn_btn.setProperty("menuBtn", "true") # 커스텀 CSS(마우스 오버 등) 적용
        self.conn_btn.setPopupMode(QToolButton.InstantPopup) # 클릭 시 즉시 메뉴 펼침

        self.action_refresh = QAction("Refresh", self)
        self.addAction(self.action_refresh)

        # 2. 하위 메뉴(QMenu) 생성
        self.conn_menu = QMenu(self.conn_btn)

        # 3. 메뉴에 들어갈 액션 생성 (외부 윈도우에서 이벤트를 연결할 수 있도록 self로 선언)
        self.action_connect = QAction("Connect", self)
        self.action_disconnect = QAction("Disconnect", self)
        self.action_settings = QAction("Settings", self)

        # 4. 메뉴에 액션 및 구분선 조립
        self.conn_menu.addAction(self.action_connect)
        self.conn_menu.addAction(self.action_disconnect)
        self.conn_menu.addSeparator() # Settings 전에 가로 구분선 추가
        self.conn_menu.addAction(self.action_settings)

        # 5. 완성된 메뉴를 툴버튼에 달고, 툴바에 위젯으로 추가
        self.conn_btn.setMenu(self.conn_menu)
        self.addWidget(self.conn_btn)

        self.__color_design()

    def __color_design(self):
        # 1. 여기서 모든 색상을 동적으로 제어합니다.
        bg_color = "#24292e"      
        border_color = "#000000"  
        handle_color = "#8b949e"  # 이동 핸들의 색상 (배경에 맞게 설정)
        
        separator_color = "#444d56"   
        btn_hover_color = "#14ffffff" 
        ext_icon_text = "\ue5cc"  

        # 2. 스타일시트 적용
        self.setStyleSheet(f"""
            QToolBar {{
                background-color: {bg_color};
                border: 1px solid {border_color};
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
                border-left: 1px solid {handle_color};
                border-right: 1px solid {handle_color};
            }}
            
            /* 세로 툴바 핸들 (툴바가 좌/우에 도킹될 경우를 대비) */
            QToolBar::handle:vertical {{
                image: none;
                height: 2px;
                margin: 8px 4px;
                border-top: 1px solid {handle_color};
                border-bottom: 1px solid {handle_color};
            }}
            
            /* ---------------------------------------------------- */
            
            QToolButton {{
                background: transparent;
                border: none;
                border-radius: 4px;
                padding: 6px;
                color: white; 
            }}
            
            QToolButton:hover {{
                background-color: {btn_hover_color}; 
            }}
            
            QToolButton::menu-indicator {{
                image: none; /* 드롭다운 기본 화살표 아이콘 제거 (원할 경우 생략 가능) */
            }}
            
            QToolButton#qt_toolbar_ext_button {{
                qproperty-toolButtonStyle: ToolButtonTextOnly;
                qproperty-text: "{ext_icon_text}";
                font-family: "Material Icons";
                font-size: 18px;
                background: transparent;
                border: none;
                color: white;
            }}

            QToolBar::separator {{
                width: 1px;
                background-color: {separator_color};
                margin: 6px 4px; 
            }}
            
            /* ---- 하위 메뉴 (QMenu) 스타일 ---- */
            QMenu {{
                background-color: {bg_color};
                color: white;
                border: 1px solid {border_color};
                padding: 4px 0px;
            }}
            
            QMenu::item {{
                padding: 6px 24px;
                background-color: transparent;
            }}
            
            QMenu::item:selected {{
                background-color: {btn_hover_color}; /* 마우스 오버 시 색상 */
            }}
            
            QMenu::separator {{
                height: 1px;
                background-color: {separator_color};
                margin: 4px 0px;
            }}
        """)

    def reg_local_btn_slot(self, slot):
        self.local_btn.clicked.connect(slot, Qt.QueuedConnection)

    def reg_remote_btn_slot(self, slot):
        self.remote_btn.clicked.connect(slot, Qt.QueuedConnection)

    def reg_connection_refresh_slot(self, slot):
        self.action_refresh.triggered.connect(slot, Qt.QueuedConnection)

    def reg_connection_connect_slot(self, slot):
        self.action_connect.triggered.connect(slot, Qt.QueuedConnection)
    
    def reg_connection_disconnect_slot(self, slot):
        self.action_disconnect.triggered.connect(slot, Qt.QueuedConnection)
    
    def reg_connection_settings_slot(self, slot):
        self.action_settings.triggered.connect(slot, Qt.QueuedConnection)