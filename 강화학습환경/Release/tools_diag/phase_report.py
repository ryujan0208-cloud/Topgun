# -*- coding: utf-8 -*-
"""대미지를 대회 3단계 phase로 분해한다.

[왜] 대회 사격 판정은 시간에 따라 3단계로 완화된다(`wez_rule.py`).
  콘 부피비 1 : 6.36 : 21.37 -> 기대 대미지 1.0 : 1.9 : 2.1 = **후반이 오히려 유리**.
  그런데 v0~v32의 판정은 전부 P1 고정 기준이었고, 지금도 우리는 총합만 본다.
  총합만 보면 "P1에서 벌고 P3에서 잃는" 기체와 그 반대를 구별하지 못한다.

[핵심 설계] 대미지는 **규칙으로 재계산하지 않고 트랙의 HP 변화에서 직접 읽는다.**
  거리 감쇠 공식은 대회가 공개하지 않았고(`wez_rule.py` 주석) 우리 공식은 추정이다.
  추정 공식으로 대미지를 만들어 내면 그건 시뮬이지 측정이 아니다.
  phase 귀속은 **시각만으로 결정**되므로(100s/150s 경계) 추정이 개입하지 않는다.
  -> 대미지는 실측, 귀속은 정확. WEZ 규칙은 **체류시간** 집계에만 쓴다.

[출력]
  1. phase별 준/받은 HP와 순이득
  2. 첫 피격·첫 가격의 시각과 phase
  3. phase 전환(100s/150s) 전후 2초 구간의 HP 변화 - 전환 순간에 몰리는지
  4. phase별 WEZ 체류시간(우리가 상대를 조준한 시간 / 상대가 우리를 조준한 시간)
  5. 200초 생존 판의 비율(= 대칭 선회 무승부 후보)

사용: python tools_diag/phase_report.py <stamp> [stamp...]
      python tools_diag/phase_report.py --from-log <배치로그> [--tag <STAMP 접두>]
"""
from __future__ import annotations

import csv
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import wez_rule  # noqa: E402

LOGS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                    "artifacts", "logs")
MLAT = 111320.0
EDGE_S = 2.0            # phase 전환 전후로 볼 창
TRANSITIONS = (100.0, 150.0)


def _fwd(row):
    y = math.radians(float(row["Yaw (deg)"]))
    p = math.radians(float(row["Pitch (deg)"]))
    return (math.sin(y) * math.cos(p), math.cos(y) * math.cos(p), math.sin(p))


def _ang(u, v):
    du = math.sqrt(sum(x * x for x in u))
    dv = math.sqrt(sum(x * x for x in v))
    c = sum(a * b for a, b in zip(u, v)) / max(du * dv, 1e-9)
    return math.degrees(math.acos(max(-1.0, min(1.0, c))))


def _load(stamp, side, tag):
    path = os.path.join(LOGS, f"{stamp}_{side}_{tag}.csv")
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def phase_at(t):
    """시각 t의 '최상위' phase 이름. 활성 phase 중 가장 늦게 시작한 것."""
    act = wez_rule.active(t)
    return act[-1]["name"] if act else "P1"


def analyze_series(series):
    """series = [(t, dist, myAta, tgtAta, ownHP, tgtHP), ...] -> 집계 dict.

    트랙 로딩과 분리해 두어 단위테스트가 CSV 없이 돌 수 있게 한다.
    """
    names = [p["name"] for p in wez_rule.PHASES]
    taken = {n: 0.0 for n in names}
    dealt = {n: 0.0 for n in names}
    dwell_us = {n: 0.0 for n in names}     # 우리가 상대를 WEZ에 넣은 시간
    dwell_them = {n: 0.0 for n in names}
    first_taken = first_dealt = None
    edge = {tr: {"taken": 0.0, "dealt": 0.0} for tr in TRANSITIONS}

    prev_o = prev_t = None
    for i, (t, dist, ma, ta, ohp, thp) in enumerate(series):
        ph = phase_at(t)
        dt = (t - series[i - 1][0]) if i else 0.0
        if prev_o is not None:
            d_take = prev_o - ohp
            d_deal = prev_t - thp
            if d_take > 1e-9:
                taken[ph] += d_take
                if first_taken is None:
                    first_taken = (t, ph)
                for tr in TRANSITIONS:
                    if abs(t - tr) <= EDGE_S:
                        edge[tr]["taken"] += d_take
            if d_deal > 1e-9:
                dealt[ph] += d_deal
                if first_dealt is None:
                    first_dealt = (t, ph)
                for tr in TRANSITIONS:
                    if abs(t - tr) <= EDGE_S:
                        edge[tr]["dealt"] += d_deal
        prev_o, prev_t = ohp, thp

        if dt > 0:
            ok_us, ph_us = wez_rule.hit(t, dist, ma)
            if ok_us:
                dwell_us[ph_us] += dt
            ok_th, ph_th = wez_rule.hit(t, dist, ta)
            if ok_th:
                dwell_them[ph_th] += dt

    return dict(taken=taken, dealt=dealt, dwell_us=dwell_us, dwell_them=dwell_them,
                first_taken=first_taken, first_dealt=first_dealt, edge=edge,
                dur=series[-1][0] if series else 0.0,
                ownHP=series[-1][4] if series else 1.0,
                tgtHP=series[-1][5] if series else 1.0)


def build_series(stamp):
    o = _load(stamp, "ownship", "(F-16)[Blue]")
    t = _load(stamp, "target", "(F-16)[Red]")
    n = min(len(o), len(t))
    if n < 2:
        return []
    c = math.cos(math.radians(float(o[0]["Latitude"])))
    t0 = float(o[0]["Time"])
    out = []
    for i in range(n):
        de = (float(t[i]["Longitude"]) - float(o[i]["Longitude"])) * c * MLAT
        dn = (float(t[i]["Latitude"]) - float(o[i]["Latitude"])) * MLAT
        du = float(t[i]["Altitude"]) - float(o[i]["Altitude"])
        d = math.sqrt(de * de + dn * dn + du * du)
        out.append((float(o[i]["Time"]) - t0, d,
                    _ang(_fwd(o[i]), (de, dn, du)),
                    _ang(_fwd(t[i]), (-de, -dn, -du)),
                    float(o[i]["Health"]), float(t[i]["Health"])))
    return out


def aggregate(reports):
    names = [p["name"] for p in wez_rule.PHASES]
    agg = dict(taken={n: 0.0 for n in names}, dealt={n: 0.0 for n in names},
               dwell_us={n: 0.0 for n in names}, dwell_them={n: 0.0 for n in names},
               edge={tr: {"taken": 0.0, "dealt": 0.0} for tr in TRANSITIONS},
               first_taken=[], first_dealt=[], full=0, n=0)
    for r in reports:
        agg["n"] += 1
        for k in ("taken", "dealt", "dwell_us", "dwell_them"):
            for nm in names:
                agg[k][nm] += r[k][nm]
        for tr in TRANSITIONS:
            agg["edge"][tr]["taken"] += r["edge"][tr]["taken"]
            agg["edge"][tr]["dealt"] += r["edge"][tr]["dealt"]
        if r["first_taken"]:
            agg["first_taken"].append(r["first_taken"])
        if r["first_dealt"]:
            agg["first_dealt"].append(r["first_dealt"])
        if r["dur"] >= 195.0:
            agg["full"] += 1
    return agg


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        print(wez_rule.describe())
        return
    stamps = []
    if args[0] == "--from-log":
        logp = args[1]
        tag = args[3] if len(args) > 3 and args[2] == "--tag" else None
        for line in open(logp, encoding="utf-8", errors="replace"):
            if line.startswith("STAMP") and (tag is None or tag in line):
                stamps.append(line.split()[-1])
    else:
        stamps = args

    reports, missing = [], 0
    for s in stamps:
        try:
            ser = build_series(s)
        except FileNotFoundError:
            missing += 1
            continue
        if ser:
            reports.append(analyze_series(ser))
    if not reports:
        print("판정 불가 — 읽을 트랙이 없다 (stamp 확인)")
        sys.exit(3)

    a = aggregate(reports)
    names = [p["name"] for p in wez_rule.PHASES]
    print(f"판수 {a['n']}" + (f"  (트랙 없음 {missing})" if missing else ""))
    print()
    print(f"{'phase':<7}{'준HP':>9}{'받은HP':>9}{'순이득':>9}"
          f"{'우리조준s':>11}{'상대조준s':>11}")
    print("-" * 58)
    for nm in names:
        print(f"{nm:<7}{a['dealt'][nm]:>9.3f}{a['taken'][nm]:>9.3f}"
              f"{a['dealt'][nm]-a['taken'][nm]:>9.3f}"
              f"{a['dwell_us'][nm]:>11.1f}{a['dwell_them'][nm]:>11.1f}")
    print("-" * 58)
    td, tt = sum(a["dealt"].values()), sum(a["taken"].values())
    print(f"{'합계':<7}{td:>9.3f}{tt:>9.3f}{td-tt:>9.3f}"
          f"{sum(a['dwell_us'].values()):>11.1f}{sum(a['dwell_them'].values()):>11.1f}")

    print()
    for label, lst in (("첫 피격", a["first_taken"]), ("첫 가격", a["first_dealt"])):
        if not lst:
            print(f"  {label}: 없음")
            continue
        ts = sorted(t for t, _ in lst)
        byph = {}
        for _, ph in lst:
            byph[ph] = byph.get(ph, 0) + 1
        print(f"  {label}: {len(lst)}판  중앙 {ts[len(ts)//2]:.0f}s  "
              f"phase분포 {byph}")

    print()
    print(f"  phase 전환 +-{EDGE_S:.0f}초 구간의 HP 변화 "
          f"(총합 대비 몰림 여부):")
    for tr in TRANSITIONS:
        e = a["edge"][tr]
        print(f"    t={tr:.0f}s  준 {e['dealt']:.3f} ({100*e['dealt']/td if td else 0:.1f}%)"
              f"  받은 {e['taken']:.3f} ({100*e['taken']/tt if tt else 0:.1f}%)")

    print()
    print(f"  200초 완주(>=195s) {a['full']}/{a['n']}판 "
          f"= {100.0*a['full']/a['n']:.0f}%  (대칭 선회 무승부 후보)")


if __name__ == "__main__":
    main()
