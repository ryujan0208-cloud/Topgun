# -*- coding: utf-8 -*-
"""리드 조준이 우리 기수를 상대에게서 몇 도나 떼어놓는지 잰다.

[질문 — 사용자가 리플레이를 보고 물었다]
  "왜 기동을 추월해서 앞으로 가는지 모르겠다. 스스로 뒤를 잡혀주는 꼴이다.
   서로 8자를 그리다가 갑자기 튀어나가서 뒤를 잡혀준다."

[가설] Task_LeadPredict의 리드가 **직선 예측**이기 때문이다.
    leadTime  = dist / mySpd        (상한 3초)
    predicted = 상대위치 + 상대기수 * (상대속도 * leadTime)
  상대가 강하게 선회 중이면 그 "직선 앞"은 선회 **바깥**이다. 거기를 겨누면 밖으로 밀린다.
  리드를 줄이는 v27 게이트는 `dist<914 AND ATA<10`일 때만 걸리는데,
  추월 국면의 ATA는 30~100도라 **리드가 100% 그대로 적용된다.**

[측정]
  1. leadTime 뒤 상대의 **실제** 위치와, 직선 예측 위치의 어긋남(m)
  2. 리드점 방향과 상대 방향 사이의 각(deg) = **리드가 기수를 떼어놓는 각도**
  3. 참고로 상대의 실제 선회율

사용: python tools_diag/lead_error.py <stamp> <seed> [시작초] [끝초] [간격초]
"""
import csv
import math
import os
import sys

R = r"C:\Users\TFX5470H\Desktop\.topgun\강화학습환경\Release\artifacts\logs"
MLAT = 111320.0
LEAD_CAP_S = 3.0          # Task_LeadPredict의 상한
V27_DIST_M = 914.0        # v27 종말조준 게이트
V27_ATA_DEG = 10.0


def load(stamp, seed, side, tag):
    p = os.path.join(R, f"{stamp}_s{seed:02d}_{side}_{tag}.csv")
    with open(p, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def enu(a, b, c):
    """a -> b 의 ENU 변위(m)."""
    return ((float(b["Longitude"]) - float(a["Longitude"])) * c * MLAT,
            (float(b["Latitude"]) - float(a["Latitude"])) * MLAT,
            float(b["Altitude"]) - float(a["Altitude"]))


def fwd(r):
    yr, pr = math.radians(float(r["Yaw (deg)"])), math.radians(float(r["Pitch (deg)"]))
    return (math.sin(yr)*math.cos(pr), math.cos(yr)*math.cos(pr), math.sin(pr))


def norm(v):
    n = math.sqrt(sum(x*x for x in v))
    return tuple(x/n for x in v) if n > 1e-9 else (0.0, 0.0, 0.0)


def angle(u, v):
    u, v = norm(u), norm(v)
    return math.degrees(math.acos(max(-1.0, min(1.0, sum(a*b for a, b in zip(u, v))))))


def speed(rows, i, c, span=10):
    a, b = max(0, i-span), min(len(rows)-1, i+span)
    if b <= a:
        return 0.0
    dt = float(rows[b]["Time"]) - float(rows[a]["Time"])
    if dt <= 0:
        return 0.0
    d = enu(rows[a], rows[b], c)
    v = math.sqrt(sum(x*x for x in d)) / dt
    return v if v < 700.0 else 0.0


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    if len(sys.argv) < 3:
        print(__doc__)
        return
    stamp, seed = sys.argv[1], int(sys.argv[2])
    t_from = float(sys.argv[3]) if len(sys.argv) > 3 else 0.0
    t_to = float(sys.argv[4]) if len(sys.argv) > 4 else 1e9
    step_s = float(sys.argv[5]) if len(sys.argv) > 5 else 1.0

    o = load(stamp, seed, "ownship", "(F-16)[Blue]")
    t = load(stamp, seed, "target", "(F-16)[Red]")
    n = min(len(o), len(t))
    c = math.cos(math.radians(float(o[0]["Latitude"])))
    t0 = float(o[0]["Time"])
    dt = (float(o[1]["Time"]) - float(o[0]["Time"])) if n > 1 else 1/60
    k = max(1, int(round(step_s / max(dt, 1e-9))))

    print(f"seed{seed}  stamp {stamp}")
    print(f"{'t':>6}{'거리':>7}{'우리ATA':>8}{'리드초':>7}{'리드거리':>9}"
          f"{'예측오차':>9}{'★리드이탈각':>12}{'상대선회율':>11}  v27리드감쇠")
    print("-" * 88)
    for i in range(0, n, k):
        et = float(o[i]["Time"]) - t0
        if et < t_from:
            continue
        if et > t_to:
            break
        d3 = enu(o[i], t[i], c)
        d = math.sqrt(sum(x*x for x in d3))
        mv = speed(o, i, c)
        tv = speed(t, i, c)
        if mv < 1.0:
            continue
        ma = angle(fwd(o[i]), d3)

        lead_s = min(LEAD_CAP_S, d / mv)
        tf = fwd(t[i])
        lead_pt = tuple(d3[j] + tf[j] * tv * lead_s for j in range(3))   # 우리 기준 상대좌표
        lead_len = tv * lead_s

        # leadTime 뒤 상대의 **실제** 위치(우리 현재 위치 기준)
        j = min(n - 1, i + int(round(lead_s / max(dt, 1e-9))))
        actual = enu(o[i], t[j], c)
        err = math.sqrt(sum((lead_pt[x] - actual[x])**2 for x in range(3)))

        # ★ 리드점이 기수를 상대에게서 떼어놓는 각
        dev = angle(lead_pt, d3)

        # 상대 선회율(1초 창)
        j1 = min(n - 1, i + int(round(1.0 / max(dt, 1e-9))))
        omega = angle(fwd(t[i]), fwd(t[j1]))

        fade = ""
        if d < V27_DIST_M and ma < V27_ATA_DEG:
            f = max(0.0, min(1.0, (ma - 3.0) / 7.0))
            fade = f"적용 x{f:.2f}"
        else:
            fade = "미적용(ATA>10)" if d < V27_DIST_M else "미적용(원거리)"

        print(f"{et:>6.1f}{d:>7.0f}{ma:>8.0f}{lead_s:>7.2f}{lead_len:>9.0f}"
              f"{err:>9.0f}{dev:>12.0f}{omega:>10.1f}°/s  {fade}")


if __name__ == "__main__":
    main()
