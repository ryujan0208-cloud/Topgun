# -*- coding: utf-8 -*-
"""상대의 '고도 하한'을 관측으로 역추정한다 — 급하강 유인 전략의 전제 검증.

[가설] 상대가 DECO_AltitudeCheck 계열 **예측식** 하한을 쓴다면
    predAlt = alt + Vz*T      (Vz<0 강하, T=선행시간, 우리 v42는 T=5.0s)
  이므로 **판의 최저고도가 그 직전 강하율에 비례해 높아진다**:
    최저고도 ≈ MinAlt + |Vz| * T
  기울기 T가 잡히면 예측식이고 = 고속 강하로 유인하면 상대가 훨씬 높이서 이탈한다(착취 가능).
  기울기 0이면 단순 고도선이라 착취 여지가 작다.

★★ [자기 검산이 되는 설계] 우리 v42는 T=5.0, MinAlt=700 으로 **정답을 안다**.
  우리 로그를 넣어 그 값을 복원하지 못하면 **이 도구는 못 쓴다.**
  (초판은 '선회 바닥'까지 전부 풀아웃으로 세어 T=-6.67, MinAlt=4684 가 나왔다 — 기각했다.)

[핵심 수정] 하한은 **판에서 가장 낮게 내려간 그 순간에만** 작동한다.
  판마다 표본 1개(최저고도, 그 직전 최대 강하율)만 뽑는다. 일반 선회는 섞이지 않는다.

사용:
  python tools_diag/dive_floor.py <alt_csv> --label 이름 --accum 파일
  python tools_diag/dive_floor.py x --accum 파일 --report
"""
from __future__ import annotations
import argparse, csv, sys, json, os


def load(p):
    out = []
    for r in csv.DictReader(open(p, newline="", encoding="utf-8-sig", errors="replace")):
        try:
            out.append((float(r["Time"]), float(r["Altitude"])))
        except (ValueError, KeyError):
            continue
    return out


def sample(rows, look_s=3.0):
    """판의 최저고도와, 그 직전 look_s초 동안의 최대 강하율."""
    if len(rows) < 10:
        return None
    imin = min(range(len(rows)), key=lambda i: rows[i][1])
    if imin == 0:
        return None
    t_end = rows[imin][0]
    worst = 0.0
    for i in range(1, imin + 1):
        if rows[i][0] < t_end - look_s:
            continue
        dt = rows[i][0] - rows[i - 1][0]
        if dt <= 0:
            continue
        vz = (rows[i][1] - rows[i - 1][1]) / dt
        worst = min(worst, vz)
    if worst >= -1.0:                       # 강하 없이 도달한 최저점은 하한과 무관
        return None
    return (abs(worst), rows[imin][1])


def regress(pts):
    n = len(pts)
    mx = sum(p[0] for p in pts) / n
    my = sum(p[1] for p in pts) / n
    den = sum((p[0] - mx) ** 2 for p in pts)
    if den < 1e-9:
        return None
    T = sum((p[0] - mx) * (p[1] - my) for p in pts) / den
    b = my - T * mx
    ss_t = sum((p[1] - my) ** 2 for p in pts)
    ss_r = sum((p[1] - (T * p[0] + b)) ** 2 for p in pts)
    r2 = 1 - ss_r / ss_t if ss_t > 1e-9 else 0.0
    return T, b, r2


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("csv"); ap.add_argument("--label", default="")
    ap.add_argument("--accum", default=""); ap.add_argument("--report", action="store_true")
    ap.add_argument("--look-s", type=float, default=3.0)
    a = ap.parse_args()

    samples = json.load(open(a.accum, encoding="utf-8")) if (a.accum and os.path.exists(a.accum)) else []

    if not a.report:
        s = sample(load(a.csv), a.look_s)
        if s:
            samples.append([a.label, s[0], s[1]])
            print(f"  {a.label:10} 최저 {s[1]:7.0f}m  직전 최대강하율 {s[0]:6.1f} m/s")
        else:
            print(f"  {a.label:10} 표본 없음(강하 없이 도달)")
        if a.accum:
            json.dump(samples, open(a.accum, "w", encoding="utf-8"))

    if a.report:
        by = {}
        for lab, r, h in samples:
            by.setdefault(lab, []).append((r, h))
        print()
        print(f"{'대상':12} {'판수':>4} {'기울기 T(s)':>11} {'절편 MinAlt(m)':>14} {'R²':>6}  해석")
        for lab, pts in sorted(by.items()):
            if len(pts) < 4:
                print(f"{lab:12} {len(pts):>4}   표본 부족")
                continue
            g = regress(pts)
            if not g:
                print(f"{lab:12} {len(pts):>4}   강하율 분산 0")
                continue
            T, b, r2 = g
            v = ("예측식 (강하율에 비례)" if T > 1.5 and r2 > 0.25
                 else "단순 고도선" if abs(T) < 1.0
                 else "불명확")
            print(f"{lab:12} {len(pts):>4} {T:>11.2f} {b:>14.0f} {r2:>6.2f}  {v}")


if __name__ == "__main__":
    main()
