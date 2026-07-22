# 고도 추이 추적: 고도차가 시간에 따라 벌어지는가(구조적 편향)?
# 그리고 VP Z 하한(3500m) / ClimbOut(3000m) 트리거에 걸리는가?
import csv, math, sys, os
R = r"C:\Users\TFX5470H\Desktop\.topgun\강화학습환경\Release\artifacts\logs"
MLAT = 111320.0

def load(p):
    rows = []
    with open(p, newline='', encoding='utf-8') as f:
        for r in csv.DictReader(f):
            rows.append((float(r['Time']), float(r['Longitude']), float(r['Latitude']),
                         float(r['Altitude']), float(r['Pitch (deg)'])))
    return rows

stamp = sys.argv[1]
own = load(os.path.join(R, f"{stamp}_ownship_(F-16)[Blue].csv"))
tgt = load(os.path.join(R, f"{stamp}_target_(F-16)[Red].csv"))
n = min(len(own), len(tgt)); c = math.cos(math.radians(own[0][2]))

print(f"[{stamp}]  20초 간격 고도 추이")
print("   t  | 내고도 상대고도 | 고도차 | 거리 | 내피치 | VP하한3500? ClimbOut3000?")
for i in range(0, n, 1200):
    o, t = own[i], tgt[i]
    de = (t[1]-o[1])*c*MLAT; dn = (t[2]-o[2])*MLAT; du = t[3]-o[3]
    d = math.sqrt(de*de+dn*dn+du*du)
    f1 = "VP바닥" if (o[3] - d*0.2) < 3500 else "  -   "
    f2 = "ClimbOut" if o[3] < 3000 else "   -    "
    print(f" {o[0]:5.0f} | {o[3]:6.0f} {t[3]:7.0f} | {du:+6.0f} | {d:5.0f} | {o[4]:+5.1f} | {f1}  {f2}")

# 고도차의 전반/후반 비교 (편향 누적 확인)
dus = []
for i in range(n):
    o, t = own[i], tgt[i]
    dus.append(t[3]-o[3])
h = n//2
import statistics as st
print(f"\n  고도차 중앙값: 전반 {st.median(dus[:h]):+.1f}m / 후반 {st.median(dus[h:]):+.1f}m")
print(f"  내 고도: 시작 {own[0][3]:.0f}m -> 끝 {own[n-1][3]:.0f}m")
print(f"  상대고도: 시작 {tgt[0][3]:.0f}m -> 끝 {tgt[n-1][3]:.0f}m")
print(f"  내 최저고도 {min(o[3] for o in own[:n]):.0f}m / 상대 최저 {min(t[3] for t in tgt[:n]):.0f}m")
print(f"  VP Z하한(3500m) 걸린 틱: {sum(1 for i in range(n) if own[i][3] < 3500+1):d}")
print(f"  ClimbOut(3000m) 걸린 틱: {sum(1 for i in range(n) if own[i][3] < 3000):d}")
