# -*- coding: utf-8 -*-
"""방어 시작(OBFM_RED)에서 왜 못 빠져나오는지 부검한다.

[배경] 대회조건 S1에서 방어 시작 전적이 v40 2승 28패 / v32 2승 28패다.
  버전 차이가 전혀 없다 = 지금까지의 개선이 방어 국면엔 아무 영향도 못 줬다.

[핵심 질문] **상대가 한 번이라도 추월(overshoot)하는가?**
  BFM에서 방어자의 일은 상대를 추월시킨 뒤 반전해 각도를 되찾는 것이다.
    - 추월이 아예 없다   -> 기동으로 못 푼다(성능/에너지 문제)
    - 추월은 나오는데 못 살린다 -> **반전 로직이 없는 것. 고칠 수 있다**

[측정]
  1. 생존시간 / 첫 피격 시각
  2. **추월 사건**: 상대 ATA가 임계를 넘는 순간(= 상대 기수가 우리에게서 벗어남)
     + 그때 거리가 가까울 것(교전거리). 지속시간과 최대 상대ATA를 함께 잰다
  3. 추월 직후 3초 동안 **우리 ATA가 줄었는가**(= 반전해서 각도를 되찾았는가)
  4. 우리·상대 속도와 고도(에너지 상태)

사용: python tools_diag/defensive_forensics.py <stamp> [라벨]
"""
import csv
import math
import os
import sys

R = r"C:\Users\TFX5470H\Desktop\.topgun\강화학습환경\Release\artifacts\logs"
MLAT = 111320.0

# 추월 판정: 상대 기수가 우리에게서 이만큼 벗어나고, 교전거리 안일 것.
OVERSHOOT_ATA_DEG = 50.0
OVERSHOOT_RANGE_M = 1200.0
RECOVER_WINDOW_S = 3.0


def load(stamp, side, tag):
    p = os.path.join(R, f"{stamp}_{side}_{tag}.csv")
    with open(p, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def fwd(r):
    yr, pr = math.radians(float(r["Yaw (deg)"])), math.radians(float(r["Pitch (deg)"]))
    return (math.sin(yr)*math.cos(pr), math.cos(yr)*math.cos(pr), math.sin(pr))


def ang(u, v):
    du = math.sqrt(sum(x*x for x in u)); dv = math.sqrt(sum(x*x for x in v))
    d = sum(a*b for a, b in zip(u, v)) / max(du*dv, 1e-9)
    return math.degrees(math.acos(max(-1.0, min(1.0, d))))


def speed(rows, i, c, span=15):
    a, b = max(0, i-span), min(len(rows)-1, i+span)
    dt = float(rows[b]["Time"]) - float(rows[a]["Time"])
    if dt <= 0:
        return 0.0
    de = (float(rows[b]["Longitude"]) - float(rows[a]["Longitude"])) * c * MLAT
    dn = (float(rows[b]["Latitude"]) - float(rows[a]["Latitude"])) * MLAT
    du = float(rows[b]["Altitude"]) - float(rows[a]["Altitude"])
    v = math.sqrt(de*de + dn*dn + du*du) / dt
    return v if v < 700.0 else 0.0


def analyze(stamp):
    o = load(stamp, "ownship", "(F-16)[Blue]")
    t = load(stamp, "target", "(F-16)[Red]")
    n = min(len(o), len(t))
    if n < 2:
        return None
    c = math.cos(math.radians(float(o[0]["Latitude"])))
    t0 = float(o[0]["Time"])
    dt = float(o[1]["Time"]) - float(o[0]["Time"])

    series = []
    for i in range(n):
        de = (float(t[i]["Longitude"]) - float(o[i]["Longitude"])) * c * MLAT
        dn = (float(t[i]["Latitude"]) - float(o[i]["Latitude"])) * MLAT
        du = float(t[i]["Altitude"]) - float(o[i]["Altitude"])
        d = math.sqrt(de*de + dn*dn + du*du)
        los = (de, dn, du)
        ma = ang(fwd(o[i]), los)                    # 우리 ATA
        ta = ang(fwd(t[i]), (-de, -dn, -du))        # 상대 ATA
        series.append((float(o[i]["Time"]) - t0, d, ma, ta,
                       float(o[i]["Health"]), float(t[i]["Health"]),
                       float(o[i]["Altitude"])))

    # 첫 피격
    first_hit = None
    prev = 1.0
    for k, s in enumerate(series):
        if s[4] < prev - 1e-6:
            first_hit = k
            break
        prev = min(prev, s[4])

    # 추월 사건: 상대ATA가 임계를 넘고 교전거리 안 (연속 구간을 하나로 묶는다)
    events = []
    k = 0
    step = max(1, int(round(0.1 / max(dt, 1e-9))))
    while k < n:
        s = series[k]
        if s[3] >= OVERSHOOT_ATA_DEG and s[1] <= OVERSHOOT_RANGE_M:
            j = k
            peak = s[3]
            while j < n and series[j][3] >= OVERSHOOT_ATA_DEG and series[j][1] <= OVERSHOOT_RANGE_M:
                peak = max(peak, series[j][3])
                j += 1
            dur = series[min(j, n-1)][0] - s[0]
            if dur >= 0.5:                      # 스치는 노이즈 제외
                # 추월 직후 우리 ATA가 줄었는가 = 반전해서 각도를 되찾았는가
                e = min(n-1, j + int(round(RECOVER_WINDOW_S / max(dt, 1e-9))))
                events.append({
                    "t": s[0], "dur": dur, "peak_tgt_ata": peak,
                    "dist": s[1], "my_ata_at": s[2], "my_ata_after": series[e][2],
                })
            k = j
        k += step

    ohp, thp = series[-1][4], series[-1][5]
    return {
        "stamp": stamp, "dur_s": series[-1][0],
        "ownHP": ohp, "tgtHP": thp,
        "first_hit_s": series[first_hit][0] if first_hit is not None else None,
        "events": events,
        "own_spd": speed(o, n//2, c), "tgt_spd": speed(t, n//2, c),
        "own_alt_end": series[-1][6],
    }


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    if len(sys.argv) < 2:
        print(__doc__)
        return
    stamps = sys.argv[1:]
    print(f"{'stamp':<22}{'생존':>7}{'첫피격':>8}{'ownHP':>8}{'추월수':>7}"
          f"{'총추월초':>9}{'최대상대ATA':>12}{'반전성공':>9}")
    print("-" * 84)
    tot_ev = tot_rec = 0
    for s in stamps:
        try:
            r = analyze(s)
        except FileNotFoundError:
            print(f"{s:<22}  로그 없음"); continue
        if not r:
            continue
        ev = r["events"]
        # 반전 성공 = 추월 직후 3초에 우리 ATA가 30도 이상 줄었다
        rec = sum(1 for e in ev if e["my_ata_at"] - e["my_ata_after"] >= 30.0)
        tot_ev += len(ev); tot_rec += rec
        fh = f"{r['first_hit_s']:.0f}s" if r["first_hit_s"] is not None else "-"
        pk = max((e["peak_tgt_ata"] for e in ev), default=0.0)
        print(f"{s:<22}{r['dur_s']:>6.0f}s{fh:>8}{r['ownHP']:>8.3f}{len(ev):>7}"
              f"{sum(e['dur'] for e in ev):>9.1f}{pk:>12.0f}{rec:>9}")
    print("-" * 84)
    print(f"  추월 사건 총 {tot_ev}건 / 그중 반전 성공 {tot_rec}건")
    print(f"  (추월 = 상대ATA >= {OVERSHOOT_ATA_DEG:.0f}도 AND 거리 <= {OVERSHOOT_RANGE_M:.0f}m, 0.5초 이상 지속)")
    print(f"  (반전 성공 = 추월 종료 후 {RECOVER_WINDOW_S:.0f}초 안에 우리 ATA가 30도 이상 감소)")


if __name__ == "__main__":
    main()
