# -*- coding: utf-8 -*-
"""LOS(시선) 회전율을 재고, v33 lag pursuit 트리거가 얼마나 발동할지 미리 계산한다.

[왜] v33은 "LOS 회전율 > 우리 선회 능력"이면 관통 확정으로 보고 lag pursuit로 바꾼다.
     만들기 전에 **그 조건이 실제로 얼마나 자주 성립하는지** 알아야 한다.
     (v28은 클램프를 풀었는데 clamped=0이라 no-op이었던 전례가 있다)

[정의] w_LOS = 시선 단위벡터의 3D 각속도(deg/s). yaw만 재면 수직 성분을 놓친다.
       트리거 = w_LOS > TURN_CAP AND dist < 900m
       TURN_CAP 기본 25.0 = turn_perf2 실측 지속 최대(하강나선 25.4deg/s)

사용: python tools_diag/los_rate.py <stamp> [TURN_CAP=25] [MAXDIST=900]
"""
import csv, math, sys, os

R = r"C:\Users\TFX5470H\Desktop\.topgun\강화학습환경\Release\artifacts\logs"
MLAT = 111320.0
stamp = sys.argv[1]
CAP     = float(sys.argv[2]) if len(sys.argv) > 2 else 25.0
MAXDIST = float(sys.argv[3]) if len(sys.argv) > 3 else 900.0


def load(p):
    rows = []
    with open(p, newline='', encoding='utf-8') as f:
        for r in csv.DictReader(f):
            rows.append((float(r['Time']), float(r['Longitude']), float(r['Latitude']),
                         float(r['Altitude'])))
    return rows


own = load(os.path.join(R, f"{stamp}_ownship_(F-16)[Blue].csv"))
tgt = load(os.path.join(R, f"{stamp}_target_(F-16)[Red].csv"))
n = min(len(own), len(tgt))
c = math.cos(math.radians(own[0][2]))

los, dists = [], []
for i in range(n):
    o, t = own[i], tgt[i]
    de = (t[1]-o[1])*c*MLAT; dn = (t[2]-o[2])*MLAT; du = t[3]-o[3]
    d = math.sqrt(de*de+dn*dn+du*du)
    if d < 1.0: d = 1.0
    los.append((de/d, dn/d, du/d)); dists.append(d)

# 에피소드 경계(위치 점프) 제외 — BT의 v29 리셋과 같은 기준
bad = set()
for i in range(1, n):
    if abs(dists[i] - dists[i-1]) > 1000.0:
        for j in range(i-8, i+9): bad.add(j)

K = 6                                   # 0.1초 창 (BT의 LHIST와 동일)
rates = []
for i in range(K, n):
    if i in bad: continue
    dt = own[i][0] - own[i-K][0]
    if dt <= 0: continue
    a, b = los[i-K], los[i]
    dot = max(-1.0, min(1.0, a[0]*b[0] + a[1]*b[1] + a[2]*b[2]))
    rates.append((math.degrees(math.acos(dot))/dt, dists[i]))

if not rates:
    print("데이터 없음"); sys.exit()

import statistics as st
inr  = [r for r in rates if r[1] <= MAXDIST]
trig = [r for r in inr   if r[0] > CAP]

print(f"[{stamp}] 유효 {len(rates)}틱  (TURN_CAP {CAP:.0f}deg/s, 거리<{MAXDIST:.0f}m)")
print(f"  LOS 회전율 중앙 {st.median(r[0] for r in rates):6.1f}deg/s  "
      f"상위5% {sorted(r[0] for r in rates)[int(len(rates)*0.95)]:6.1f}deg/s  "
      f"최대 {max(r[0] for r in rates):7.1f}deg/s")
print(f"  거리<{MAXDIST:.0f}m 구간: {len(inr)}틱")
if inr:
    print(f"     LOS 회전율 중앙 {st.median(r[0] for r in inr):6.1f}deg/s")
    print(f"  ★v33 트리거 발동: {len(trig)}/{len(inr)}틱 "
          f"({100.0*len(trig)/len(inr):.1f}% of 근거리, "
          f"{100.0*len(trig)/len(rates):.2f}% of 전체)")
    if trig:
        print(f"     발동 시 LOS 회전율 중앙 {st.median(r[0] for r in trig):.1f}deg/s "
              f"(능력 {CAP:.0f}의 {st.median(r[0] for r in trig)/CAP:.1f}배), "
              f"거리 중앙 {st.median(r[1] for r in trig):.0f}m")
    else:
        print("     -> 발동 0. 이 상대에겐 no-op이므로 만들 가치 없음.")

# 임계값 민감도 — CAP을 낮추면 얼마나 늘어나는지
print("  [TURN_CAP 민감도] ", end="")
for cap in (15.0, 20.0, 25.0, 30.0, 40.0):
    k = sum(1 for r in inr if r[0] > cap)
    print(f"{cap:.0f}:{100.0*k/len(inr) if inr else 0:.1f}%  ", end="")
print()
