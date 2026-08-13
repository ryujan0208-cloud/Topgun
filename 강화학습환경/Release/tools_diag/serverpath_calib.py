# -*- coding: utf-8 -*-
"""DLL의 (위도,경도,고도) -> 직교 변환 계수를 실측한다.
   서버 경로 수정 시 Unreal 직교를 위경도로 되돌리려면 이 계수가 필요하다."""
import sys, os, re, io, contextlib
sys.path.insert(0, "."); sys.path.insert(0, "src")
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
for k in ("TOPGUN_RULE","TOPGUN_ABLATE","TOPGUN_MATCH"): os.environ.pop(k, None)
from dogfight.ai.native_bt import AIPilot

ap = AIPilot("AIP_final.dll"); ap.CreateBehaviorTree(0, 1)
LAT0, LON0, ALT = 37.923556, 128.181881, 3000.0

def measure(dlat, dlon, dalt):
    """지정한 위경도차를 주고 BT가 계산한 거리를 stderr에서 읽는다."""
    err = io.StringIO()
    fd = os.dup(2); r, w = os.pipe(); os.dup2(w, 2)
    for _ in range(31):
        a = AIPilot.BuildPlaneData([LAT0, LON0, ALT], [0,0,0], 250.0, 1)
        b = AIPilot.BuildPlaneData([LAT0+dlat, LON0+dlon, ALT+dalt], [0,0,0], 250.0, 2)
        ap.StepWithPlaneData(a, b)
    os.dup2(fd, 2); os.close(w)
    txt = os.read(r, 200000).decode("utf-8", "replace"); os.close(r); os.close(fd)
    m = re.findall(r"Dist=([\d.e+]+)", txt)
    return float(m[-1]) if m else None

print("DLL 좌표 변환 계수 실측")
print()
for d in (0.001, 0.01, 0.1):
    v = measure(d, 0.0, 0.0)
    if v: print(f"  위도 +{d}도  -> 거리 {v:>12,.2f} m   =>  {v/d:,.1f} m/도")
print()
for d in (0.001, 0.01, 0.1):
    v = measure(0.0, d, 0.0)
    if v: print(f"  경도 +{d}도  -> 거리 {v:>12,.2f} m   =>  {v/d:,.1f} m/도")
print()
v = measure(0.0, 0.0, 500.0)
if v: print(f"  고도 +500m  -> 거리 {v:>12,.2f} m   (고도는 그대로 미터여야 함)")
