"""창 등록부 (win_id → 창) 싱글턴.

- show_window(): 같은 win_id 의 창이 있으면 앞으로 가져오고(생성 인자는 무시), 없으면 만들어
  등록·표시한다. 창은 WA_DeleteOnClose 로 닫히면 파괴되고 파괴 시 등록부에서 빠진다
  (close() 직후에는 아직 등록돼 있다 — deleteLater 라 이벤트 루프로 돌아간 뒤 빠진다).
- close_all(): 등록된 창 전부 close(). 하나라도 거부하면 False (앱 업데이트 설치 전 등).
MainWin 은 등록부에 없다 (앱 수명 창).
"""

import threading

from PySide6.QtCore import Qt


class WinManager:
    _instance = None
    _creation_lock = threading.Lock()  # 다른 싱글턴(매니저/컨버터/ServicePort)과 같은 방식 (F095)

    def __new__(cls):
        with cls._creation_lock:
            if cls._instance is None:
                cls._instance = super(WinManager, cls).__new__(cls)
                cls._instance.windows = {}
        return cls._instance

    def show_window(self, win_class, win_id=None, parent=None, is_modal=False, *args, **kwargs):
        """win_id(없으면 클래스 이름)의 창을 띄우고 반환한다.

        이미 있으면 앞으로 가져오고 그 창을 반환한다 — 이때 생성 인자는 무시된다
        (생성 인자를 새로 반영해야 하면 다른 win_id 로 띄운다). 새로 만들면 WA_DeleteOnClose 로
        닫힐 때 파괴되고, 파괴 시 등록부에서 빠진다."""
        name = win_id if win_id else win_class.__name__

        # 창이 이미 존재하면 앞으로 가져오기만 한다
        if name in self.windows:
            win = self.windows[name]
            win.showNormal()    # (추가) 최소화되어 있을 경우 원래 상태로 복구
            win.activateWindow() # 최상단으로 활성화
            win.raise_()         # Z-Order 맨 위로 올림
            return win

        # 창이 없으면 새로 생성
        new_win = win_class(parent, *args, **kwargs)
        self.windows[name] = new_win

        if is_modal:
            new_win.setWindowModality(Qt.WindowModal)

        new_win.setAttribute(Qt.WA_DeleteOnClose)

        # 창이 닫혀서 파괴될 때 딕셔너리에서 제거하도록 연결
        # QWidget의 destroyed 시그널을 이용 (WA_DeleteOnClose 속성이 있어야 함)
        new_win.destroyed.connect(lambda obj=None, n=name: self._on_window_destroyed(n))

        new_win.show()
        return new_win

    def close_all(self, exclude: tuple = ()) -> bool:
        """등록된 창을 모두 close() 한다 (앱 업데이트 설치 전 등).

        하나라도 닫기를 거부하면(closeEvent ignore — 펌웨어 쓰기 중, FU 백업 중 등)
        그 자리에서 False 를 돌려주고 나머지 창은 건드리지 않는다. exclude 의 창은 건너뛴다.
        (파괴는 deleteLater 라 목록 제거는 이벤트 루프로 돌아간 뒤 — 스냅샷을 돈다)"""
        for win in list(self.windows.values()):
            if win in exclude:
                continue
            if not win.close():
                return False
        return True

    def _on_window_destroyed(self, win_name):
        """창이 소멸될 때 호출되어 관리 딕셔너리에서 삭제"""
        if win_name in self.windows:
            del self.windows[win_name]