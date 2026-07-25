# -*- coding: utf-8 -*-
# 패배판 부검: 우리 HP가 처음 떨어진 순간(=상대에게 잡힌 순간)의 기하를 특정한다.
# 시뮬 안 돌림. 분리본(_sNN) 로그만 읽는다.
# 사용: python tools_diag/loss_forensics.py <batch_stamp> <seed1,seed2,...>
import csv, math, sys, os
R = r"C:\Users\TFX5470H\Desktop\.topgun\강화학습환경\Release\artifacts\logs"
MLAT = 111320.0

def load(p):
    rows=[]
    with open(p,newline='',encoding='utf-8') as f:
        for r in csv.DictReader(f):
            rows.append(r)
    return rows

def geo(o,t,c):
    de=(float(t['Longitude'])-float(o['Longitude']))*c*MLAT
    dn=(float(t['Latitude'])-float(o['Latitude']))*MLAT
    du=float(t['Altitude'])-float(o['Altitude'])
    d=math.sqrt(de*de+dn*dn+du*du)
    def ata(src,de,dn,du,d):
        yr,pr=math.radians(float(src['Yaw (deg)'])),math.radians(float(src['Pitch (deg)']))
        fe,fn,fu=math.sin(yr)*math.cos(pr),math.cos(yr)*math.cos(pr),math.sin(pr)
        return math.degrees(math.acos(max(-1,min(1,(fe*de+fn*dn+fu*du)/max(d,1e-6)))))
    myA=ata(o,de,dn,du,d)
    tgA=ata(t,-de,-dn,-du,d)
    return d,myA,tgA

stamp=sys.argv[1]; seeds=[int(x) for x in sys.argv[2].split(',')]
for k in seeds:
    op=os.path.join(R,f"{stamp}_s{k:02d}_ownship_(F-16)[Blue].csv")
    tp=os.path.join(R,f"{stamp}_s{k:02d}_target_(F-16)[Red].csv")
    if not os.path.exists(op): print(f"seed{k}: 로그없음"); continue
    o=load(op); t=load(tp); n=min(len(o),len(t)); c=math.cos(math.radians(float(o[0]['Latitude'])))
    t0=float(o[0]['Time'])
    # 우리/상대 HP 첫 하락 시점
    def first_drop(rows):
        p=1.0
        for i in range(len(rows)):
            h=float(rows[i]['Health'])
            if h<p-0.01: return i,h
            p=h
        return None,1.0
    mi,mh=first_drop(o); ti,th=first_drop(t)
    ownHP=float(o[n-1]['Health']); tgtHP=float(t[n-1]['Health'])
    print(f"\n===== seed{k}  (최종 ourHP {ownHP:.2f} / tgtHP {tgtHP:.2f}) =====")
    # 총 피격/가격 시간
    myhit=sum(1 for i in range(n) if geo(o[i],t[i],c)[2]<=1.0 and 152<geo(o[i],t[i],c)[0]<914)
    tghit=sum(1 for i in range(n) if geo(o[i],t[i],c)[1]<=1.0 and 152<geo(o[i],t[i],c)[0]<914)
    print(f"  사격성립: 우리가 쏨 {tghit}틱 / 우리가 맞음 {myhit}틱")
    if mi is None:
        print("  우리 피격 없음(HP비교 패는 상대도 무피해=완전 무승부 아님 재확인 필요)")
    else:
        d,ma,ta=geo(o[mi],t[mi],c)
        print(f"  ★우리 첫 피격 t={float(o[mi]['Time'])-t0:.1f}s: dist {d:.0f}m 내ATA {ma:.0f} 상대ATA {ta:.0f} 고도 {float(o[mi]['Altitude']):.0f}m")
        # 그 15초 전 국면
        j=max(0,mi-900)
        d0,ma0,ta0=geo(o[j],t[j],c)
        print(f"   15초전 t={float(o[j]['Time'])-t0:.1f}s: dist {d0:.0f}m 내ATA {ma0:.0f} 상대ATA {ta0:.0f} 고도 {float(o[j]['Altitude']):.0f}m")
    if ti is not None:
        d,ma,ta=geo(o[ti],t[ti],c)
        print(f"   (우리 첫 가격 t={float(t[ti]['Time'])-t0:.1f}s: dist {d:.0f}m 내ATA {ma:.0f})")
