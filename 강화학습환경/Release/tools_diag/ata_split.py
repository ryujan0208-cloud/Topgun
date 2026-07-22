# ATA를 "수평(요) 성분"과 "수직(피치) 성분"으로 분해한다.
# 목적: 조준이 안 되는 원인이 좌우인지 상하인지 가린다.
#  - 수직이 지배적이면 -> VP의 Z 클램프(diveSlope=dist*0.2)가 범인
#  - 수평이 지배적이면 -> 리드 조준 / 선회 추종이 범인
import csv, math, sys, os
R = r"C:\Users\TFX5470H\Desktop\.topgun\강화학습환경\Release\artifacts\logs"
MLAT = 111320.0
MINR, MAXR = 152.4, 914.4

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
    rows.append((o[0], d, ata, az, el, du, dist_clamp := d*0.2))

inr = [r for r in rows if MINR <= r[1] <= MAXR]
print(f"[{stamp}] 사거리 내 {len(inr)}틱 ({len(inr)/60:.1f}초)")
if not inr: sys.exit()

import statistics as st
print(f"  |수평오차 az| 중앙값 {st.median(abs(r[3]) for r in inr):6.2f}deg   "
      f"|수직오차 el| 중앙값 {st.median(abs(r[4]) for r in inr):6.2f}deg")
print(f"  고도차(상대-나) 중앙값 {st.median(r[5] for r in inr):+7.1f}m  "
      f"(음수=상대가 아래)")

# Z 클램프에 걸렸는지: |고도차| > dist*0.2 이면 VP가 잘린다
clipped = [r for r in inr if r[5] < -r[6]]
print(f"  ★VP Z클램프 발동(상대가 dist*0.2보다 아래): {len(clipped)}/{len(inr)}틱 "
      f"({100*len(clipped)/len(inr):.1f}%)")

# 최소 ATA 상위 구간에서 성분 비교
best = sorted(inr, key=lambda r: r[2])[:400]
print(f"\n  [조준이 가장 잘 된 400틱]")
print(f"    ATA 중앙값 {st.median(r[2] for r in best):.2f}deg = "
      f"수평 {st.median(abs(r[3]) for r in best):.2f} / 수직 {st.median(abs(r[4]) for r in best):.2f}")
print(f"    고도차 중앙값 {st.median(r[5] for r in best):+.1f}m, "
      f"Z클램프 발동 {sum(1 for r in best if r[5] < -r[6])}/400틱")

print(f"\n   t  |  dist | ATA  |  az    el   | 고도차 | 클램프한계")
for r in best[:12]:
    flag = "  <-잘림" if r[5] < -r[6] else ""
    print(f" {r[0]:5.1f} | {r[1]:5.0f} | {r[2]:4.1f} | {r[3]:+6.1f} {r[4]:+6.1f} | {r[5]:+6.0f} | {-r[6]:+6.0f}{flag}")
