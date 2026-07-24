# -*- coding: utf-8 -*-
# 추격 중 속도 소모 진단 (v21 게이트 P2 판정용).
# "확립된 원거리 추격" 구간 = 내ATA<15 & dist>1200 & 상대ATA>150 (dead-six로 멀리 쫓는 중).
# 그 구간에서:
#   bleed%   = |내 선회율| > 15deg/s 인 틱 비율 (선회 스파이크로 속도 태우는 정도)
#   drift    = 구간 시작->끝 거리 변화(m). 양수=벌어짐(폐쇄 실패), 음수=좁혀짐
#   dV       = 평균 (내속도 - 상대속도). 음수=우리가 느림
# 사용: python tools_diag/chase_bleed.py <batch_stamp> [tag]
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

def ata(o, t, c):
    de=(t[1]-o[1])*c*MLAT; dn=(t[2]-o[2])*MLAT; du=t[3]-o[3]
    d=math.sqrt(de*de+dn*dn+du*du)
    if d<1e-6: return 0.0,0.0
    yr,pr=math.radians(o[4]),math.radians(o[5])
    fe,fn,fu=math.sin(yr)*math.cos(pr),math.cos(yr)*math.cos(pr),math.sin(pr)
    return math.degrees(math.acos(max(-1,min(1,(fe*de+fn*dn+fu*du)/d)))), d

def spd(rows, i, c, k=6):
    if i < k: return 0.0
    o0,o1 = rows[i-k], rows[i]
    de=(o1[1]-o0[1])*c*MLAT; dn=(o1[2]-o0[2])*MLAT; dz=o1[3]-o0[3]; dtt=o1[0]-o0[0]
    return math.sqrt(de*de+dn*dn+dz*dz)/dtt if dtt>0 else 0.0

def yawrate(rows, i, k=6):
    if i < k: return 0.0
    dy = (rows[i][4]-rows[i-k][4]+540) % 360 - 180   # -180~180 wrap
    dtt = rows[i][0]-rows[i-k][0]
    return abs(dy)/dtt if dtt>0 else 0.0

stamp = sys.argv[1]
tag = sys.argv[2] if len(sys.argv)>2 else "(F-16)"
rows_out=[]
print(f"[{stamp}]  s## | 추격틱 | bleed% | drift(m) | dV(m/s)")
for k in range(30):
    op = os.path.join(R, f"{stamp}_s{k:02d}_ownship_{tag}[Blue].csv")
    tp = os.path.join(R, f"{stamp}_s{k:02d}_target_{tag}[Red].csv")
    if not os.path.exists(op): continue
    own,tgt=load(op),load(tp); n=min(len(own),len(tgt)); c=math.cos(math.radians(own[0][2]))
    reg=[]
    for i in range(n):
        a1,d=ata(own[i],tgt[i],c); a2,_=ata(tgt[i],own[i],c)
        if a1<15 and d>1200 and a2>150:
            reg.append((i,d))
    if len(reg)<30:
        print(f"  s{k:02d} | {len(reg):5d} | (추격구간 부족)")
        continue
    idxs=[r[0] for r in reg]
    bleed=100*sum(1 for i in idxs if yawrate(own,i)>15.0)/len(idxs)
    drift=reg[-1][1]-reg[0][1]
    dv=sum(spd(own,i,c)-spd(tgt,i,c) for i in idxs)/len(idxs)
    rows_out.append((bleed,drift,dv))
    print(f"  s{k:02d} | {len(reg):5d} | {bleed:5.0f}% | {drift:+8.0f} | {dv:+6.1f}")
if rows_out:
    import statistics as st
    print(f"  ---- 평균: bleed {st.mean(r[0] for r in rows_out):.0f}% | "
          f"drift {st.mean(r[1] for r in rows_out):+.0f}m | dV {st.mean(r[2] for r in rows_out):+.1f}m/s "
          f"(추격구간 있는 {len(rows_out)}판)")
