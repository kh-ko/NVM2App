from PySide6.QtCore import Signal
from PySide6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout

from b_core.f_helper.float_util import is_float_equal, to_sig_str

from c_ui.b_control_ver2.a_theme.tokens import tokens
from c_ui.b_control_ver2.a_theme.color_styled import ColorStyled, WidgetColors
from c_ui.b_control_ver2.b_base.labels import BaseLabel

# 값 위젯 통일 기준 높이 — 최초 1회만 측정해 캐시한다.
# (앱 폰트/스타일 적용 후 시점이어야 하므로 import 시점이 아니라
#  첫 위젯 생성 시점에 지연 측정. 폰트는 시작 시 한 번 정해지므로 캐시 안전 —
#  런타임에 바뀌는 색 토큰의 캐시 금지 규칙과는 다른 경우다)
_ref_height = None

def _value_widget_ref_height():
    global _ref_height
    if _ref_height is None:
        from c_ui.b_control_ver2.b_base.inputs import BaseComboBox
        _ref_height = BaseComboBox().sizeHint().height()
    return _ref_height

class ValueWidget(QWidget, ColorStyled):
    sig_edited_by_user   = Signal(object)    # 위젯 자신(self) 전달
    sig_assigned_by_code = Signal(object)    # 위젯 자신(self) 전달
    sig_edited_by_enter  = Signal(object)    # 위젯 자신(self) 전달
    sig_editing_by_user  = Signal(object)    # 편집 진행 중 (표시 전용 — 쓰기 경로 연결 금지)

    def __init__(self, label_text="", label_width=150, is_show_dirty = False, value_widget = None, is_vertical_mode = False, parent=None):
        super().__init__(parent)

        self._enable_conditions = []
        self._is_not_support = False
        # 라벨/dirty 마커는 구성에 따라 생성되지 않을 수 있다 — 사용측은 None 가드 필요
        self.lbl_label = None
        self.dirty_label = None
        self.value_widget = None
        self.ori_value = None
        
        if is_vertical_mode:
            self._build_vertical_gui(label_text, label_width, is_show_dirty, value_widget)
        else:
            self._build_horizontal_gui(label_text, label_width, is_show_dirty, value_widget)

        # 값 위젯 종류(라벨/입력기/콤보)마다 기본 높이가 달라 행이 들쭉날쭉해지므로
        # 가장 큰 콤보박스 높이를 기준으로 통일한다 (Fixed 가 아닌 Minimum —
        # QSS padding 변경 등으로 더 커져야 할 때 잘리지 않도록)
        if self.value_widget is not None:
            self.value_widget.setMinimumHeight(_value_widget_ref_height())

        self._init_colors(WidgetColors())

        self.reg_value_widget_event()

    def _build_qss(self, c: WidgetColors) -> str:
        return f"""
            ValueWidget {{
                background-color: {c.bg};
            }}
        """

    def _build_vertical_gui(self, label_text="", label_width=150, is_show_dirty = False, value_widget = None):
        """[라벨 행(라벨 + dirty 마커)] 아래 [값 위젯] 의 세로 배치.

        BaseGroupBox 를 쓰지 않는 이유: 그룹박스의 오버레이 타이틀 장치는
        '타이틀이 테두리 선에 걸치는' 효과용인데 세로 모드는 테두리가 없어
        전부 불필요한 무게가 된다. 단순 세로 배치로 충분하고, 속성명
        (lbl_label/dirty_label/value_widget)이 가로 모드와 동일해서 상위
        레이어 핸들러가 모드를 구분할 필요도 없다.
        (입력기 호버 강조가 필요해지면 ValueWidget 의 _build_qss 에
        테두리/호버 규칙을 추가하는 방식으로 확장한다)

        label_width 는 가로 정렬용이므로 세로 모드에서는 사용하지 않는다."""
        self._root_layout = QVBoxLayout(self)
        self._root_layout.setContentsMargins(0, 0, 0, 0)
        self._root_layout.setSpacing(0)

        label_layout = QHBoxLayout()
        label_layout.setContentsMargins(0, 0, 0, 0)
        label_layout.setSpacing(5)

        if label_text:
            self.lbl_label = BaseLabel(label_text)
            self.lbl_label.setWordWrap(False)
            label_layout.addWidget(self.lbl_label)

        if is_show_dirty:
            self.dirty_label = BaseLabel("*")
            self.dirty_label.set_colors(text=tokens().danger)
            sp = self.dirty_label.sizePolicy()
            sp.setRetainSizeWhenHidden(True)
            self.dirty_label.setSizePolicy(sp)
            self.dirty_label.setVisible(False) # 초기에는 숨김
            label_layout.addWidget(self.dirty_label)

        label_layout.addStretch()
        self._root_layout.addLayout(label_layout)

        if value_widget is not None:
            self.value_widget = value_widget
            self._root_layout.addWidget(value_widget)

    def _build_horizontal_gui(self, label_text="", label_width=150, is_show_dirty = False, value_widget = None):
        # 주의: 'layout' 속성명은 QWidget.layout() 을 가리므로 사용 금지 (buttons.py 와 동일 규칙)
        self._root_layout = QHBoxLayout(self)
        self._root_layout.setContentsMargins(0, 0, 0, 0)
        self._root_layout.setSpacing(5)

        if label_text:
            self.lbl_label = BaseLabel(label_text)
            self.lbl_label.setFixedWidth(label_width)
            self._root_layout.addWidget(self.lbl_label)

        if is_show_dirty:
            self.dirty_label = BaseLabel("*")
            self.dirty_label.set_colors(text=tokens().danger)
            sp = self.dirty_label.sizePolicy()
            sp.setRetainSizeWhenHidden(True)
            self.dirty_label.setSizePolicy(sp)
            self.dirty_label.setVisible(False) # 초기에는 숨김
            self._root_layout.addWidget(self.dirty_label)

        if value_widget is not None:
            self.value_widget = value_widget
            self._root_layout.addWidget(value_widget, 1)

    def reg_enable_condition(self, ref_widget, conditions):
        self._enable_conditions.append((ref_widget, conditions))
        ref_widget.sig_edited_by_user.connect(self.on_enable_condition_changed)
        ref_widget.sig_assigned_by_code.connect(self.on_enable_condition_changed)
        self.on_enable_condition_changed()

    def on_enable_condition_changed(self):
        self._sync_enabled()

    # ------------------------------------------------------------ 활성 상태 — 단일 결정 지점 (8-d)
    def _is_enabled_by_state(self) -> bool:
        """Not Support 아님 AND 값 조건 AND enable 조건. 위젯 자신의 상태만 본다 (부모의 비활성은 무관)."""
        return (not self._is_not_support
                and self._value_allows_enable()
                and all(ref_widget.get_value() in conditions for ref_widget, conditions in self._enable_conditions))

    def _sync_enabled(self):
        """활성 여부를 바꾸는 유일한 곳. set_value / set_not_support / enable 조건 변경이 모두 여기로 온다 —
        어느 경로도 setEnabled(True) 로 다른 경로의 비활성을 되돌리지 않는다 (F060)."""
        self.setEnabled(self._is_enabled_by_state())

    def _value_allows_enable(self) -> bool:
        """값 기준 활성 조건 — 기본 True. RO 위젯은 '값 없음(Unknown) = 비활성' 을 유지하려고 override 한다."""
        return True

    def _no_value_text(self, detail=None) -> str:
        """값 없음 문구 — Not Support 중이면 "Not Support", 아니면 "Unknown"(detail 이 있으면 "Unknown (detail)").
        set_value 의 값 없음 분기가 이것을 쓰므로, Not Support 중에 set_value 가 다시 불려도(컨버터 시그널,
        Load File) 문구가 "Unknown" 으로 바뀌지 않는다."""
        if self._is_not_support:
            return "Not Support"
        return "Unknown" if detail is None else f"Unknown ({detail})"

    def is_editable(self) -> bool:
        """Apply 수집 기준 — 상태상 활성이고 숨겨지지 않은 위젯의 편집값만 보낸다 (F064).
        조건으로 비활성화된 위젯의 dirty 편집은 보내지 않되 되돌리지도 않는다 (2026-09-30 결정)."""
        return self._is_enabled_by_state() and not self.isHidden()

    def on_edited_by_user(self):
        self.proc_dirty()
        self.sig_edited_by_user.emit(self)

    def on_edit_by_enter(self):
        self.sig_edited_by_enter.emit(self)

    def on_editing_by_user(self):
        # 편집 진행 중 — dirty 마커를 실시간 갱신하고 표시 전용 시그널만 릴레이
        self.proc_dirty()
        self.sig_editing_by_user.emit(self)

    def on_assigned_by_code(self):
        self.proc_dirty()
        self.sig_assigned_by_code.emit(self)

    def commit(self):
        self.ori_value = self.get_value()
        self.proc_dirty()

    def proc_dirty(self):
        if self.dirty_label is None:
            return

        if self.is_dirty():
            self.dirty_label.setVisible(True)
        else:
            self.dirty_label.setVisible(False)


    def is_dirty(self):
        curr_value = self.get_value()

        # 실수가 끼면 앱 전역 유효숫자 6자리 정책으로 비교 (float↔None 혼합도 안전)
        if isinstance(curr_value, float) or isinstance(self.ori_value, float):
            return not is_float_equal(curr_value, self.ori_value)

        return curr_value != self.ori_value
        
    def get_value_str(self):
        curr_value = self.get_value()

        if curr_value is None:
            return None

        if isinstance(curr_value, float):
            # 앱 전역 유효숫자 정책의 단일 구현(float_util.to_sig_str)에 위임한다
            return to_sig_str(curr_value)
        elif isinstance(curr_value, int):
            try:
                return str(curr_value)
            except Exception:
                return None
        elif isinstance(curr_value, str):
            return curr_value
        
        return None        

    def set_value(self, value):
        #하위 클래스에서 구현해야하며 각 value_widget의 종류에 따라 알맞게 구현해야됨.
        #표시만 바꾸고 self._sync_enabled() 를 부른다 — setEnabled 를 직접 호출하지 않는다 (8-d)
        pass

    def get_value(self):
        #하위 클래스에서 구현해야하며 각 value_widget의 종류에 따라 알맞게 구현해야됨
        #
        # [계약] get_value 는 '화면에 표시되고 있는 값'을 반환한다.
        # 화면에서 소수점이 잘렸다면 잘린 값을 반환해야 한다 — 표시된 값과
        # 실제 동작 값이 다르면 사용자가 혼란스럽기 때문.
        # (enum 도 예외가 아니다 — RO 는 from_desc 역변환, RW 는 currentData)
        pass

    def set_not_support(self, is_not_support):
        """Not Support 상태 지정 — 문구 표시는 위젯별 _render_not_support, 활성 여부는 _sync_enabled 가 정한다."""
        self._is_not_support = bool(is_not_support)
        self._render_not_support(self._is_not_support)
        self._sync_enabled()

    def _render_not_support(self, is_not_support):
        # 기본: True 면 값 없음 표시로("Not Support" 문구는 set_value 가 _no_value_text 로 플래그에서 정한다),
        # False 면 값이 없을 때만 다시 그려 문구를 "Unknown" 으로 되돌린다 — 그 사이 set_value 로 들어온 값은 유지.
        # 값 재표시는 호출측(ParamWidget.handle_param_is_not_support_changed)이 set_value 로 한다.
        if is_not_support or self.get_value() is None:
            self.set_value(None)

    def reg_value_widget_event(self):
        #하위 클래스에서 구현해야하며 각 value_widget의 종류에 따라 알맞게 이벤트를 연결해야됨
        #
        # [계약] 모든 자식 클래스는 동일한 루틴을 따른다:
        # 1. 이 메서드에서 value_widget 의 시그널을 연결한다 (해당되는 것만).
        #    self.value_widget.sig_edited_by_user.connect(self.on_edited_by_user)
        #    self.value_widget.sig_assigned_by_code.connect(self.on_assigned_by_code)
        #    self.value_widget.sig_edited_by_enter.connect(self.on_edit_by_enter)
        #    self.value_widget.sig_editing_by_user.connect(self.on_editing_by_user)  # 실시간 dirty 표시용
        # 2. 값 할당은 value_widget 의 setter 를 그냥 호출한다 (시그널이 릴레이됨).
        # 3. 값 할당이 아닌 표시 전용 조작(예: "Not Support" 표기)만
        #    QSignalBlocker(self.value_widget) 로 감싸 알림을 차단한다.
        pass

        

    
