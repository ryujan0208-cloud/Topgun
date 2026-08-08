# -*- coding: utf-8 -*-
"""의도한 기동이 **실제로 일어났는가**를 검증한다.

[왜 필요한가 — 2026-08-06 사용자 지적]
지금까지 BT 노드를 검증할 때 나는 **트리거가 발동했는지**만 봤다.
그런데 BT는 VP만 설정하고 실제 기동은 Controller_CY가 만든다.
"VP를 70도 위에 찍었으니 최대 당김이 되겠지"는 **가정이지 검증이 아니다.**
게다가 vp_probe는 **스틱을 직접** 덮어쓰는데 BT 노드는 **VP로** 같은 걸 시도한다.
둘이 같은 기동이 된다는 보장이 없다.

-> 두 버전을 같은 시드로 돌려 **속도/자세 시계열을 직접 비교**한다.
   기동이 일어났다면 속도·뱅크·피치에 뚜렷한 차이가 보여야 한다.

사용: python tools_diag/maneuver_check.py <stampA> <stampB> [라벨A] [라벨B]
"""
import csv, math, sys, os
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
R = r"C:\Users\TFX5470H\Desktop\.topgun\강화학습환경\Release\artifacts\logs"
MLAT = 111320.0

# ★ 배치 로그는 판이 이어붙어 있다(CLAUDE.md 함정). 판이 바뀌면 위치가 순간이동해
#   위치차분 속도가 수백만 m/s로 튄다. 안 거르면 상위 차이 구간이 전부 경계로 채워진다.
#   F-16이 낼 수 있는 속도의 물리 상한으로 잘라낸다.
MAX_PHYS = 700.0    # m/s. 실측 최고가 ~500이라 넉넉한 여유.

def load(stamp):
    p = os.path.join(R, f"{stamp}_ownship_(F-16)[Blue].csv")
    rows = []
    with open(p, newline='', encoding='utf-8') as f:
        for r in csv.DictReader(f):
            rows.append((float(r['Time']), float(r['Longitude']), float(r['Latitude']),
                         float(r['Altitude']), float(r['Roll (deg)']), float(r['Pitch (deg)'])))
    out = []
    dropped = 0
    for i in range(1, len(rows)):
        t0, t1 = rows[i-1], rows[i]
        dt = t1[0] - t0[0]
        if dt <= 0:                       # 시간이 되감기면 그것도 판 경계다
            dropped += 1
            continue
        c = math.cos(math.radians(t0[2]))
        dx = (t1[1]-t0[1])*c*MLAT; dy = (t1[2]-t0[2])*MLAT; dz = t1[3]-t0[3]
        v = math.sqrt(dx*dx+dy*dy+dz*dz)/dt
        if v > MAX_PHYS:                  # 판 경계
            dropped += 1
            continue
        out.append((t1[0], v, t1[3], t1[4], t1[5]))     # t, speed, alt, roll, pitch
    if dropped:
        print(f"  [{stamp}] 판 경계 {dropped}틱 제외")
    return out

a = load(sys.argv[1]); b = load(sys.argv[2])
LA = sys.argv[3] if len(sys.argv) > 3 else "A"
LB = sys.argv[4] if len(sys.argv) > 4 else "B"
n = min(len(a), len(b))

print(f"\n[기동 실행 검증] {LA} vs {LB}   (같은 시드, 틱 {n})")
print(f"{'시간':>6} {LA+' 속도':>9} {LB+' 속도':>9} {'차이':>7} | {LA+' 뱅크':>8} {LB+' 뱅크':>8} | {LA+' 피치':>8} {LB+' 피치':>8}")
print("-"*78)
# 속도 차이가 큰 구간 = 기동이 실제로 달랐던 곳
diffs = sorted(range(n), key=lambda i: -abs(a[i][1]-b[i][1]))[:400]
shown = set()
for i in sorted(diffs):
    k = int(a[i][0])
    if k in shown: continue
    shown.add(k)
    if len(shown) > 14: break
    print(f"{a[i][0]:6.1f} {a[i][1]:8.0f}m/s {b[i][1]:8.0f}m/s {b[i][1]-a[i][1]:+7.0f} | "
          f"{a[i][3]:+7.0f}° {b[i][3]:+7.0f}° | {a[i][4]:+7.0f}° {b[i][4]:+7.0f}°")

import statistics as st
sd = [abs(a[i][1]-b[i][1]) for i in range(n)]
print("-"*78)
print(f"  속도 차이: 중앙 {st.median(sd):.1f}m/s / 최대 {max(sd):.1f}m/s / "
      f"5m/s 초과 틱 {sum(1 for x in sd if x>5)}/{n} ({100*sum(1 for x in sd if x>5)/n:.1f}%)")
print(f"  {LA} 속도 중앙 {st.median([x[1] for x in a[:n]]):.0f}m/s / "
      f"{LB} 속도 중앙 {st.median([x[1] for x in b[:n]]):.0f}m/s")
print(f"  {LA} 최저속도 {min(x[1] for x in a[:n]):.0f}m/s / {LB} 최저속도 {min(x[1] for x in b[:n]):.0f}m/s")
print("\n  ※ 기동이 실제로 일어났다면 발동 구간에서 속도가 뚜렷이 떨어져야 한다.")
print("     차이가 미미하면 **VP가 의도한 스틱을 만들지 못한 것**이다.")
