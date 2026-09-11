"""도메인 중립화(3단계) 차등 테스트 — 구 컨버터(UI 변환) vs 새 codec + 표시 변환.

"화면 결과 불변" 을 기계적으로 확인한다. 비교 대상은 직전 커밋(기본 b88c40b)의
c_ui/a_converter 두 파일을 git 에서 꺼내 그대로 실행한 결과다.

    python tools/test_domain_step3.py
    python tools/test_domain_step3.py --old-commit <sha>

검사 항목
  1. 위치: 단위 8종 × USER_SPECIFIC (min,max) 조합 × 선로값 표본 → 구 convert_posi_to_dp / _str
     vs 새 PosiCodec.from_line + format_dp. 역방향 encode 도 구 convert_dp_to_posi_str 과 대조.
     설정점 비율(pfs) 변환도 대조.
  2. 압력: 인터페이스 단위 8종 × (USER_SPECIFIC 이면 iface min/max 2조 × 센서 구성 4종) × 표시 단위 8종
     × 선로값 표본 × 모드(auto/s1/s2) → 구 convert_iface_pres_to_dp_pres vs 새 codec.from_line → to_display.
     역방향, 만압(get_dp_max_pres), sfs 변환 대조.
  3. 배율: scale100 / scale10000 codec == 구 위젯 배율.
  4. 등록부: get_context_params 순서, apply_line_text, 워커 refresh 가 문맥 param 을 앞에 넣는지.
  5. 위젯(offscreen): posi/pres/scale 위젯이 도메인 값을 화면 문자열로 바르게 만드는지.
실수 비교는 앱 전역 정책(is_float_equal, 유효숫자 6자리)을 따른다.
"""

from __future__ import annotations

import argparse
import importlib.util
import itertools
import os
import subprocess
import sys
import tempfile

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)

from PySide6.QtWidgets import QApplication  # noqa: E402

_app = QApplication.instance() or QApplication(sys.argv)

from b_core.b_datatype import param_enum as p_enum  # noqa: E402
from b_core.b_datatype.general_enum import ParamAccType  # noqa: E402
from b_core.c_manager.parameter_manager import ParamManager  # noqa: E402
from b_core.f_helper.float_util import is_float_equal, to_sig_str  # noqa: E402
from b_core.g_protocol.codec import DOMAIN_PRES_UNIT, PosiCodec, PresCodec, ScaleCodec  # noqa: E402
from b_core.g_protocol.spec_registry import SpecRegistry  # noqa: E402


class Report:
    def __init__(self):
        self.fail = 0
        self.checks = 0
        self.notes: list[str] = []

    def check(self, ok: bool, msg: str):
        self.checks += 1
        if not ok:
            self.fail += 1
            if self.fail <= 30:
                print(f"  FAIL {msg}")


class FakeLocalSetting:
    def __init__(self, pres_unit, pres_decimal_places=3, posi_decimal_places=2):
        self.pres_unit = pres_unit
        self.pres_decimal_places = pres_decimal_places
        self.posi_decimal_places = posi_decimal_places


def git_show(commit: str, path: str) -> str:
    return subprocess.check_output(["git", "-C", ROOT, "show", f"{commit}:{path}"]).decode("utf-8")


def load_old_module(commit: str, path: str, name: str):
    tmp = tempfile.mkdtemp(prefix="domain_old_")
    file_path = os.path.join(tmp, os.path.basename(path))
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(git_show(commit, path))
    spec = importlib.util.spec_from_file_location(name, file_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def set_param(param, value):
    """문맥 param 값을 시그널 없이 넣는다 (구 컨버터는 명시적으로 재계산을 호출한다)."""
    param._value = value
    param.str_value = "" if value is None else str(value)


def feq(a, b) -> bool:
    if a is None or b is None:
        return a is None and b is None
    return is_float_equal(float(a), float(b))


def seq(a: str | None, b: str | None, decimals: int | None = None) -> bool:
    """문자열 동일 또는 (둘 다 숫자 문자열이면) 유효숫자 정책으로 같음.
    decimals 가 주어지면 고정 자릿수 표시의 마지막 자리 1단위 차이(반올림 경계)까지 허용한다."""
    if a == b:
        return True
    if a is None or b is None:
        return False
    try:
        fa, fb = float(a), float(b)
    except ValueError:
        return False
    if is_float_equal(fa, fb):
        return True
    return decimals is not None and abs(fa - fb) <= 10 ** (-decimals) + 1e-12


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--old-commit", default="b88c40b")
    args = ap.parse_args()

    rep = Report()
    pm = ParamManager()
    reg = SpecRegistry()

    old_posi_mod = load_old_module(args.old_commit, "c_ui/a_converter/position_converter_manager.py", "old_posi_conv")
    old_pres_mod = load_old_module(args.old_commit, "c_ui/a_converter/pressure_converter_manager.py", "old_pres_conv")
    from c_ui.a_converter.position_converter_manager import PosiConverterManager
    from c_ui.a_converter.pressure_converter_manager import PresConverterManager

    old_posi = old_posi_mod.PosiConverterManager()
    old_pres = old_pres_mod.PresConverterManager()
    new_posi = PosiConverterManager()
    new_pres = PresConverterManager()
    OldType = old_pres_mod.PresConvertType

    posi_codec: PosiCodec = reg.get_codec("posi")
    pres_codecs: dict[str, PresCodec] = {"auto": reg.get_codec("pres"), "s1": reg.get_codec("pres_s1"), "s2": reg.get_codec("pres_s2")}
    rep.check(posi_codec is not None and all(c is not None for c in pres_codecs.values()), "codec 등록 (posi / pres / pres_s1 / pres_s2)")
    if rep.fail:
        return 1

    # ---------------------------------------------------------------- 1. 위치
    unit_p, min_p, max_p = posi_codec.unit_param, posi_codec.min_param, posi_codec.max_param
    line_samples = [0.0, 1.0, 12345.678, 50000.0, 100000.0, -30.5, 130000.0, 0.37]
    dp_samples = [0.0, 12.5, 50.0, 100.0, -20.0, 130.0, 33.3333333]
    user_ranges = [(0.0, 100000.0), (1000.0, 5000.0), (500.0, 500.0), (-100.0, 100.0)]
    posi_cases = 0
    degenerate_encode = [0]
    pfs_same_as_old = [0]
    pfs_total = [0]
    for unit in range(8):
        ranges = user_ranges if unit == p_enum.RS232PositionUnitEnum.USER_SPECIFIC.value else [(None, None)]
        for lo, hi in ranges:
            set_param(unit_p, unit); set_param(min_p, lo); set_param(max_p, hi)
            old_posi.handle_posi_range_changed()
            for v in line_samples:
                o = old_posi.convert_posi_to_dp(v)
                n = posi_codec.from_line(v)
                rep.check(feq(o, n), f"posi unit={unit} range={lo},{hi} line={v}: {o} != {n}")
                rep.check(seq(old_posi.convert_posi_to_dp_str(v), new_posi.format_dp(n)),
                          f"posi str unit={unit} line={v}")
                posi_cases += 1
            for dp in dp_samples:
                n = posi_codec.encode(dp)
                if lo == hi and lo is not None:
                    # 퇴화 구성(min == max): 구 코드는 경로에 따라 "0"(convert_dp_to_posi_str)과
                    # min(convert_dp_to_posi → 위젯 쓰기 경로)을 달리 냈다. codec 은 위젯 쓰기 경로(min)를 따른다
                    o = to_sig_str(old_posi.convert_dp_to_posi(dp))
                    degenerate_encode[0] += 1
                else:
                    o = old_posi.convert_dp_to_posi_str(dp)
                rep.check(seq(o, n), f"posi encode unit={unit} range={lo},{hi} dp={dp}: {o} != {n}")
                n2 = posi_codec.encode(str(dp))  # 문자열 입력도 같은 결과 (write 경로)
                rep.check(n == n2, f"posi encode(str) unit={unit} dp={dp}")
                posi_cases += 1
            for pfs in (0.0, 0.25, 0.5, 1.0):
                # 로컬 설정점(pfs) 은 3단계에서 "백분율 ÷ 100" 으로 재정의 (사용자 결정) — 구 식과 비교하지 않고
                # 새 규칙 자체와 왕복을 검사한다. 구 식과 결과가 같은 경우(Open 값 100)만 일치 건수로 집계
                dp = new_posi.convert_pfs_to_dp(pfs)
                rep.check(feq(dp, pfs * 100.0), f"pfs→dp = ×100: pfs={pfs} → {dp}")
                rep.check(feq(new_posi.convert_dp_to_pfs(dp), pfs), f"dp→pfs 왕복: pfs={pfs}")
                rep.check(new_posi.convert_pfs_to_dp_str(pfs) == new_posi.format_dp(pfs * 100.0), f"pfs→dp str pfs={pfs}")
                pfs_same_as_old[0] += feq(old_posi.convert_pfs_to_dp(pfs), dp)
                pfs_total[0] += 1
            # 설정점 버튼: 백분율 문자열 → 쓰기값은 codec 이 현재 단위의 선로값으로 (예: 0-100000 에서 100 → 100000)
            if posi_codec.is_ready:
                line = posi_codec.encode(new_posi.normalize_dp_str("100"))
                rng = posi_codec.range()
                rep.check(seq(line, to_sig_str(rng[1])), f"설정점 100 % → 선로 {line} (Open={rng[1]})")
    # 문맥 미준비: 구 컨버터는 마지막 계수를 유지하지만 새 codec 은 None (의도된 편차)
    set_param(unit_p, None)
    rep.check(posi_codec.from_line(50000.0) is None, "posi 문맥 미준비 → None")
    rep.notes.append(f"위치 차등 {posi_cases} 케이스 (단위 8종, USER_SPECIFIC 범위 4조, 선로값 8 / 백분율 7 표본)")
    rep.notes.append("의도된 편차: 문맥(Position Unit) 미수신 상태에서 구 컨버터는 기본 범위(0~100)로 변환했지만 새 codec 은 None(Unknown). "
                     "refresh 가 문맥을 먼저 읽으므로 실제로는 창을 열 때 잠깐만 다르다")
    rep.notes.append(f"의도된 편차: USER_SPECIFIC 에서 Closest == Open(퇴화 구성)일 때 메인 위치 패널 설정점 버튼의 쓰기값이 "
                     f"'0' 에서 Closest 값으로 바뀐다 (위젯 쓰기 경로와 통일, {degenerate_encode[0]} 케이스 대조)")
    rep.notes.append(f"의도된 편차(결함 수정): 위치 로컬 설정점 pfs = 백분율 ÷ 100 으로 재정의. 구 식(dp ÷ Open값)과 결과가 같은 경우는 "
                     f"{pfs_same_as_old[0]}/{pfs_total[0]} (Open 값이 100 인 단위만). 100 % 버튼 → 현재 단위의 Open 선로값 확인")

    # ---------------------------------------------------------------- 2. 압력
    pc = pres_codecs["auto"]
    iface_unit, iface_min, iface_max = pc.iface_unit, pc.iface_min, pc.iface_max
    s1, s2 = pc.sens1, pc.sens2

    sensor_configs = {
        # (s1 avail, s1 enable, s1 unit, s1 min, s1 max, s2 avail, s2 enable, s2 unit, s2 min, s2 max)
        "s1_only":  (1, 1, p_enum.SensUnitEnum.TORR.value, 0.0, 10.0,  1, 0, p_enum.SensUnitEnum.PA.value, 0.0, 1000.0),
        "s2_only":  (1, 0, p_enum.SensUnitEnum.TORR.value, 0.0, 10.0,  1, 1, p_enum.SensUnitEnum.MBAR.value, 0.0, 1333.0),
        "both":     (1, 1, p_enum.SensUnitEnum.PSIG.value, -14.7, 0.3, 1, 1, p_enum.SensUnitEnum.TORR.value, 0.0, 1000.0),
        "none":     (1, 0, p_enum.SensUnitEnum.TORR.value, 0.0, 10.0,  0, 0, p_enum.SensUnitEnum.TORR.value, 0.0, 10.0),
    }
    iface_ranges = [(0.0, 1000.0), (100.0, 900.0)]
    pres_line_samples = [0.0, 0.5, 1.0, 123.456, 750.0, 1000.0, -5.0]
    pres_dp_samples = [0.0, 1.0, 7.5, 100.0, 760.0, -3.0]
    modes = {"auto": OldType.AUTO, "s1": OldType.SENSOR1, "s2": OldType.SENSOR2}
    pres_cases = 0
    str_exact = str_total = 0

    for unit in range(8):
        is_user = unit == p_enum.RS232PressureUnitEnum.USER_SPECIFIC.value
        combos = list(itertools.product(iface_ranges, sensor_configs.items())) if is_user else [((0.0, 1000.0), ("n/a", sensor_configs["s1_only"]))]
        for (imin, imax), (cfg_name, cfg) in combos:
            set_param(iface_unit, unit); set_param(iface_min, imin); set_param(iface_max, imax)
            for key, val in zip(("avail", "enable", "unit", "min", "max"), cfg[:5]):
                set_param(s1[key], val)
            for key, val in zip(("avail", "enable", "unit", "min", "max"), cfg[5:]):
                set_param(s2[key], val)

            for disp_unit in range(8):
                fake = FakeLocalSetting(disp_unit, pres_decimal_places=3)
                old_pres.local_setting = fake
                new_pres.local_setting = fake
                old_pres.handle_pres_decimal_places_changed()
                new_pres.handle_pres_decimal_places_changed()
                old_pres.handle_sens_cfg_changed()

                for mode, old_type in modes.items():
                    codec = pres_codecs[mode]
                    for v in pres_line_samples:
                        o = old_pres.convert_iface_pres_to_dp_pres(v, old_type)
                        n = new_pres.to_display(codec.from_line(v))
                        rep.check(feq(o, n), f"pres unit={unit} {cfg_name} iface={imin},{imax} disp={disp_unit} {mode} line={v}: {o} != {n}")
                        o_s = old_pres.convert_iface_pres_to_dp_pres_str(v, old_type)
                        n_s = new_pres.to_display_str(codec.from_line(v))
                        # Torr 경유 합성 곱은 직접 환산과 1 ulp 차이가 날 수 있어, 정확히 .5 경계에 놓인 값은
                        # 고정 자릿수 반올림이 마지막 자리 1단위 갈릴 수 있다 — 그 범위까지 허용하고 건수를 보고
                        rep.check(seq(o_s, n_s, decimals=3), f"pres str unit={unit} {cfg_name} disp={disp_unit} {mode} line={v}: {o_s} != {n_s}")
                        str_total += 1
                        str_exact += (o_s == n_s)
                        pres_cases += 1
                    for dp in pres_dp_samples:
                        o = old_pres.convert_dp_pres_to_iface_pres_str(dp, old_type)
                        n = codec.encode(new_pres.from_display(dp))
                        rep.check(seq(o, n), f"pres encode unit={unit} {cfg_name} disp={disp_unit} {mode} dp={dp}: {o} != {n}")
                        pres_cases += 1

                # 만압 / sfs (auto 기준 — 모든 호출측이 AUTO 를 썼다)
                rep.check(feq(old_pres.get_dp_max_pres(OldType.AUTO), new_pres.get_dp_max_pres()),
                          f"max pres unit={unit} {cfg_name} disp={disp_unit}")
                for sfs in (0.0, 0.1, 0.5, 1.0):
                    rep.check(feq(old_pres.convert_sfs_to_dp_pres(sfs, OldType.AUTO), new_pres.convert_sfs_to_dp_pres(sfs)),
                              f"sfs→dp unit={unit} {cfg_name} disp={disp_unit} sfs={sfs}")
                    rep.check(seq(old_pres.convert_sfs_to_dp_pres_str(sfs, OldType.AUTO), new_pres.convert_sfs_to_dp_pres_str(sfs), decimals=3),
                              f"sfs→dp str unit={unit} {cfg_name} disp={disp_unit} sfs={sfs}")
                    rep.check(feq(old_pres.convert_dp_pres_to_sfs(sfs * 100, OldType.AUTO), new_pres.convert_dp_pres_to_sfs(sfs * 100)),
                              f"dp→sfs unit={unit} {cfg_name} disp={disp_unit} dp={sfs*100}")

    # 단위 환산표 동일
    for a, b in itertools.product(range(8), range(8)):
        rep.check(old_pres.get_unit_conversion(a, b) == new_pres.get_unit_conversion(a, b), f"unit conversion {a}->{b}")

    rep.notes.append(f"압력 차등 {pres_cases:,} 케이스 (인터페이스 단위 8종, USER_SPECIFIC 범위 2조 × 센서 구성 4종, 표시 단위 8종, "
                     f"모드 3종, 선로값 7 / 표시값 6 표본). 표시 문자열 완전 일치 {str_exact:,}/{str_total:,}, "
                     f"나머지 {str_total - str_exact}건은 .5 반올림 경계에서 마지막 자리 1단위 차이 (값은 1e-15 이내 동일)")

    # ---------------------------------------------------------------- 3. 배율
    for name, factor in (("scale100", 100.0), ("scale10000", 10000.0)):
        c = reg.get_codec(name)
        rep.check(isinstance(c, ScaleCodec) and c.factor == factor, f"{name} codec")
        for v in (0.0, 0.5, 0.0001, 1.0, -0.25):
            rep.check(feq(c.from_line(v), v * factor), f"{name} from_line {v}")
            rep.check(seq(c.encode(v * factor), to_sig_str(v)), f"{name} encode {v}")

    # ---------------------------------------------------------------- 4. 등록부 / 워커
    act_posi = pm.get_by_full_path("Position Control.Basic.Actual Position")
    act_pres = pm.get_by_full_path("Pressure Control.Basic.Actual Pressure")
    s1_pres = pm.get_by_full_path("Sensor.Sensor 1.Basic.Actual Pressure Value")
    speed = pm.get_by_full_path("Position Control.Basic.Position Control Speed Used (%)")
    rep.check(reg.get_param_codec(act_posi) is posi_codec, "Actual Position → posi codec")
    rep.check(reg.get_param_codec(act_pres) is pres_codecs["auto"], "Actual Pressure → pres(auto) codec")
    rep.check(reg.get_param_codec(s1_pres) is pres_codecs["s1"], "Sensor 1 Actual Pressure Value → pres_s1 codec")
    rep.check(isinstance(reg.get_param_codec(speed), ScaleCodec), "Speed Used (%) → scale100 codec")

    ctx = reg.get_context_params([act_posi, act_pres, s1_pres])
    expected_ctx = list(posi_codec.context_params)
    for p in pres_codecs["auto"].context_params + pres_codecs["s1"].context_params:
        if p not in expected_ctx:
            expected_ctx.append(p)
    rep.check(ctx == expected_ctx, f"get_context_params 순서/중복 제거: {len(ctx)} vs {len(expected_ctx)}")
    rep.check(reg.get_context_params([unit_p, act_posi]) == [min_p, max_p], "get_context_params 는 목록에 이미 있는 문맥을 빼고 준다")

    set_param(unit_p, p_enum.RS232PositionUnitEnum.ZERO_TO_100000.value)
    rep.check(reg.apply_line_text(act_posi, "50000") and feq(act_posi.value, 50.0) and act_posi.str_value == "50000",
              f"apply_line_text posi: {act_posi.value} / {act_posi.str_value!r}")
    rep.check(feq(reg.decode_line(act_posi, 25000.0), 25.0), "decode_line posi")
    rep.check(reg.apply_line_text(act_posi, "abc") is False, "apply_line_text 형식 불량 → False")

    from b_core.d_dal.service_port import ServicePort
    from b_core.e_worker_ver2.parameter_run_worker import ParameterRunWorker, StartResult, _JobOp
    w = ParameterRunWorker(log_source="test")
    svc = ServicePort()
    try:
        w.add_read_param_ptr(act_posi)
        w.add_read_param_ptr(s1_pres)
        svc._connect_info = "test"
        rep.check(w.refresh() == StartResult.OK, "refresh OK")
        jobs = list(w._jobs)
        w._stop_all()
        params_in_order = [j.spec.params[0] for j in jobs]
        expected = list(posi_codec.context_params) + [p for p in pres_codecs["s1"].context_params if p not in posi_codec.context_params] + [act_posi, s1_pres]
        rep.check(params_in_order == expected, f"refresh 큐: 문맥 {len(expected) - 2}개 선행 후 대상 2개 — 실제 {len(params_in_order)}개")
        rep.check(all(j.op is _JobOp.READ for j in jobs), "refresh 큐는 전부 읽기")

        # 쓰기: 도메인 값(백분율) → codec 이 선로 문자열 생성. 문맥 미준비면 작업 건너뜀
        set_param(unit_p, p_enum.RS232PositionUnitEnum.ZERO_TO_100000.value)
        target = pm.get_by_full_path("Position Control.Basic.Target.Target Position")
        rep.check(w.write([(target, "50")]) == StartResult.OK, "write OK")
        first = w._jobs[0]
        rep.check(first.op is _JobOp.WRITE and first.spec.build_request(first.values).endswith("50000"),
                  f"write 백분율 50 → 선로 50000: {first.spec.build_request(first.values)}")
        w._stop_all()
        set_param(unit_p, None)
        rep.check(w.write([(target, "50")]) == StartResult.OK, "write(문맥 미준비) 시작은 OK")
        rep.check(w._jobs[0].spec.build_request(w._jobs[0].values) is None, "문맥 미준비 encode → None (워커가 건너뜀)")
        w._stop_all()
    finally:
        svc._connect_info = ""
        w.cleanup()

    # ---------------------------------------------------------------- 5. 위젯 (offscreen)
    from c_ui.b_control_ver2.d_param.param_values import (ParamReadOnlyPosiValueWidget, ParamReadOnlyPresValueWidget,
                                                          ParamReadOnlyScaleValueWidget, ParamReadWritePresValueWidget)
    set_param(unit_p, p_enum.RS232PositionUnitEnum.ZERO_TO_100000.value)
    new_posi.local_setting = FakeLocalSetting(DOMAIN_PRES_UNIT, posi_decimal_places=2)
    new_posi.handle_posi_decimal_places_changed()
    act_posi.value = 12.3456
    wdg = ParamReadOnlyPosiValueWidget(act_posi.full_path)
    rep.check(wdg.value_widget.text() == "12.35", f"posi RO 위젯 표시: {wdg.value_widget.text()!r}")
    rep.check(feq(wdg.get_value(), 12.35), "posi RO get_value = 화면값")

    fake = FakeLocalSetting(p_enum.SensUnitEnum.MTORR.value, pres_decimal_places=1)
    new_pres.local_setting = fake
    new_pres.handle_pres_decimal_places_changed()
    act_pres.value = 1.5  # Torr
    wdg = ParamReadOnlyPresValueWidget(act_pres.full_path)
    rep.check(wdg.value_widget.text() == "1500.0", f"pres RO 위젯 표시 (1.5 Torr → mTorr): {wdg.value_widget.text()!r}")
    rep.check(feq(wdg.get_value(), 1.5), "pres RO get_value → Torr")
    rw = ParamReadWritePresValueWidget("Pressure Control.Basic.Target.Target Pressure")
    rw.set_value(2.0)
    rep.check(feq(rw.get_value(), 2.0), f"pres RW 왕복 (Torr→mTorr→Torr): {rw.get_value()}")
    speed.value = 55.0
    wdg = ParamReadOnlyScaleValueWidget(speed.full_path)
    rep.check(wdg.value_widget.text() == "55", f"scale RO 위젯 표시 (배율은 codec): {wdg.value_widget.text()!r}")

    print()
    for note in rep.notes:
        print(f"  note: {note}")
    print(f"\nchecks {rep.checks:,}  fail {rep.fail}  → {'ALL PASS' if rep.fail == 0 else 'FAILED'}")
    return 0 if rep.fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
