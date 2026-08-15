# -*- coding: utf-8 -*-
"""우리 기수가 '상대 현재 위치'와 '리드 예측점' 중 어디를 향하는지 잰다.

[가설] Task_LeadPredict는 전 거리에서 leadTime = min(dist/mySpd, 3.0)초 리드를 건다.
  채점 콘은 상대의 **현재 위치** 기준이므로, 사거리 안에서도 리드가 살아 있으면
  기수가 구조적으로 콘 밖에 놓인다. v27 게이트(ATA<10도에서 리드 fade)가 있으나
  절제실험에서 발동률 0.3~5.7%로 측정됐다.

[검증 방법] 사거리 안 틱마다
    ata_now  = 기수와 '상대 현재 위치' 사이 각
    ata_lead = 기수와 '리드 예측점' 사이 각
  ata_lead < ata_now 이면 우리는 예측점을 겨누고 있다 = 리드가 살아 있다.
  그 틱들의 ata_now 가 콘(1도) 밖이면 **리드 때문에 득점을 못 하는 것**이다.

[주의] 이건 상관이 아니라 직접 측정이다. 다만 '리드를 끄면 좋아진다'는 것은
  증명하지 않는다 — v25(거리로 리드 제거)가 추종 붕괴로 기각된 전례가 있다.

사용: python tools_diag/lead_bias.py <own.csv> <tgt.csv> [--cone 1.0] [--maxlead 3.0]
"""
from __future__ import annotations
import argparse, csv, math, sys
try:
    import pymap3d as pm
except ImportError:
    sys.exit("pymap3d 필요 (conda env 'aip')")


def load(p):
    out = []
    with open(p, newline="", encoding="utf-8-sig", errors="replace") as f:
        for r in csv.DictReader(f):
            try:
                out.append(dict(t=float(r["Time"]), lat=float(r["Latitude"]),
                                lon=float(r["Longitude"]), alt=float(r["Altitude"]),
                                pitch=float(r["Pitch (deg)"]), yaw=float(r["Yaw (deg)"])))
            except (ValueError, KeyError):
                continue
    return out


def nose(pitch, yaw):
    p, y = math.radians(pitch), math.radians(yaw)
    return (math.cos(p) * math.sin(y), math.cos(p) * math.cos(y), math.sin(p))


def ang(v, w):
    dv = math.sqrt(sum(a * a for a in v)); dw = math.sqrt(sum(a * a for a in w))
    if dv < 1e-9 or dw < 1e-9:
        return 0.0
    c = max(-1.0, min(1.0, sum(a * b for a, b in zip(v, w)) / (dv * dw)))
    return math.degrees(math.acos(c))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("own"); ap.add_argument("tgt")
    ap.add_argument("--cone", type=float, default=1.0)
    ap.add_argument("--maxlead", type=float, default=3.0, help="Task_LeadPredict의 상한(초)")
    ap.add_argument("--min", dest="rmin", type=float, default=500 * 0.3048)
    ap.add_argument("--max", dest="rmax", type=float, default=3000 * 0.3048)
    a = ap.parse_args()

    O, T = load(a.own), load(a.tgt)
    n = min(len(O), len(T))
    if n < 3:
        sys.exit("행 부족")
    lat0, lon0, alt0 = O[0]["lat"], O[0]["lon"], O[0]["alt"]
    enu = lambda r: pm.geodetic2enu(r["lat"], r["lon"], r["alt"], lat0, lon0, alt0)

    lead_win = 0; now_win = 0; inr = 0
    lead_but_miss = 0            # 예측점을 겨누느라 현재위치 콘을 놓친 틱
    sum_gap = 0.0
    for i in range(1, n - 1):
        po, pt = enu(O[i]), enu(T[i])
        d = math.dist(po, pt)
        if not (a.rmin <= d <= a.rmax):
            continue
        inr += 1
        # 상대 속도/진행방향은 위치 차분으로 (헤딩과 실제 진행이 다를 수 있다)
        p_prev, p_next = enu(T[i - 1]), enu(T[i + 1])
        dt = T[i + 1]["t"] - T[i - 1]["t"]
        if dt <= 0:
            continue
        vel = tuple((p_next[k] - p_prev[k]) / dt for k in range(3))
        spd = math.sqrt(sum(v * v for v in vel))
        # 우리 속도도 같은 방식
        o_prev, o_next = enu(O[i - 1]), enu(O[i + 1])
        odt = O[i + 1]["t"] - O[i - 1]["t"]
        ospd = math.sqrt(sum(((o_next[k] - o_prev[k]) / odt) ** 2 for k in range(3))) if odt > 0 else 250.0
        lt = min(d / ospd, a.maxlead) if ospd > 1 else a.maxlead
        pred = tuple(pt[k] + vel[k] * lt for k in range(3))

        f = nose(O[i]["pitch"], O[i]["yaw"])
        los_now = tuple(pt[k] - po[k] for k in range(3))
        los_pred = tuple(pred[k] - po[k] for k in range(3))
        a_now, a_pred = ang(f, los_now), ang(f, los_pred)
        sum_gap += (a_now - a_pred)
        if a_pred < a_now:
            lead_win += 1
            if a_now > a.cone and a_pred <= a.cone:
                lead_but_miss += 1
        else:
            now_win += 1

    if inr == 0:
        print("사거리 체류 0틱"); return
    pc = lambda x: 100.0 * x / inr
    print(f"사거리 안 {inr}틱")
    print(f"  기수가 '리드 예측점'에 더 가까움 : {lead_win:5} ({pc(lead_win):5.1f}%)")
    print(f"  기수가 '현재 위치'에 더 가까움   : {now_win:5} ({pc(now_win):5.1f}%)")
    print(f"  평균 각도차 (현재-예측)          : {sum_gap/inr:+6.2f}도  (+면 예측점 쪽으로 치우침)")
    print(f"  ★ 예측점은 콘 안인데 현재위치는 콘 밖 : {lead_but_miss} 틱")
    if lead_but_miss:
        print("     -> 이 틱들은 리드만 껐으면 득점이었다.")


if __name__ == "__main__":
    main()
