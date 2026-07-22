# 실제 데미지 조건 감사: WEZ = 152.4~914.4m AND |ATA| <= 1.0deg (angle_deg 2.0 / 2)
# 데미지 계수 = (914.4 - dist) / 762.0  -> 가까울수록 크다
import csv, math, sys, glob, os
R = r"C:\Users\TFX5470H\Desktop\.topgun\강화학습환경\Release\artifacts\logs"
MLAT = 111320.0
MINR, MAXR, HALF = 152.4, 914.4, 1.0

def load(p):
    rows = []
    with open(p, newline='', encoding='utf-8') as f:
        for r in csv.DictReader(f):
            rows.append((float(r['Time']), float(r['Longitude']), float(r['Latitude']),
                         float(r['Altitude']), float(r['Yaw (deg)']), float(r['Pitch (deg)'])))
    return rows

def ata_of(o, t, c):
    de = (t[1]-o[1])*c*MLAT; dn = (t[2]-o[2])*MLAT; du = t[3]-o[3]
    d = math.sqrt(de*de+dn*dn+du*du)
    if d < 1e-6: return 0.0, 0.0
    yr, pr = math.radians(o[4]), math.radians(o[5])
    fe, fn, fu = math.sin(yr)*math.cos(pr), math.cos(yr)*math.cos(pr), math.sin(pr)
    return math.degrees(math.acos(max(-1, min(1, (fe*de+fn*dn+fu*du)/d)))), d

stamp = sys.argv[1]
own = load(os.path.join(R, f"{stamp}_ownship_(F-16)[Blue].csv"))
tgt = load(os.path.join(R, f"{stamp}_target_(F-16)[Red].csv"))
n = min(len(own), len(tgt)); c = math.cos(math.radians(own[0][2]))

myHit = oppHit = 0; myDmg = oppDmg = 0.0
inRange = 0; bestATA = 999.0; bestAtBest = 0.0
buckets = {}
for i in range(n):
    o, t = own[i], tgt[i]
    myATA, d = ata_of(o, t, c)
    opATA, _ = ata_of(t, o, c)
    if MINR <= d <= MAXR:
        inRange += 1
        k = int(d // 100) * 100
        buckets[k] = min(buckets.get(k, 999.0), myATA)
        coef = (MAXR - d) / 762.0
        if myATA <= HALF: myHit += 1; myDmg += coef / 60.0
        if opATA <= HALF: oppHit += 1; oppDmg += coef / 60.0
        if myATA < bestATA: bestATA, bestAtBest = myATA, d

print(f"[{stamp}]  총 {n}틱 ({n/60:.0f}초)")
print(f"  사거리(152~914m) 체류 : {inRange}틱 ({inRange/60:.1f}초)")
print(f"  ★사격조건(|ATA|<=1.0) : 내가 {myHit}틱 / 상대가 {oppHit}틱")
print(f"  누적 데미지 추정       : 내가 준 {myDmg:.4f} / 내가 받은 {oppDmg:.4f}")
print(f"  사거리 내 최소 ATA     : {bestATA:.2f}deg @ {bestAtBest:.0f}m")
print("  거리대별 최소 ATA (사거리 내):")
for k in sorted(buckets):
    coef = (MAXR - (k+50)) / 762.0
    print(f"    {k:4d}~{k+100:4d}m : minATA {buckets[k]:5.1f}deg  (데미지계수 {max(coef,0):.2f})")
