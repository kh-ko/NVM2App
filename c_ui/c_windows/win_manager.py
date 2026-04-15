from PySide6.QtCore import Qt

class WinManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(WinManager, cls).__new__(cls)
            cls._instance.windows = {}
        return cls._instance

    def show_window(self, win_class, win_id=None, parent=None, is_modal=False, *args, **kwargs):
        """
        win_class: 생성할 윈도우 클래스
        지정된 클래스의 창을 싱글톤으로 관리하여 띄웁니다.
        창이 파괴(닫힘)되면 관리 목록에서 자동으로 제거합니다.
        """
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

    def _on_window_destroyed(self, win_name):
        """창이 소멸될 때 호출되어 관리 딕셔너리에서 삭제"""
        if win_name in self.windows:
            del self.windows[win_name]