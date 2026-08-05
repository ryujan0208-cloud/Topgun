# -*- coding: utf-8 -*-
"""상대가 '바닥 강제 풀아웃'에 몰리는 빈도를 잰다.

[왜]
 규정상 고도 300m = 즉시 패배(config.py min_altitude). 따라서 바닥으로 내려가며
 하강 중인 상대는 **반드시 기수를 든다.** 경기 중 유일하게 규정이 보장하는 예측 가능 순간이다.
 이 상황을 노리는 분기를 만들 가치가 있는지 판단하려면 **먼저 빈도를 재야 한다.**
 (드물면 공들일 가치가 없다. 만들기 전에 재는 게 우리 원칙.)

[정의] 상대가 하강 중(Vz<0)이고, 지금 속도로 바닥(300m)까지 남은 시간이 TTF초 이하.
       그 순간 상대의 선택지는 사실상 '기수 들기' 하나뿐이다.

사용: python tools_diag/floor_pullout.py <stamp> [TTF초=6] [바닥=300]
"""
import csv, math, sys, os

R = r"C:\Users\TFX5470H\Desktop\.topgun\강화학습환경\Release\artifacts\logs"
MLAT = 111320.0
stamp = sys.argv[1]
TTF   = float(sys.argv[2]) if len(sys.argv) > 2 else 6.0
FLOOR = float(sys.argv[3]) if len(sys.argv) > 3 else 300.0


def load(p):
    rows = []
    with open(p, newline='', encoding='utf-8') as f:
        for r in csv.DictReader(f):
            rows.append((float(r['Time']), float(r['Longitude']), float(r['Latitude']),
                         float(r['Altitude']), float(r['Pitch (deg)'])))
    return rows


own = load(os.path.join(R, f"{stamp}_ownship_(F-16)[Blue].csv"))
tgt = load(os.path.join(R, f"{stamp}_target_(F-16)[Red].csv"))
n = min(len(own), len(tgt))
c = math.cos(math.radians(own[0][2]))

K = 6                                   # 0.1초 창으로 수직속도 추정
# ★ 에피소드 경계 제외: 배치 로그는 판이 이어붙어 있어 경계에서 고도가 1900m -> 7000m로
#   점프한다. 이걸 거르지 않으면 "강하율 -9639m/s" 같은 물리적으로 불가능한 값이 잡혀
#   실제 0회인데 발생한 것처럼 보인다(첫 측정에서 실제로 당했다).
JUMP = 500.0                            # 한 샘플(1/60초)에 이만큼 변하면 경계로 간주
bad = set()
for i in range(1, n):
    if abs(tgt[i][3] - tgt[i-1][3]) > JUMP:
        for j in range(i - K - 1, i + K + 2):
            bad.add(j)

hits = []                               # (t, 상대고도, Vz, 남은시간, 거리)
for i in range(K, n):
    if i in bad:
        continue
    o, t = own[i], tgt[i]
    dt = t[0] - tgt[i-K][0]
    if dt <= 0:
        continue
    vz = (t[3] - tgt[i-K][3]) / dt
    if vz < -400.0:                     # F-16이 낼 수 없는 강하율 = 남은 경계 아티팩트
        continue
    if vz >= -1.0:                      # 하강 중이 아니면 제외
        continue
    ttf = (t[3] - FLOOR) / (-vz)
    if ttf > TTF:
        continue
    de = (t[1]-o[1])*c*MLAT; dn = (t[2]-o[2])*MLAT; du = t[3]-o[3]
    hits.append((t[0], t[3], vz, ttf, math.sqrt(de*de+dn*dn+du*du)))

print(f"[{stamp}] 총 {n}틱 ({n/60:.0f}초)  기준: 하강중 & 바닥({FLOOR:.0f}m)까지 {TTF:.0f}초 이내")
print(f"  ★상대 바닥 강제 풀아웃 상황: {len(hits)}틱 ({len(hits)/60:.1f}초, {100.0*len(hits)/n:.2f}%)")

if not hits:
    print("  -> 이 로그에선 발생하지 않음. 이 분기는 이 상대에게 가치 없음.")
    # 그래도 상대가 얼마나 낮게 내려가는지는 보여준다(임계값 조정 판단용)
    lo = min(t[3] for t in tgt[:n])
    print(f"  참고: 상대 최저고도 {lo:.0f}m (바닥 대비 +{lo-FLOOR:.0f}m)")
    sys.exit()

import statistics as st
print(f"     상대고도 중앙 {st.median(h[1] for h in hits):.0f}m / "
      f"강하율 중앙 {st.median(h[2] for h in hits):+.0f}m/s / "
      f"거리 중앙 {st.median(h[4] for h in hits):.0f}m")
print(f"     사거리(914m) 안에서 발생한 비율: "
      f"{100.0*sum(1 for h in hits if h[4] <= 914.4)/len(hits):.0f}%")

# 연속 구간(에피소드 내 이벤트)으로 묶어 몇 '번' 일어나는지
ev, prev = [], None
for h in hits:
    if prev is None or h[0] - prev > 1.0:
        ev.append([h[0], h[0]])
    else:
        ev[-1][1] = h[0]
    prev = h[0]
print(f"     이벤트 {len(ev)}회, 1회당 평균 {sum(e[1]-e[0] for e in ev)/len(ev):.1f}초")
print(f"  [처음 5회] " + ", ".join(f"t={e[0]:.0f}~{e[1]:.0f}s" for e in ev[:5]))
