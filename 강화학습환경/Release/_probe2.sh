#!/bin/bash
# 2순위 재측정 — 오염된 1차 스윕을 대회 규칙(3단계 phase)으로 일관되게 다시 잰다.
# ※ 이 배치가 도는 동안 시뮬/설정/도구를 절대 수정하지 않는다(1차 오염 원인).
cd "$(dirname "$0")"
PY="/c/Users/TFX5470H/anaconda3/envs/aip/python.exe"
cp -f AIP_v32.dll AIP_DCS_ownship.dll
for S in 3 6 9 12; do
  for T in 60 120; do
    echo "@@@@@ seed=$S t=$T"
    "$PY" tools_diag/vp_probe.py AIP_onecircle.dll $S $T 5 2>&1 \
      | grep -aE "^(BT\(기준\)|우선회|좌선회|우하강|좌하강|수직당김|이탈|감속)|순위|\[창시작\]"
    echo ""
  done
done
echo "=== 완료 ==="
