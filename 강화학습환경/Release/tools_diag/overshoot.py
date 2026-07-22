# 추월(오버슈트) 메커니즘 규명: "뒤를 잡은 구간 -> 추월"의 틱 단위 추적.
# 뒤 잡음 = ATA<45 & dist<1500. 그 구간에서 거리 최소점(=최근접) 전후를 출력.
import csv, math, sys, glob, os
R = r"C:\Users\TFX5470H\Desktop\.topgun\강화학습환경\Release\artifacts\logs"
MLAT = 111320.0

def load(p):
    rows = []
    with open(p, newline='', encoding='utf-8') as f:
        for r in csv.DictReader(f):
            rows.append((float(r['Time']), float(r['Longitude']), float(r['Latitude']),
                         float(r['Altitude']), float(r['Yaw (deg)']), float(r['Pitch (deg)']),
                         float(r['Roll (deg)'])))
    return rows

stamp = sys.argv[1] if len(sys.argv) > 1 else os.path.basename(
    max(glob.glob(os.path.join(R, "*_ownship_*.csv")), key=os.path.getmtime)).split("_ownship")[0]
own = load(os.path.join(R, f"{stamp}_ownship_(F-16)[Blue].csv"))
tgt = load(os.path.join(R, f"{stamp}_target_(F-16)[Red].csv"))
n = min(len(own), len(tgt)); lat0 = own[0][2]; c = math.cos(math.radians(lat0))

def xy(r): return ((r[1]-own[0][1])*c*MLAT, (r[2]-own[0][2])*MLAT)
rec = []
for i in range(n):
    o, t = own[i], tgt[i]
    de = (t[1]-o[1])*c*MLAT; dn = (t[2]-o[2])*MLAT; du = t[3]-o[3]
    d = math.sqrt(de*de+dn*dn+du*du)
    if d < 1e-6: continue
    yr, pr = math.radians(o[4]), math.radians(o[5])
    fe, fn, fu = math.sin(yr)*math.cos(pr), math.cos(yr)*math.cos(pr), math.sin(pr)
    ata = math.degrees(math.acos(max(-1, min(1, (fe*de+fn*dn+fu*du)/d))))
    rec.append({'t': o[0], 'd': d, 'ata': ata, 'i': i, 'tRoll': t[6]})

def spd(rows, i, k=6):
    if i < k: return 0.0
    (x0,y0),(x1,y1) = xy(rows[i-k]), xy(rows[i])
    dz = rows[i][3]-rows[i-k][3]; dt = rows[i][0]-rows[i-k][0]
    return math.sqrt((x1-x0)**2+(y1-y0)**2+dz*dz)/dt if dt > 0 else 0.0

# 뒤 잡은 구간(ATA<45 & dist<1500) 찾기
inbox = [r for r in rec if r['ata'] < 45 and r['d'] < 1500]
print(f"[{stamp}]  뒤잡음(ATA<45 & <1500m) 총 {len(inbox)}틱 ({len(inbox)/60:.1f}초)")
if not inbox:
    print("  뒤를 잡은 구간이 없음"); sys.exit()

# 연속 구간으로 묶기
runs, cur = [], [inbox[0]]
for r in inbox[1:]:
    if r['i'] - cur[-1]['i'] <= 30: cur.append(r)
    else: runs.append(cur); cur = [r]
runs.append(cur)
runs.sort(key=len, reverse=True)
print(f"  연속 구간 {len(runs)}개, 최장 {len(runs[0])}틱 ({len(runs[0])/60:.1f}초)\n")

for ri, run in enumerate(runs[:2]):
    lo, hi = run[0]['i'], run[-1]['i']
    # 이 구간 전후 확장해서 최근접점 전후를 본다
    seg = [r for r in rec if lo-120 <= r['i'] <= hi+240]
    mn = min(seg, key=lambda r: r['d'])
    print(f"=== 구간{ri+1}: t={run[0]['t']:.1f}~{run[-1]['t']:.1f}s, 최근접 {mn['d']:.0f}m @t={mn['t']:.1f}s ===")
    print("   t |  dist | ATA  | ownSpd tgtSpd | dV   | tgtRoll")
    for r in seg:
        if (r['i'] - mn['i']) % 30: continue
        if abs(r['t'] - mn['t']) > 8.0: continue
        os_, ts_ = spd(own, r['i']), spd(tgt, r['i'])
        print(f" {r['t']:5.1f} | {r['d']:5.0f} | {r['ata']:4.0f} | {os_:5.0f}  {ts_:5.0f} | {os_-ts_:+5.0f} | {r['tRoll']:+6.1f}")
    print()
