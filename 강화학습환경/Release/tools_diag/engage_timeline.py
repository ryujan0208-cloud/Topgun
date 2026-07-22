# -*- coding: utf-8 -*-
# 교전 성립 진단: 10초 간격으로 거리/내ATA/상대ATA/AA근사/고도차를 찍는다.
# 목적: "사거리에 아예 못 들어가는 판"에서 무엇이 접근을 막는지 본다.
#  - 내 ATA 크고 거리 유지 -> 우리가 안 쫓는 것(Evade/ClimbOut 등 다른 분기?)
#  - 내 ATA 작은데 거리 안 줄어듦 -> 쫓는데 못 따라잡는 것(속도/기하)
#  - 상대 ATA 작음 -> 상대가 우리를 물고 있는 것
import csv, math, sys, os
R = r"C:\Users\TFX5470H\Desktop\.topgun\강화학습환경\Release\artifacts\logs"
MLAT = 111320.0

def load(p):
    rows = []
    with open(p, newline='', encoding='utf-8') as f:
        for r in csv.DictReader(f):
            rows.append((float(r['Time']), float(r['Longitude']), float(r['Latitude']),
                         float(r['Altitude']), float(r['Yaw (deg)']), float(r['Pitch (deg)'])))
    return rows

def fwd(yaw, pit):
    yr, pr = math.radians(yaw), math.radians(pit)
    return (math.sin(yr)*math.cos(pr), math.cos(yr)*math.cos(pr), math.sin(pr))

def ata(o, t, c):
    de = (t[1]-o[1])*c*MLAT; dn = (t[2]-o[2])*MLAT; du = t[3]-o[3]
    d = math.sqrt(de*de+dn*dn+du*du)
    if d < 1e-6: return 0.0, 0.0
    fe, fn, fu = fwd(o[4], o[5])
    return math.degrees(math.acos(max(-1, min(1, (fe*de+fn*dn+fu*du)/d)))), d

stamp = sys.argv[1]
own = load(os.path.join(R, f"{stamp}_ownship_(F-16)[Blue].csv"))
tgt = load(os.path.join(R, f"{stamp}_target_(F-16)[Red].csv"))
n = min(len(own), len(tgt)); c = math.cos(math.radians(own[0][2]))

print(f"[{stamp}]")
print("   t  |  dist  | 내ATA 상대ATA |  내고도  상대고도")
for i in range(0, n, 600):
    o, t = own[i], tgt[i]
    a1, d = ata(o, t, c)
    a2, _ = ata(t, o, c)
    print(f" {o[0]:5.0f} | {d:6.0f} | {a1:5.0f} {a2:6.0f} | {o[3]:7.0f} {t[3]:8.0f}")

# 요약 통계
a1s = []; a2s = []; ds = []
for i in range(n):
    a1, d = ata(own[i], tgt[i], c)
    a2, _ = ata(tgt[i], own[i], c)
    a1s.append(a1); a2s.append(a2); ds.append(d)
import statistics as st
print(f"\n  거리: 중앙 {st.median(ds):.0f}m / 최소 {min(ds):.0f}m")
print(f"  내ATA 중앙 {st.median(a1s):.0f}deg / 상대ATA 중앙 {st.median(a2s):.0f}deg")
print(f"  내가 무는 중(내ATA<45) {100*sum(1 for a in a1s if a<45)/n:.0f}% / "
      f"물리는 중(상대ATA<45) {100*sum(1 for a in a2s if a2 is not None and a<45)/n:.0f}%")
