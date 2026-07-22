# 궤적 분석: 왜 뒤를 못 잡는가. 시간별 거리/속도/선회율/방위.
import csv, math, sys, glob, os
R = r"C:\Users\TFX5470H\Desktop\.topgun\강화학습환경\Release\artifacts\logs"
MLAT = 111320.0
def load(p):
    rows=[]
    with open(p,newline='',encoding='utf-8') as f:
        for r in csv.DictReader(f):
            rows.append((float(r['Time']),float(r['Longitude']),float(r['Latitude']),float(r['Altitude']),float(r['Yaw (deg)'])))
    return rows
stamp = sys.argv[1] if len(sys.argv)>1 else os.path.basename(max(glob.glob(os.path.join(R,"*_ownship_*.csv")),key=os.path.getmtime)).split("_ownship")[0]
own=load(os.path.join(R,f"{stamp}_ownship_(F-16)[Blue].csv"))
tgt=load(os.path.join(R,f"{stamp}_target_(F-16)[Red].csv"))
n=min(len(own),len(tgt)); lat0=own[0][2]; c=math.cos(math.radians(lat0))
def xy(row): return ((row[1]-own[0][1])*c*MLAT,(row[2]-own[0][2])*MLAT)
def spd(rows,i):
    if i<3 or i>=len(rows): return 0
    (x0,y0),(x1,y1)=xy(rows[i-3]),xy(rows[i])
    dz=rows[i][3]-rows[i-3][3]; dt=rows[i][0]-rows[i-3][0]
    return math.sqrt((x1-x0)**2+(y1-y0)**2+dz*dz)/dt if dt>0 else 0
def turnrate(rows,i):
    if i<6 or i>=len(rows): return 0
    d=rows[i][4]-rows[i-6][4]; d=(d+180)%360-180; dt=rows[i][0]-rows[i-6][0]
    return d/dt if dt>0 else 0
print(f"[{stamp}]  t | dist | ownSpd tgtSpd | ownTurn tgtTurn (deg/s) | bearing(내기수->적)")
for sec in range(0,201,10):
    i=min(int(sec*60),n-1)
    o,t=own[i],tgt[i]
    de=(t[1]-o[1])*c*MLAT; dn=(t[2]-o[2])*MLAT; du=t[3]-o[3]
    dist=math.sqrt(de*de+dn*dn+du*du)
    brg=(math.degrees(math.atan2(de,dn))-o[4]+180)%360-180
    print(f"  {o[0]:5.0f} | {dist:6.0f} | {spd(own,i):5.0f} {spd(tgt,i):5.0f} | {turnrate(own,i):6.1f} {turnrate(tgt,i):6.1f} | {brg:6.0f}")
