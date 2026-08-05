# 실제 데미지 조건 감사.
#
# ★ 2026-08-06: 대회 공식 규칙과 대조해 **phase 인식**으로 전면 교체.
#   기존엔 `152.4~914.4m AND |ATA|<=1.0deg`를 200초 내내 적용했는데(= 대회 Phase 1),
#   대회는 100초/150초를 지나며 판정이 완화된다(LOS 1->2->3도, 사거리 3000->3500->4000ft).
#   즉 이 도구는 **후반 100초의 득점 기회를 통째로 못 보고 있었다.**
#   규칙은 tools_diag/wez_rule.py 한 곳에 모았다(상수 분산이 오늘만 4번 사고를 냈다).
import csv, math, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import wez_rule as W

try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass

R = r"C:\Users\TFX5470H\Desktop\.topgun\강화학습환경\Release\artifacts\logs"
MLAT = 111320.0

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
byphase = {p["name"]: 0 for p in W.PHASES}
# 구 기준(Phase 1 고정)과의 대조용 — 규칙 변경의 영향을 바로 보이게 한다
oldHit = 0
t0 = own[0][0]

for i in range(n):
    o, t = own[i], tgt[i]
    tm = o[0] - t0                     # 교전 경과 시간(에피소드 시작 기준)
    myATA, d = ata_of(o, t, c)
    opATA, _ = ata_of(t, o, c)
    if W.ABS_MIN_M <= d <= W.ABS_MAX_M:
        inRange += 1
        k = int(d // 100) * 100
        buckets[k] = min(buckets.get(k, 999.0), myATA)
        if d <= 914.4 and myATA < bestATA: bestATA, bestAtBest = myATA, d

        ok, ph = W.hit(tm, d, myATA)
        if ok:
            myHit += 1; byphase[ph] += 1
            myDmg += W.damage(tm, d, myATA, dt=1.0/60.0)
        if W.hit(tm, d, opATA)[0]:
            oppHit += 1; oppDmg += W.damage(tm, d, opATA, dt=1.0/60.0)
        if 152.4 <= d <= 914.4 and myATA <= 1.0: oldHit += 1

print(f"[{stamp}]  총 {n}틱 ({n/60:.0f}초)")
print(f"  사거리(152~1219m, 전 phase 포괄) 체류 : {inRange}틱 ({inRange/60:.1f}초)")
print(f"  ★사격 성립 : 내가 {myHit}틱 / 상대가 {oppHit}틱")
print(f"     phase별 내 성립: " + " / ".join(f"{k} {v}틱" for k, v in byphase.items()))
print(f"     (구 기준 Phase1 고정이었다면 {oldHit}틱 — 차이 {myHit-oldHit:+d})")
print(f"  누적 데미지 추정 : 내가 준 {myDmg:.4f} / 내가 받은 {oppDmg:.4f}")
print(f"  Phase1 사거리 내 최소 ATA : {bestATA:.2f}deg @ {bestAtBest:.0f}m")
print("  거리대별 최소 ATA:")
for k in sorted(buckets):
    print(f"    {k:4d}~{k+100:4d}m : minATA {buckets[k]:5.1f}deg")
