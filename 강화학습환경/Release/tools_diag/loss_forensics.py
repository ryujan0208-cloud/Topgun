# -*- coding: utf-8 -*-
# 패배판 부검: 우리 HP가 처음 떨어진 순간(=상대에게 잡힌 순간)의 기하를 특정한다.
# 시뮬 안 돌림. 분리본(_sNN) 로그만 읽는다.
# 사용: python tools_diag/loss_forensics.py <batch_stamp> <seed1,seed2,...>
import csv, math, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import wez_rule as wez            # 사격 규칙의 단일 출처. 여기 상수를 다시 적지 않는다.
try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass
R = r"C:\Users\TFX5470H\Desktop\.topgun\강화학습환경\Release\artifacts\logs"
MLAT = 111320.0

# 코덱스 CV10이 사전등록 후 holdout까지 통과시킨 **패배 전조 규칙**.
#   피격 5초 전에 셋이 동시에 참이면 위험: 상대가 사거리 안에서 우리 뒤에 정렬되는 동안
#   우리 기수는 크게 등져 즉시 반격이 불가능한 상태.
#   (discovery 6/8, holdout 2/3, 오탐 0/4 — 커밋 d668e91)
# 우리 트리의 Evade 트리거는 `거리<1100 AND 상대조준각<25`뿐이고
# **"우리 기수가 등졌는가"는 안 본다.** 그 차이를 여기서 잰다.
PRE_RANGE_M   = 914.4
PRE_TGT_ATA   = 30.0
PRE_OWN_ATA   = 130.0
PRE_LEAD_S    = 5.0
EVADE_RANGE_M = 1100.0            # Rule_v32.xml의 DECO_DistanceCheck
EVADE_AIM_DEG = 25.0              # Rule_v32.xml의 DECO_ThreatAimCheck

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
    # ★ 2026-08-09 수정: 여기 상수가 ATA<=1.0 + 152~914m로 **P1 고정**이었다.
    #   대회 규칙은 3단계 phase이고 단일 출처는 tools_diag/wez_rule.py다.
    #   (후반 phase는 LOS 3도/4000ft까지 넓어져 P1 기준으론 성립 사격을 놓친다)
    myhit=tghit=0
    for i in range(n):
        et=float(o[i]['Time'])-t0
        d,ma,ta=geo(o[i],t[i],c)
        if wez.hit(et,d,ta)[0]: myhit+=1
        if wez.hit(et,d,ma)[0]: tghit+=1
    print(f"  사격성립(3단계 phase): 우리가 쏨 {tghit}틱 / 우리가 맞음 {myhit}틱")
    if mi is None:
        print("  우리 피격 없음(HP비교 패는 상대도 무피해=완전 무승부 아님 재확인 필요)")
    else:
        d,ma,ta=geo(o[mi],t[mi],c)
        print(f"  ★우리 첫 피격 t={float(o[mi]['Time'])-t0:.1f}s: dist {d:.0f}m 내ATA {ma:.0f} 상대ATA {ta:.0f} 고도 {float(o[mi]['Altitude']):.0f}m")
        # 코덱스 CV10 전조 규칙 교차검증 + 우리 Evade 트리거와 대조
        step=float(o[1]['Time'])-float(o[0]['Time']) if len(o)>1 else 1/60
        j5=max(0,mi-int(round(PRE_LEAD_S/max(step,1e-9))))
        d5,ma5,ta5=geo(o[j5],t[j5],c)
        pre   = (d5<=PRE_RANGE_M and abs(ta5)<=PRE_TGT_ATA and ma5>=PRE_OWN_ATA)
        evade = (d5<=EVADE_RANGE_M and abs(ta5)<=EVADE_AIM_DEG)
        print(f"   5초전 t={float(o[j5]['Time'])-t0:.1f}s: dist {d5:.0f}m 내ATA {ma5:.0f} 상대ATA {ta5:.0f}"
              f"   [코덱스 전조 {'O' if pre else 'X'}]  [우리 Evade 조건 {'O' if evade else 'X'}]")
        # 그 15초 전 국면
        j=max(0,mi-900)
        d0,ma0,ta0=geo(o[j],t[j],c)
        print(f"   15초전 t={float(o[j]['Time'])-t0:.1f}s: dist {d0:.0f}m 내ATA {ma0:.0f} 상대ATA {ta0:.0f} 고도 {float(o[j]['Altitude']):.0f}m")
    if ti is not None:
        d,ma,ta=geo(o[ti],t[ti],c)
        print(f"   (우리 첫 가격 t={float(t[ti]['Time'])-t0:.1f}s: dist {d:.0f}m 내ATA {ma:.0f})")
