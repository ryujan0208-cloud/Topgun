#!/bin/bash
# vp_probe 재현성 확인: 여러 시드 x 여러 구간에서 '수직 기동이 교착을 깬다'가 유지되는가?
# 한 시드 결과로 일반화하지 않는다(오늘 2번 당한 오류).
cd "$(dirname "$0")"
PY="/c/Users/TFX5470H/anaconda3/envs/aip/python.exe"
cp -f AIP_v32.dll AIP_DCS_ownship.dll
for S in 3 6 9 12; do
  for T in 60 120; do
    echo "@@@@@ seed=$S t=$T"
    "$PY" tools_diag/vp_probe.py AIP_onecircle.dll $S $T 5 2>&1 \
      | grep -aE "^(BT\(기준\)|우선회|좌선회|우하강|좌하강|수직당김|이탈|감속)|순위"
    echo ""
  done
done
echo "=== 완료 ==="
