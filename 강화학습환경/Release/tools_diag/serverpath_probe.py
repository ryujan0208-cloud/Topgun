# -*- coding: utf-8 -*-
"""가설 검증: OPlaneData.Location이 (위도도, 경도도, 고도m)라면
   위경도를 넣었을 때 BT가 올바른 거리를 계산해야 한다."""
import sys, os
sys.path.insert(0, "."); sys.path.insert(0, "src")
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
for k in ("TOPGUN_RULE","TOPGUN_ABLATE","TOPGUN_MATCH"): os.environ.pop(k, None)
from dogfight.ai.native_bt import AIPilot

ap = AIPilot("AIP_final.dll"); ap.CreateBehaviorTree(0, 1)
LAT, LON, ALT = 37.923556, 128.181881, 3000.0
DLAT = 610.0 / 111320.0          # 610m 북쪽 = 위도 약 0.00548도

for label, mine, tgt in (
    ("[A] Unreal 직교 그대로 (현재 서버 경로)", [0.0,0.0,ALT], [610.0,0.0,ALT]),
    ("[B] 위경도로 변환해서 넣기",              [LAT,LON,ALT], [LAT+DLAT,LON,ALT]),
):
    for _ in range(40):
        a = AIPilot.BuildPlaneData(mine, [0.0,0.0,0.0], 250.0, 1)
        b = AIPilot.BuildPlaneData(tgt,  [0.0,0.0,0.0], 250.0, 2)
        ap.StepWithPlaneData(a, b)
    vp = ap.GetVPWithPlaneData(a)
    print(f"{label}")
    print(f"    VP=({vp.X:,.1f}, {vp.Y:,.1f}, {vp.Z:,.1f})")
