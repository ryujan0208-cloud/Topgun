# 고도 추이 추적: 고도차가 시간에 따라 벌어지는가(구조적 편향)?
# 그리고 VP Z 하한 / ClimbOut 트리거에 걸리는가?
#
# ★ 2026-08-04 수정: 임계값이 v17 시절 값(VP하한 3500m / ClimbOut 3000m)으로 박혀 있어
#   v18 이후(VP하한 1500m / ClimbOut 1800m)에는 전혀 다른 걸 세고 있었다.
#   "ClimbOut 18987틱"은 실제로는 "3000m 아래에 있던 틱"일 뿐 트리거와 무관했다.
#   측정 도구의 상수는 코드가 바뀌면 같이 바뀌어야 한다(turn_perf.py와 같은 사고).
#   기본값을 현재 코드에 맞추고, 인자로 덮어쓸 수 있게 한다.
#     사용: python alt_trace.py <stamp> [vp_floor] [climbout_alt]
import csv, math, sys, os
R = r"C:\Users\TFX5470H\Desktop\.topgun\강화학습환경\Release\artifacts\logs"
MLAT = 111320.0

# 현재 코드 기준 (Task_LeadPredict/Task_Evade: vp.Z<1500 -> 1500 / Rule_v29.xml: MinAlt="1800")
VP_FLOOR = float(sys.argv[2]) if len(sys.argv) > 2 else 1500.0
CLIMBOUT = float(sys.argv[3]) if len(sys.argv) > 3 else 1800.0


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

print(f"[{stamp}]  20초 간격 고도 추이   (VP하한 {VP_FLOOR:.0f}m / ClimbOut {CLIMBOUT:.0f}m 기준)")
print(f"   t  | 내고도 상대고도 | 고도차 | 거리 | 내피치 | VP하한? ClimbOut?")
for i in range(0, n, 1200):
    o, t = own[i], tgt[i]
    de = (t[1]-o[1])*c*MLAT; dn = (t[2]-o[2])*MLAT; du = t[3]-o[3]
    d = math.sqrt(de*de+dn*dn+du*du)
    f1 = "VP바닥" if (o[3] - d*0.2) < VP_FLOOR else "  -   "
    f2 = "ClimbOut" if o[3] < CLIMBOUT else "   -    "
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
print(f"  VP Z하한({VP_FLOOR:.0f}m) 걸린 틱: "
      f"{sum(1 for i in range(n) if own[i][3] < VP_FLOOR + 1):d} / {n}")
print(f"  ClimbOut({CLIMBOUT:.0f}m) 걸린 틱: "
      f"{sum(1 for i in range(n) if own[i][3] < CLIMBOUT):d} / {n}")

# 저고도 체류 = 수직 기동 여유가 없는 구간. 하강 나선은 156도당 고도 2000m가 든다.
LOWROOM = CLIMBOUT + 2000.0
low = sum(1 for i in range(n) if own[i][3] < LOWROOM)
print(f"  ★수직여유 없음(<{LOWROOM:.0f}m = ClimbOut+2000): {low:d} / {n} ({100.0*low/n:.1f}%)")
