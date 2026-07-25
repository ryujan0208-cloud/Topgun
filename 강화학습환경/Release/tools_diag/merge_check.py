# -*- coding: utf-8 -*-
# 머지 오버슈트 검증: 각 패배판에서 "첫 피격 전" 우리 내ATA 궤적을 본다.
#  머지 오버슈트 패턴 = 내ATA가 (작아짐: 상대 향해 돎) → (급증 >90: 지나침) → (뒤잡힘)
# 시뮬 안 돌림. 분리본만.
# 사용: python tools_diag/merge_check.py <stamp> <seeds>
import csv, math, sys, os
R = r"C:\Users\TFX5470H\Desktop\.topgun\강화학습환경\Release\artifacts\logs"
MLAT=111320.0
def load(p):
    with open(p,newline='',encoding='utf-8') as f: return list(csv.DictReader(f))
def geo(o,t,c):
    de=(float(t['Longitude'])-float(o['Longitude']))*c*MLAT
    dn=(float(t['Latitude'])-float(o['Latitude']))*MLAT
    du=float(t['Altitude'])-float(o['Altitude'])
    d=math.sqrt(de*de+dn*dn+du*du)
    def ata(s,vx,vy,vz):
        y,p=math.radians(float(s['Yaw (deg)'])),math.radians(float(s['Pitch (deg)']))
        f=(math.sin(y)*math.cos(p),math.cos(y)*math.cos(p),math.sin(p))
        return math.degrees(math.acos(max(-1,min(1,(f[0]*vx+f[1]*vy+f[2]*vz)/max(d,1e-6)))))
    return d,ata(o,de,dn,du),ata(t,-de,-dn,-du)

stamp=sys.argv[1]; seeds=[int(x) for x in sys.argv[2].split(',')]
for k in seeds:
    o=load(os.path.join(R,f"{stamp}_s{k:02d}_ownship_(F-16)[Blue].csv"))
    t=load(os.path.join(R,f"{stamp}_s{k:02d}_target_(F-16)[Red].csv"))
    n=min(len(o),len(t)); c=math.cos(math.radians(float(o[0]['Latitude']))); t0=float(o[0]['Time'])
    # 첫 피격 시점 (우리 HP 첫 하락, 임계 0.003)
    hit=None; p=1.0
    for i in range(n):
        h=float(o[i]['Health'])
        if h<p-0.003: hit=i; break
        p=h
    if hit is None: hit=n-1
    # 첫 근접머지 = 첫 피격 전, dist가 국소최소이면서 1500 아래로 처음 들어간 구간
    # 내ATA 최소점(=상대 가장 잘 조준한 순간) 전후를 본다
    lo=max(0,hit-1500)
    seg=list(range(lo,min(hit+60,n),30))
    # 그 구간 내ATA 최소(상대 향해 가장 정렬)와 그 후 최대(오버슈트)
    myA=[geo(o[i],t[i],c)[1] for i in seg]
    dists=[geo(o[i],t[i],c)[0] for i in seg]
    # 근접(dist<1500) 첫 진입 인덱스
    close=[j for j,dd in enumerate(dists) if dd<1500]
    print(f"\n=== seed{k} (첫피격 t={float(o[hit]['Time'])-t0:.0f}s) ===")
    if not close:
        print("  근접(<1500m) 구간 없음 - 원거리 피격?"); continue
    j0=close[0]
    # j0부터 첫피격까지 내ATA 흐름 (머지 진입~피격)
    print("  머지진입~첫피격 내ATA 흐름 (dist<1500 이후):")
    line=""
    minA=999; minJ=j0; sawlow=False
    for j in range(j0,len(seg)):
        d,ma,ta=geo(o[seg[j]],t[seg[j]],c)
        tt=float(o[seg[j]]['Time'])-t0
        line+=f"{ma:.0f} "
        if ma<minA: minA=ma; minJ=j
    print(f"   {line}")
    # 오버슈트 판정: 내ATA가 90 아래(상대 향함)까지 갔다가 90 위(지나침)로 급증했나
    seq=[geo(o[seg[j]],t[seg[j]],c)[1] for j in range(j0,len(seg))]
    wentlow=any(a<70 for a in seq)
    thenhigh=False
    if wentlow:
        li=next(i for i,a in enumerate(seq) if a<70)
        thenhigh=any(a>110 for a in seq[li:])
    print(f"   → 상대 향함(ATA<70) {wentlow} → 그 후 지나침(ATA>110) {thenhigh}  "
          f"{'★머지 오버슈트 확인' if (wentlow and thenhigh) else '패턴 다름'}")
