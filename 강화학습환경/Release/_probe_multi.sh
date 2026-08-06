#!/bin/bash
# v34 실패의 핵심 질문: '감속+당김'이 onecircle 전용인가, 조건만 맞으면 범용인가?
# -> 우리가 이기고 있던 상대(v7, ACE)에서도 같은 탐색을 한다.
#    onecircle에서만 이기면 그 조건은 그 상대용이고(과적합), 어디서나 이기면
#    트리거에 위협 조건을 더해 살릴 수 있다.
# ※ 도는 동안 시뮬/설정/도구를 수정하지 않는다.
cd "$(dirname "$0")"
PY="/c/Users/TFX5470H/anaconda3/envs/aip/python.exe"
trap 'cp -f AIP_v32.dll AIP_DCS_ownship.dll' EXIT
cp -f AIP_v32.dll AIP_DCS_ownship.dll     # 기준은 현역 v32
for OPP in AIP_v7.dll ACE; do
  for S in 3 6 9; do
    for T in 60 120; do
      echo "@@@@@ ${OPP} seed=$S t=$T"
      "$PY" tools_diag/vp_probe.py "$OPP" $S $T 5 2>&1 \
        | grep -aE "^(BT\(기준\)|우선회|좌선회|우하강|좌하강|수직당김|이탈|감속)|순이득|\[창시작\]"
      echo ""
    done
  done
done
echo "=== 완료 ==="
