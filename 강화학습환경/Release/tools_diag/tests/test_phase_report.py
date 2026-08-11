# -*- coding: utf-8 -*-
"""phase_report.analyze_series 회귀 테스트.

도구 상수 문제로 하루에 네 번 당한 전례가 있어(turn_perf/alt_trace/ata_split/bfm_syllabus)
집계 함수는 CSV 없이 검증 가능하게 분리해 두었다. 여기서 그걸 고정한다.

실행: python -m pytest tools_diag/tests/test_phase_report.py -q
  또는 python tools_diag/tests/test_phase_report.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import phase_report as pr  # noqa: E402
import wez_rule  # noqa: E402


def mk(t, dist=600.0, ma=90.0, ta=90.0, ohp=1.0, thp=1.0):
    return (t, dist, ma, ta, ohp, thp)


def test_phase_boundary_is_exact():
    """phase 귀속은 시각만으로 결정된다 — 경계값이 흔들리면 안 된다."""
    assert pr.phase_at(0.0) == "P1"
    assert pr.phase_at(99.9) == "P1"
    assert pr.phase_at(100.0) == "P2"
    assert pr.phase_at(149.9) == "P2"
    assert pr.phase_at(150.0) == "P3"
    assert pr.phase_at(200.0) == "P3"


def test_damage_attributed_to_phase_of_its_time():
    """P1/P2/P3에서 각각 한 번씩 맞으면 그 phase에 귀속돼야 한다."""
    s = [mk(0.0), mk(50.0, ohp=0.9), mk(120.0, ohp=0.7), mk(180.0, ohp=0.4)]
    r = pr.analyze_series(s)
    assert abs(r["taken"]["P1"] - 0.1) < 1e-9
    assert abs(r["taken"]["P2"] - 0.2) < 1e-9
    assert abs(r["taken"]["P3"] - 0.3) < 1e-9


def test_dealt_reads_target_hp_not_a_formula():
    """준 대미지는 상대 HP 감소분 실측이다. 규칙으로 재계산하지 않는다."""
    s = [mk(0.0), mk(10.0, thp=0.55)]
    r = pr.analyze_series(s)
    assert abs(r["dealt"]["P1"] - 0.45) < 1e-9
    assert sum(r["taken"].values()) == 0.0


def test_hp_increase_is_ignored():
    """에피소드 경계 등에서 HP가 올라가도 음수 대미지로 새지 않아야 한다."""
    s = [mk(0.0, ohp=0.5), mk(10.0, ohp=1.0), mk(20.0, ohp=0.8)]
    r = pr.analyze_series(s)
    assert abs(sum(r["taken"].values()) - 0.2) < 1e-9


def test_first_hit_records_time_and_phase():
    s = [mk(0.0), mk(30.0), mk(130.0, ohp=0.8), mk(160.0, ohp=0.6)]
    r = pr.analyze_series(s)
    assert r["first_taken"][1] == "P2"
    assert abs(r["first_taken"][0] - 130.0) < 1e-9
    assert r["first_dealt"] is None


def test_transition_window_counts_only_nearby_damage():
    """전환 +-2초 안의 것만 잡아야 한다. 3초 밖은 안 잡힌다."""
    s = [mk(0.0), mk(99.0, ohp=0.9), mk(103.0, ohp=0.8), mk(151.0, ohp=0.5)]
    r = pr.analyze_series(s)
    assert abs(r["edge"][100.0]["taken"] - 0.1) < 1e-9   # 99s만 (103s는 3초 밖)
    assert abs(r["edge"][150.0]["taken"] - 0.3) < 1e-9   # 151s


def test_wez_dwell_uses_phase_widening():
    """ATA 1.5도는 P1(<1.0)에선 불성립, P2(<2.0)부터 성립.
    도구가 P1 고정 기준이면 여기서 걸린다 — v0~v32 판정이 실제로 그랬다."""
    dt = 1.0
    early = [mk(t, dist=600.0, ma=1.5) for t in (10.0, 10.0 + dt, 10.0 + 2 * dt)]
    late = [mk(t, dist=600.0, ma=1.5) for t in (120.0, 120.0 + dt, 120.0 + 2 * dt)]
    r_e = pr.analyze_series(early)
    r_l = pr.analyze_series(late)
    assert sum(r_e["dwell_us"].values()) == 0.0
    assert r_l["dwell_us"]["P2"] > 0.0


def test_wez_dwell_separates_us_from_them():
    """우리 조준과 상대 조준을 섞으면 안 된다(대칭 지표는 양쪽 다 잰다)."""
    s = [mk(t, dist=600.0, ma=0.5, ta=90.0) for t in (10.0, 11.0, 12.0)]
    r = pr.analyze_series(s)
    assert r["dwell_us"]["P1"] > 0.0
    assert sum(r["dwell_them"].values()) == 0.0


def test_max_coefficient_phase_wins():
    """활성 phase 중 최대 계수를 채택한다 - P3 시간대에 P1 콘 안이면 P1으로 잡힌다.
    운영측 답변(7/2): "Phase3이 켜진 상태에서 적기가 Phase1의 범위안에 위치에
    있다면 Phase1의 대미지가 적용됩니다"."""
    assert wez_rule.hit(170.0, 600.0, 0.5) == (True, "P1")    # P1 콘 안 -> 계수 1.0
    assert wez_rule.hit(170.0, 600.0, 1.5) == (True, "P2")    # P1 밖 P2 안
    assert wez_rule.hit(170.0, 600.0, 2.5) == (True, "P3")    # P2(<2.0)도 밖
    assert wez_rule.hit(170.0, 600.0, 3.5) == (False, None)   # 전부 밖
    assert wez_rule.hit(50.0, 600.0, 1.5) == (False, None)    # P2가 아직 안 켜짐


def test_aggregate_sums_across_games():
    a = pr.aggregate([pr.analyze_series([mk(0.0), mk(50.0, ohp=0.9)]),
                      pr.analyze_series([mk(0.0), mk(50.0, thp=0.7)])])
    assert a["n"] == 2
    assert abs(a["taken"]["P1"] - 0.1) < 1e-9
    assert abs(a["dealt"]["P1"] - 0.3) < 1e-9
    assert a["full"] == 0


if __name__ == "__main__":
    fails = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"  ok   {name}")
            except AssertionError as e:
                fails += 1
                print(f"  FAIL {name}: {e}")
    print(f"\n{'모두 통과' if not fails else str(fails) + '건 실패'}")
    sys.exit(1 if fails else 0)
