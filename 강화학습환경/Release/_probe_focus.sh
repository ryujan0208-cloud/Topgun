#!/bin/bash
# '감속+당김'이 언제 통하는가 = 트리거 조건 탐색.
# 기준(BT) 대비로 구간을 많이 본다. 창시작 기하가 함께 기록된다.
cd "$(dirname "$0")"
PY="/c/Users/TFX5470H/anaconda3/envs/aip/python.exe"
export PROBE_FOCUS=1
cp -f AIP_v32.dll AIP_DCS_ownship.dll
for S in 3 6 9 12; do
  for T in 40 70 100 130 160; do
    echo "@@@@@ seed=$S t=$T"
    "$PY" tools_diag/vp_probe.py AIP_onecircle.dll $S $T 5 2>&1 \
      | grep -aE "^(BT\(기준\)|감속)|\[창시작\]"
  done
done
echo "=== 완료 ==="
