# -*- coding: utf-8 -*-
# STEP 1 분류기: 배치 분리본(_sNN)을 계획서 A/B/C 기준으로 자동 분류한다.
#  A형 고착      : 마지막 60초 내ATA<15 & 상대ATA>150 & dist 950~2500 가 대부분 지속
#  B형 교전미성립: 전체에서 "내가 무는 중(내ATA<45)" 비율 < 40%
#  C형 기타      : 위 둘 다 아님
# 사용: python tools_diag/classify_rounds.py <batch_stamp> [tag]
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

stamp = sys.argv[1]
tag = sys.argv[2] if len(sys.argv)>2 else "(F-16)"
print(f"[{stamp}]  s## | 분류 | 무는%| 막판 dist/내ATA/상ATA | 최종HP차 | 비고")
for k in range(30):
    op = os.path.join(R, f"{stamp}_s{k:02d}_ownship_{tag}[Blue].csv")
    tp = os.path.join(R, f"{stamp}_s{k:02d}_target_{tag}[Red].csv")
    if not os.path.exists(op): continue
    own, tgt = load(op), load(tp)
    n=min(len(own),len(tgt)); c=math.cos(math.radians(own[0][2]))
    bite=0; last=[]
    a1last=a2last=dlast=0
    for i in range(n):
        a1,d=ata(own[i],tgt[i],c); a2,_=ata(tgt[i],own[i],c)
        if a1<45: bite+=1
        if own[i][0] >= own[n-1][0]-60.0:   # 마지막 60초
            last.append((a1,a2,d))
        a1last,a2last,dlast=a1,a2,d
    bpct=100*bite/n
    # A형 판정: 막판 표본 중 (내<15 & 상>150 & 950<d<2500) 비율
    if last:
        astick=sum(1 for a1,a2,d in last if a1<15 and a2>150 and 950<d<2500)
        apct=100*astick/len(last)
    else:
        apct=0
    if bpct < 40:
        cls="B 미성립"
    elif apct >= 50:
        cls="A 고착  "
    else:
        cls="C 기타  "
    print(f"  s{k:02d} | {cls} | {bpct:3.0f}% | {dlast:5.0f}m {a1last:3.0f} {a2last:3.0f} "
          f"| A막판{apct:3.0f}%")
