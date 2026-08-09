# -*- coding: utf-8 -*-
"""유리했던 국면이 뒤집히는 구간을 초 단위로 펼쳐 본다.

[왜] 신형 도전자전 11패는 전부 dead-six에서 끝나는데, 그 15초 전에는
우리가 유리한 판이 있었다(seed 0·6·9). **어디서 어떻게 뒤집히는지**를
집계값이 아니라 시계열로 봐야 기동을 특정할 수 있다.

출력: 시각 / 거리 / 우리ATA / 상대ATA / 양쪽 속도·고도·뱅크·피치 / 고도차
     ATA는 "기수와 상대방향의 각". 우리ATA가 작으면 우리가 겨눈 것,
     상대ATA가 작으면 상대가 우리를 겨눈 것이다.

사용: python tools_diag/reversal_window.py <stamp> <seed> [시작초] [끝초] [간격초]
"""
import csv
import math
import os
import sys

R = r"C:\Users\TFX5470H\Desktop\.topgun\강화학습환경\Release\artifacts\logs"
MLAT = 111320.0


def load(stamp, seed, side, tag):
    p = os.path.join(R, f"{stamp}_s{seed:02d}_{side}_{tag}.csv")
    with open(p, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def speed(rows, i, c, span=10):
    """위치 차분 속도(m/s). span 샘플 간격으로 재 노이즈를 줄인다."""
    a = max(0, i - span)
    b = min(len(rows) - 1, i + span)
    if b <= a:
        return 0.0
    dt = float(rows[b]["Time"]) - float(rows[a]["Time"])
    if dt <= 0:
        return 0.0
    de = (float(rows[b]["Longitude"]) - float(rows[a]["Longitude"])) * c * MLAT
    dn = (float(rows[b]["Latitude"]) - float(rows[a]["Latitude"])) * MLAT
    du = float(rows[b]["Altitude"]) - float(rows[a]["Altitude"])
    v = math.sqrt(de*de + dn*dn + du*du) / dt
    return v if v < 700.0 else 0.0        # 판 경계 튐 방지


def ata(src, de, dn, du, d):
    yr = math.radians(float(src["Yaw (deg)"]))
    pr = math.radians(float(src["Pitch (deg)"]))
    fe, fn, fu = math.sin(yr)*math.cos(pr), math.cos(yr)*math.cos(pr), math.sin(pr)
    return math.degrees(math.acos(max(-1.0, min(1.0, (fe*de + fn*dn + fu*du) / max(d, 1e-6)))))


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    if len(sys.argv) < 3:
        print(__doc__)
        return
    stamp = sys.argv[1]
    seed = int(sys.argv[2])
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

    print(f"seed{seed}  stamp {stamp}  샘플 {n}  간격 {dt*1000:.1f}ms")
    print(f"{'t':>6}{'거리':>7}{'우리ATA':>8}{'상대ATA':>8}"
          f"{'우속도':>7}{'적속도':>7}{'우고도':>7}{'적고도':>7}{'고도차':>7}"
          f"{'우뱅크':>7}{'적뱅크':>7}{'우피치':>7}{'적피치':>7}  HP")
    print("-" * 104)
    prev_hp = None
    for i in range(0, n, k):
        et = float(o[i]["Time"]) - t0
        if et < t_from:
            continue
        if et > t_to:
            break
        de = (float(t[i]["Longitude"]) - float(o[i]["Longitude"])) * c * MLAT
        dn = (float(t[i]["Latitude"]) - float(o[i]["Latitude"])) * MLAT
        du = float(t[i]["Altitude"]) - float(o[i]["Altitude"])
        d = math.sqrt(de*de + dn*dn + du*du)
        ma = ata(o[i], de, dn, du, d)
        ta = ata(t[i], -de, -dn, -du, d)
        oz, tz = float(o[i]["Altitude"]), float(t[i]["Altitude"])
        ohp, thp = float(o[i]["Health"]), float(t[i]["Health"])
        mark = ""
        if prev_hp is not None and ohp < prev_hp - 1e-9:
            mark = "  <- 우리 피격"
        prev_hp = ohp
        # ★ 트랙 CSV에 속도 열이 없다(Time/Lon/Lat/Alt/Roll/Pitch/Yaw/Health뿐).
        #   위치 차분으로 낸다. 추월(overshoot) 진단엔 속도와 폐쇄율이 핵심이다.
        ov = speed(o, i, c)
        tv = speed(t, i, c)
        print(f"{et:>6.1f}{d:>7.0f}{ma:>8.0f}{ta:>8.0f}"
              f"{ov:>7.0f}{tv:>7.0f}{oz:>7.0f}{tz:>7.0f}{tz-oz:>7.0f}"
              f"{float(o[i]['Roll (deg)']):>7.0f}{float(t[i]['Roll (deg)']):>7.0f}"
              f"{float(o[i]['Pitch (deg)']):>7.0f}{float(t[i]['Pitch (deg)']):>7.0f}"
              f"  {ohp:.3f}/{thp:.3f}{mark}")


if __name__ == "__main__":
    main()
