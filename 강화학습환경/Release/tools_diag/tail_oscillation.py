# -*- coding: utf-8 -*-
"""뒤를 잡은 뒤 왜 유지 못 하고 진동하다 추월하는가.

[사용자 관찰 — 리플레이]
  "충분히 가까워졌음에도 뒤를 잡고 동일선상에 유지한 채 지속을 못하고
   마치 사인함수처럼 왔다갔다 하다 결국 상대기체를 추월해 되려 뒤를 잡혀준다."

[가설] `Task_LeadPredict`의 v21 뱅크 횡예측이 **상대 롤 부호로 조준점을 좌우로 민다.**
    if (|roll|>10 && omegaNow>0.06)
        s = sign(roll);  turnMag = (|roll|/90)*0.25*dist  (<=600m, dist<600이면 축소)
        predicted += TgtRight * (s * turnMag)
  상대가 롤을 뒤집으면 조준점이 좌우로 튄다. 원 설계는 그걸 막으려 `omega>0.06` 게이트를
  뒀지만(주석: "롤 위글은 무시한다"), **dt 버그로 omega가 6~9배라 게이트가 항상 열린다.**

[측정] 뒤를 잡은 국면에서
  - 상대 롤 부호가 몇 번 뒤집히는가
  - 그때 v21이 조준점을 얼마나 미는가(turnMag, 실제 공식 그대로)
  - 우리 기수 방향이 따라서 진동하는가 (우리 롤 부호 전환 횟수)

사용: python tools_diag/tail_oscillation.py <stamp> <seed> [시작초] [끝초]
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


def v21_turnmag(roll_deg, dist_m):
    """Task_LeadPredict의 v21 공식 그대로."""
    if abs(roll_deg) <= 10.0:
        return 0.0
    bank = min(1.0, abs(roll_deg) / 90.0)
    mag = bank * 0.25 * dist_m
    if mag > 600.0:
        mag = 600.0
    if dist_m < 600.0:
        mag *= dist_m / 600.0
    return mag * (1.0 if roll_deg > 0 else -1.0)


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

    o = load(stamp, seed, "ownship", "(F-16)[Blue]")
    t = load(stamp, seed, "target", "(F-16)[Red]")
    n = min(len(o), len(t))
    c = math.cos(math.radians(float(o[0]["Latitude"])))
    t0 = float(o[0]["Time"])
    dt = (float(o[1]["Time"]) - float(o[0]["Time"])) if n > 1 else 1/60
    k = max(1, int(round(0.5 / max(dt, 1e-9))))          # 0.5초 간격

    print(f"seed{seed}  stamp {stamp}   (0.5초 간격)")
    print(f"{'t':>6}{'거리':>7}{'우리ATA':>8}{'상대롤':>8}{'v21횡이동':>11}"
          f"{'우리롤':>8}{'우리기수변화':>12}")
    print("-" * 62)
    prev_s = None
    flips_t = 0
    flips_o = 0
    prev_so = None
    mags = []
    rows_shown = 0
    for i in range(0, n - k, k):
        et = float(o[i]["Time"]) - t0
        if et < t_from:
            continue
        if et > t_to:
            break
        de = (float(t[i]["Longitude"]) - float(o[i]["Longitude"])) * c * MLAT
        dn = (float(t[i]["Latitude"]) - float(o[i]["Latitude"])) * MLAT
        du = float(t[i]["Altitude"]) - float(o[i]["Altitude"])
        d = math.sqrt(de*de + dn*dn + du*du)
        yr = math.radians(float(o[i]["Yaw (deg)"]))
        pr = math.radians(float(o[i]["Pitch (deg)"]))
        fe, fn, fu = math.sin(yr)*math.cos(pr), math.cos(yr)*math.cos(pr), math.sin(pr)
        ma = math.degrees(math.acos(max(-1.0, min(1.0, (fe*de+fn*dn+fu*du)/max(d, 1e-6)))))

        troll = float(t[i]["Roll (deg)"])
        oroll = float(o[i]["Roll (deg)"])
        mag = v21_turnmag(troll, d)
        mags.append(abs(mag))

        s = 1 if troll > 0 else -1
        if prev_s is not None and s != prev_s and abs(troll) > 10:
            flips_t += 1
        prev_s = s
        so = 1 if oroll > 0 else -1
        if prev_so is not None and so != prev_so and abs(oroll) > 10:
            flips_o += 1
        prev_so = so

        # 우리 기수 변화(0.5초)
        yr2 = math.radians(float(o[i+k]["Yaw (deg)"]))
        pr2 = math.radians(float(o[i+k]["Pitch (deg)"]))
        f2 = (math.sin(yr2)*math.cos(pr2), math.cos(yr2)*math.cos(pr2), math.sin(pr2))
        dh = math.degrees(math.acos(max(-1.0, min(1.0, fe*f2[0]+fn*f2[1]+fu*f2[2]))))

        print(f"{et:>6.1f}{d:>7.0f}{ma:>8.0f}{troll:>8.0f}{mag:>+11.0f}"
              f"{oroll:>8.0f}{dh:>11.1f}°")
        rows_shown += 1

    if rows_shown:
        import statistics as st
        print("-" * 62)
        print(f"  상대 롤 부호 전환 {flips_t}회 / 우리 롤 부호 전환 {flips_o}회 "
              f"({rows_shown*0.5:.0f}초 구간)")
        print(f"  v21 횡이동 중앙 {st.median(mags):.0f}m / 최대 {max(mags):.0f}m")
        print(f"  -> 상대가 롤을 뒤집을 때마다 조준점이 좌우로 그만큼 튄다.")


if __name__ == "__main__":
    main()
