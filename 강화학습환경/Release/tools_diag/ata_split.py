# ATA를 "수평(요) 성분"과 "수직(피치) 성분"으로 분해한다.
# 목적: 조준이 안 되는 원인이 좌우인지 상하인지 가린다.
#  - 수직이 지배적이면 -> VP의 Z 클램프가 범인
#  - 수평이 지배적이면 -> 리드 조준 / 선회 추종이 범인
#
# ★ 2026-08-04 수정 2건 (alt_trace.py와 같은 사고: 도구가 코드를 못 따라감)
#  (1) 상수가 v17 시절 dist*0.2로 박혀 있었다. 현재 코드는 climbSlope=diveSlope=dist*0.5.
#  (2) **아래쪽 클램프만 보고 있었다.** 정작 실측에서 반복되는 건 "상대가 위에 있을 때
#      조준 실패"다(v17 수직 22.88deg / v22 실패판 고도차 +202,+439m / onecircle +289m).
#      위/아래를 나눠서 센다.
#
# 핵심: climbSlope=diveSlope=dist*0.5 는 거리와 무관하게 **최대 앙각 atan(0.5)=26.57deg**를 뜻한다.
#      상대가 그보다 가파르게 위/아래에 있으면 VP가 구조적으로 그쪽을 못 가리킨다.
import csv, math, sys, os
R = r"C:\Users\TFX5470H\Desktop\.topgun\강화학습환경\Release\artifacts\logs"
MLAT = 111320.0
MINR, MAXR = 152.4, 914.4
SLOPE = float(sys.argv[2]) if len(sys.argv) > 2 else 0.5   # 코드의 climbSlope/diveSlope 계수
DIVE_CAP = 650.0                                            # v20: 강하만 절대 상한
CLAMP_DEG = math.degrees(math.atan(SLOPE))

def load(p):
    rows = []
    with open(p, newline='', encoding='utf-8') as f:
        for r in csv.DictReader(f):
            rows.append((float(r['Time']), float(r['Longitude']), float(r['Latitude']),
                         float(r['Altitude']), float(r['Yaw (deg)']), float(r['Pitch (deg)']),
                         float(r['Roll (deg)'])))
    return rows

stamp = sys.argv[1]
own = load(os.path.join(R, f"{stamp}_ownship_(F-16)[Blue].csv"))
tgt = load(os.path.join(R, f"{stamp}_target_(F-16)[Red].csv"))
n = min(len(own), len(tgt)); c = math.cos(math.radians(own[0][2]))

rows = []
for i in range(n):
    o, t = own[i], tgt[i]
    de = (t[1]-o[1])*c*MLAT; dn = (t[2]-o[2])*MLAT; du = t[3]-o[3]
    d = math.sqrt(de*de+dn*dn+du*du)
    if d < 1e-6: continue
    # 내 기수의 방위/고각
    myYaw, myPit = math.radians(o[4]), math.radians(o[5])
    # 상대 방향의 방위/고각
    tgtBear = math.atan2(de, dn)
    tgtElev = math.asin(max(-1, min(1, du/d)))
    # 수평 오차(방위차, -180~180), 수직 오차(고각차)
    az = math.degrees((tgtBear - myYaw + math.pi) % (2*math.pi) - math.pi)
    el = math.degrees(tgtElev - myPit)
    fe, fn, fu = math.sin(myYaw)*math.cos(myPit), math.cos(myYaw)*math.cos(myPit), math.sin(myPit)
    ata = math.degrees(math.acos(max(-1, min(1, (fe*de+fn*dn+fu*du)/d))))
    # 위쪽 한계 = +d*SLOPE (상한 없음) / 아래쪽 한계 = -min(d*SLOPE, 650) (v20 절대 상한)
    up_lim = d * SLOPE
    dn_lim = min(d * SLOPE, DIVE_CAP)
    rows.append((o[0], d, ata, az, el, du, up_lim, dn_lim))

inr = [r for r in rows if MINR <= r[1] <= MAXR]
print(f"[{stamp}] 사거리 내 {len(inr)}틱 ({len(inr)/60:.1f}초)")
if not inr: sys.exit()

import statistics as st
print(f"  |수평오차 az| 중앙값 {st.median(abs(r[3]) for r in inr):6.2f}deg   "
      f"|수직오차 el| 중앙값 {st.median(abs(r[4]) for r in inr):6.2f}deg")
print(f"  고도차(상대-나) 중앙값 {st.median(r[5] for r in inr):+7.1f}m  "
      f"(음수=상대가 아래)")

# Z 클램프: 고도차가 한계를 넘으면 VP가 그 방향을 못 가리킨다. 위/아래를 나눠 센다.
up_clip = [r for r in inr if r[5] >  r[6]]     # 상대가 위쪽 한계보다 더 위
dn_clip = [r for r in inr if r[5] < -r[7]]     # 상대가 아래쪽 한계보다 더 아래
print(f"  ★VP Z클램프 (한계 앙각 {CLAMP_DEG:.1f}deg, slope {SLOPE})")
print(f"     위로 잘림(상대가 더 위) : {len(up_clip):5d}/{len(inr)}틱 "
      f"({100*len(up_clip)/len(inr):5.1f}%)")
print(f"     아래로 잘림(상대가 더 아래): {len(dn_clip):5d}/{len(inr)}틱 "
      f"({100*len(dn_clip)/len(inr):5.1f}%)")
if up_clip:
    print(f"     └ 위로 잘린 틱의 필요앙각 중앙값 "
          f"{st.median(math.degrees(math.atan2(r[5], max(1.0, math.sqrt(max(0.0, r[1]**2 - r[5]**2))))) for r in up_clip):.1f}deg")

# 최소 ATA 상위 구간에서 성분 비교
best = sorted(inr, key=lambda r: r[2])[:400]
print(f"\n  [조준이 가장 잘 된 400틱]")
print(f"    ATA 중앙값 {st.median(r[2] for r in best):.2f}deg = "
      f"수평 {st.median(abs(r[3]) for r in best):.2f} / 수직 {st.median(abs(r[4]) for r in best):.2f}")
print(f"    고도차 중앙값 {st.median(r[5] for r in best):+.1f}m, "
      f"위로잘림 {sum(1 for r in best if r[5] > r[6])}/400틱, "
      f"아래로잘림 {sum(1 for r in best if r[5] < -r[7])}/400틱")

print(f"\n   t  |  dist | ATA  |  az    el   | 고도차 | 위한계 아래한계")
for r in best[:12]:
    flag = "  <-위로잘림" if r[5] > r[6] else ("  <-아래로잘림" if r[5] < -r[7] else "")
    print(f" {r[0]:5.1f} | {r[1]:5.0f} | {r[2]:4.1f} | {r[3]:+6.1f} {r[4]:+6.1f} | {r[5]:+6.0f} | "
          f"{r[6]:+6.0f} {-r[7]:+7.0f}{flag}")
