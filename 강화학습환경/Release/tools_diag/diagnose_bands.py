# 거리 구간별 최소 ATA 분석: "조준 능력이 원거리엔 있는가"를 확정한다.
import csv, math, sys, glob, os
R = r"C:\Users\TFX5470H\Desktop\.topgun\강화학습환경\Release\artifacts\logs"
MLAT = 111320.0
BANDS = [(0,914,"WEZ"),(914,1500,"914-1.5k"),(1500,2500,"1.5-2.5k"),(2500,4000,"2.5-4k"),(4000,99999,">4k")]

def load(p):
    rows=[]
    with open(p,newline='',encoding='utf-8') as f:
        for r in csv.DictReader(f):
            rows.append((float(r['Time']),float(r['Longitude']),float(r['Latitude']),float(r['Altitude']),float(r['Yaw (deg)']),float(r['Pitch (deg)'])))
    return rows

def analyze(stamp):
    try:
        own=load(os.path.join(R,f"{stamp}_ownship_(F-16)[Blue].csv"))
        tgt=load(os.path.join(R,f"{stamp}_target_(F-16)[Red].csv"))
    except Exception as e:
        print(f"[skip {stamp}: {e}]"); return
    n=min(len(own),len(tgt)); lat0=own[0][2]; c=math.cos(math.radians(lat0))
    recs=[]
    for i in range(n):
        o,t=own[i],tgt[i]
        de=(t[1]-o[1])*c*MLAT; dn=(t[2]-o[2])*MLAT; du=t[3]-o[3]
        dist=math.sqrt(de*de+dn*dn+du*du)
        if dist<1e-6: continue
        yr,pr=math.radians(o[4]),math.radians(o[5])
        fe=math.sin(yr)*math.cos(pr); fn=math.cos(yr)*math.cos(pr); fu=math.sin(pr)
        dot=max(-1.0,min(1.0,(fe*de+fn*dn+fu*du)/dist))
        recs.append((dist,math.degrees(math.acos(dot))))
    print(f"\n== {stamp} ==  (거리대 | 틱 | 최소ATA | <5° | <2°)")
    for lo,hi,name in BANDS:
        b=[a for d,a in recs if lo<=d<hi]
        if b:
            print(f"  {name:>9}: {len(b):5d}틱  minATA={min(b):5.1f}°  <5°={sum(1 for a in b if a<5):4d}  <2°={sum(1 for a in b if a<2):4d}")

stamps=sys.argv[1:] if len(sys.argv)>1 else [os.path.basename(f).split("_ownship")[0] for f in sorted(glob.glob(os.path.join(R,"*_ownship_*.csv")),key=os.path.getmtime,reverse=True)[:7]]
for s in stamps: analyze(s)
