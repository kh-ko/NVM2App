"""연결 설정(connections.json) 관리자.

기존에는 ConnectionConnectWin / ConnectionSettingWin 이 각자 json 파일을
읽고 쓰면서 로드/저장/기본값 생성/선택(isSelect) 코드가 중복되어 있었다.
ver2 는 이 매니저가 파일 IO 와 목록 관리를 전담하고, 윈도우 레이어는
조회/변경 호출과 사용자 메시지(QMessageBox) 표시만 담당한다.

- 변경 메서드(select / add / update / remove)는 내부에서 저장까지 수행하고
  성공 여부를 반환한다. 저장 실패 시 메모리 상태를 롤백한다.
- 항목 구성이 바뀌면 sig_list_changed, 선택이 바뀌면 sig_selection_changed
  가 발생한다. (두 윈도우가 동시에 열려 있어도 목록이 동기화됨)
- get() / selected() 는 복사본을 반환한다 — 항목 수정은 반드시 update() 로.
"""

import threading
import json
import os

from PySide6.QtCore import Signal, QObject

from b_core.a_define import file_folder_path as path_def
from b_core.c_manager.app_log_manager import AppLogManager


class ConnectionSettingManager(QObject):
    _instance = None
    _creation_lock = threading.Lock()

    sig_list_changed = Signal()          # 항목 추가/삭제/내용 변경
    sig_selection_changed = Signal(int)  # 선택(isSelect) 항목 변경

    _DEFAULT_CONNECTION = {
        "name": "default",
        "network": 0,      # 네트워크 방식(0=RS232, 1=RS485, 2=TCP/IP) - 현재 0번만 사용 가능
        "address": "",     # 연결 주소 - 현재 사용 안함
        "baudrate": 38400, # 통신 속도(9600~115200)
        "dataBits": 7,     # 데이터 비트(5~8)
        "parity": 2,       # 패리티 비트(0=NoParity, 2=EvenParity, 3=OddParity, 4=SpaceParity, 5=MarkParity)
        "stopBits": 1,     # 정지 비트(1=OneStop, 2=TwoStop, 3=OneAndHalfStop)
        "termination": 0,  # 종료 문자(0=CR+LF, 1=LF, 2=CR)
        "isSelect": True,
    }

    def __new__(cls, *args, **kwargs):
        # 멀티스레드 환경에서 동시에 생성되는 것을 방지
        with cls._creation_lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        # 중복 초기화 방어
        if self._initialized:
            return

        super().__init__()

        self._initialized = True

        self._log = AppLogManager().get_logger("ConnectionSettingManager", is_global=True)
        self._connections: list[dict] = []
        self._load()

    # ------------------------------------------------------------ 조회
    def count(self) -> int:
        return len(self._connections)

    def names(self) -> list[str]:
        return [item.get("name", "Unknown") for item in self._connections]

    def get(self, index: int) -> dict | None:
        """index 항목의 복사본 반환. 범위를 벗어나면 None."""
        if index < 0 or index >= len(self._connections):
            return None
        return dict(self._connections[index])

    def selected_index(self) -> int:
        for i, item in enumerate(self._connections):
            if item.get("isSelect", False):
                return i
        return 0 if self._connections else -1

    def selected(self) -> dict | None:
        """현재 선택된 설정의 복사본 반환 (스캔/포트 open 용)."""
        return self.get(self.selected_index())

    # ------------------------------------------------------------ 변경
    def select(self, index: int) -> None:
        """index 항목을 선택(isSelect) 상태로 만들고 저장한다."""
        if index < 0 or index >= len(self._connections):
            return
        if index == self.selected_index():
            return

        for i, item in enumerate(self._connections):
            item["isSelect"] = (i == index)

        self._save()
        self.sig_selection_changed.emit(index)

    def add(self, data: dict) -> str | None:
        """항목 추가. 이름이 비어 있으면 기본 이름, 중복이면 _N 접미사를 붙인다.

        성공 시 확정된 이름, 저장 실패 시 None 을 반환한다."""
        base_name = str(data.get("name", "")).strip() or "New_Connection"

        new_name = base_name
        counter = 1
        while new_name in self.names():
            new_name = f"{base_name}_{counter}"
            counter += 1

        new_data = dict(data)
        new_data["name"] = new_name
        new_data["isSelect"] = False
        self._connections.append(new_data)

        if not self._save():
            self._connections.pop()
            return None

        self.sig_list_changed.emit()
        return new_name

    def update(self, index: int, data: dict) -> bool:
        """index 항목 내용 교체. 이름이 비었거나 다른 항목과 중복이면 실패.

        선택 상태(isSelect)는 update 로 바꿀 수 없다 — select() 를 사용할 것."""
        if index < 0 or index >= len(self._connections):
            return False

        new_name = str(data.get("name", "")).strip()
        if not new_name:
            return False
        if any(i != index and item.get("name") == new_name
               for i, item in enumerate(self._connections)):
            return False

        target = self._connections[index]
        backup = dict(target)

        target.update(data)
        target["name"] = new_name
        target["isSelect"] = backup.get("isSelect", False)

        if not self._save():
            target.clear()
            target.update(backup)
            return False

        self.sig_list_changed.emit()
        return True

    def remove(self, index: int) -> bool:
        """index 항목 삭제. 최소 1개는 유지한다.

        선택 항목을 삭제하면 첫 항목이 새로 선택된다."""
        if index < 0 or index >= len(self._connections):
            return False
        if len(self._connections) <= 1:
            return False

        backup = [dict(item) for item in self._connections]
        was_selected = self._connections[index].get("isSelect", False)

        self._connections.pop(index)
        if was_selected:
            self._normalize_selection()

        if not self._save():
            self._connections[:] = backup
            return False

        self.sig_list_changed.emit()
        if was_selected:
            self.sig_selection_changed.emit(self.selected_index())
        return True

    # ------------------------------------------------------------ 파일 IO
    def _load(self):
        self._connections = []

        if os.path.exists(path_def.RSRC_CONNECTIONS_JSON_FILE):
            try:
                with open(path_def.RSRC_CONNECTIONS_JSON_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                if isinstance(data, list):
                    self._connections = data
            except Exception as e:
                self._log.error(f"connections.json load failed: {e}")

        # 파일이 없거나 읽기 실패 시 기본 항목 1개로 시작
        if not self._connections:
            self._connections = [dict(self._DEFAULT_CONNECTION)]

        self._normalize_selection()

    def _normalize_selection(self):
        """isSelect 가 정확히 하나만 True 가 되도록 정리 (없으면 첫 항목)."""
        selected = self.selected_index()
        for i, item in enumerate(self._connections):
            item["isSelect"] = (i == selected)

    def _save(self) -> bool:
        try:
            os.makedirs(os.path.dirname(path_def.RSRC_CONNECTIONS_JSON_FILE), exist_ok=True)
            with open(path_def.RSRC_CONNECTIONS_JSON_FILE, 'w', encoding='utf-8') as f:
                json.dump(self._connections, f, indent=4, ensure_ascii=False)
            return True
        except Exception as e:
            self._log.error(f"connections.json save failed: {e}")
            return False
