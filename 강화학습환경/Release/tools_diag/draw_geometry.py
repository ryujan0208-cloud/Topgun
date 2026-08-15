# -*- coding: utf-8 -*-
"""무승부 판의 기하를 잰다 — "왜 아무도 득점하지 못하는가"를 가른다.

[왜 만들었나] 2026-08-15. 팀원 3인(jung/yuno/TW)과 우리가 서로 거의 무승부다.
  yuno 자체 측정: yuno vs 우리 0승0패 20무(준 1.25), 그런데 yuno vs 직선표적은 20승(준 20.11).
  능력은 있는데 기회가 없다. 그 "기회 없음"이 무엇인지 이 도구가 가른다.

[가르는 것]
  A. 사거리에 아예 못 들어간다        -> 접근/추종 문제
  B. 사거리엔 있는데 각이 크게 어긋난다 -> 조준 문제
  C. 사거리+각 1~3도에서 아깝게 빗나간다 -> **마지막 1도 문제** (스킬로 깰 수 있다)
  D. 양쪽이 동시에 콘에 들어가 상쇄된다  -> 정면교전 문제 (회피가 답)

[도구 규칙 — CLAUDE.md '측정 도구를 먼저 의심할 것']
  - 콘 각도/사거리는 **인자로 받는다**. 코드에 박지 않는다.
  - **대칭 지표는 양쪽 다 잰다** (우리 ATA / 상대 ATA).
  - 에피소드 경계에서 위치가 점프하므로 한 판씩만 넣는다.

사용:
  python tools_diag/draw_geometry.py <ownship.csv> <target.csv> [--cone 1.0] [--min 152.4] [--max 914.4]
"""
from __future__ import annotations
import argparse, csv, math, sys

try:
    import pymap3d as pm
except ImportError:
    sys.exit("pymap3d가 필요하다. conda env 'aip'로 실행할 것.")


def load(path):
    rows = []
    with open(path, newline="", encoding="utf-8-sig", errors="replace") as f:
        for r in csv.DictReader(f):
            try:
                rows.append(dict(
                    t=float(r["Time"]), lat=float(r["Latitude"]), lon=float(r["Longitude"]),
                    alt=float(r["Altitude"]), roll=float(r["Roll (deg)"]),
                    pitch=float(r["Pitch (deg)"]), yaw=float(r["Yaw (deg)"]),
                    hp=float(r.get("Health", "nan")),
                ))
            except (ValueError, KeyError):
                continue
    return rows


def nose(pitch_deg, yaw_deg):
    """기수 단위벡터 (ENU). roll은 기수 방향에 영향이 없다."""
    p, y = math.radians(pitch_deg), math.radians(yaw_deg)
    cp = math.cos(p)
    return (cp * math.sin(y), cp * math.cos(y), math.sin(p))   # E, N, U


def ata_deg(me, other, lat0, lon0, alt0):
    """me의 기수와 me->other LOS 사이 각(도). 0이면 정확히 겨눔."""
    e1, n1, u1 = pm.geodetic2enu(me["lat"], me["lon"], me["alt"], lat0, lon0, alt0)
    e2, n2, u2 = pm.geodetic2enu(other["lat"], other["lon"], other["alt"], lat0, lon0, alt0)
    dx, dy, dz = e2 - e1, n2 - n1, u2 - u1
    d = math.sqrt(dx * dx + dy * dy + dz * dz)
    if d < 1e-6:
        return 0.0, 0.0
    fx, fy, fz = nose(me["pitch"], me["yaw"])
    c = max(-1.0, min(1.0, (dx * fx + dy * fy + dz * fz) / d))
    return math.degrees(math.acos(c)), d


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("own"); ap.add_argument("tgt")
    ap.add_argument("--cone", type=float, default=1.0, help="사격 콘 반각(도). 대회 P1 = 1.0")
    ap.add_argument("--min", dest="rmin", type=float, default=500 * 0.3048)
    ap.add_argument("--max", dest="rmax", type=float, default=3000 * 0.3048)
    ap.add_argument("--quiet", action="store_true")
    a = ap.parse_args()

    O, T = load(a.own), load(a.tgt)
    n = min(len(O), len(T))
    if n == 0:
        sys.exit("행이 없다")
    lat0, lon0, alt0 = O[0]["lat"], O[0]["lon"], O[0]["alt"]

    # 밴드: 콘 안 / 콘~2배 / 2배~3배 / 그 밖
    b_own = [0, 0, 0, 0]; b_tgt = [0, 0, 0, 0]
    in_rng = 0; both_cone = 0; tot = 0
    min_own = 999.0; min_tgt = 999.0
    score_own = 0; score_tgt = 0
    for i in range(n):
        ao, d = ata_deg(O[i], T[i], lat0, lon0, alt0)
        at, _ = ata_deg(T[i], O[i], lat0, lon0, alt0)
        tot += 1
        min_own = min(min_own, ao); min_tgt = min(min_tgt, at)
        inr = a.rmin <= d <= a.rmax
        if inr:
            in_rng += 1
            for val, b in ((ao, b_own), (at, b_tgt)):
                if val <= a.cone: b[0] += 1
                elif val <= a.cone * 2: b[1] += 1
                elif val <= a.cone * 3: b[2] += 1
                else: b[3] += 1
            if ao <= a.cone: score_own += 1
            if at <= a.cone: score_tgt += 1
            if ao <= a.cone and at <= a.cone: both_cone += 1

    pct = lambda x, d=tot: (100.0 * x / d) if d else 0.0
    print(f"틱 {tot}   사거리({a.rmin:.0f}~{a.rmax:.0f}m) 체류 {in_rng} ({pct(in_rng):.1f}%)")
    print(f"최소 ATA   우리 {min_own:6.2f}도   상대 {min_tgt:6.2f}도   (콘 {a.cone}도)")
    print()
    print(f"{'사거리 안에서의 각도 분포':<26} {'우리':>12} {'상대':>12}")
    lbl = [f"<= {a.cone}도 (득점)", f"{a.cone}~{a.cone*2}도 (아깝다)",
           f"{a.cone*2}~{a.cone*3}도", f"> {a.cone*3}도 (멀다)"]
    for k in range(4):
        print(f"  {lbl[k]:<24} {b_own[k]:>6} {pct(b_own[k], in_rng):>5.1f}% "
              f"{b_tgt[k]:>6} {pct(b_tgt[k], in_rng):>5.1f}%")
    print()
    print(f"득점틱   우리 {score_own}   상대 {score_tgt}   동시(상쇄) {both_cone}")
    if not a.quiet:
        near = b_own[1] + b_own[2]
        print()
        print("[해석]")
        if in_rng == 0:
            print("  A: 사거리에 아예 못 들어갔다 -> 접근/추종 문제")
        elif score_own == 0 and near > 0:
            print(f"  C: 사거리엔 있는데 콘 밖 {a.cone}~{a.cone*3}도에서 {near}틱 맴돈다")
            print("     = **마지막 1도 문제**. 조준을 못 해서가 아니라 못 좁혀서 0점이다.")
        elif score_own == 0:
            print("  B: 사거리엔 있으나 각이 크게 어긋난다 -> 조준 문제")
        if both_cone > 0:
            print(f"  D: 양쪽 동시 콘 진입 {both_cone}틱 = 정면교전 상쇄 구간이 있다")


if __name__ == "__main__":
    main()
